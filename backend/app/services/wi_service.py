import logging
import httpx
from typing import List, Dict, Any
import re
from app.utils.pdf_utils import extract_text_from_pdf
from app.utils.wi_patterns import form_patterns
from app.utils.tps_parser import TPSParser

# Create logger for this module
logger = logging.getLogger(__name__)

LOGIQS_GRID_URL = "https://tps.logiqs.com/API/Document/gridBind?caseid={case_id}&type=grid"
LOGIQS_DOWNLOAD_URL = "https://tps.logiqs.com/API/Document/DownloadFile?CaseDocumentID={case_doc_id}&caseId={case_id}"

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
        
        other_income = sum(form.get('Income', 0) for form in year_forms if form.get('Category') == 'Neither' and form.get('Income') is not None)
        other_withholding = sum(form.get('Withholding', 0) for form in year_forms if form.get('Category') == 'Neither' and form.get('Withholding') is not None)
        
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

def parse_wi_pdfs(wi_files: List[Dict[str, Any]], cookies: dict, case_id: str, include_tps_analysis: bool = False, filing_status: str = None) -> Dict[str, Any]:
    """
    Download and parse all WI PDFs for the case, returning enhanced WI summary JSON with summary at top.
    Optionally includes TP/S analysis if include_tps_analysis=True.
    """
    logger.info(f"🔍 Starting PDF parsing for {len(wi_files)} WI files")
    if include_tps_analysis:
        logger.info(f"🔍 TP/S analysis enabled with filing status: {filing_status}")
    
    all_data = {}
    
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
            
            # Extract tax year from filename (e.g., "WI 19.pdf" -> "2019")
            year_match = re.search(r'WI\s+(\d{2})', file_name)
            if year_match:
                year_suffix = year_match.group(1)
                # Convert 2-digit year to 4-digit (assuming 20xx for recent years)
                if int(year_suffix) <= 50:  # 00-50 -> 2000-2050
                    tax_year = f"20{year_suffix}"
                else:  # 51-99 -> 1951-1999
                    tax_year = f"19{year_suffix}"
                logger.info(f"📅 Extracted tax year from filename: {tax_year}")
            else:
                # Fallback: try to find 4-digit year in filename or text
                year_match = re.search(r"(20\d{2})", file_name)
                if year_match:
                    tax_year = year_match.group(1)
                else:
                    year_match = re.search(r"(20\d{2})", text)
                    tax_year = year_match.group(1) if year_match else "Unknown"
                logger.info(f"📅 Determined tax year (fallback): {tax_year}")
            
            # Parse forms using form_patterns
            logger.info(f"🔍 Parsing forms in {file_name}...")
            forms_found = 0
            
            for form_name, pattern_info in form_patterns.items():
                logger.debug(f"🔍 Checking for form: {form_name}")
                matches = list(re.finditer(pattern_info['pattern'], text, re.MULTILINE | re.IGNORECASE))
                
                if matches:
                    logger.info(f"✅ Found {len(matches)} matches for form: {form_name}")
                    forms_found += len(matches)
                
                for match in matches:
                    start = match.start()
                    # Find the end of this form by looking for the next form or end of text
                    end = len(text)
                    for next_match in matches[matches.index(match) + 1:]:
                        if next_match.start() > start:
                            end = next_match.start()
                            break
                    
                    form_text = text[start:end]
                    logger.debug(f"📄 Form text length: {len(form_text)} characters")
                    
                    # Extract fields with enhanced error handling
                    fields_data = {}
                    for field_name, regex in pattern_info['fields'].items():
                        if regex:
                            field_match = re.search(regex, form_text, re.IGNORECASE)
                            if field_match:
                                try:
                                    value_str = field_match.group(1).replace(',', '')
                                    # Handle numeric vs string values
                                    if field_name in ['Direct Sales Indicator', 'FATCA Filing Requirement', 'Second Notice Indicator']:
                                        fields_data[field_name] = value_str
                                    else:
                                        value = float(value_str)
                                        fields_data[field_name] = value
                                except (ValueError, AttributeError) as e:
                                    logger.warning(f"⚠️ Could not parse field {field_name}: {e}")
                                    fields_data[field_name] = 0
                    
                    # Extract identifiers with enhanced logic
                    unique_id = None
                    label = None
                    
                    # Enhanced UniqueID extraction
                    if 'identifiers' in pattern_info:
                        identifiers = pattern_info['identifiers']
                        
                        # Extract EIN/FIN for UniqueID
                        if 'EIN' in identifiers:
                            ein_match = re.search(identifiers['EIN'], form_text, re.IGNORECASE)
                            if ein_match:
                                unique_id = ein_match.group(1)
                        elif 'FIN' in identifiers:
                            fin_match = re.search(identifiers['FIN'], form_text, re.IGNORECASE)
                            if fin_match:
                                unique_id = fin_match.group(1)
                        
                        # Extract Label (E for Employer, P for Payer)
                        if 'Employer' in identifiers:
                            label = 'E'
                        elif 'Payer' in identifiers:
                            label = 'P'
                    
                    # Additional fallback for UniqueID if not found
                    if not unique_id:
                        if form_name == 'W-2':
                            ein_match = re.search(r'Employer Identification Number \(EIN\):\s*([\d\-]+)', form_text, re.IGNORECASE)
                            unique_id = ein_match.group(1) if ein_match else 'UNKNOWN'
                        elif form_name == '1099-INT':
                            fin_match = re.search(r"Payer's Federal Identification Number \(FIN\):\s*([\d\-]+)", form_text, re.IGNORECASE)
                            unique_id = fin_match.group(1) if fin_match else 'UNKNOWN'
                        elif form_name.startswith('1099'):
                            fin_match = re.search(r"Payer's Federal Identification Number \(FIN\):\s*([\d\-]+)", form_text, re.IGNORECASE)
                            unique_id = fin_match.group(1) if fin_match else 'UNKNOWN'
                    
                    # Additional fallback for Label if not found
                    if not label:
                        if form_name == 'W-2':
                            label = 'E'
                        elif form_name.startswith('1099'):
                            label = 'P'
                    
                    # Enhanced PayerBlurb extraction
                    payer_blurb = extract_enhanced_payer_blurb(form_text, form_name, unique_id)
                    
                    # Calculate income and withholding with enhanced error handling
                    calc = pattern_info.get('calculation', {})
                    income = None
                    withholding = None
                    
                    try:
                        if 'Income' in calc and callable(calc['Income']):
                            income = calc['Income'](fields_data)
                        if 'Withholding' in calc and callable(calc['Withholding']):
                            withholding = calc['Withholding'](fields_data)
                    except Exception as e:
                        logger.warning(f"⚠️ Error calculating income/withholding for {form_name}: {e}")
                        income = 0
                        withholding = 0
                    
                    # Ensure withholding is 0 instead of null for consistency
                    if withholding is None:
                        withholding = 0
                    
                    # Build form dict with enhanced structure and owner
                    form_dict = {
                        'Form': form_name,
                        'UniqueID': unique_id,
                        'Label': label,
                        'Income': income,
                        'Withholding': withholding,
                        'Category': pattern_info.get('category'),
                        'Fields': fields_data,
                        'PayerBlurb': payer_blurb,
                        'Owner': owner,  # Use extracted owner from filename
                        'SourceFile': file_name
                    }
                    
                    if tax_year not in all_data:
                        all_data[tax_year] = []
                    all_data[tax_year].append(form_dict)
            
            logger.info(f"✅ Completed parsing {file_name}. Found {forms_found} forms")
            
        except Exception as e:
            logger.error(f"❌ Error processing {file_name}: {str(e)}")
            logger.error(f"🔍 Error type: {type(e).__name__}")
            import traceback
            logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
            continue
    
    logger.info(f"✅ PDF parsing completed. Total tax years: {len(all_data)}")
    for tax_year, forms in all_data.items():
        logger.info(f"   📅 {tax_year}: {len(forms)} forms")
    
    # Calculate summary and restructure output
    summary = calculate_summary(all_data)
    
    # Create final output with summary at top and tax years below
    final_output = {
        'summary': summary,
        **all_data  # Add all tax year data
    }
    
    # Add TP/S analysis if requested
    if include_tps_analysis:
        logger.info("🔍 Generating TP/S analysis...")
        tps_analysis = TPSParser.generate_tps_analysis_summary(
            wi_data=all_data,
            filing_status=filing_status
        )
        final_output['tps_analysis'] = tps_analysis
        logger.info("✅ TP/S analysis added to output")
    
    logger.info("✅ Enhanced WI parsing completed with summary")
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
