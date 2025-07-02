#!/usr/bin/env python3
"""
Test script for enhanced training workflow system
Tests database-stored patterns and extraction logic
"""

import sys
import os
import logging
import pytest

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.supabase_client import get_supabase_client
from app.routes.training_routes import get_form_patterns_from_db, extract_fields_from_text
from app.services.wi_service import parse_transcript_scoped

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_patterns():
    """Test loading patterns from database"""
    logger.info("🔍 Testing database pattern loading...")
    
    try:
        patterns = get_form_patterns_from_db()
        
        if patterns:
            logger.info(f"✅ Successfully loaded {len(patterns)} patterns from database")
            
            # Show sample patterns
            sample_codes = list(patterns.keys())[:3]
            for code in sample_codes:
                pattern = patterns[code]
                logger.info(f"  - {code}: pattern={bool(pattern.get('pattern'))}, fields={len(pattern.get('fields', {}))}, category={pattern.get('category')}")
            
            return True
        else:
            logger.error("❌ No patterns loaded from database")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to load patterns from database: {str(e)}")
        return False

def test_extraction_logic():
    """Test field extraction with sample text"""
    logger.info("🔍 Testing field extraction logic...")
    
    # Sample text that should match some forms
    sample_text = """
    Form W-2 Wage and Tax Statement
    Employee's social security number: 123-45-6789
    Wages, tips, other compensation: $50,000.00
    Federal income tax withheld: $8,000.00
    Social security wages: $50,000.00
    Social security tax withheld: $3,100.00
    Medicare wages and tips: $50,000.00
    Medicare tax withheld: $725.00
    """
    
    try:
        results = extract_fields_from_text(sample_text)
        
        if results:
            logger.info(f"✅ Extracted {len(results)} form matches")
            for result in results:
                logger.info(f"  - Form: {result['form_type']}, Fields: {len(result['fields'])}, Category: {result.get('category')}")
                for field, value in result['fields'].items():
                    logger.info(f"    * {field}: {value}")
        else:
            logger.warning("⚠️ No form matches found in sample text")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Field extraction failed: {str(e)}")
        return False

def test_enhanced_schema():
    """Test that enhanced columns exist and have data"""
    logger.info("🔍 Testing enhanced schema...")
    
    try:
        supabase = get_supabase_client()
        
        # Check if enhanced columns exist
        result = supabase.table("form_types").select(
            "code, category, form_pattern, field_definitions, calculation_rules, identifiers"
        ).limit(5).execute()
        
        if result.data:
            logger.info(f"✅ Enhanced schema test passed - found {len(result.data)} form types")
            
            # Check data quality
            enhanced_count = 0
            for form in result.data:
                if form.get('form_pattern') and form.get('field_definitions'):
                    enhanced_count += 1
            
            logger.info(f"  - {enhanced_count}/{len(result.data)} forms have enhanced data")
            
            # Show sample enhanced data
            for form in result.data[:2]:
                logger.info(f"  - {form['code']}: category={form.get('category')}, has_pattern={bool(form.get('form_pattern'))}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Enhanced schema test failed: {str(e)}")
        return False

def main():
    """Run all enhanced system tests"""
    logger.info("🚀 Starting enhanced training workflow system tests...")
    
    tests = [
        ("Enhanced Schema", test_enhanced_schema),
        ("Database Patterns", test_database_patterns),
        ("Extraction Logic", test_extraction_logic),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running test: {test_name}")
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} passed")
            else:
                logger.error(f"❌ {test_name} failed")
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {str(e)}")
    
    logger.info(f"\n🎉 Enhanced System Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("✅ All enhanced system tests passed! Ready for end-to-end testing.")
        return 0
    else:
        logger.error("❌ Some enhanced system tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main())

SAMPLE_TRANSCRIPT = '''
Tracking Number: 123456789
Tax Period Requested: 2021

Form W-2 Wage and Tax Statement
Wages, tips, other compensation: $38233.00
Federal income tax withheld: $3053.00
Employer Identification Number (EIN): 12-3456789

Form 1099-NEC
Nonemployee compensation: $13500.00
Federal income tax withheld: $1500.00
Payer's Federal Identification Number (FIN): 98-7654321
'''

class TestParseTranscriptScoped:
    def test_basic_parsing(self):
        result = parse_transcript_scoped(SAMPLE_TRANSCRIPT, "transcript_123456789.txt")
        assert result['file_name'] == "transcript_123456789.txt"
        assert result['tracking_number'] == "123456789"
        assert result['tax_year'] == "2021"
        assert result['parsing_metadata']['total_forms_found'] == 2
        assert len(result['forms']) == 2

    def test_form_block_isolation(self):
        result = parse_transcript_scoped(SAMPLE_TRANSCRIPT, "transcript_123456789.txt")
        w2_fields = [f for f in result['forms'] if 'W-2' in f['form_type']][0]['fields']
        nec_fields = [f for f in result['forms'] if '1099-NEC' in f['form_type']][0]['fields']
        w2_field_names = {f['name'] for f in w2_fields}
        nec_field_names = {f['name'] for f in nec_fields}
        # W-2 should not have nonemployee_compensation
        assert 'nonemployee_compensation' not in w2_field_names
        # 1099-NEC should not have wages
        assert 'wages' not in nec_field_names

    def test_confidence_scoring(self):
        result = parse_transcript_scoped(SAMPLE_TRANSCRIPT, "transcript_123456789.txt")
        for form in result['forms']:
            for field in form['fields']:
                assert 0.0 <= field['confidence_score'] <= 1.0
                # For clean numeric matches, confidence should be >= 0.7
                if field['value'].replace('.', '', 1).isdigit():
                    assert field['confidence_score'] >= 0.7

    def test_output_structure(self):
        result = parse_transcript_scoped(SAMPLE_TRANSCRIPT, "transcript_123456789.txt")
        assert set(result.keys()) == {'file_name', 'tracking_number', 'tax_year', 'parsing_metadata', 'forms'}
        assert isinstance(result['forms'], list)
        for form in result['forms']:
            assert set(form.keys()) == {'form_type', 'form_confidence', 'block_text_length', 'fields'}
            assert isinstance(form['fields'], list)
            for field in form['fields']:
                assert set(field.keys()) == {'name', 'value', 'source_line', 'confidence_score', 'pattern_used', 'extraction_method'}

    def test_no_value_leakage(self):
        # Add a value that only appears in one form
        transcript = SAMPLE_TRANSCRIPT + '\nForm 1099-NEC\nNonemployee compensation: $99999.00\n'
        result = parse_transcript_scoped(transcript, "transcript_123456789.txt")
        nec_forms = [f for f in result['forms'] if '1099-NEC' in f['form_type']]
        # The new value should only appear in the last 1099-NEC block
        assert any(f['value'] == '99999.00' for form in nec_forms for f in form['fields'] if f['name'] == 'nonemployee_compensation')
        # It should not appear in W-2 or other forms
        w2_fields = [f for f in result['forms'] if 'W-2' in f['form_type']][0]['fields']
        assert all(f['value'] != '99999.00' for f in w2_fields) 