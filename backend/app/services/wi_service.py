import logging
import httpx
from typing import List, Dict, Any
import re
from app.utils.pdf_utils import extract_text_from_pdf
from app.utils.wi_patterns import form_patterns
from app.utils.tps_parser import TPSParser
import json
import inspect

# Create logger for this module
logger = logging.getLogger(__name__)

LOGIQS_GRID_URL = "https://tps.logiqs.com/API/Document/gridBind?caseid={case_id}&type=grid"
LOGIQS_DOWNLOAD_URL = "https://tps.logiqs.com/API/Document/DownloadFile?CaseDocumentID={case_doc_id}&caseId={case_id}"

NAME_REGEX = r"Name[:\s]+([A-Za-z ,.'-]+)"
SSN_REGEX = r"SSN[:\s]+(\d{3}-\d{2}-\d{4})"

# --- WI Service Layer ---

def fetch_wi_file_grid(case_id: str, cookies: dict) -> List[Dict[str, Any]]:
    """
    Fetch WI file grid for a given case from Logiqs.
    Returns a list of WI file metadata dicts.
    """
    logger.info(f"🔍 Starting WI file grid fetch for case_id: {case_id}")
    
    # Extract cookie string and user agent from cookies dict
    cookie_header = None
    user_agent = None
    if cookies:
        if isinstance(cookies, dict):
            # New format: { 'cookies': [...], 'user_agent': ... }
            if 'cookies' in cookies:
                cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies['cookies']])
                logger.info(f"🍪 Extracted cookie header with {len(cookies['cookies'])} cookies")
            if 'user_agent' in cookies:
                user_agent = cookies['user_agent']
                logger.info(f"🌐 Using custom user agent: {user_agent[:50]}...")
        elif isinstance(cookies, str):
            cookie_header = cookies
            logger.info("🍪 Using string cookie format")
    
    if not cookie_header:
        logger.error("❌ No valid cookies found for authentication")
        raise Exception("No valid cookies found for authentication.")
    
    if not user_agent:
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        logger.info("🌐 Using default user agent")

    url = LOGIQS_GRID_URL.format(case_id=case_id)
    logger.info(f"🌐 Making API request to: {url}")
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": user_agent,
        "Cookie": cookie_header
    }

    try:
        logger.info("📡 Sending POST request to Logiqs API...")
        response = httpx.post(
            url,
            headers=headers,
            timeout=30,
            follow_redirects=False
        )
        
        logger.info(f"📊 Response status: {response.status_code}")
        logger.info(f"📊 Response headers: {dict(response.headers)}")
        
        if response.status_code == 302:
            location = response.headers.get("Location", "").lower()
            logger.warning(f"⚠️ Received 302 redirect to: {location}")
            if "login" in location or "default.aspx" in location:
                logger.error("❌ Redirected to login page - authentication failed")
                raise Exception("Authentication required. Please ensure cookies are valid.")
        
        response.raise_for_status()
        
        logger.info("📄 Parsing JSON response...")
        response_data = response.json()
        
        if not isinstance(response_data, dict) or "Result" not in response_data:
            logger.error(f"❌ Invalid response structure: {type(response_data)}")
            logger.error(f"📋 Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Not a dict'}")
            raise Exception("Invalid response structure from API")
        
        docs = response_data["Result"]
        logger.info(f"📋 Found {len(docs) if isinstance(docs, list) else 'non-list'} documents in response")
        
        if not isinstance(docs, list):
            logger.error(f"❌ Invalid document list format: {type(docs)}")
            raise Exception("Invalid document list format")
        
        wi_files = []
        logger.info("🔍 Filtering for WI files...")
        
        for i, doc in enumerate(docs):
            if not isinstance(doc, dict):
                logger.warning(f"⚠️ Skipping non-dict document at index {i}: {type(doc)}")
                continue
            
            name = doc.get("Name", "")
            if not name:
                logger.warning(f"⚠️ Skipping document with no name at index {i}")
                continue
            
            logger.debug(f"🔍 Checking document: {name}")
            
            # Check for standalone WI in the filename (not part of another word)
            if re.search(r'\bWI\s+\d', name):
                case_doc_id = doc.get("CaseDocumentID")
                if case_doc_id:
                    wi_files.append({
                        "FileName": name,
                        "CaseDocumentID": case_doc_id
                    })
                    logger.info(f"✅ Found WI file: {name} (ID: {case_doc_id})")
                else:
                    logger.warning(f"⚠️ WI file {name} has no CaseDocumentID")
            else:
                logger.debug(f"⏭️ Skipping non-WI file: {name}")
        
        logger.info(f"✅ WI file grid fetch completed. Found {len(wi_files)} WI files")
        return wi_files
        
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error {e.response.status_code}: {e.response.text}")
        raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"❌ Request error: {str(e)}")
        raise Exception(f"Request error: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error fetching WI file grid: {str(e)}")
        raise Exception(f"Error fetching WI file grid: {str(e)}")

def download_wi_pdf(case_doc_id: str, case_id: str, cookies: dict) -> bytes:
    """
    Download a WI PDF file using its CaseDocumentID and case_id.
    Returns PDF bytes.
    """
    logger.info(f"📥 Downloading WI PDF - CaseDocumentID: {case_doc_id}, case_id: {case_id}")
    
    cookie_header = None
    user_agent = None
    if cookies:
        if isinstance(cookies, dict):
            if 'cookies' in cookies:
                cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies['cookies']])
            if 'user_agent' in cookies:
                user_agent = cookies['user_agent']
        elif isinstance(cookies, str):
            cookie_header = cookies
    
    if not cookie_header:
        logger.error("❌ No valid cookies found for PDF download")
        raise Exception("No valid cookies found for authentication.")
    
    if not user_agent:
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    url = LOGIQS_DOWNLOAD_URL.format(case_doc_id=case_doc_id, case_id=case_id)
    logger.info(f"🌐 Downloading from: {url}")
    
    headers = {
        "User-Agent": user_agent,
        "Cookie": cookie_header
    }
    
    try:
        logger.info("📡 Sending GET request for PDF...")
        response = httpx.get(
            url,
            headers=headers,
            timeout=30,
            follow_redirects=True
        )
        
        logger.info(f"📊 PDF download response status: {response.status_code}")
        logger.info(f"📊 PDF download response headers: {dict(response.headers)}")
        
        response.raise_for_status()
        
        content = response.content
        logger.info(f"✅ PDF downloaded successfully. Size: {len(content)} bytes")
        
        return content
        
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error downloading PDF {e.response.status_code}: {e.response.text}")
        raise Exception(f"HTTP error downloading PDF {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"❌ Request error downloading PDF: {str(e)}")
        raise Exception(f"Request error downloading PDF: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error downloading WI PDF: {str(e)}")
        raise Exception(f"Error downloading WI PDF: {str(e)}")

def calculate_summary(all_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Calculate summary statistics from parsed WI data.
    Returns summary with TP/SE/Non-SE breakdowns and Estimated AGI.
    """
    logger.info("📊 Calculating summary statistics...")
    
    summary = {
        'total_years': len(all_data),
        'years_analyzed': sorted(all_data.keys(), reverse=True),
        'total_forms': sum(len(forms) for forms in all_data.values()),
        'by_year': {}
    }
    
    for year in sorted(all_data.keys(), reverse=True):
        year_forms = all_data[year]
        
        # Calculate totals by category
        se_income = sum(form.get('Income', 0) for form in year_forms if form.get('Category') == 'SE' and form.get('Income') is not None)
        se_withholding = sum(form.get('Withholding', 0) for form in year_forms if form.get('Category') == 'SE' and form.get('Withholding') is not None)
        
        nonse_income = sum(form.get('Income', 0) for form in year_forms if form.get('Category') == 'Non-SE' and form.get('Income') is not None)
        nonse_withholding = sum(form.get('Withholding', 0) for form in year_forms if form.get('Category') == 'Non-SE' and form.get('Withholding') is not None)
        
        other_income = sum(form.get('Income', 0) for form in year_forms if form.get('Category') in ('Other', 'Neither') and form.get('Income') is not None)
        other_withholding = sum(form.get('Withholding', 0) for form in year_forms if form.get('Category') in ('Other', 'Neither') and form.get('Withholding') is not None)
        
        total_income = se_income + nonse_income + other_income
        total_withholding = se_withholding + nonse_withholding + other_withholding
        
        # Calculate Estimated AGI (Total Income - SE Tax Adjustment)
        estimated_agi = total_income - (se_income * 0.0765)  # 7.65% SE tax adjustment
        
        summary['by_year'][year] = {
            'number_of_forms': len(year_forms),
            'se_income': se_income,
            'se_withholding': se_withholding,
            'non_se_income': nonse_income,
            'non_se_withholding': nonse_withholding,
            'other_income': other_income,
            'other_withholding': other_withholding,
            'total_income': total_income,
            'total_withholding': total_withholding,
            'estimated_agi': round(estimated_agi, 2)
        }
    
    # Calculate overall totals
    total_se_income = sum(year_data['se_income'] for year_data in summary['by_year'].values())
    total_non_se_income = sum(year_data['non_se_income'] for year_data in summary['by_year'].values())
    total_other_income = sum(year_data['other_income'] for year_data in summary['by_year'].values())
    total_income = sum(year_data['total_income'] for year_data in summary['by_year'].values())
    
    summary['overall_totals'] = {
        'total_se_income': total_se_income,
        'total_non_se_income': total_non_se_income,
        'total_other_income': total_other_income,
        'total_income': total_income,
        'estimated_agi': round(total_income - (total_se_income * 0.0765), 2)
    }
    
    logger.info(f"✅ Summary calculated for {len(summary['by_year'])} years")
    return summary

def extract_enhanced_payer_blurb(form_text: str, form_name: str, unique_id: str = None) -> str:
    """
    Enhanced payer/employer extraction with multiple fallback strategies.
    """
    logger.debug(f"🔍 Extracting enhanced payer blurb for {form_name}")
    
    # Strategy 1: Look for EIN/FIN with payer name
    if form_name == 'W-2':
        # W-2 specific patterns
        patterns = [
            r'Employer[\s,]*:?\s*([A-Z0-9 &.,\-()\n]+?)(?=\n|Recipient|$)',
            r'Employer Identification Number \(EIN\):\s*([\d\-]+)[\s\n]*([A-Z0-9 &.,\-()\n]+?)(?=\n|Recipient|$)',
            r'([A-Z0-9 &.,\-()\n]+?)[\s\n]*Employer Identification Number \(EIN\):\s*([\d\-]+)'
        ]
    else:
        # 1099 forms specific patterns
        patterns = [
            r'Payer[\s,]*:?\s*([A-Z0-9 &.,\-()\n]+?)(?=\n|Recipient|$)',
            r"Payer's Federal Identification Number \(FIN\):\s*([\d\-]+)[\s\n]*([A-Z0-9 &.,\-()\n]+?)(?=\n|Recipient|$)",
            r'([A-Z0-9 &.,\-()\n]+?)[\s\n]*Payer[\s,]*:?\s*([A-Z0-9 &.,\-()\n]+?)(?=\n|Recipient|$)'
        ]
    
    for pattern in patterns:
        match = re.search(pattern, form_text, re.IGNORECASE | re.MULTILINE)
        if match:
            parts = []
            
            # Add EIN/FIN if we have it
            if unique_id:
                if form_name == 'W-2':
                    parts.append(f"Employer Identification Number (EIN):{unique_id}")
                else:
                    parts.append(f"Payer's Federal Identification Number (FIN):{unique_id}")
            
            # Add the matched text
            for group in match.groups():
                if group and group.strip():
                    parts.append(group.strip())
            
            if parts:
                result = '\n'.join(parts)
                logger.debug(f"✅ Extracted payer blurb: {result[:100]}...")
                return result
    
    # Strategy 2: Fallback to line-by-line extraction
    lines = form_text.split('\n')
    if form_name == 'W-2':
        # Try to grab lines after 'Employer:' up to 3 lines
        for i, line in enumerate(lines):
            if 'Employer:' in line:
                blurb_lines = [line.strip()]
                for j in range(i + 1, min(i + 4, len(lines))):
                    next_line = lines[j].strip()
                    if not next_line or next_line.startswith('Recipient:'):
                        break
                    blurb_lines.append(next_line)
                result = '\n'.join(blurb_lines).strip()
                if result:
                    logger.debug(f"✅ Extracted W-2 employer blurb (fallback): {result[:100]}...")
                    return result
    elif form_name.startswith('1099'):
        # Try to grab lines after 'Payer:' up to 3 lines
        for i, line in enumerate(lines):
            if 'Payer:' in line:
                blurb_lines = [line.strip()]
                for j in range(i + 1, min(i + 4, len(lines))):
                    next_line = lines[j].strip()
                    if not next_line or next_line.startswith('Recipient:'):
                        break
                    blurb_lines.append(next_line)
                result = '\n'.join(blurb_lines).strip()
                if result:
                    logger.debug(f"✅ Extracted 1099 payer blurb (fallback): {result[:100]}...")
                    return result
    
    # Strategy 3: Look for any EIN/FIN pattern and extract surrounding text
    if form_name == 'W-2':
        ein_pattern = r'Employer Identification Number \(EIN\):\s*([\d\-]+)'
    else:
        ein_pattern = r"Payer's Federal Identification Number \(FIN\):\s*([\d\-]+)"
    
    ein_match = re.search(ein_pattern, form_text, re.IGNORECASE)
    if ein_match:
        # Get the line with EIN/FIN and a few lines before/after
        lines = form_text.split('\n')
        for i, line in enumerate(lines):
            if ein_match.group(0) in line:
                start = max(0, i - 1)
                end = min(len(lines), i + 2)
                result_lines = []
                for j in range(start, end):
                    if lines[j].strip():
                        result_lines.append(lines[j].strip())
                result = '\n'.join(result_lines)
                if result:
                    logger.debug(f"✅ Extracted blurb from EIN/FIN context: {result[:100]}...")
                    return result
    
    logger.debug(f"⚠️ Could not extract payer blurb for {form_name}")
    return None

def parse_form_block(block_text, form_type, file_name, tracking_number, tax_year):
    """
    Parse a single form block using only the regexes for the detected form_type.
    Returns a structured dict as specified.
    Adds deep debug prints for each field regex and block text sample.
    Uses case-insensitive matching for better field extraction.
    """
    print(f"\n[DEEP DEBUG] === Parsing block for form_type: {form_type} in file: {file_name} ===")
    print(f"[DEEP DEBUG] Full block text:\n{block_text}\n---END BLOCK---\n")
    pattern_info = form_patterns.get(form_type)
    if not pattern_info:
        print(f"[DEEP DEBUG] No pattern_info for form_type: {form_type}")
        return None
    
    fields = []
    field_patterns = pattern_info.get('fields', {})
    
    for field_key, regex in field_patterns.items():
        if not regex:
            continue
        print(f"[DEEP DEBUG] Trying field '{field_key}' with regex: {regex}")
        try:
            match = re.search(regex, block_text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1) if match.group(1) else match.group(2) if len(match.groups()) > 1 else match.group(0)
                source_line = match.group(0)
                print(f"[DEEP DEBUG]  e Matched '{field_key}': {value} from '{source_line}'")
                fields.append({
                    'name': field_key,
                    'value': value,
                    'source_line': source_line
                })
            else:
                print(f"[DEEP DEBUG]  c No match for field '{field_key}' in form_type '{form_type}'.")
                # Try line-by-line matching as fallback
                lines = block_text.split('\n')
                for line in lines:
                    line_match = re.search(regex, line, re.IGNORECASE)
                    if line_match:
                        value = line_match.group(1) if line_match.group(1) else line_match.group(2) if len(line_match.groups()) > 1 else line_match.group(0)
                        source_line = line_match.group(0)
                        print(f"[DEEP DEBUG]  e Line match for '{field_key}': {value} from '{source_line}'")
                        fields.append({
                            'name': field_key,
                            'value': value,
                            'source_line': source_line
                        })
                        break
        except Exception as e:
            print(f"[DEEP DEBUG] Error matching field '{field_key}': {e}")
    # --- Convert fields to dict for calculation and EntityName extraction ---
    fields_data = {}
    for field in fields:
        field_name = field.get('name', '').replace('_', ' ').title()
        field_value = field.get('value', '')
        try:
            fields_data[field_name] = float(field_value.replace(',', ''))
        except Exception:
            fields_data[field_name] = field_value
    # --- EntityName extraction ---
    pattern_identifiers = pattern_info.get('identifiers', {})
    NAME_RGX = re.compile(r"(name|payer|employer|lender|trustee)$", re.I)
    entity = ""
    # 1. Try identifiers: apply regex to block_text, use first match group
    for k, rgx in pattern_identifiers.items():
        if NAME_RGX.search(k):
            try:
                m = re.search(rgx, block_text)
                if m and m.group(1) and m.group(1).strip():
                    entity = m.group(1).strip()
                    break
            except Exception:
                continue
    # 2. If not found, try fields: use value directly if key matches
    if not entity:
        for k, v in fields_data.items():
            if NAME_RGX.search(k) and isinstance(v, str) and v.strip():
                entity = v.strip()
                break
    # 3. Fallback: first all-caps 3+ char run
    if not entity:
        m = re.search(r"[A-Z][A-Z0-9 &.,'-]{2,120}", block_text)
        entity = m.group(0).strip() if m else ""
    # 4. Remove duplicate from Fields
    for k in list(fields_data.keys()):
        if fields_data[k] == entity:
            del fields_data[k]
    if not fields:
        print(f"[DEEP DEBUG] No fields matched for form_type '{form_type}' in file: {file_name}")
        return None
    print(f"[DEEP DEBUG] Final parsed fields for form_type '{form_type}': {fields}\n")
    return {
        'Form': form_type,
        'UniqueID': tracking_number or 'UNKNOWN',
        'EntityName': entity,
        'Label': 'E' if form_type == 'W-2' else 'P',
        'Income': 0.0,  # Will be set later
        'Withholding': 0.0,  # Will be set later
        'Category': pattern_info.get('category', 'Other'),
        'Fields': fields_data,
        'Owner': 'TP',
        'SourceFile': file_name,
        'Year': tax_year
    }

# NOTE: This function is the main consumer of form_patterns for WI parsing.
# All endpoints that use parse_wi_pdfs (and thus parse_transcript_scoped) will be affected by changes here.
# Do NOT apply regexes globally—scope them to each form block as described.
def parse_transcript_scoped(text, file_name):
    """
    Parse a WI transcript with form-block-scoped regex extraction.
    Returns a list of structured form results.
    Logs skipped blocks or unmatched forms for QA.
    """
    logger = logging.getLogger(__name__)
    tracking_number_match = re.search(r"\b(\d{11,})\b", text[:500])
    tracking_number = tracking_number_match.group(1) if tracking_number_match else None
    tax_year_match = re.search(r"(20\d{2}|\d{2})", file_name)
    tax_year = None
    if tax_year_match:
        y = tax_year_match.group(1)
        tax_year = f"20{y}" if len(y) == 2 else y

    # Dynamically build form type pattern from wi_patterns.py keys
    form_types = [
        r'W-2G', r'W-2', r'SSA-1099', r'1042-S', r'1098(?:-[A-Z]+)?', r'1099-(?:[A-Z]+)', r'5498(?:-[A-Z]+)?', r'3922',
        r'Schedule\s+K-1\s+\(Form\s+(?:1065|1041|1120S)\)'
    ]
    # Add any additional form types from form_patterns if not already present
    import re as _re
    for k in form_patterns.keys():
        if not any(_re.fullmatch(ft.replace('(?:', '(').replace(')?', ')').replace('[A-Z]+', ''), k) for ft in form_types):
            form_types.append(_re.escape(k))
    form_type_pattern = '|'.join(form_types)
    # Build the segmentation regex
    form_block_pattern = re.compile(
        rf'(Form\s+({form_type_pattern}).*?)(?=Form\s+({form_type_pattern})|This Product Contains|\Z)',
        re.DOTALL | re.IGNORECASE
    )
    results = []
    skipped_blocks = 0
    for match in form_block_pattern.finditer(text):
        block_text = match.group(1)
        # Loosen form type extraction: match 'Form W-2', 'Form 1099-G', etc., possibly with extra text after
        form_type_match = re.search(r"Form\s+([A-Z0-9\-]+)", block_text, re.IGNORECASE)
        form_type = form_type_match.group(1) if form_type_match else None
        print(f"[DEBUG] Extracted form_type: {form_type}")
        print(f"[DEBUG] Block snippet: {block_text[:120].replace('\n', ' ')}")
        if not form_type or form_type not in form_patterns:
            logger.info(f"[WI Parser QA] Skipped block: Could not determine form type or not in form_patterns. Block snippet: {block_text[:80]}")
            print(f"[DEBUG] form_type not in form_patterns. Available keys: {list(form_patterns.keys())}")
            skipped_blocks += 1
            continue
        parsed = parse_form_block(block_text, form_type, file_name, tracking_number, tax_year)
        if parsed:
            results.append(parsed)
        else:
            logger.info(f"[WI Parser QA] Skipped block: No fields matched for form {form_type} in file {file_name}.")
            print(f"[DEBUG] No fields matched for form_type: {form_type}")
            skipped_blocks += 1
    logger.info(f"[WI Parser QA] Total skipped blocks: {skipped_blocks} for file {file_name}.")
    return results

def parse_wi_pdfs(
    wi_files: List[Dict[str, Any]],
    cookies: dict,
    case_id: str,
    include_tps_analysis: bool = False,
    filing_status: str = None,
    return_scoped_structure: bool = False
) -> Dict[str, Any]:
    """
    Download and parse all WI PDFs for the case, returning enhanced WI summary JSON with summary at top.
    Optionally includes TP/S analysis if include_tps_analysis=True.
    If return_scoped_structure=True, returns the new scoped parsing structure per file.
    """
    logger.info(f"🔍 Starting PDF parsing for {len(wi_files)} WI files")
    if include_tps_analysis:
        logger.info(f"🔍 TP/S analysis enabled with filing status: {filing_status}")

    all_data = {}
    scoped_results = []

    for i, wi_file in enumerate(wi_files):
        file_name = wi_file["FileName"]
        case_doc_id = wi_file["CaseDocumentID"]

        logger.info(f"📄 Processing WI file {i+1}/{len(wi_files)}: {file_name}")

        # Extract owner from filename for TP/S analysis
        owner = TPSParser.extract_owner_from_filename(file_name)
        logger.info(f"👤 Extracted owner from filename '{file_name}': {owner}")

        try:
            # Download PDF
            logger.info(f"📥 Downloading PDF for {file_name}...")
            pdf_bytes = download_wi_pdf(case_doc_id, case_id, cookies)

            if not pdf_bytes:
                logger.warning(f"⚠️ No PDF content received for {file_name}")
                continue

            # Extract text
            logger.info(f"📝 Extracting text from {file_name}...")
            text = extract_text_from_pdf(pdf_bytes)

            if not text:
                logger.warning(f"⚠️ No text extracted from {file_name}")
                continue

            logger.info(f"📝 Extracted {len(text)} characters from {file_name}")

            # Use new scoped parser
            scoped_result = parse_transcript_scoped(text, file_name)
            scoped_results.append(scoped_result)

        except Exception as e:
            logger.error(f"❌ Error processing {file_name}: {str(e)}")
            logger.error(f"🔍 Error type: {type(e).__name__}")
            import traceback
            logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
            continue

    # If requested, return the new scoped structure directly
    if return_scoped_structure:
        logger.info("✅ Returning new scoped parsing structure for all files")
        # Flatten the list of lists
        flat_results = [item for sublist in scoped_results for item in sublist]
        logger.info(f"[DEBUG] flat_results: {json.dumps(flat_results, indent=2, default=str)[:1000]}")
        return {'forms': flat_results}

    # Otherwise, build years_data and summary from the parsed results
    logger.info(f"[DEBUG] scoped_results: {json.dumps(scoped_results, indent=2, default=str)[:1000]}")
    years_data = {}
    all_forms = []
    for file_result in scoped_results:
        for form in file_result:
            year = form.get('Year') or form.get('tax_year') or 'Unknown'
            if year not in years_data:
                years_data[year] = []
            # --- Adaptive calculation for Income/Withholding ---
            cat = form.get('Category', 'Other')
            fields = form.get('Fields', {})
            # Get pattern info for this form
            pattern_info = form_patterns.get(form.get('Form', ''), {})
            calc = pattern_info.get('calculation', {})
            # Ensure safe defaults for SSA-1099 etc
            filing_status = form.get('filing_status', 'Single')
            combined_income = form.get('combined_income', 0.0)
            # Income
            income = 0.0
            try:
                if 'Income' in calc and callable(calc['Income']):
                    income = safe_call(calc['Income'], fields, filing_status, combined_income)
            except Exception as e:
                logger.exception(f"⚠️ Error calculating income for {form.get('Form', '')}: {e}")
            # Withholding
            withholding = 0.0
            try:
                if 'Withholding' in calc and callable(calc['Withholding']):
                    withholding = safe_call(calc['Withholding'], fields, filing_status, combined_income)
            except Exception as e:
                logger.exception(f"⚠️ Error calculating withholding for {form.get('Form', '')}: {e}")
            form['Income'] = income
            form['Withholding'] = withholding
            years_data[year].append(form)
            all_forms.append((year, cat, income, withholding))
    # --- Build summary using calculated values ---
    summary = {
        'total_years': len(years_data),
        'years_analyzed': list(years_data.keys()),
        'total_forms': sum(len(forms) for forms in years_data.values()),
        'by_year': {},
        'overall_totals': {
            'total_se_income': 0.0,
            'total_non_se_income': 0.0,
            'total_other_income': 0.0,
            'total_income': 0.0,
            'estimated_agi': 0.0
        }
    }
    for year, forms in years_data.items():
        se_income = 0.0
        se_withholding = 0.0
        non_se_income = 0.0
        non_se_withholding = 0.0
        other_income = 0.0
        other_withholding = 0.0
        for form in forms:
            cat = form.get('Category', 'Other')
            inc = form.get('Income', 0.0)
            wh = form.get('Withholding', 0.0)
            if cat == 'SE':
                se_income += inc
                se_withholding += wh
            elif cat == 'Non-SE':
                non_se_income += inc
                non_se_withholding += wh
            else:
                other_income += inc
                other_withholding += wh
        total_income = se_income + non_se_income + other_income
        total_withholding = se_withholding + non_se_withholding + other_withholding
        summary['by_year'][year] = {
            'number_of_forms': len(forms),
            'se_income': se_income,
            'se_withholding': se_withholding,
            'non_se_income': non_se_income,
            'non_se_withholding': non_se_withholding,
            'other_income': other_income,
            'other_withholding': other_withholding,
            'total_income': total_income,
            'total_withholding': total_withholding,
            'estimated_agi': total_income
        }
        summary['overall_totals']['total_se_income'] += se_income
        summary['overall_totals']['total_non_se_income'] += non_se_income
        summary['overall_totals']['total_other_income'] += other_income
        summary['overall_totals']['total_income'] += total_income
        summary['overall_totals']['estimated_agi'] += total_income
    logger.info(f"[DEBUG] years_data: {json.dumps(years_data, indent=2, default=str)[:1000]}")
    logger.info(f"[DEBUG] final_output: {{'summary': {json.dumps(summary, indent=2, default=str)[:1000]}, 'years_data': ...}}")
    final_output = {'summary': summary, 'years_data': years_data}
    return final_output

def fetch_ti_file_grid(case_id: str, cookies: dict) -> list:
    """
    Fetch TI file grid for a given case from Logiqs.
    Returns a list of TI file metadata dicts, including FileName, CaseDocumentID, and FileComment.
    Only includes files where 'TI' is a standalone word in the filename.
    """
    logger.info(f"🔍 Starting TI file grid fetch for case_id: {case_id}")
    # Extract cookie string and user agent from cookies dict
    cookie_header = None
    user_agent = None
    if cookies:
        if isinstance(cookies, dict):
            if 'cookies' in cookies:
                cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies['cookies']])
            if 'user_agent' in cookies:
                user_agent = cookies['user_agent']
        elif isinstance(cookies, str):
            cookie_header = cookies
    if not cookie_header:
        logger.error("❌ No valid cookies found for authentication")
        raise Exception("No valid cookies found for authentication.")
    if not user_agent:
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    url = f"https://tps.logiqs.com/API/Document/gridBind?caseid={case_id}&type=grid"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": user_agent,
        "Cookie": cookie_header
    }
    try:
        logger.info("📡 Sending POST request to Logiqs API for TI files...")
        response = httpx.post(
            url,
            headers=headers,
            timeout=30,
            follow_redirects=False
        )
        response.raise_for_status()
        response_data = response.json()
        if not isinstance(response_data, dict) or "Result" not in response_data:
            logger.error(f"❌ Invalid response structure: {type(response_data)}")
            raise Exception("Invalid response structure from API")
        docs = response_data["Result"]
        logger.info(f"📋 Found {len(docs) if isinstance(docs, list) else 'non-list'} documents in response")
        if not isinstance(docs, list):
            logger.error(f"❌ Invalid document list format: {type(docs)}")
            raise Exception("Invalid document list format")
        ti_files = []
        logger.info("🔍 Filtering for standalone TI files...")
        for i, doc in enumerate(docs):
            if not isinstance(doc, dict):
                continue
            name = doc.get("Name", "")
            if not name:
                continue
            # Only match standalone 'TI' (not part of another word)
            if re.search(r'\bTI\b', name.upper()):
                case_doc_id = doc.get("CaseDocumentID")
                file_comment = doc.get("FileComment", "")
                if case_doc_id:
                    ti_files.append({
                        "FileName": name,
                        "CaseDocumentID": case_doc_id,
                        "FileComment": file_comment
                    })
        logger.info(f"✅ TI file grid fetch completed. Found {len(ti_files)} TI files")
        return ti_files
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error {e.response.status_code}: {e.response.text}")
        raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"❌ Request error: {str(e)}")
        raise Exception(f"Request error: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error fetching TI file grid: {str(e)}")
        raise Exception(f"Error fetching TI file grid: {str(e)}")

def download_ti_pdf(case_doc_id: str, case_id: str, cookies: dict) -> bytes:
    """
    Download a specific TI PDF file by its CaseDocumentID and case_id.
    Returns the PDF file as bytes.
    """
    logger.info(f"📥 Downloading TI PDF for case_id: {case_id}, case_doc_id: {case_doc_id}")
    cookie_header = None
    user_agent = None
    if cookies:
        if isinstance(cookies, dict):
            if 'cookies' in cookies:
                cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies['cookies']])
            if 'user_agent' in cookies:
                user_agent = cookies['user_agent']
        elif isinstance(cookies, str):
            cookie_header = cookies
    if not cookie_header:
        logger.error("❌ No valid cookies found for authentication")
        raise Exception("No valid cookies found for authentication.")
    if not user_agent:
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    url = f"https://tps.logiqs.com/API/Document/DownloadFile?CaseDocumentID={case_doc_id}&caseId={case_id}"
    headers = {
        "User-Agent": user_agent,
        "Cookie": cookie_header
    }
    try:
        logger.info(f"📡 Sending GET request to download TI PDF: {url}")
        response = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
        
        logger.info(f"📊 TI PDF download response status: {response.status_code}")
        logger.info(f"📊 TI PDF download response headers: {dict(response.headers)}")
        
        response.raise_for_status()
        
        content = response.content
        logger.info(f"✅ Successfully downloaded TI PDF. Size: {len(content)} bytes")
        return content
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error {e.response.status_code}: {e.response.text}")
        raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"❌ Request error: {str(e)}")
        raise Exception(f"Request error: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error downloading TI PDF: {str(e)}")
        raise Exception(f"Error downloading TI PDF: {str(e)}")

def parse_ti_pdfs(ti_files: list, cookies: dict, case_id: str) -> dict:
    """
    Download and parse all TI PDFs for the case, returning extracted text for each file.
    Returns a dict with file metadata and extracted text.
    """
    logger.info(f"🔍 Starting TI PDF parsing for {len(ti_files)} TI files")
    all_data = {}
    for i, ti_file in enumerate(ti_files):
        file_name = ti_file["FileName"]
        case_doc_id = ti_file["CaseDocumentID"]
        logger.info(f"📄 Processing TI file {i+1}/{len(ti_files)}: {file_name}")
        try:
            # Download PDF
            logger.info(f"📥 Downloading PDF for {file_name}...")
            pdf_bytes = download_ti_pdf(case_doc_id, case_id, cookies)
            if not pdf_bytes:
                logger.warning(f"⚠️ No PDF content received for {file_name}")
                continue
            # Extract text
            logger.info(f"📝 Extracting text from {file_name}...")
            text = extract_text_from_pdf(pdf_bytes)
            if not text:
                logger.warning(f"⚠️ No text extracted from {file_name}")
                continue
            logger.info(f"📝 Extracted {len(text)} characters from {file_name}")
            all_data[file_name] = {
                "CaseDocumentID": case_doc_id,
                "Text": text
            }
        except Exception as e:
            logger.error(f"❌ Error processing {file_name}: {str(e)}")
            continue
    logger.info(f"✅ TI PDF parsing completed. Total files: {len(all_data)}")
    return all_data

def extract_form_blocks(text):
    """
    Extract form blocks with support for ALL form types in wi_patterns.
    """
    # More flexible form type patterns that match real transcript data
    form_types = [
        r'W-2(?:\s+Wage\s+and\s+Tax\s+Statement)?',  # Matches "Form W-2 Wage and Tax Statement"
        r'W-2G',
        r'SSA-1099',
        r'1042-S',
        r'1098(?:-[ETS])?',
        r'1099-(?:MISC|NEC|K|PATR|R|B|DIV|INT|G|S|LTC|OID|C|Q|SA)',
        r'3922',
        r'5498(?:-SA)?',
        r'Schedule\s+K-1\s+\(Form\s+(?:1065|1041|1120S)\)'
    ]
    
    # Build a more flexible pattern that matches the actual transcript format
    # The key insight: real transcripts have "Form W-2 Wage and Tax Statement" on one line
    # followed by form content, then another form or end of file
    blocks = []
    
    # Split text into lines for better processing
    lines = text.split('\n')
    current_block = None
    current_content = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts a new form
        form_started = False
        for form_type in form_types:
            # Look for "Form" followed by the form type
            pattern = rf"^Form\s+{form_type}"
            if re.search(pattern, line, re.IGNORECASE):
                # Save previous block if exists
                if current_block:
                    current_block['content'] = '\n'.join(current_content).strip()
                    blocks.append(current_block)
                
                # Start new block
                raw_form_type = re.search(rf"Form\s+({form_type})", line, re.IGNORECASE)
                if raw_form_type:
                    form_type_name = raw_form_type.group(1)
                    # Clean up form type name
                    if re.match(r'W-2(?:\s|$)', form_type_name, re.IGNORECASE):
                        clean_form_type = 'W-2'
                    elif re.match(r'Schedule\s+K-1.*1065', form_type_name, re.IGNORECASE):
                        clean_form_type = 'K-1 (Form 1065)'
                    elif re.match(r'Schedule\s+K-1.*1041', form_type_name, re.IGNORECASE):
                        clean_form_type = 'K-1 (Form 1041)'
                    elif re.match(r'Schedule\s+K-1.*1120S', form_type_name, re.IGNORECASE):
                        clean_form_type = 'K-1 1120S'
                    else:
                        clean_form_type = form_type_name.upper()
                else:
                    clean_form_type = line
                
                current_block = {
                    'form_type': clean_form_type,
                    'original_header': line,
                    'content': '',
                    'position': {'start': i, 'end': i}
                }
                current_content = []
                form_started = True
                break
        
        # If we didn't start a new form, add line to current content
        if not form_started and current_block:
            current_content.append(line)
    
    # Don't forget the last block
    if current_block:
        current_block['content'] = '\n'.join(current_content).strip()
        blocks.append(current_block)
    
    return blocks

def extract_file_metadata(text):
    """Extract file-level metadata"""
    tracking_number = re.search(r"Tracking Number:\s*(\d+)", text)
    tax_year = re.search(r"(?:Tax Period Requested|Form Year).*?(\d{4})", text)
    return {
        'tracking_number': tracking_number.group(1) if tracking_number else None,
        'tax_year': tax_year.group(1) if tax_year else None
    }

def calculate_field_confidence(match, expected_patterns=None):
    """Calculate confidence based on regex match characteristics"""
    if not match:
        return 0.0
    confidence = 0.7  # Base confidence for any match
    # Boost confidence for clean matches
    if re.match(r'^\d+\.?\d*$', match.strip('$,')):
        confidence += 0.2
    # Reduce confidence for suspicious patterns
    if len(match) > 20:  # Very long matches are suspicious
        confidence -= 0.1
    return min(1.0, max(0.0, confidence))

def safe_call(fn, *args):
    sig = inspect.signature(fn)
    n = len(sig.parameters)
    return fn(*args[:n])

# Add a unit test at the bottom or in your test suite
if __name__ == "__main__":
    # Quick unit test for 1099-INT income calculation
    test_fields = {'Interest': 1000, 'Interest Forfeiture': 200, 'Federal Withholding': 0}
    calc = form_patterns['1099-INT']['calculation']
    income = safe_call(calc['Income'], test_fields)
    assert income == 800, f"Expected 800, got {income}"
    print("✅ 1099-INT income calculation test passed.")

    # Unit test for a two-argument lambda
    def dummy_two_arg(fields, extra):
        return float(fields.get('A', 0)) + float(extra)
    test_fields2 = {'A': 5}
    result2 = safe_call(dummy_two_arg, test_fields2, 7)
    assert result2 == 12, f"Expected 12, got {result2}"
    print("✅ safe_call handles two-argument lambda test passed.")
