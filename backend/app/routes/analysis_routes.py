import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from app.utils.cookies import cookies_exist, get_cookies
from app.services.wi_service import fetch_wi_file_grid, parse_wi_pdfs
from app.services.at_service import fetch_at_file_grid, parse_at_pdfs
from app.utils.tps_parser import TPSParser
from app.utils.client_info import extract_client_info_from_logiqs
from app.models.response_models import (
    WIAnalysisResponse, ATAnalysisResponse, ComprehensiveAnalysisResponse, 
    ClientAnalysisResponse, ErrorResponse, WIFormData
)
from datetime import datetime

# Create logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()

def clean_wi_form_data(form_data: Dict[str, Any]) -> WIFormData:
    """
    Clean and validate WI form data to ensure it matches the response model.
    """
    return WIFormData(
        Form=form_data.get('Form', ''),
        UniqueID=form_data.get('UniqueID'),
        Label=form_data.get('Label'),
        Income=form_data.get('Income', 0.0),
        Withholding=form_data.get('Withholding', 0.0),
        Category=form_data.get('Category', ''),
        Fields=form_data.get('Fields', {}),
        PayerBlurb=form_data.get('PayerBlurb', ''),
        Owner=form_data.get('Owner', ''),
        SourceFile=form_data.get('SourceFile', '')
    )

def get_wi_summary_dict(wi_result) -> Dict[str, Any]:
    """
    Safely extract summary dict from WI result, handling both dict and object types.
    """
    if hasattr(wi_result, 'summary'):
        # If it's a Pydantic model, convert to dict
        if hasattr(wi_result.summary, 'dict'):
            return wi_result.summary.dict()
        elif hasattr(wi_result.summary, 'model_dump'):
            return wi_result.summary.model_dump()
        else:
            return wi_result.summary
    elif isinstance(wi_result, dict) and 'summary' in wi_result:
        return wi_result['summary']
    else:
        return {}

@router.get("/wi/{case_id}", tags=["Analysis"], summary="Wage & Income Multi-Year Analysis", 
           description="Get parsed and aggregated Wage & Income (WI) transcript data for all available years in the case.",
           response_model=WIAnalysisResponse)
def wi_analysis(
    case_id: str,
    include_tps_analysis: Optional[bool] = Query(False, description="Include TP/S analysis in response"),
    filing_status: Optional[str] = Query(None, description="Client filing status for TP/S analysis (e.g., 'Married Filing Jointly')")
):
    """
    Get parsed and aggregated Wage & Income (WI) transcript data for all available years in the case.
    Returns a summary of all WI forms and income by year, with optional TP/S analysis.
    """
    logger.info(f"🔍 Received WI data request for case_id: {case_id}")
    logger.info(f"🔍 TP/S analysis requested: {include_tps_analysis}")
    if filing_status:
        logger.info(f"🔍 Filing status provided: {filing_status}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    logger.info("✅ Cookies found, proceeding with authentication")
    cookies = get_cookies()
    logger.info(f"🍪 Loaded {len(cookies.get('cookies', [])) if isinstance(cookies, dict) and 'cookies' in cookies else 'unknown'} cookies")
    
    try:
        # Fetch WI file grid
        logger.info(f"📋 Fetching WI file grid for case_id: {case_id}")
        wi_files = fetch_wi_file_grid(case_id, cookies)
        
        if not wi_files:
            logger.warning(f"⚠️ No WI files found for case_id: {case_id}")
            raise HTTPException(status_code=404, detail="404: No WI files found for this case.")
        
        logger.info(f"✅ Found {len(wi_files)} WI files for case_id: {case_id}")
        for i, wi_file in enumerate(wi_files):
            filename = wi_file.get('FileName', 'Unknown')
            owner = TPSParser.extract_owner_from_filename(filename)
            logger.info(f"   📄 {i+1}. {filename} (ID: {wi_file.get('CaseDocumentID', 'Unknown')}, Owner: {owner})")
        
        # Parse WI PDFs with optional TP/S analysis
        logger.info(f"🔍 Starting PDF parsing for {len(wi_files)} WI files")
        wi_data = parse_wi_pdfs(wi_files, cookies, case_id, include_tps_analysis, filing_status)
        
        logger.info(f"✅ Successfully parsed WI data for case_id: {case_id}")
        logger.info(f"📊 Summary: {wi_data.get('summary', {}).get('total_years', 0)} years, {wi_data.get('summary', {}).get('total_forms', 0)} forms")
        
        # Convert to response model format and clean data
        years_data = {}
        for k, v in wi_data.items():
            if k.isdigit():
                # Clean each form in the year data
                cleaned_forms = []
                for form in v:
                    if isinstance(form, dict):
                        cleaned_form = clean_wi_form_data(form)
                        cleaned_forms.append(cleaned_form)
                years_data[k] = cleaned_forms
        
        summary = wi_data.get('summary', {})
        
        return WIAnalysisResponse(
            summary=summary,
            years_data=years_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting WI data for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/at/{case_id}", tags=["Analysis"], summary="Account Transcript Multi-Year Analysis", 
           description="Get parsed and aggregated Account Transcript (AT) data for all available years in the case.",
           response_model=ATAnalysisResponse)
def at_analysis(
    case_id: str,
    include_tps_analysis: Optional[bool] = Query(False, description="Include TP/S analysis in response"),
    filing_status: Optional[str] = Query(None, description="Client filing status for TP/S analysis (e.g., 'Married Filing Jointly')")
):
    """
    Get parsed and aggregated Account Transcript (AT) data for all available years in the case.
    Returns a summary of all AT data by year, with optional TP/S analysis.
    """
    logger.info(f"🔍 Received AT data request for case_id: {case_id}")
    logger.info(f"🔍 TP/S analysis requested: {include_tps_analysis}")
    if filing_status:
        logger.info(f"🔍 Filing status provided: {filing_status}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    logger.info("✅ Cookies found, proceeding with authentication")
    cookies = get_cookies()
    logger.info(f"🍪 Loaded {len(cookies.get('cookies', [])) if isinstance(cookies, dict) and 'cookies' in cookies else 'unknown'} cookies")
    
    try:
        # Fetch AT file grid
        logger.info(f"📋 Fetching AT file grid for case_id: {case_id}")
        at_files = fetch_at_file_grid(case_id, cookies)
        
        if not at_files:
            logger.warning(f"⚠️ No AT files found for case_id: {case_id}")
            raise HTTPException(status_code=404, detail="404: No AT files found for this case.")
        
        logger.info(f"✅ Found {len(at_files)} AT files for case_id: {case_id}")
        for i, at_file in enumerate(at_files):
            filename = at_file.get('FileName', 'Unknown')
            owner = TPSParser.extract_owner_from_filename(filename)
            logger.info(f"   📄 {i+1}. {filename} (ID: {at_file.get('CaseDocumentID', 'Unknown')}, Owner: {owner})")
        
        # Parse AT PDFs with optional TP/S analysis
        logger.info(f"🔍 Starting PDF parsing for {len(at_files)} AT files")
        at_result = parse_at_pdfs(at_files, cookies, case_id, include_tps_analysis, filing_status)
        
        # Handle different return formats based on TP/S analysis
        if include_tps_analysis and isinstance(at_result, dict):
            at_data = at_result['at_data']
            logger.info(f"✅ Successfully parsed AT data for case_id: {case_id} with TP/S analysis")
            logger.info(f"📊 Summary: {len(at_data)} AT records")
            for at_record in at_data:
                logger.info(f"   📅 {at_record['tax_year']}: {len(at_record['transactions'])} transactions")
            return ATAnalysisResponse(at_records=at_data)
        else:
            at_data = at_result
            logger.info(f"✅ Successfully parsed AT data for case_id: {case_id}")
            logger.info(f"📊 Summary: {len(at_data)} AT records")
            for at_record in at_data:
                logger.info(f"   📅 {at_record['tax_year']}: {len(at_record['transactions'])} transactions")
            return ATAnalysisResponse(at_records=at_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting AT data for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{case_id}", tags=["Analysis"], response_model=ComprehensiveAnalysisResponse)
def get_comprehensive_analysis(
    case_id: str,
    include_tps_analysis: Optional[bool] = Query(False, description="Include TP/S analysis in response"),
    filing_status: Optional[str] = Query(None, description="Client filing status for TP/S analysis")
):
    """
    Get comprehensive tax analysis combining WI and AT data.
    Returns advanced analytics including income trends, filing patterns, and recommendations.
    """
    logger.info(f"🔍 Received comprehensive analysis request for case_id: {case_id}")
    logger.info(f"🔍 TP/S analysis requested: {include_tps_analysis}")
    if filing_status:
        logger.info(f"🔍 Filing status provided: {filing_status}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Get WI analysis
        logger.info(f"📋 Getting WI analysis for comprehensive analysis")
        wi_result = wi_analysis(case_id, include_tps_analysis, filing_status)
        
        # Get AT analysis
        logger.info(f"📋 Getting AT analysis for comprehensive analysis")
        at_result = at_analysis(case_id, include_tps_analysis, filing_status)
        
        # Perform comprehensive analysis
        logger.info(f"🔍 Performing comprehensive analysis")
        
        # Calculate income trends
        income_trends = {}
        wi_summary_dict = get_wi_summary_dict(wi_result)
        if wi_summary_dict and 'by_year' in wi_summary_dict:
            for year, year_data in wi_summary_dict['by_year'].items():
                income_trends[year] = {
                    'total_income': year_data.get('total_income', 0),
                    'estimated_agi': year_data.get('estimated_agi', 0),
                    'forms_count': year_data.get('number_of_forms', 0)
                }
        
        # Calculate filing patterns
        filing_patterns = {}
        if hasattr(at_result, 'at_records') and at_result.at_records:
            for record in at_result.at_records:
                filing_patterns[record.tax_year] = {
                    'filing_status': record.filing_status,
                    'agi': record.adjusted_gross_income,
                    'tax_liability': record.tax_per_return
                }
        
        # Generate recommendations
        recommendations = []
        if income_trends:
            recent_years = sorted(income_trends.keys(), reverse=True)[:3]
            if len(recent_years) >= 2:
                current_income = income_trends[recent_years[0]]['total_income']
                previous_income = income_trends[recent_years[1]]['total_income']
                
                if current_income > previous_income * 1.1:
                    recommendations.append("Income has increased significantly - consider adjusting withholdings")
                elif current_income < previous_income * 0.9:
                    recommendations.append("Income has decreased - review payment plan affordability")
        
        if filing_patterns:
            statuses = [data['filing_status'] for data in filing_patterns.values()]
            if len(set(statuses)) > 1:
                recommendations.append("Filing status has changed - review tax planning strategies")
        
        logger.info(f"✅ Successfully completed comprehensive analysis for case_id: {case_id}")
        
        return ComprehensiveAnalysisResponse(
            case_id=case_id,
            analysis_type="comprehensive",
            summary={
                "total_years_analyzed": len(income_trends),
                "income_trends": income_trends,
                "filing_patterns": filing_patterns
            },
            detailed_analysis={
                "wi_analysis": wi_result.dict() if hasattr(wi_result, 'dict') else wi_result,
                "at_analysis": at_result.dict() if hasattr(at_result, 'dict') else at_result
            },
            recommendations=recommendations,
            generated_at=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error performing comprehensive analysis for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/client-analysis/{case_id}", tags=["Analysis"], response_model=ClientAnalysisResponse)
def get_client_analysis(case_id: str):
    """
    Analyze file names to detect TP/S ownership patterns and extract client information.
    Returns automated detection of filing status and TP/S breakdown.
    """
    logger.info(f"🔍 Received client analysis request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch file grids for analysis
        logger.info(f"📋 Fetching WI files for client analysis")
        wi_files = fetch_wi_file_grid(case_id, cookies)
        
        logger.info(f"📋 Fetching AT files for client analysis")
        at_files = fetch_at_file_grid(case_id, cookies)
        
        # Analyze file patterns
        logger.info(f"🔍 Analyzing file patterns")
        tp_files = []
        spouse_files = []
        
        # Analyze WI files
        for file in wi_files or []:
            filename = file.get('FileName', '')
            owner = TPSParser.extract_owner_from_filename(filename)
            if owner == 'TP':
                tp_files.append(filename)
            elif owner == 'S':
                spouse_files.append(filename)
        
        # Analyze AT files
        for file in at_files or []:
            filename = file.get('FileName', '')
            owner = TPSParser.extract_owner_from_filename(filename)
            if owner == 'TP':
                tp_files.append(filename)
            elif owner == 'S':
                spouse_files.append(filename)
        
        # Detect filing status
        filing_status_detected = None
        if any('MFJ' in f for f in tp_files + spouse_files):
            filing_status_detected = "Married Filing Jointly"
        elif any('MFS' in f for f in tp_files + spouse_files):
            filing_status_detected = "Married Filing Separately"
        elif spouse_files:
            filing_status_detected = "Married Filing Jointly"  # Default if spouse files exist
        else:
            filing_status_detected = "Single"
        
        # Try to extract additional client info from Logiqs
        logiqs_client_info = None
        try:
            logiqs_client_info = extract_client_info_from_logiqs(case_id, cookies)
        except Exception as e:
            logger.warning(f"⚠️ Could not extract Logiqs client info: {str(e)}")
        
        logger.info(f"✅ Successfully completed client analysis for case_id: {case_id}")
        
        return ClientAnalysisResponse(
            case_id=case_id,
            filing_status_detected=filing_status_detected,
            tp_spouse_breakdown={
                "tp_files": tp_files,
                "spouse_files": spouse_files,
                "total_tp_files": len(tp_files),
                "total_spouse_files": len(spouse_files)
            },
            suggested_filing_status=filing_status_detected,
            tps_analysis_enabled=len(spouse_files) > 0,
            file_patterns={
                "wi_files": [f.get('FileName', '') for f in wi_files or []],
                "at_files": [f.get('FileName', '') for f in at_files or []],
                "total_files": len(wi_files or []) + len(at_files or [])
            },
            logiqs_client_info=logiqs_client_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error performing client analysis for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/pricing-model/{case_id}", tags=["Analysis"])
def pricing_model(
    case_id: str,
    product_id: Optional[int] = Query(1, description="Product ID for Logiqs case"),
    include_analysis: Optional[bool] = Query(True, description="Include comprehensive analysis in response")
):
    """
    Get pricing model schema combining Logiqs client data with comprehensive analysis.
    Returns pricing recommendations, client insights, and financial analysis.
    """
    # This will be implemented in the next iteration
    return {"message": "Pricing model endpoint - to be implemented"} 