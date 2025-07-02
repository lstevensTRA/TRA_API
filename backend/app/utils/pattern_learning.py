"""
ML-Enhanced Pattern Learning System for IRS Transcript Parsers

This module provides a learning layer that wraps existing regex patterns
with confidence scoring, performance tracking, and adaptive improvements
while preserving all existing functionality.
"""

import re
import uuid
import logging
import json
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
# import tensorflow as tf
# from tensorflow import keras

from app.models.pattern_learning_models import (
    PatternType, FieldType, ConfidenceLevel, PatternPerformance, 
    ExtractionResult, PatternSuggestion, UserFeedback
)

logger = logging.getLogger(__name__)

class PatternLearningSystem:
    """
    ML-enhanced pattern learning system that wraps existing regex patterns
    with confidence scoring and adaptive learning capabilities.
    """
    
    def __init__(self):
        self.pattern_performance: Dict[str, PatternPerformance] = {}
        self.extraction_results: Dict[str, ExtractionResult] = {}
        self.user_feedback: Dict[str, UserFeedback] = {}
        self.pattern_suggestions: Dict[str, PatternSuggestion] = {}
        
        # ML models for confidence scoring
        self.confidence_model = None
        self.similarity_model = None
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        
        # Initialize the system
        self._initialize_models()
        self._load_existing_patterns()
    
    def _initialize_models(self):
        """Initialize ML models for confidence scoring and pattern learning"""
        logger.warning("⚠️ TensorFlow is disabled. ML models will not be initialized.")
        self.confidence_model = None
        # self.similarity_model = None
        # self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        # self._load_existing_patterns()
    
    def _load_existing_patterns(self):
        """Load existing regex patterns from the current system"""
        try:
            from app.utils.wi_patterns import form_patterns
            
            # Load WI patterns
            for form_name, pattern_info in form_patterns.items():
                for field_name, regex_pattern in pattern_info.get('fields', {}).items():
                    if regex_pattern:
                        pattern_id = f"WI_{form_name}_{field_name}"
                        self._register_pattern(
                            pattern_id=pattern_id,
                            pattern_type=PatternType.WI,
                            form_name=form_name,
                            field_name=field_name,
                            original_regex=regex_pattern,
                            field_type=self._determine_field_type(field_name)
                        )
            
            logger.info(f"✅ Loaded {len(self.pattern_performance)} existing patterns")
            
        except Exception as e:
            logger.error(f"❌ Error loading existing patterns: {e}")
    
    def _determine_field_type(self, field_name: str) -> FieldType:
        """Determine the field type based on field name"""
        field_name_lower = field_name.lower()
        
        if any(keyword in field_name_lower for keyword in ['income', 'wages', 'compensation', 'dividends', 'interest']):
            return FieldType.INCOME
        elif any(keyword in field_name_lower for keyword in ['withholding', 'tax withheld']):
            return FieldType.WITHHOLDING
        elif any(keyword in field_name_lower for keyword in ['ein', 'fin', 'identification']):
            return FieldType.IDENTIFIER
        elif any(keyword in field_name_lower for keyword in ['date', 'year']):
            return FieldType.DATE
        elif any(keyword in field_name_lower for keyword in ['status', 'filing']):
            return FieldType.STATUS
        elif any(keyword in field_name_lower for keyword in ['amount', 'balance']):
            return FieldType.AMOUNT
        else:
            return FieldType.TEXT
    
    def _register_pattern(self, pattern_id: str, pattern_type: PatternType, 
                         form_name: str, field_name: str, original_regex: str, 
                         field_type: FieldType):
        """Register a new pattern in the learning system"""
        if pattern_id not in self.pattern_performance:
            self.pattern_performance[pattern_id] = PatternPerformance(
                pattern_id=pattern_id,
                pattern_type=pattern_type,
                form_name=form_name,
                field_name=field_name,
                field_type=field_type,
                original_regex=original_regex,
                enhanced_regex=None,
                success_count=0,
                failure_count=0,
                total_attempts=0,
                success_rate=0.0,
                average_confidence=0.0,
                last_updated=datetime.now(),
                is_active=True
            )
    
    def extract_with_learning(self, text: str, pattern_id: str, case_id: str, 
                            document_id: str, context_window: int = 100) -> Tuple[Optional[str], float, str]:
        """
        Extract value using pattern with learning capabilities
        
        Args:
            text: Text to extract from
            pattern_id: Pattern ID to use
            case_id: Case ID for tracking
            document_id: Document ID for tracking
            context_window: Number of characters around match for context
            
        Returns:
            Tuple of (extracted_value, confidence_score, extraction_id)
        """
        if pattern_id not in self.pattern_performance:
            logger.warning(f"⚠️ Pattern {pattern_id} not found in learning system")
            return None, 0.0, ""
        
        pattern_info = self.pattern_performance[pattern_id]
        regex_pattern = pattern_info.enhanced_regex or pattern_info.original_regex
        
        # Perform extraction
        match = re.search(regex_pattern, text, re.IGNORECASE)
        extracted_value = match.group(1) if match else None
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            text, pattern_id, extracted_value, match
        )
        
        # Generate extraction ID
        extraction_id = str(uuid.uuid4())
        
        # Determine success (basic heuristic - can be improved with user feedback)
        success = extracted_value is not None and len(str(extracted_value).strip()) > 0
        
        # Get context text
        context_text = ""
        if match:
            start = max(0, match.start() - context_window)
            end = min(len(text), match.end() + context_window)
            context_text = text[start:end]
        
        # Record extraction result
        extraction_result = ExtractionResult(
            extraction_id=extraction_id,
            case_id=case_id,
            pattern_id=pattern_id,
            document_id=document_id,
            field_name=pattern_info.field_name,
            extracted_value=extracted_value,
            expected_value=None,
            confidence_score=confidence_score,
            confidence_level=self._get_confidence_level(confidence_score),
            success=success,
            user_feedback=None,
            feedback_timestamp=None,
            extraction_timestamp=datetime.now(),
            context_text=context_text
        )
        
        self.extraction_results[extraction_id] = extraction_result
        
        # Update pattern performance
        self._update_pattern_performance(pattern_id, success, confidence_score)
        
        return extracted_value, confidence_score, extraction_id
    
    def _calculate_confidence_score(self, text: str, pattern_id: str, 
                                  extracted_value: Optional[str], match) -> float:
        """Calculate confidence score for extraction result"""
        if not extracted_value:
            return 0.0
        
        # Base confidence from pattern performance
        pattern_info = self.pattern_performance[pattern_id]
        base_confidence = pattern_info.success_rate if pattern_info.total_attempts > 0 else 0.5
        
        # Pattern complexity factor (simpler patterns get higher confidence)
        regex_complexity = len(pattern_info.original_regex) / 100.0
        complexity_factor = max(0.1, 1.0 - regex_complexity)
        
        # Value validation factor
        value_factor = self._validate_extracted_value(extracted_value, pattern_info.field_type)
        
        # Context similarity factor
        context_factor = self._calculate_context_similarity(text, pattern_id)
        
        # Combine factors
        confidence = (
            base_confidence * 0.4 +
            complexity_factor * 0.2 +
            value_factor * 0.2 +
            context_factor * 0.2
        )
        
        return min(1.0, max(0.0, confidence))
    
    def _validate_extracted_value(self, value: str, field_type: FieldType) -> float:
        """Validate extracted value based on field type"""
        if not value:
            return 0.0
        
        try:
            if field_type == FieldType.INCOME or field_type == FieldType.WITHHOLDING:
                # Should be numeric
                float(value.replace(',', '').replace('$', ''))
                return 0.9
            elif field_type == FieldType.IDENTIFIER:
                # Should contain digits and possibly dashes
                if re.search(r'\d', value):
                    return 0.8
                return 0.3
            elif field_type == FieldType.DATE:
                # Should contain date-like patterns
                if re.search(r'\d{4}', value) or re.search(r'\d{1,2}[/-]\d{1,2}', value):
                    return 0.8
                return 0.3
            elif field_type == FieldType.AMOUNT:
                # Should be numeric
                float(value.replace(',', '').replace('$', ''))
                return 0.9
            else:
                # Text fields - basic validation
                return 0.7 if len(value.strip()) > 0 else 0.0
        except (ValueError, AttributeError):
            return 0.1
    
    def _calculate_context_similarity(self, text: str, pattern_id: str) -> float:
        """Calculate similarity between current text and historical successful extractions"""
        try:
            # Get historical successful extractions for this pattern
            successful_extractions = [
                result for result in self.extraction_results.values()
                if result.pattern_id == pattern_id and result.success
            ]
            
            if not successful_extractions:
                return 0.5  # Default similarity if no history
            
            # Extract context texts
            context_texts = [ex.context_text for ex in successful_extractions if ex.context_text]
            
            if not context_texts:
                return 0.5
            
            # Calculate TF-IDF vectors
            all_texts = context_texts + [text[:1000]]  # Limit text length
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            
            # Calculate similarity with historical contexts
            current_vector = tfidf_matrix[-1:]
            historical_vectors = tfidf_matrix[:-1]
            
            similarities = cosine_similarity(current_vector, historical_vectors)[0]
            avg_similarity = np.mean(similarities)
            
            return float(avg_similarity)
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculating context similarity: {e}")
            return 0.5
    
    def _get_confidence_level(self, confidence_score: float) -> ConfidenceLevel:
        """Convert confidence score to confidence level"""
        if confidence_score >= 0.8:
            return ConfidenceLevel.HIGH
        elif confidence_score >= 0.6:
            return ConfidenceLevel.MEDIUM
        elif confidence_score >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.UNKNOWN
    
    def _update_pattern_performance(self, pattern_id: str, success: bool, confidence_score: float):
        """Update pattern performance statistics"""
        if pattern_id not in self.pattern_performance:
            return
        
        pattern = self.pattern_performance[pattern_id]
        pattern.total_attempts += 1
        
        if success:
            pattern.success_count += 1
        else:
            pattern.failure_count += 1
        
        # Update success rate
        pattern.success_rate = pattern.success_count / pattern.total_attempts
        
        # Update average confidence
        total_confidence = pattern.average_confidence * (pattern.total_attempts - 1) + confidence_score
        pattern.average_confidence = total_confidence / pattern.total_attempts
        
        pattern.last_updated = datetime.now()
    
    def provide_feedback(self, extraction_id: str, is_correct: bool, 
                        correct_value: Optional[str] = None, 
                        comments: Optional[str] = None, 
                        user_id: Optional[str] = None) -> bool:
        """
        Provide user feedback on an extraction result
        
        Args:
            extraction_id: ID of the extraction to provide feedback for
            is_correct: Whether the extraction was correct
            correct_value: Correct value if extraction was wrong
            comments: Additional comments
            user_id: ID of user providing feedback
            
        Returns:
            True if feedback was recorded successfully
        """
        if extraction_id not in self.extraction_results:
            logger.warning(f"⚠️ Extraction ID {extraction_id} not found")
            return False
        
        extraction = self.extraction_results[extraction_id]
        
        # Create feedback record
        feedback = UserFeedback(
            feedback_id=str(uuid.uuid4()),
            extraction_id=extraction_id,
            case_id=extraction.case_id,
            user_id=user_id,
            is_correct=is_correct,
            correct_value=correct_value,
            comments=comments,
            feedback_timestamp=datetime.now()
        )
        
        self.user_feedback[feedback.feedback_id] = feedback
        
        # Update extraction result
        extraction.user_feedback = "correct" if is_correct else "incorrect"
        extraction.feedback_timestamp = feedback.feedback_timestamp
        if not is_correct and correct_value:
            extraction.expected_value = correct_value
        
        # Update pattern performance based on feedback
        self._update_pattern_performance_from_feedback(extraction.pattern_id, is_correct)
        
        # Generate pattern suggestions if needed
        if not is_correct:
            self._generate_pattern_suggestions(extraction, correct_value)
        
        logger.info(f"✅ Feedback recorded for extraction {extraction_id}")
        return True
    
    def _update_pattern_performance_from_feedback(self, pattern_id: str, is_correct: bool):
        """Update pattern performance based on user feedback"""
        if pattern_id not in self.pattern_performance:
            return
        
        pattern = self.pattern_performance[pattern_id]
        
        # Adjust success/failure counts based on feedback
        if is_correct:
            pattern.success_count += 1
        else:
            pattern.failure_count += 1
        
        # Recalculate success rate
        pattern.success_rate = pattern.success_count / (pattern.success_count + pattern.failure_count)
        pattern.last_updated = datetime.now()
    
    def _generate_pattern_suggestions(self, extraction: ExtractionResult, correct_value: str):
        """Generate pattern suggestions for failed extractions"""
        if not extraction.context_text or not correct_value:
            return
        
        pattern_info = self.pattern_performance[extraction.pattern_id]
        
        # Generate alternative patterns based on context
        suggestions = self._generate_alternative_patterns(
            extraction.context_text, correct_value, pattern_info.original_regex
        )
        
        for i, suggested_regex in enumerate(suggestions):
            suggestion_id = f"{extraction.pattern_id}_suggestion_{i}"
            
            suggestion = PatternSuggestion(
                suggestion_id=suggestion_id,
                pattern_id=extraction.pattern_id,
                suggested_regex=suggested_regex,
                confidence_score=0.6,  # Moderate confidence for suggestions
                reasoning=f"Generated from failed extraction with correct value: {correct_value}",
                test_cases=[extraction.context_text],
                created_at=datetime.now(),
                is_implemented=False
            )
            
            self.pattern_suggestions[suggestion_id] = suggestion
    
    def _generate_alternative_patterns(self, context: str, correct_value: str, 
                                     original_regex: str) -> List[str]:
        """Generate alternative regex patterns for failed extractions"""
        suggestions = []
        
        # Escape special characters in correct value
        escaped_value = re.escape(correct_value)
        
        # Pattern 1: Look for the value with flexible spacing
        pattern1 = rf'\b{escaped_value}\b'
        suggestions.append(pattern1)
        
        # Pattern 2: Look for common prefixes/suffixes
        common_prefixes = ['amount', 'value', 'total', 'income', 'withholding']
        for prefix in common_prefixes:
            pattern2 = rf'{prefix}[:\s]*\$?{escaped_value}'
            suggestions.append(pattern2)
        
        # Pattern 3: Look for the value in context with surrounding text
        if len(context) > 50:
            # Find position of correct value in context
            value_pos = context.find(correct_value)
            if value_pos >= 0:
                start = max(0, value_pos - 20)
                end = min(len(context), value_pos + len(correct_value) + 20)
                surrounding_text = context[start:end]
                
                # Create pattern from surrounding text
                pattern3 = rf'{re.escape(surrounding_text[:10])}.*?{escaped_value}.*?{re.escape(surrounding_text[-10:])}'
                suggestions.append(pattern3)
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def get_pattern_statistics(self, pattern_type: Optional[PatternType] = None) -> Dict[str, Any]:
        """Get statistics for patterns"""
        stats = {
            'total_patterns': len(self.pattern_performance),
            'active_patterns': sum(1 for p in self.pattern_performance.values() if p.is_active),
            'total_extractions': len(self.extraction_results),
            'successful_extractions': sum(1 for e in self.extraction_results.values() if e.success),
            'patterns_with_feedback': len(set(e.pattern_id for e in self.extraction_results.values() if e.user_feedback)),
            'suggestions_generated': len(self.pattern_suggestions),
            'suggestions_implemented': sum(1 for s in self.pattern_suggestions.values() if s.is_implemented)
        }
        
        if stats['total_extractions'] > 0:
            stats['overall_success_rate'] = stats['successful_extractions'] / stats['total_extractions']
        else:
            stats['overall_success_rate'] = 0.0
        
        if stats['total_extractions'] > 0:
            avg_confidence = sum(e.confidence_score for e in self.extraction_results.values()) / stats['total_extractions']
            stats['average_confidence'] = avg_confidence
        else:
            stats['average_confidence'] = 0.0
        
        # Filter by pattern type if specified
        if pattern_type:
            filtered_patterns = {k: v for k, v in self.pattern_performance.items() if v.pattern_type == pattern_type}
            stats['pattern_type'] = pattern_type.value
            stats['total_patterns'] = len(filtered_patterns)
            stats['active_patterns'] = sum(1 for p in filtered_patterns.values() if p.is_active)
        
        return stats
    
    def get_pattern_suggestions(self, pattern_id: Optional[str] = None) -> List[PatternSuggestion]:
        """Get pattern suggestions"""
        if pattern_id:
            return [s for s in self.pattern_suggestions.values() if s.pattern_id == pattern_id]
        else:
            return list(self.pattern_suggestions.values())
    
    def implement_suggestion(self, suggestion_id: str) -> bool:
        """Implement a pattern suggestion"""
        if suggestion_id not in self.pattern_suggestions:
            return False
        
        suggestion = self.pattern_suggestions[suggestion_id]
        pattern_id = suggestion.pattern_id
        
        if pattern_id not in self.pattern_performance:
            return False
        
        # Update pattern with enhanced regex
        self.pattern_performance[pattern_id].enhanced_regex = suggestion.suggested_regex
        self.pattern_performance[pattern_id].last_updated = datetime.now()
        
        # Mark suggestion as implemented
        suggestion.is_implemented = True
        
        logger.info(f"✅ Implemented suggestion {suggestion_id} for pattern {pattern_id}")
        return True

    def train(self, training_data: list, field_name: str, epochs: int = 5):
        logger.warning("⚠️ TensorFlow training is disabled. No model will be trained.")
        return

    def load_model(self, field_name: str):
        logger.warning("⚠️ TensorFlow model loading is disabled. No model will be loaded.")
        return None, None, None

def fetch_wi_training_data(field_name: str, supabase=None, limit: int = 1000):
    """
    Fetch and prepare WI training data for a specific field.
    Returns a list of dicts: { 'text': ..., 'label': ... }
    Note: Supabase training data functionality has been removed.
    """
    logger.warning("⚠️ Supabase training data functionality has been removed. Returning empty training data.")
    return []

# Global instance of the pattern learning system
pattern_learning_system = PatternLearningSystem() 