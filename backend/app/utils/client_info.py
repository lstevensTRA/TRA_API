import logging
import re
import requests
from datetime import datetime
from typing import Dict, Any

# Create logger for this module
logger = logging.getLogger(__name__)

def extract_client_info_from_logiqs(case_id: str, cookies: dict) -> dict:
    """
    Extract client information from Logiqs case page.
    """
    logger.info(f"🔍 Extracting client info from Logiqs for case_id: {case_id}")
    
    try:
        # Build case URL
        case_url = f"https://tps.logiqs.com/Cases/Case.aspx?CaseID={case_id}&ProductID=1"
        
        # Convert cookies dict to string
        cookies_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        
        headers = {
            'Cookie': cookies_string,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(case_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            html_content = response.text
            
            # Extract TaxAmount using multiple patterns
            tax_amount = None
            tax_patterns = [
                r'TaxAmount["\s]*:["\s]*([0-9.]+)',
                r'name=["\']taxamount["\'][^>]*value=["\']([0-9.]+)["\']',
                r'taxAmount["\s]*=["\s]*([0-9.]+)',
                r'\$([0-9,]+\.?[0-9]*)'
            ]
            
            for pattern in tax_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    try:
                        tax_amount = float(match.group(1).replace(',', ''))
                        break
                    except ValueError:
                        continue
            
            # Extract ClientDetailNetIncome
            client_agi = None
            net_income_match = re.search(r'ClientDetailNetIncom["\s]*:["\s]*"?\$?([0-9,.]+)', html_content, re.IGNORECASE)
            if net_income_match:
                try:
                    monthly_income = float(net_income_match.group(1).replace(',', ''))
                    client_agi = round(monthly_income * 12)
                except ValueError:
                    pass
            
            # Extract MaritalStatus
            marital_status_map = {
                "0": "Single",
                "1": "Married Filing Jointly", 
                "2": "Married Filing Separately",
                "3": "Head of Household",
                "4": "Qualifying Widow(er)"
            }
            
            current_filing_status = None
            marital_status_match = re.search(r'MartialStatus["\s]*:["\s]*([0-4])', html_content, re.IGNORECASE)
            if marital_status_match and marital_status_match.group(1) in marital_status_map:
                current_filing_status = marital_status_map[marital_status_match.group(1)]
            
            return {
                "total_tax_debt": tax_amount,
                "client_agi": client_agi,
                "current_filing_status": current_filing_status,
                "currency": "USD" if tax_amount else None,
                "extracted_at": datetime.now().isoformat(),
                "url": case_url,
                "success": True
            }
        else:
            logger.warning(f"⚠️ Logiqs request failed with status {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        logger.error(f"❌ Error extracting Logiqs client info: {str(e)}")
        return {"success": False, "error": str(e)} 