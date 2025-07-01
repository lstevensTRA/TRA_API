"""
Enhanced Analysis Routes with ML-Enhanced Pattern Learning

This module provides enhanced analysis endpoints that integrate the pattern learning system
while preserving all existing functionality and API responses.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from app.utils.cookies import cookies_exist, get_cookies
from app.services.wi_service import fetch_wi_file_grid
from app.services.wi_service_enhanced import parse_wi_pdfs_enhanced
from app.services.at_service import fetch_at_file_grid, parse_at_pdfs
from app.utils.tps_parser import TPSParser
from app.utils.client_info import extract_client_info_from_logiqs
from app.models.response_models import (
    WIAnalysisResponse, ATAnalysisResponse, ComprehensiveAnalysisResponse, 
    ClientAnalysisResponse, ErrorResponse, WIFormData
)
from app.models.pattern_learning_models import PatternLearningResponse
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

@router.get("/wi/{case_id}/enhanced", tags=["Analysis"], 
           summary="Enhanced WI Analysis with Pattern Learning",
           description="Get enhanced WI analysis with ML-enhanced pattern learning and confidence scoring",
           response_model=WIAnalysisResponse)
def wi_analysis_enhanced(
    case_id: str,
    include_tps_analysis: Optional[bool] = Query(False, description="Include TP/S analysis in response"),
    filing_status: Optional[str] = Query(None, description="Client filing status for TP/S analysis"),
    enable_learning: Optional[bool] = Query(True, description="Enable pattern learning features")
):
    """
    Get enhanced WI analysis with ML-enhanced pattern learning capabilities.
    
    This endpoint provides the same functionality as the standard WI analysis
    but with additional learning metadata, confidence scoring, and pattern performance tracking.
    """
    logger.info(f"🔍 Received enhanced WI analysis request for case_id: {case_id}")
    logger.info(f"🔍 Learning enabled: {enable_learning}")
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
        
        # Parse WI PDFs with enhanced learning capabilities
        logger.info(f"🔍 Starting enhanced PDF parsing for {len(wi_files)} WI files")
        wi_data = parse_wi_pdfs_enhanced(
            wi_files, cookies, case_id, include_tps_analysis, filing_status, enable_learning
        )
        
        logger.info(f"✅ Successfully parsed enhanced WI data for case_id: {case_id}")
        logger.info(f"📊 Summary: {wi_data.get('summary', {}).get('total_years', 0)} years, {wi_data.get('summary', {}).get('total_forms', 0)} forms")
        
        # Extract learning metadata if available
        learning_metadata = wi_data.get('learning_metadata', {})
        if learning_metadata:
            logger.info(f"🧠 Learning metadata: {learning_metadata.get('total_files_processed', 0)} files processed")
            confidence_summary = learning_metadata.get('confidence_summary', {})
            if confidence_summary:
                logger.info(f"📈 Confidence summary: {confidence_summary.get('total_extractions', 0)} extractions, "
                          f"avg confidence: {confidence_summary.get('average_confidence', 0.0):.3f}")
        
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
        
        # Add learning metadata to summary if available
        if learning_metadata:
            summary['learning_metadata'] = learning_metadata
        
        return WIAnalysisResponse(
            summary=summary,
            years_data=years_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting enhanced WI data for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/learning-insights/{case_id}", tags=["Analysis"],
           summary="Get Pattern Learning Insights",
           description="Get insights and recommendations from the pattern learning system",
           response_model=PatternLearningResponse)
def get_learning_insights(case_id: str):
    """
    Get insights and recommendations from the pattern learning system for a specific case.
    
    This endpoint provides pattern learning insights, confidence analysis, and recommendations
    for improving extraction accuracy.
    """
    logger.info(f"🔍 Received learning insights request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    try:
        # Get pattern learning statistics
        from app.services.wi_service_enhanced import get_pattern_learning_statistics
        stats = get_pattern_learning_statistics('WI')
        
        # Generate insights based on statistics
        insights = {
            'case_id': case_id,
            'analysis_timestamp': datetime.now().isoformat(),
            'pattern_performance': stats,
            'recommendations': []
        }
        
        # Generate recommendations based on statistics
        if stats.get('overall_success_rate', 0) < 0.8:
            insights['recommendations'].append({
                'type': 'success_rate',
                'message': 'Overall success rate is below 80%. Consider reviewing low-confidence extractions.',
                'priority': 'high'
            })
        
        if stats.get('average_confidence', 0) < 0.7:
            insights['recommendations'].append({
                'type': 'confidence',
                'message': 'Average confidence is below 70%. Consider implementing pattern suggestions.',
                'priority': 'medium'
            })
        
        if stats.get('suggestions_generated', 0) > 0:
            insights['recommendations'].append({
                'type': 'suggestions',
                'message': f'{stats.get("suggestions_generated", 0)} pattern suggestions available for review.',
                'priority': 'low'
            })
        
        logger.info(f"✅ Successfully generated learning insights for case_id: {case_id}")
        
        return PatternLearningResponse(
            success=True,
            message="Learning insights generated successfully",
            data=insights
        )
        
    except Exception as e:
        logger.error(f"❌ Error generating learning insights for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 