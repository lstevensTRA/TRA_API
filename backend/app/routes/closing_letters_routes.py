import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from app.utils.cookies import cookies_exist, get_cookies
from app.utils.pdf_utils import generate_pdf_letter
import requests
import json
from datetime import datetime
from app.utils.client_info import extract_client_info_from_logiqs
from app.models.response_models import ClosingLettersResponse

# Create logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/{case_id}", tags=["Closing Letters"], 
           summary="Generate Closing Letters",
           description="Generate closing letters for a specific case.",
           response_model=ClosingLettersResponse)
def generate_case_closing_letters(case_id: str):
    """
    Generate closing letters for a specific case.
    """
    logger.info(f"🔍 Received closing letters request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch case data
        logger.info(f"📋 Fetching case data for case_id: {case_id}")
        case_data = extract_client_info_from_logiqs(case_id, cookies)
        
        # Fetch letter templates
        logger.info(f"📋 Fetching letter templates")
        templates = fetch_letter_templates(cookies)
        
        # Generate closing letters
        logger.info(f"🔍 Generating closing letters")
        letters = generate_closing_letters(case_data, templates)
        
        logger.info(f"✅ Generated {len(letters)} closing letters")
        
        logger.info(f"✅ Successfully generated {len(letters)} closing letters for case_id: {case_id}")
        
        return ClosingLettersResponse(
            case_id=case_id,
            total_letters=len(letters),
            letters=letters,
            generated_at=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating closing letters for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/{case_id}/generate", tags=["Closing Letters"])
def generate_closing_letter_pdf(case_id: str, letter_type: str = Query(..., description="Type of closing letter to generate"), custom_content: Optional[str] = Query(None, description="Custom content to include in the letter")):
    """
    Generate a PDF closing letter for a specific case.
    """
    logger.info(f"🔍 Received PDF closing letter generation request for case_id: {case_id}, type: {letter_type}")
    
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch case data
        case_data = fetch_case_data(case_id, cookies)
        
        # Fetch letter template
        letter_template = fetch_letter_template(letter_type, cookies)
        
        if not letter_template:
            raise HTTPException(status_code=404, detail=f"Letter template '{letter_type}' not found")
        
        # Generate PDF letter
        pdf_content = generate_pdf_letter(case_data, letter_template, custom_content)
        
        result = {
            "case_id": case_id,
            "letter_type": letter_type,
            "pdf_generated": True,
            "pdf_content": pdf_content,
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Successfully generated PDF closing letter for case_id: {case_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating PDF closing letter for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def fetch_case_data(case_id: str, cookies: dict) -> Dict[str, Any]:
    """
    Fetch case data from Logiqs.
    """
    logger.info(f"📋 Fetching case data for case_id: {case_id}")
    
    try:
        # Build case URL
        case_url = f"https://tps.logiqs.com/API/Case/GetCase?caseId={case_id}"
        
        # Convert cookies dict to string
        cookies_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        
        headers = {
            'Cookie': cookies_string,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        response = requests.get(case_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            case_data = response.json()
            logger.info(f"✅ Successfully fetched case data for case_id: {case_id}")
            return case_data
        else:
            logger.warning(f"⚠️ Case data request failed with status {response.status_code}")
            return {}
            
    except Exception as e:
        logger.error(f"❌ Error fetching case data: {str(e)}")
        return {}

def fetch_letter_templates(cookies: dict) -> List[Dict[str, Any]]:
    """
    Fetch letter templates from Logiqs API.
    """
    logger.info("📋 Fetching letter templates")
    
    try:
        # This would make an actual API call to fetch letter templates
        # For now, return mock data
        return []
    except Exception as e:
        logger.error(f"❌ Error fetching letter templates: {str(e)}")
        raise Exception(f"Error fetching letter templates: {str(e)}")

def fetch_letter_template(template_type: str, cookies: dict) -> Optional[Dict[str, Any]]:
    """
    Fetch a specific letter template from Logiqs.
    """
    logger.info(f"📋 Fetching letter template: {template_type}")
    
    try:
        # Build template URL
        template_url = f"https://tps.logiqs.com/API/Letters/GetTemplate?type={template_type}"
        
        # Convert cookies dict to string
        cookies_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        
        headers = {
            'Cookie': cookies_string,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        response = requests.get(template_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            template = response.json()
            logger.info(f"✅ Successfully fetched letter template: {template_type}")
            return template
        else:
            logger.warning(f"⚠️ Letter template request failed with status {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error fetching letter template: {str(e)}")
        return None

def generate_closing_letters(case_data: Dict[str, Any], templates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate closing letters based on case data and templates.
    """
    logger.info("🔍 Generating closing letters")
    
    try:
        # This would generate actual closing letters
        # For now, return mock data
        return []
    except Exception as e:
        logger.error(f"❌ Error generating closing letters: {str(e)}")
        raise Exception(f"Error generating closing letters: {str(e)}")

def create_ia_closing_letter(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create an Installment Agreement closing letter.
    """
    client_name = case_data.get("ClientName", "Client")
    case_id = case_data.get("CaseID", "")
    resolution_amount = case_data.get("ResolutionAmount", 0)
    payment_terms = case_data.get("PaymentTerms", "")
    
    letter_content = f"""
    Dear {client_name},
    
    This letter confirms that your Installment Agreement has been successfully established with the Internal Revenue Service.
    
    Case ID: {case_id}
    Agreement Amount: ${resolution_amount:,.2f}
    Payment Terms: {payment_terms}
    
    Please ensure all payments are made according to the agreed schedule. Failure to make timely payments may result in default of the agreement.
    
    If you have any questions regarding your installment agreement, please contact our office.
    
    Sincerely,
    Tax Resolution Associates
    """
    
    return {
        "letter_type": "IA_Closing",
        "subject": f"Installment Agreement Confirmation - Case {case_id}",
        "content": letter_content,
        "generated_at": datetime.now().isoformat()
    }

def create_oic_closing_letter(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create an Offer in Compromise closing letter.
    """
    client_name = case_data.get("ClientName", "Client")
    case_id = case_data.get("CaseID", "")
    resolution_amount = case_data.get("ResolutionAmount", 0)
    
    letter_content = f"""
    Dear {client_name},
    
    This letter confirms that your Offer in Compromise has been accepted by the Internal Revenue Service.
    
    Case ID: {case_id}
    Accepted Offer Amount: ${resolution_amount:,.2f}
    
    The IRS has agreed to settle your tax debt for the amount specified above. Please ensure all payments are made according to the accepted offer terms.
    
    If you have any questions regarding your offer in compromise, please contact our office.
    
    Sincerely,
    Tax Resolution Associates
    """
    
    return {
        "letter_type": "OIC_Closing",
        "subject": f"Offer in Compromise Acceptance - Case {case_id}",
        "content": letter_content,
        "generated_at": datetime.now().isoformat()
    }

def create_cnc_closing_letter(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a Currently Not Collectible closing letter.
    """
    client_name = case_data.get("ClientName", "Client")
    case_id = case_data.get("CaseID", "")
    
    letter_content = f"""
    Dear {client_name},
    
    This letter confirms that your account has been placed in Currently Not Collectible status by the Internal Revenue Service.
    
    Case ID: {case_id}
    
    This means that the IRS has determined that you are unable to pay your tax debt at this time. Collection activities have been suspended, but the debt remains and may be subject to future collection efforts if your financial situation improves.
    
    If you have any questions regarding your CNC status, please contact our office.
    
    Sincerely,
    Tax Resolution Associates
    """
    
    return {
        "letter_type": "CNC_Closing",
        "subject": f"Currently Not Collectible Status - Case {case_id}",
        "content": letter_content,
        "generated_at": datetime.now().isoformat()
    }

def create_generic_closing_letter(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a generic closing letter.
    """
    client_name = case_data.get("ClientName", "Client")
    case_id = case_data.get("CaseID", "")
    resolution_type = case_data.get("ResolutionType", "Resolution")
    
    letter_content = f"""
    Dear {client_name},
    
    This letter confirms that your tax case has been successfully resolved.
    
    Case ID: {case_id}
    Resolution Type: {resolution_type}
    
    Your case has been closed and all necessary documentation has been completed. If you have any questions regarding your case resolution, please contact our office.
    
    Sincerely,
    Tax Resolution Associates
    """
    
    return {
        "letter_type": "Generic_Closing",
        "subject": f"Case Resolution Confirmation - Case {case_id}",
        "content": letter_content,
        "generated_at": datetime.now().isoformat()
    } 