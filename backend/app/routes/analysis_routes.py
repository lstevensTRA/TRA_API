import logging
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, Dict, Any, List
from app.utils.cookies import cookies_exist, get_cookies
from app.services.wi_service import fetch_wi_file_grid, parse_wi_pdfs
from app.services.at_service import fetch_at_file_grid, parse_at_pdfs
from app.utils.tps_parser import TPSParser
from app.utils.client_info import extract_client_info_from_logiqs
from app.models.response_models import (
    WIAnalysisResponse, ATAnalysisResponse, ComprehensiveAnalysisResponse, 
    ClientAnalysisResponse, ErrorResponse, WIFormData, PricingModelResponse, RegexReviewResponse
)
from datetime import datetime
from app.utils.wi_patterns import form_patterns
import re

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
        
        # Parse WI PDFs with new scoped parsing (default) and optional TP/S analysis
        logger.info(f"🔍 Starting scoped PDF parsing for {len(wi_files)} WI files")
        wi_data = parse_wi_pdfs(wi_files, cookies, case_id, include_tps_analysis, filing_status, return_scoped_structure=True)
        
        logger.info(f"✅ Successfully parsed WI data for case_id: {case_id}")
        
        # Process new scoped structure format
        years_data = {}
        total_forms = 0
        total_files = len(wi_data) if isinstance(wi_data, list) else 0
        
        # Group forms by tax year from file metadata
        for file_result in wi_data:
            if not isinstance(file_result, dict):
                continue
                
            file_name = file_result.get('file_name', '')
            tax_year = file_result.get('tax_year')
            forms = file_result.get('forms', [])
            
            logger.info(f"📄 File: {file_name}, Tax Year: {tax_year}, Forms: {len(forms)}")
            
            # Extract year from filename if not in metadata
            if not tax_year:
                year_match = re.search(r'WI\s+(\d{2})', file_name)
                if year_match:
                    year_suffix = year_match.group(1)
                    if int(year_suffix) <= 50:
                        tax_year = f"20{year_suffix}"
                    else:
                        tax_year = f"19{year_suffix}"
                else:
                    year_match = re.search(r"(20\d{2})", file_name)
                    if year_match:
                        tax_year = year_match.group(1)
                    else:
                        tax_year = "Unknown"
            
            # Convert scoped forms to legacy format for compatibility
            for form in forms:
                form_type = form.get('form_type', '')
                fields = form.get('fields', [])
                
                # Find canonical form name
                canonical_form = None
                for k, v in form_patterns.items():
                    if re.search(v['pattern'], form_type, re.IGNORECASE):
                        canonical_form = k
                        break
                
                if not canonical_form:
                    continue
                
                pattern_info = form_patterns[canonical_form]
                
                # Convert fields to legacy format
                fields_data = {}
                for field in fields:
                    field_name = field.get('name', '').replace('_', ' ').title()
                    field_value = field.get('value', '')
                    
                    # Try to find original field name
                    orig_field_name = None
                    for fname in pattern_info.get('fields', {}).keys():
                        if fname.lower().replace(' ', '_') == field.get('name', ''):
                            orig_field_name = fname
                            break
                    
                    if orig_field_name:
                        # Try to cast to float if not a string field
                        try:
                            if orig_field_name in ['Direct Sales Indicator', 'FATCA Filing Requirement', 'Second Notice Indicator']:
                                fields_data[orig_field_name] = field_value
                            else:
                                fields_data[orig_field_name] = float(field_value)
                        except Exception:
                            fields_data[orig_field_name] = field_value
                    else:
                        fields_data[field_name] = field_value
                
                # Calculate income and withholding
                calc = pattern_info.get('calculation', {})
                income = 0
                withholding = 0
                try:
                    if 'Income' in calc and callable(calc['Income']):
                        income = calc['Income'](fields_data)
                    if 'Withholding' in calc and callable(calc['Withholding']):
                        withholding = calc['Withholding'](fields_data)
                except Exception as e:
                    logger.warning(f"⚠️ Error calculating income/withholding for {canonical_form}: {e}")
                
                # Create legacy form format
                form_dict = {
                    'Form': canonical_form,
                    'UniqueID': 'UNKNOWN',  # Would need additional logic to extract
                    'Label': 'E' if canonical_form == 'W-2' else 'P',
                    'Income': income,
                    'Withholding': withholding,
                    'Category': pattern_info.get('category', ''),
                    'Fields': fields_data,
                    'PayerBlurb': '',
                    'Owner': TPSParser.extract_owner_from_filename(file_name),
                    'SourceFile': file_name,
                    'Year': tax_year,
                    'Name': None,
                    'SSN': None
                }
                
                if tax_year not in years_data:
                    years_data[tax_year] = []
                years_data[tax_year].append(form_dict)
                total_forms += 1
        
        # Create summary with proper structure
        summary = {
            'total_years': len(years_data),
            'years_analyzed': list(years_data.keys()),
            'total_forms': total_forms,
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
            # Calculate income by category
            se_income = 0.0
            se_withholding = 0.0
            non_se_income = 0.0
            non_se_withholding = 0.0
            other_income = 0.0
            other_withholding = 0.0
            
            for form in forms:
                form_type = form.get('Form', '')
                income = form.get('Income', 0)
                withholding = form.get('Withholding', 0)
                
                # Categorize by form type
                if form_type == 'W-2':
                    non_se_income += income
                    non_se_withholding += withholding
                elif form_type.startswith('1099'):
                    if form_type in ['1099-MISC', '1099-NEC'] and form.get('Category') == 'Self-Employment':
                        se_income += income
                        se_withholding += withholding
                    else:
                        other_income += income
                        other_withholding += withholding
                else:
                    other_income += income
                    other_withholding += withholding
            
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
            
            # Add to overall totals
            summary['overall_totals']['total_se_income'] += se_income
            summary['overall_totals']['total_non_se_income'] += non_se_income
            summary['overall_totals']['total_other_income'] += other_income
            summary['overall_totals']['total_income'] += total_income
            summary['overall_totals']['estimated_agi'] += total_income
        
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

@router.get("/pricing-model/{case_id}", tags=["Analysis"], response_model=PricingModelResponse)
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

@router.post("/batch/wi-structured", tags=["Analysis"], summary="Batch get structured WI data", description="Get structured WI data for multiple case IDs at once.")
def batch_wi_structured(
    case_ids: list = Body(..., embed=True),
    use_scoped_parsing: bool = Query(False, description="Use scoped parsing (new format) instead of legacy format")
):
    """
    Batch endpoint to get structured WI data for multiple case IDs.
    Input: {"case_ids": ["caseid1", "caseid2", ...]}
    Output: {"caseid1": {...}, "caseid2": {...}, ...}
    
    If use_scoped_parsing=True, returns the new scoped parsing format with:
    - File-level metadata
    - Form-specific blocks
    - Source line numbers
    - Confidence scoring
    """
    logger.info(f"🔍 Batch WI structured request for {len(case_ids)} cases, use_scoped_parsing: {use_scoped_parsing}")
    
    results = {}
    for case_id in case_ids:
        try:
            if use_scoped_parsing:
                # Use new scoped parsing
                from app.services.wi_service import fetch_wi_file_grid, download_wi_pdf, parse_transcript_scoped
                from app.utils.pdf_utils import extract_text_from_pdf
                from app.utils.cookies import get_cookies
                
                cookies = get_cookies()
                wi_files = fetch_wi_file_grid(case_id, cookies)
                
                if not wi_files:
                    results[case_id] = {"error": "No WI files found"}
                    continue
                
                scoped_results = []
                for wi_file in wi_files:
                    try:
                        file_name = wi_file["FileName"]
                        case_doc_id = wi_file["CaseDocumentID"]
                        
                        # Download and extract text
                        pdf_bytes = download_wi_pdf(case_doc_id, case_id, cookies)
                        if not pdf_bytes:
                            continue
                        
                        text = extract_text_from_pdf(pdf_bytes)
                        if not text:
                            continue
                        
                        # Use scoped parser
                        scoped_result = parse_transcript_scoped(text, file_name)
                        scoped_results.append(scoped_result)
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing WI file {file_name}: {str(e)}")
                        continue
                
                results[case_id] = {
                    "case_id": case_id,
                    "scoped_results": scoped_results,
                    "total_files_processed": len(scoped_results)
                }
            else:
                # Use legacy parsing
                results[case_id] = wi_analysis(case_id)
        except Exception as e:
            results[case_id] = {"error": str(e)}
    return results

@router.post("/regex-review/batch/wi", tags=["Regex Review"], summary="Batch WI regex review", description="Review regex extraction for WI forms across multiple cases using new scoped parsing.", response_model=List[RegexReviewResponse])
async def batch_regex_review_wi(case_ids: list = Body(..., embed=True)):
    """
    For each case, fetch raw WI text and structured WI data using new scoped parsing, compare regex extraction, and suggest improvements.
    Returns a JSON report for frontend review.
    """
    from app.services.wi_service import fetch_wi_file_grid, download_wi_pdf
    from app.utils.pdf_utils import extract_text_from_pdf
    from app.utils.cookies import get_cookies
    
    results = {}
    
    # 1. Get all raw text in batch
    raw_texts = {}
    cookies = get_cookies()
    
    for case_id in case_ids:
        try:
            wi_files = fetch_wi_file_grid(case_id, cookies)
            if not wi_files:
                raw_texts[case_id] = ""
                continue
            
            all_text = []
            for wi_file in wi_files:
                try:
                    case_doc_id = wi_file.get("CaseDocumentID")
                    if not case_doc_id:
                        continue
                    
                    pdf_bytes = download_wi_pdf(case_doc_id, case_id, cookies)
                    if not pdf_bytes:
                        continue
                    
                    text = extract_text_from_pdf(pdf_bytes)
                    if text:
                        all_text.append(text)
                except Exception as e:
                    logger.error(f"Error processing WI file for case {case_id}: {str(e)}")
                    continue
            
            raw_texts[case_id] = "\n".join(all_text)
        except Exception as e:
            logger.error(f"Error getting raw text for case {case_id}: {str(e)}")
            raw_texts[case_id] = ""
    
    # 2. Get all structured WI data in batch using new scoped parsing
    batch_structured = batch_wi_structured(case_ids, use_scoped_parsing=True)
    
    # 3. For each case, compare fields using scoped parsing results
    for case_id in case_ids:
        case_report = []
        raw_text = raw_texts.get(case_id, "")
        structured = batch_structured.get(case_id, {})
        
        # Handle new scoped structure format
        scoped_results = structured.get("scoped_results", [])
        
        for file_result in scoped_results:
            if not isinstance(file_result, dict):
                continue
                
            file_name = file_result.get('file_name', '')
            forms = file_result.get('forms', [])
            
            for form_idx, form in enumerate(forms):
                if not isinstance(form, dict):
                    continue
                    
                form_type = form.get('form_type', '')
                fields = form.get('fields', [])
                
                # Find canonical form name
                canonical_form = None
                for k, v in form_patterns.items():
                    if re.search(v['pattern'], form_type, re.IGNORECASE):
                        canonical_form = k
                        break
                
                if not canonical_form:
                    continue
                
                # Process each field from scoped parsing
                for field in fields:
                    if not isinstance(field, dict):
                        continue
                        
                    field_name = field.get('name', '').replace('_', ' ').title()
                    field_value = field.get('value', '')
                    source_line = field.get('source_line', '')
                    confidence = field.get('confidence_score', 0)
                    
                    # Try to find original field name in patterns
                    orig_field_name = None
                    for fname in form_patterns[canonical_form].get('fields', {}).keys():
                        if fname.lower().replace(' ', '_') == field.get('name', ''):
                            orig_field_name = fname
                            break
                    
                    if not orig_field_name:
                        continue
                    
                    current_regex = form_patterns[canonical_form]['fields'].get(orig_field_name, '')
                    
                    # Find matches in the source line (scoped approach)
                    match_info = []
                    found_expected = False
                    
                    if current_regex and source_line:
                        try:
                            for match in re.finditer(current_regex, source_line, re.IGNORECASE):
                                captured = match.group(1) if match.groups() else match.group(0)
                                is_expected = captured.strip('$,') == str(field_value).strip('$,')
                                if is_expected:
                                    found_expected = True
                                match_info.append({
                                    'full_match': match.group(0),
                                    'captured': captured,
                                    'position': match.start(),
                                    'is_expected': is_expected,
                                    'context': source_line,
                                    'source_line': source_line
                                })
                        except re.error as e:
                            match_info.append({
                                'error': f"Regex error: {str(e)}",
                                'context': source_line
                            })
                    
                    # Also check if value appears in the broader raw text (for debugging)
                    raw_text_matches = []
                    if str(field_value) in raw_text:
                        for match in re.finditer(re.escape(str(field_value)), raw_text):
                            raw_text_matches.append({
                                'position': match.start(),
                                'context': raw_text[max(0, match.start()-50):match.end()+50]
                            })
                    
                    # Suggest improved regex
                    suggestions = []
                    if not found_expected and source_line:
                        # Suggest pattern based on source line
                        if str(field_value) in source_line:
                            line_pattern = re.escape(source_line.strip()).replace(re.escape(str(field_value)), r'([\\d,.]+)')
                            suggestions.append({
                                'pattern': line_pattern,
                                'description': 'Pattern from source line'
                            })
                        
                        # Generic suggestions based on field type
                        if 'income' in orig_field_name.lower() or 'wage' in orig_field_name.lower():
                            suggestions.append({
                                'pattern': f'{re.escape(orig_field_name)}[:\\s]*\\$?([\\d,.]+)',
                                'description': 'Generic income field pattern'
                            })
                        elif 'tax' in orig_field_name.lower() or 'withheld' in orig_field_name.lower():
                            suggestions.append({
                                'pattern': f'{re.escape(orig_field_name)}[:\\s]*\\$?([\\d,.]+)',
                                'description': 'Generic tax field pattern'
                            })
                    
                    # Copy-paste ready code
                    wi_patterns_snippet = f'    "{orig_field_name}": r"{current_regex}"'
                    
                    case_report.append({
                        'case_id': case_id,
                        'file_name': file_name,
                        'form_type': canonical_form,
                        'form_index': form_idx,
                        'field': orig_field_name,
                        'extracted_value': str(field_value),
                        'current_regex': current_regex,
                        'source_line': source_line,
                        'confidence_score': confidence,
                        'matches': match_info,
                        'raw_text_matches': raw_text_matches,
                        'found_expected': found_expected,
                        'suggestions': suggestions,
                        'wi_patterns_snippet': wi_patterns_snippet
                    })
        
        results[case_id] = case_report
    
    return results 