import logging
import httpx
from typing import List, Dict, Any
import re
from datetime import datetime
from app.utils.pdf_utils import extract_text_from_pdf
from app.utils.at_codes import at_codes
from app.utils.tps_parser import TPSParser

# Create logger for this module
logger = logging.getLogger(__name__)

LOGIQS_GRID_URL = "https://tps.logiqs.com/API/Document/gridBind?caseid={case_id}&type=grid"
LOGIQS_DOWNLOAD_URL = "https://tps.logiqs.com/API/Document/DownloadFile?CaseDocumentID={case_doc_id}&caseId={case_id}"

# --- AT Service Layer ---

def fetch_at_file_grid(case_id: str, cookies: dict) -> List[Dict[str, Any]]:
    """
    Fetch AT file grid for a given case from Logiqs.
    Returns a list of AT file metadata dicts.
    """
    logger.info(f"🔍 Starting AT file grid fetch for case_id: {case_id}")
    
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
        
        at_files = []
        logger.info("🔍 Filtering for AT files...")
        
        for i, doc in enumerate(docs):
            if not isinstance(doc, dict):
                logger.warning(f"⚠️ Skipping non-dict document at index {i}: {type(doc)}")
                continue
            
            name = doc.get("Name", "")
            if not name:
                logger.warning(f"⚠️ Skipping document with no name at index {i}")
                continue
            
            logger.debug(f"🔍 Checking document: {name}")
            
            # Check for AT files - more flexible pattern to match "AT 23 E.pdf", "AT 22.pdf", etc.
            if re.search(r'AT\s+\d{2}', name, re.IGNORECASE):
                case_doc_id = doc.get("CaseDocumentID")
                if case_doc_id:
                    at_files.append({
                        "FileName": name,
                        "CaseDocumentID": case_doc_id
                    })
                    logger.info(f"✅ Found AT file: {name} (ID: {case_doc_id})")
                else:
                    logger.warning(f"⚠️ AT file {name} has no CaseDocumentID")
            else:
                logger.debug(f"⏭️ Skipping non-AT file: {name}")
        
        logger.info(f"✅ AT file grid fetch completed. Found {len(at_files)} AT files")
        return at_files
        
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error {e.response.status_code}: {e.response.text}")
        raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"❌ Request error: {str(e)}")
        raise Exception(f"Request error: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error fetching AT file grid: {str(e)}")
        raise Exception(f"Error fetching AT file grid: {str(e)}")

def download_at_pdf(case_doc_id: str, case_id: str, cookies: dict) -> bytes:
    """
    Download an AT PDF file using its CaseDocumentID and case_id.
    Returns PDF bytes.
    """
    logger.info(f"📥 Downloading AT PDF - CaseDocumentID: {case_doc_id}, case_id: {case_id}")
    
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
        logger.error(f"❌ Error downloading AT PDF: {str(e)}")
        raise Exception(f"Error downloading AT PDF: {str(e)}")

def format_year(year):
    """Format year consistently by removing commas and converting to string"""
    if isinstance(year, str):
        return year.replace(',', '')
    return str(year)

def extract_at_transactions(text):
    """Extract transaction data from AT transcript text (robust to compact and spaced formats)"""
    # Find the transactions section
    idx = text.find("TRANSACTIONS")
    if idx < 0:
        return []
    buf = text[idx:]
    transactions = []
    # Regex for compact format (single line, no spaces between columns)
    compact_regex = re.compile(r'^(\d{3}|n/a)([^\d\n]+?)(\d{8})\s+(\d{2}-\d{2}-\d{4})\s+(-?\$?[\d,]+\.\d{2})', re.MULTILINE)
    # Regex for spaced/multiline format (columns with headers)
    spaced_regex = re.compile(r'^(\d{3}|n/a)\s*([^\n]+)\n(?:[\w\s]*)?(\d{2}-\d{2}-\d{4})\s*\n\$?([\d,\.-]+)', re.MULTILINE)
    # Try compact format first
    for match in compact_regex.finditer(buf):
        code, desc, cyc, post, amt = match.groups()
        # Try to parse cycle date
        try:
            cycle_date = f"{cyc[:4]}-{cyc[4:6]}-{cyc[6:]}"
        except Exception:
            cycle_date = ''
        # Parse post date
        try:
            post_date = datetime.strptime(post, "%m-%d-%Y").date().isoformat()
        except Exception:
            post_date = post
        # Parse amount
        try:
            amount = float(amt.replace('$','').replace(',',''))
        except Exception:
            amount = 0.0
        transactions.append({
            "code": code.strip(),
            "meaning": desc.strip(),
            "cycle_date": cycle_date,
            "date": post_date,
            "amount": amount
        })
    # If no compact matches, try spaced format
    if not transactions:
        # Look for special lines like 'No tax return filed'
        for line in buf.splitlines():
            if re.search(r'no tax return filed', line, re.IGNORECASE):
                transactions.append({
                    'code': 'n/a',
                    'meaning': 'No tax return filed',
                    'cycle_date': '',
                    'date': '',
                    'amount': 0.0
                })
        for match in spaced_regex.finditer(buf):
            code, desc, post, amt = match.groups()
            # Parse post date
            try:
                post_date = datetime.strptime(post, "%m-%d-%Y").date().isoformat()
            except Exception:
                post_date = post
            # Parse amount
            try:
                amount = float(amt.replace('$','').replace(',',''))
            except Exception:
                amount = 0.0
            transactions.append({
                "code": code.strip(),
                "meaning": desc.strip(),
                "cycle_date": '',
                "date": post_date,
                "amount": amount
            })
    return transactions

def extract_at_data(text):
    """Extract data from Account Transcript text (robust to all formats)"""
    data = {}
    # Extract tax year (handle all known formats)
    year_match = re.search(r'Report for Tax Period Ending:\s*\d{2}-\d{2}-(\d{4})', text)
    if year_match:
        year = year_match.group(1)
        data['tax_year'] = format_year(year)
        logger.info(f"Found tax year from Report for Tax Period Ending: {data['tax_year']}")
    else:
        year_match = re.search(r'TAX PERIOD:\s*Dec\.\s*31,\s*(\d{4})', text, re.IGNORECASE)
        if year_match:
            year = year_match.group(1)
            data['tax_year'] = format_year(year)
            logger.info(f"Found tax year from TAX PERIOD: {data['tax_year']}")
        else:
            year_match = re.search(r'TAX PERIOD:\s*([A-Za-z]+\.\s*\d{1,2},?\s*\d{4})', text, re.IGNORECASE)
            if year_match:
                # Try to extract year from the matched string
                year = re.search(r'(\d{4})', year_match.group(1))
                if year:
                    data['tax_year'] = format_year(year.group(1))
                    logger.info(f"Found tax year from TAX PERIOD alt: {data['tax_year']}")
                else:
                    data['tax_year'] = 'Unknown'
            else:
                year_match = re.search(r'(\d{4})', text)
                if year_match:
                    data['tax_year'] = format_year(year_match.group(1))
                    logger.info(f"Found tax year from fallback pattern: {data['tax_year']}")
                else:
                    logger.warning("No tax year found")
                    data['tax_year'] = 'Unknown'
    # Extract financial data (robust to upper/lowercase, colon/space, missing values)
    financial_patterns = {
        'account_balance': r'(?:ACCOUNT BALANCE|Account balance)[:\s]*[\$]?([\d,\.\-]+)',
        'accrued_interest': r'(?:ACCRUED INTEREST|Accrued interest)[:\s]*[\$]?([\d,\.\-]+)',
        'accrued_penalty': r'(?:ACCRUED PENALTY|Accrued penalty)[:\s]*[\$]?([\d,\.\-]+)',
        'adjusted_gross_income': r'(?:ADJUSTED GROSS INCOME|Adjusted gross income)[:\s]*[\$]?([\d,\.\-]+)',
        'taxable_income': r'(?:TAXABLE INCOME|Taxable income)[:\s]*[\$]?([\d,\.\-]+)',
        'tax_per_return': r'(?:TAX PER RETURN|Tax per return)[:\s]*[\$]?([\d,\.\-]+)',
        'se_tax_taxpayer': r'(?:SE TAXABLE INCOME TAXPAYER|SE taxable income taxpayer)[:\s]*[\$]?([\d,\.\-]+)',
        'se_tax_spouse': r'(?:SE TAXABLE INCOME SPOUSE|SE taxable income spouse)[:\s]*[\$]?([\d,\.\-]+)',
        'total_se_tax': r'(?:TOTAL SELF EMPLOYMENT TAX|Total self employment tax)[:\s]*[\$]?([\d,\.\-]+)'
    }
    for key, pattern in financial_patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                amount = float(match.group(1).replace(',', ''))
                data[key] = amount
                logger.info(f"Found {key}: {amount}")
            except ValueError:
                logger.warning(f"Could not parse amount for {key}: {match.group(1)}")
                data[key] = 0.00
        else:
            logger.warning(f"No match found for {key}")
            data[key] = 0.00
    
    # Calculate total_balance as sum of account_balance + accrued_interest + accrued_penalty
    total_balance = data.get('account_balance', 0.0) + data.get('accrued_interest', 0.0) + data.get('accrued_penalty', 0.0)
    data['total_balance'] = total_balance
    logger.info(f"Calculated total_balance: {total_balance} (account: {data.get('account_balance', 0.0)} + interest: {data.get('accrued_interest', 0.0)} + penalty: {data.get('accrued_penalty', 0.0)})")
    # Extract filing status - make it more robust
    filing_patterns = [
        r'(?:FILING STATUS|Filing status)[:\s]*([^,\n]+)',
        r'FILING STATUS[:\s]*([^,\n]+)',
        r'Filing status[:\s]*([^,\n]+)',
        r'Filing Status[:\s]*([^,\n]+)',
        # Look for filing status near the top of the document
        r'([A-Za-z\s]+(?:Filing|Joint|Single|Married|Head|Widow))'
    ]
    
    filing_status_found = False
    for i, pattern in enumerate(filing_patterns):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            filing_status = match.group(1).strip()
            # Clean up the filing status
            if filing_status:
                data['filing_status'] = filing_status
                logger.info(f"Found filing_status (pattern {i+1}): {filing_status}")
                filing_status_found = True
                break
    
    if not filing_status_found:
        logger.warning(f"No filing_status found in text. Setting to 'Unknown'. Text preview: {text[:200]}...")
        data['filing_status'] = "Unknown"
    # Extract processing date (robust to all formats)
    processing_patterns = [
        # Standard format: "PROCESSING DATE: January 15, 2024"
        r'(?:PROCESSING DATE|Processing date)[:\s]*([A-Za-z]+\.?\s+\d{1,2},?\s*\d{4})',
        # Alternative format: "PROCESSING DATE: Jan 15, 2024"
        r'(?:PROCESSING DATE|Processing date)[:\s]*([A-Za-z]+\.?\s+\d{1,2},?\s*\d{4})',
        # No comma format: "PROCESSING DATE: January 15 2024"
        r'(?:PROCESSING DATE|Processing date)[:\s]*([A-Za-z]+\.?\s+\d{1,2}\s+\d{4})',
        # Abbreviated month: "PROCESSING DATE: Jan. 15, 2024"
        r'(?:PROCESSING DATE|Processing date)[:\s]*([A-Za-z]+\.\s+\d{1,2},?\s*\d{4})',
        # Different spacing: "PROCESSING DATE:January 15, 2024"
        r'(?:PROCESSING DATE|Processing date)[:\s]*([A-Za-z]+\.?\s+\d{1,2},?\s*\d{4})',
        # With extra spaces: "PROCESSING DATE:  January  15,  2024"
        r'(?:PROCESSING DATE|Processing date)[:\s]*([A-Za-z]+\.?\s+\d{1,2},?\s*\d{4})',
        # Different case variations
        r'(?:processing date|Processing Date|PROCESSING DATE)[:\s]*([A-Za-z]+\.?\s+\d{1,2},?\s*\d{4})',
        # Look for date patterns near "PROCESSING" keyword
        r'PROCESSING[^:]*:\s*([A-Za-z]+\.?\s+\d{1,2},?\s*\d{4})',
        # Look for date patterns near "DATE" keyword
        r'DATE[^:]*:\s*([A-Za-z]+\.?\s+\d{1,2},?\s*\d{4})',
        # Fallback: look for any date pattern in the header area
        r'([A-Za-z]+\.?\s+\d{1,2},?\s*\d{4})'
    ]
    
    processing_date_found = False
    for i, pattern in enumerate(processing_patterns):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Additional validation: make sure it's actually a date and not some other field
            date_text = match.group(1).strip()
            
            # Skip if it looks like a tax year or other non-processing date
            if re.match(r'^\d{4}$', date_text):  # Skip if just a year
                continue
            if 'TAX PERIOD' in text and date_text in text.split('TAX PERIOD')[0]:  # Skip if in tax period section
                continue
            if 'REPORT FOR TAX PERIOD' in text and date_text in text.split('REPORT FOR TAX PERIOD')[0]:  # Skip if in report section
                continue
            
            data['processing_date'] = date_text
            logger.info(f"Found processing date (pattern {i+1}): {data['processing_date']}")
            processing_date_found = True
            break
    
    if not processing_date_found:
        logger.warning("No processing date found with any pattern")
        data['processing_date'] = None
    # Extract transactions
    data['transactions'] = extract_at_transactions(text)
    return data

def parse_at_pdfs(at_files: List[Dict[str, Any]], cookies: dict, case_id: str, include_tps_analysis: bool = False, filing_status: str = None) -> List[Dict[str, Any]]:
    """
    Download and parse all AT PDFs for the case, returning list of AT data matching Streamlit format.
    Optionally includes TP/S analysis if include_tps_analysis=True.
    """
    logger.info(f"🔍 Starting AT PDF parsing for {len(at_files)} AT files")
    if include_tps_analysis:
        logger.info(f"🔍 TP/S analysis enabled with filing status: {filing_status}")
    
    all_at_data = []
    
    for i, at_file in enumerate(at_files):
        file_name = at_file["FileName"]
        case_doc_id = at_file["CaseDocumentID"]
        
        logger.info(f"📄 Processing AT file {i+1}/{len(at_files)}: {file_name}")
        
        # Extract owner from filename for TP/S analysis
        owner = TPSParser.extract_owner_from_filename(file_name)
        logger.info(f"👤 Extracted owner from filename '{file_name}': {owner}")
        
        try:
            # Download PDF
            logger.info(f"📥 Downloading PDF for {file_name}...")
            pdf_bytes = download_at_pdf(case_doc_id, case_id, cookies)
            
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
            
            # Parse AT data using the exact same logic as Streamlit app
            logger.info(f"🔍 Parsing AT data in {file_name}...")
            data = extract_at_data(text)
            
            if data:
                # Use extracted owner from filename instead of simple E check
                data['owner'] = owner
                data['source_file'] = file_name
                all_at_data.append(data)
                logger.info(f"✅ Found AT data for {data.get('tax_year', 'Unknown')} with owner {owner}")
            else:
                logger.warning(f"⚠️ No AT data found in {file_name}")
            
            logger.info(f"✅ Completed parsing {file_name}")
            
        except Exception as e:
            logger.error(f"❌ Error processing {file_name}: {str(e)}")
            logger.error(f"🔍 Error type: {type(e).__name__}")
            import traceback
            logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
            continue
    
    logger.info(f"✅ AT PDF parsing completed. Total AT records: {len(all_at_data)}")
    for at_record in all_at_data:
        logger.info(f"   📅 {at_record['tax_year']}: {len(at_record['transactions'])} transactions")
    
    # Add TP/S analysis if requested
    if include_tps_analysis:
        logger.info("🔍 Generating TP/S analysis for AT data...")
        tps_analysis = TPSParser.generate_tps_analysis_summary(
            at_data=all_at_data,
            filing_status=filing_status
        )
        # Return enhanced structure with analysis
        return {
            'at_data': all_at_data,
            'tps_analysis': tps_analysis
        }
    
    return all_at_data 