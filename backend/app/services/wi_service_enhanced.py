"""
Enhanced WI Service with ML-Enhanced Pattern Learning

This module wraps the existing WI parsing functionality with learning capabilities
while preserving all existing behavior and API responses.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from app.services.wi_service import parse_wi_pdfs as original_parse_wi_pdfs
from app.utils.pattern_learning import pattern_learning_system
from app.models.pattern_learning_models import PatternType, EnhancedExtractionResult

logger = logging.getLogger(__name__)

def parse_wi_pdfs_enhanced(wi_files: List[Dict[str, Any]], cookies: dict, case_id: str, 
                          include_tps_analysis: bool = False, filing_status: str = None,
                          enable_learning: bool = True) -> Dict[str, Any]:
    """
    Enhanced WI PDF parsing with ML-enhanced pattern learning
    
    This function wraps the original parse_wi_pdfs function and adds:
    - Confidence scoring for each extraction
    - Learning metadata for user feedback
    - Pattern performance tracking
    - Enhanced extraction results
    
    Args:
        wi_files: List of WI file information
        cookies: Authentication cookies
        case_id: Case ID for tracking
        include_tps_analysis: Whether to include TP/S analysis
        filing_status: Client filing status
        enable_learning: Whether to enable learning features
        
    Returns:
        Enhanced WI data with learning metadata
    """
    logger.info(f"🔍 Starting enhanced WI parsing for case_id: {case_id}")
    logger.info(f"🔍 Learning enabled: {enable_learning}")
    
    # Get original parsing results
    original_result = original_parse_wi_pdfs(wi_files, cookies, case_id, include_tps_analysis, filing_status)
    
    if not enable_learning:
        logger.info("ℹ️ Learning disabled, returning original results")
        return original_result
    
    # Enhance results with learning metadata
    enhanced_result = _enhance_wi_results(original_result, case_id, wi_files)
    
    logger.info(f"✅ Enhanced WI parsing completed for case_id: {case_id}")
    return enhanced_result

def _enhance_wi_results(original_result: Dict[str, Any], case_id: str, 
                       wi_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Enhance original WI results with learning metadata
    
    Args:
        original_result: Original parsing results
        case_id: Case ID for tracking
        wi_files: List of WI file information
        
    Returns:
        Enhanced results with learning metadata
    """
    enhanced_result = original_result.copy()
    
    # Add learning metadata section
    enhanced_result['learning_metadata'] = {
        'case_id': case_id,
        'processing_timestamp': datetime.now().isoformat(),
        'total_files_processed': len(wi_files),
        'extraction_results': [],
        'pattern_performance': {},
        'confidence_summary': {}
    }
    
    # Process each year's data
    for year_key, year_data in original_result.items():
        if year_key.isdigit() and isinstance(year_data, list):
            enhanced_year_data = []
            
            for form_data in year_data:
                if isinstance(form_data, dict):
                    enhanced_form = _enhance_form_data(form_data, case_id, year_key)
                    enhanced_year_data.append(enhanced_form)
                else:
                    enhanced_year_data.append(form_data)
            
            enhanced_result[year_key] = enhanced_year_data
    
    # Add pattern performance statistics
    stats = pattern_learning_system.get_pattern_statistics(PatternType.WI)
    enhanced_result['learning_metadata']['pattern_performance'] = stats
    
    # Add confidence summary
    confidence_summary = _calculate_confidence_summary(enhanced_result)
    enhanced_result['learning_metadata']['confidence_summary'] = confidence_summary
    
    return enhanced_result

def _enhance_form_data(form_data: Dict[str, Any], case_id: str, year: str) -> Dict[str, Any]:
    """
    Enhance individual form data with learning metadata
    
    Args:
        form_data: Original form data
        case_id: Case ID for tracking
        year: Tax year
        
    Returns:
        Enhanced form data
    """
    enhanced_form = form_data.copy()
    
    # Add learning metadata to form
    enhanced_form['learning_metadata'] = {
        'extraction_id': None,
        'confidence_score': 0.0,
        'confidence_level': 'unknown',
        'pattern_used': None,
        'field_extractions': {}
    }
    
    # Process each field extraction
    if 'Fields' in form_data and isinstance(form_data['Fields'], dict):
        enhanced_fields = {}
        
        for field_name, field_value in form_data['Fields'].items():
            if field_value is not None and str(field_value).strip():
                # Generate pattern ID
                form_name = form_data.get('Form', 'Unknown')
                pattern_id = f"WI_{form_name}_{field_name}"
                
                # Get extraction metadata (simulated since we don't have original text)
                confidence_score = _estimate_confidence_score(field_name, field_value, form_name)
                extraction_id = f"{case_id}_{year}_{form_name}_{field_name}_{hash(str(field_value))}"
                
                enhanced_fields[field_name] = {
                    'value': field_value,
                    'confidence_score': confidence_score,
                    'confidence_level': _get_confidence_level(confidence_score),
                    'pattern_id': pattern_id,
                    'extraction_id': extraction_id
                }
                
                # Record extraction in learning system
                _record_extraction_in_learning_system(
                    pattern_id, field_name, field_value, confidence_score, 
                    extraction_id, case_id, f"{year}_{form_name}"
                )
        
        enhanced_form['learning_metadata']['field_extractions'] = enhanced_fields
    
    return enhanced_form

def _estimate_confidence_score(field_name: str, field_value: Any, form_name: str) -> float:
    """
    Estimate confidence score for a field extraction
    
    Args:
        field_name: Name of the field
        field_value: Extracted value
        form_name: Name of the form
        
    Returns:
        Estimated confidence score (0.0-1.0)
    """
    if not field_value:
        return 0.0
    
    # Base confidence from field type
    field_name_lower = field_name.lower()
    if any(keyword in field_name_lower for keyword in ['income', 'wages', 'compensation']):
        base_confidence = 0.8
    elif any(keyword in field_name_lower for keyword in ['withholding', 'tax']):
        base_confidence = 0.8
    elif any(keyword in field_name_lower for keyword in ['ein', 'fin', 'identification']):
        base_confidence = 0.7
    else:
        base_confidence = 0.6
    
    # Value validation factor
    try:
        if isinstance(field_value, (int, float)):
            value_factor = 0.9
        elif isinstance(field_value, str):
            # Check if it looks like a number
            if re.match(r'^[\d,\.]+$', field_value.replace('$', '')):
                value_factor = 0.9
            elif re.match(r'^[\d\-]+$', field_value):  # EIN/FIN pattern
                value_factor = 0.8
            else:
                value_factor = 0.7
        else:
            value_factor = 0.5
    except:
        value_factor = 0.3
    
    # Form reliability factor (some forms are more reliable than others)
    form_reliability = {
        'W-2': 0.9,
        '1099-MISC': 0.8,
        '1099-NEC': 0.8,
        '1099-INT': 0.8,
        '1099-DIV': 0.8,
        '1099-R': 0.8
    }
    form_factor = form_reliability.get(form_name, 0.7)
    
    # Combine factors
    confidence = (base_confidence * 0.4 + value_factor * 0.3 + form_factor * 0.3)
    return min(1.0, max(0.0, confidence))

def _get_confidence_level(confidence_score: float) -> str:
    """Convert confidence score to confidence level"""
    if confidence_score >= 0.8:
        return 'high'
    elif confidence_score >= 0.6:
        return 'medium'
    elif confidence_score >= 0.3:
        return 'low'
    else:
        return 'unknown'

def _record_extraction_in_learning_system(pattern_id: str, field_name: str, 
                                        field_value: Any, confidence_score: float,
                                        extraction_id: str, case_id: str, document_id: str):
    """
    Record extraction in the learning system
    
    Args:
        pattern_id: Pattern ID used for extraction
        field_name: Field name extracted
        field_value: Extracted value
        confidence_score: Confidence score
        extraction_id: Unique extraction ID
        case_id: Case ID
        document_id: Document ID
    """
    try:
        # This would normally record the extraction in the learning system
        # For now, we'll just log it
        logger.debug(f"📝 Recording extraction: {pattern_id} -> {field_name} = {field_value} (confidence: {confidence_score:.2f})")
        
    except Exception as e:
        logger.warning(f"⚠️ Error recording extraction in learning system: {e}")

def _calculate_confidence_summary(enhanced_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate confidence summary for all extractions
    
    Args:
        enhanced_result: Enhanced WI results
        
    Returns:
        Confidence summary statistics
    """
    all_confidence_scores = []
    confidence_by_level = {'high': 0, 'medium': 0, 'low': 0, 'unknown': 0}
    
    # Collect confidence scores from all forms
    for year_key, year_data in enhanced_result.items():
        if year_key.isdigit() and isinstance(year_data, list):
            for form_data in year_data:
                if isinstance(form_data, dict) and 'learning_metadata' in form_data:
                    field_extractions = form_data['learning_metadata'].get('field_extractions', {})
                    
                    for field_name, field_data in field_extractions.items():
                        if isinstance(field_data, dict):
                            confidence_score = field_data.get('confidence_score', 0.0)
                            confidence_level = field_data.get('confidence_level', 'unknown')
                            
                            all_confidence_scores.append(confidence_score)
                            confidence_by_level[confidence_level] += 1
    
    # Calculate summary statistics
    if all_confidence_scores:
        avg_confidence = sum(all_confidence_scores) / len(all_confidence_scores)
        min_confidence = min(all_confidence_scores)
        max_confidence = max(all_confidence_scores)
    else:
        avg_confidence = min_confidence = max_confidence = 0.0
    
    return {
        'total_extractions': len(all_confidence_scores),
        'average_confidence': round(avg_confidence, 3),
        'min_confidence': round(min_confidence, 3),
        'max_confidence': round(max_confidence, 3),
        'confidence_distribution': confidence_by_level,
        'high_confidence_rate': round(confidence_by_level['high'] / max(len(all_confidence_scores), 1), 3)
    }

def get_enhanced_extraction_feedback(extraction_id: str) -> Optional[Dict[str, Any]]:
    """
    Get feedback information for a specific extraction
    
    Args:
        extraction_id: Extraction ID to get feedback for
        
    Returns:
        Feedback information or None if not found
    """
    try:
        # This would normally query the learning system
        # For now, return a placeholder
        return {
            'extraction_id': extraction_id,
            'feedback_available': False,
            'user_feedback': None,
            'pattern_suggestions': []
        }
    except Exception as e:
        logger.error(f"❌ Error getting extraction feedback: {e}")
        return None

def provide_extraction_feedback(extraction_id: str, is_correct: bool, 
                              correct_value: Optional[str] = None,
                              comments: Optional[str] = None) -> bool:
    """
    Provide feedback for a specific extraction
    
    Args:
        extraction_id: Extraction ID to provide feedback for
        is_correct: Whether the extraction was correct
        correct_value: Correct value if extraction was wrong
        comments: Additional comments
        
    Returns:
        True if feedback was recorded successfully
    """
    try:
        success = pattern_learning_system.provide_feedback(
            extraction_id=extraction_id,
            is_correct=is_correct,
            correct_value=correct_value,
            comments=comments
        )
        
        if success:
            logger.info(f"✅ Feedback recorded for extraction {extraction_id}")
        else:
            logger.warning(f"⚠️ Failed to record feedback for extraction {extraction_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error providing extraction feedback: {e}")
        return False

def get_pattern_learning_statistics(pattern_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Get pattern learning statistics
    
    Args:
        pattern_type: Optional pattern type filter (WI/AT/TI)
        
    Returns:
        Pattern learning statistics
    """
    try:
        if pattern_type and pattern_type.upper() == 'WI':
            stats = pattern_learning_system.get_pattern_statistics(PatternType.WI)
        else:
            stats = pattern_learning_system.get_pattern_statistics()
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error getting pattern learning statistics: {e}")
        return {}

def get_pattern_suggestions(pattern_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get pattern suggestions
    
    Args:
        pattern_id: Optional pattern ID filter
        
    Returns:
        List of pattern suggestions
    """
    try:
        suggestions = pattern_learning_system.get_pattern_suggestions(pattern_id)
        return [suggestion.dict() for suggestion in suggestions]
        
    except Exception as e:
        logger.error(f"❌ Error getting pattern suggestions: {e}")
        return []

def implement_pattern_suggestion(suggestion_id: str) -> bool:
    """
    Implement a pattern suggestion
    
    Args:
        suggestion_id: Suggestion ID to implement
        
    Returns:
        True if suggestion was implemented successfully
    """
    try:
        success = pattern_learning_system.implement_suggestion(suggestion_id)
        
        if success:
            logger.info(f"✅ Implemented pattern suggestion {suggestion_id}")
        else:
            logger.warning(f"⚠️ Failed to implement pattern suggestion {suggestion_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error implementing pattern suggestion: {e}")
        return False 