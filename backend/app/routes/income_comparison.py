import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from app.utils.cookies import cookies_exist, get_cookies
from app.services.wi_service import fetch_wi_file_grid, parse_wi_pdfs
from app.services.at_service import fetch_at_file_grid, parse_at_pdfs
from app.utils.client_info import extract_client_info_from_logiqs
from app.models.response_models import IncomeComparisonResponse, ClientData, ClientInfo, ContactInfo, TaxInfo, FinancialProfile, CaseManagement, RawData, ComparisonInfo

# Create logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()

def build_client_data_from_logiqs(case_id: str, logiqs_data: Dict[str, Any]) -> ClientData:
    """
    Build ClientData structure from Logiqs API response.
    """
    # Extract basic client info
    client_info = ClientInfo(
        case_id=case_id,
        full_name=logiqs_data.get('client_name', ''),
        first_name=logiqs_data.get('first_name', ''),
        middle_name=logiqs_data.get('middle_name', ''),
        last_name=logiqs_data.get('last_name', ''),
        ssn=logiqs_data.get('ssn', ''),
        ein=logiqs_data.get('ein', ''),
        marital_status=logiqs_data.get('marital_status'),
        business_name=logiqs_data.get('business_name', ''),
        business_type=logiqs_data.get('business_type', ''),
        business_address=logiqs_data.get('business_address', '')
    )
    
    # Build contact info
    contact_info = ContactInfo(
        primary_phone=logiqs_data.get('primary_phone', ''),
        home_phone=logiqs_data.get('home_phone', ''),
        work_phone=logiqs_data.get('work_phone', ''),
        email=logiqs_data.get('email', ''),
        address=logiqs_data.get('address', {}),
        sms_permitted=logiqs_data.get('sms_permitted', False),
        best_time_to_call=logiqs_data.get('best_time_to_call', '')
    )
    
    # Build tax info
    tax_info = TaxInfo(
        total_liability=logiqs_data.get('total_tax_debt'),
        years_owed=logiqs_data.get('years_owed', []),
        unfiled_years=logiqs_data.get('unfiled_years', []),
        status_id=logiqs_data.get('status_id', 0),
        status_name=logiqs_data.get('status_name', ''),
        tax_type=logiqs_data.get('tax_type', '')
    )
    
    # Build financial profile
    financial_profile = FinancialProfile(
        income=logiqs_data.get('income', {}),
        expenses=logiqs_data.get('expenses', {}),
        assets=logiqs_data.get('assets', {}),
        business=logiqs_data.get('business', {}),
        family=logiqs_data.get('family', {})
    )
    
    # Build case management
    case_management = CaseManagement(
        sale_date=logiqs_data.get('sale_date', ''),
        created_date=logiqs_data.get('created_date', ''),
        modified_date=logiqs_data.get('modified_date', ''),
        days_in_status=logiqs_data.get('days_in_status', 0),
        source_name=logiqs_data.get('source_name', ''),
        team=logiqs_data.get('team', {})
    )
    
    # Build raw data
    raw_data = RawData(
        total_tax_debt=logiqs_data.get('total_tax_debt'),
        client_agi=logiqs_data.get('client_agi'),
        current_filing_status=logiqs_data.get('current_filing_status'),
        currency=logiqs_data.get('currency'),
        extracted_at=logiqs_data.get('extracted_at', ''),
        url=logiqs_data.get('url', ''),
        success=logiqs_data.get('success', False)
    )
    
    return ClientData(
        client_info=client_info,
        contact_info=contact_info,
        tax_info=tax_info,
        financial_profile=financial_profile,
        case_management=case_management,
        raw_data=raw_data
    )

@router.get("/{case_id}", tags=["Income Comparison"], 
           summary="Client Profile vs Transcript Income Comparison",
           description="Compare client profile income to WI/AT transcript income for the most recent year.",
           response_model=IncomeComparisonResponse)
def income_comparison(case_id: str):
    """
    Compare client profile income to WI/AT transcript income for the most recent year.
    Returns detailed comparison with client data, WI summary, and AT data.
    """
    logger.info(f"🔍 Received income comparison request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Extract client info from Logiqs
        logger.info(f"📋 Extracting client info from Logiqs for case_id: {case_id}")
        logiqs_data = extract_client_info_from_logiqs(case_id, cookies)
        
        # Build proper client data structure
        client_data = build_client_data_from_logiqs(case_id, logiqs_data)
        
        # Get WI data
        logger.info(f"📋 Fetching WI data for case_id: {case_id}")
        wi_files = fetch_wi_file_grid(case_id, cookies)
        wi_summary = {}
        if wi_files:
            wi_data = parse_wi_pdfs(wi_files, cookies, case_id, False, None, return_scoped_structure=True)
            # Convert scoped structure to summary format
            if isinstance(wi_data, list):
                # New scoped structure - convert to summary
                total_forms = 0
                by_year = {}
                for file_result in wi_data:
                    if not isinstance(file_result, dict):
                        continue
                    forms = file_result.get('forms', [])
                    total_forms += len(forms)
                    
                    # Group by year (simplified - would need proper year extraction)
                    year = "2023"  # Default year
                    if year not in by_year:
                        by_year[year] = {
                            'number_of_forms': 0,
                            'total_income': 0,
                            'total_withholding': 0,
                            'estimated_agi': 0
                        }
                    
                    for form in forms:
                        if isinstance(form, dict):
                            fields = form.get('fields', [])
                            income = 0
                            withholding = 0
                            for field in fields:
                                if isinstance(field, dict):
                                    field_name = field.get('name', '')
                                    field_value = field.get('value', 0)
                                    try:
                                        field_value = float(field_value)
                                    except:
                                        field_value = 0
                                    
                                    if 'income' in field_name.lower() or 'wage' in field_name.lower():
                                        income += field_value
                                    elif 'withholding' in field_name.lower() or 'tax' in field_name.lower():
                                        withholding += field_value
                            
                            by_year[year]['number_of_forms'] += 1
                            by_year[year]['total_income'] += income
                            by_year[year]['total_withholding'] += withholding
                            by_year[year]['estimated_agi'] += income
                
                wi_summary = {
                    'total_years': len(by_year),
                    'total_forms': total_forms,
                    'by_year': by_year
                }
            else:
                # Legacy structure
                wi_summary = wi_data.get('summary', {})
        
        # Get AT data
        logger.info(f"📋 Fetching AT data for case_id: {case_id}")
        at_files = fetch_at_file_grid(case_id, cookies)
        at_data = []
        if at_files:
            at_result = parse_at_pdfs(at_files, cookies, case_id, False, None)
            at_data = at_result if isinstance(at_result, list) else []
        
        # Calculate comparison info
        logger.info(f"🔍 Calculating income comparison")
        most_recent_year = "2019"  # Default, would be calculated from data
        wi_total_income = 0
        at_agi = None
        
        if wi_summary and 'by_year' in wi_summary:
            years = list(wi_summary['by_year'].keys())
            if years:
                most_recent_year = max(years)
                wi_total_income = wi_summary['by_year'][most_recent_year].get('total_income', 0)
        
        if at_data:
            # Find most recent AT record
            recent_at = max(at_data, key=lambda x: x.get('tax_year', '0'))
            at_agi = recent_at.get('adjusted_gross_income')
        
        # Determine which transcript income to use
        transcript_income_used = wi_total_income if wi_total_income > 0 else (at_agi or 0)
        transcript_source = "Transcript Total Income (from WI)" if wi_total_income > 0 else "Adjusted Gross Income (from AT)"
        
        # Calculate percentage difference if client income is available
        percentage_difference = None
        client_annual_income = None
        if logiqs_data and logiqs_data.get('success'):
            client_annual_income = logiqs_data.get('client_agi') or logiqs_data.get('total_tax_debt')
            if client_annual_income and transcript_income_used > 0:
                percentage_difference = ((transcript_income_used - client_annual_income) / client_annual_income) * 100
        
        comparison_info = ComparisonInfo(
            most_recent_year=most_recent_year,
            client_annual_income=client_annual_income,
            wi_total_income=wi_total_income,
            at_agi=at_agi,
            transcript_income_used=transcript_income_used,
            transcript_source=transcript_source,
            percentage_difference=percentage_difference
        )
        
        logger.info(f"✅ Successfully completed income comparison for case_id: {case_id}")
        
        return IncomeComparisonResponse(
            comparison_info=comparison_info,
            client_data=client_data,
            wi_summary=wi_summary,
            at_data=at_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error performing income comparison for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 