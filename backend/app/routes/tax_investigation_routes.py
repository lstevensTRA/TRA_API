import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from app.utils.cookies import cookies_exist, get_cookies
from app.utils.client_info import extract_client_info_from_logiqs
from app.models.response_models import TaxInvestigationCompareResponse, TaxInvestigationClientInfo

# Create logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/client-info/{case_id}", tags=["Tax Investigation"], 
           summary="Get Tax Investigation Client Info",
           description="Get tax investigation client information for a specific case.",
           response_model=TaxInvestigationClientInfo)
def get_tax_investigation_client(case_id: str):
    """
    Get tax investigation client information for a specific case.
    """
    logger.info(f"🔍 Received tax investigation client request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch case data
        logger.info(f"📋 Fetching case data for case_id: {case_id}")
        case_data = extract_client_info_from_logiqs(case_id, cookies)
        
        # Extract client info
        logger.info(f"🔍 Extracting client info from case data")
        client_info = {
            "name": case_data.get('client_name', 'N/A'),
            "annual_income": case_data.get('client_agi', 0),
            "employer": case_data.get('employer', 'N/A'),
            "case_id": case_id,
            "ssn": case_data.get('ssn', ''),
            "address": case_data.get('address', ''),
            "phone": case_data.get('phone', ''),
            "email": case_data.get('email', ''),
            "marital_status": case_data.get('marital_status', ''),
            "filing_status": case_data.get('filing_status', ''),
            "total_liability": case_data.get('total_tax_debt', 0),
            "years_owed": case_data.get('years_owed', []),
            "unfiled_years": case_data.get('unfiled_years', []),
            "status": case_data.get('status', ''),
            "resolution_type": case_data.get('resolution_type', ''),
            "resolution_amount": case_data.get('resolution_amount', 0),
            "payment_terms": case_data.get('payment_terms', ''),
            "created_date": case_data.get('created_date', ''),
            "modified_date": case_data.get('modified_date', '')
        }
        
        logger.info(f"✅ Successfully retrieved tax investigation client info for case_id: {case_id}")
        
        return client_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting tax investigation client info for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/test", tags=["Tax Investigation"])
def test_tax_investigation_router():
    """Test route to verify the router is working."""
    return {"message": "Tax Investigation router is working!"}

@router.get("/compare/{case_id}", tags=["Tax Investigation"], 
           summary="Compare Tax Investigation Data",
           description="Compare TI, WI, and AT data for a specific case.",
           response_model=TaxInvestigationCompareResponse)
def compare_tax_investigation_data(case_id: str):
    """
    Compare TI, WI, and AT data for a specific case.
    """
    logger.info(f"🔍 Received tax investigation compare request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch case data
        logger.info(f"📋 Fetching case data for case_id: {case_id}")
        case_data = extract_client_info_from_logiqs(case_id, cookies)
        
        # Extract client info
        logger.info(f"🔍 Extracting client info from case data")
        client_info = TaxInvestigationClientInfo(
            name=case_data.get('client_name', 'N/A'),
            annual_income=case_data.get('client_agi', 0),
            employer=case_data.get('employer', 'N/A'),
            case_id=case_id,
            ssn=case_data.get('ssn', ''),
            address=case_data.get('address', ''),
            phone=case_data.get('phone', ''),
            email=case_data.get('email', ''),
            marital_status=case_data.get('marital_status', ''),
            filing_status=case_data.get('filing_status', ''),
            total_liability=case_data.get('total_tax_debt', 0),
            years_owed=case_data.get('years_owed', []),
            unfiled_years=case_data.get('unfiled_years', []),
            status=case_data.get('status', ''),
            resolution_type=case_data.get('resolution_type', ''),
            resolution_amount=case_data.get('resolution_amount', 0),
            payment_terms=case_data.get('payment_terms', ''),
            created_date=case_data.get('created_date', ''),
            modified_date=case_data.get('modified_date', '')
        )
        
        # Mock data for comparison
        comparison = {
            "income_discrepancies": [],
            "employment_discrepancies": [],
            "tax_year_discrepancies": [],
            "balance_discrepancies": [],
            "summary": {
                "total_discrepancies": 0,
                "critical_discrepancies": 0,
                "data_sources_available": []
            }
        }
        
        logger.info(f"✅ Successfully compared tax investigation data for case_id: {case_id}")
        
        return TaxInvestigationCompareResponse(
            case_id=case_id,
            client_info=client_info,
            ti_data={},
            wi_data={},
            at_data={},
            comparison=comparison
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error comparing tax investigation data for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 

@router.get("/ti-sheet/{case_id}", tags=["Tax Investigation"], summary="Get structured TI sheet data", description="Parse and return structured Tax Investigation (TI) sheet data for a case.")
def get_ti_sheet(case_id: str):
    """
    Get structured TI sheet data for a case by parsing the raw TI text using the enhanced, version-aware parser.
    """
    from app.utils.ti_parser import EnhancedTIParser
    from app.services.wi_service import fetch_ti_file_grid, download_ti_pdf, extract_text_from_pdf
    logger.info(f"🔍 Received TI sheet request for case_id: {case_id}")
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    cookies = get_cookies()
    try:
        ti_files = fetch_ti_file_grid(case_id, cookies)
        if not ti_files:
            raise HTTPException(status_code=404, detail="No TI files found for this case.")
        ti_file = ti_files[0]
        pdf_bytes = download_ti_pdf(ti_file["CaseDocumentID"], case_id, cookies)
        if not pdf_bytes:
            raise HTTPException(status_code=404, detail="TI PDF file not found or empty.")
        raw_text = extract_text_from_pdf(pdf_bytes)
        if not raw_text:
            raise HTTPException(status_code=500, detail="Could not extract text from TI PDF.")
        structured = EnhancedTIParser.parse_ti_text_enhanced(raw_text, filename=ti_file["FileName"])
        return structured
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting TI sheet for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 