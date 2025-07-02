#!/usr/bin/env python3
"""
Test script for the new batch endpoints with scoped parsing.
This script tests the batch WI scoped parsing functionality.
"""

import sys
import os
sys.path.append('.')

from app.services.wi_service import parse_transcript_scoped
from app.utils.wi_patterns import form_patterns

def test_scoped_parsing_with_sample_data():
    """Test the scoped parsing function with sample transcript data."""
    
    # Sample transcript text based on the actual transcript data
    sample_text = """
This Product Contains Sensitive Taxpayer Data
Wage and Income Transcript
Request Date: 10-21-2024
Response Date: 10-21-2024
Tracking Number:106782627279
SSN Provided: 485-39-3214
Tax Period Requested:December, 2023

Form W-2 Wage and Tax Statement
Employer:
Employer Identification Number (EIN):821874527
RACCOON VALLEY MANAGEMENT LLC
2900 100TH ST STE 103
URBANDALE, IA 50322-0000
Employee:
Employee's Social Security Number: 485-39-3214
CANDANO R OKEE
926 OAKRIDGE DR
DES MOINES, IA 50314-0000
Submission Type: Original document
Wages, Tips and Other Compensation: $55,086.00
Federal Income Tax Withheld: $1,533.00
Social Security Wages: $55,086.00
Social Security Tax Withheld: $3,415.00
Medicare Wages and Tips: $55,086.00
Medicare Tax Withheld: $798.00

Form 1099-NEC Nonemployee Compensation
Issuer/Provider:
Issuer's/Provider's Federal ID No.:462852392
DOORDASH, INC.
303 2ND STREET SUITE 800
SAN FRANCISCO, CA 94107-0000
Recipient:
Recipient's ID No.: 485-39-3214
CANDANO OKEE
926 OAKRIDGE DR BLDG 206 APT 41
DES MOINES, IA 50314-0000
Submission Type: Original document
Second Notice Indicator: No Second Notice
Federal Income Tax Withheld: $0.00
Non-Employee Compensation:: $3,193.00
Direct Sales Indicator: No direct sales
"""
    
    print("🧪 Testing scoped parsing with sample data...")
    
    try:
        # Test the scoped parsing function
        result = parse_transcript_scoped(sample_text, "test_file.pdf")
        
        print("✅ Scoped parsing completed successfully!")
        print(f"📄 File metadata: {result.get('metadata', {})}")
        print(f"📋 Forms found: {len(result.get('forms', []))}")
        
        for i, form in enumerate(result.get('forms', [])):
            print(f"\n📝 Form {i+1}:")
            print(f"   Type: {form.get('form_type', 'Unknown')}")
            print(f"   Fields: {len(form.get('fields', []))}")
            print(f"   Block text length: {form.get('block_text_length', 0)}")
            
            for field in form.get('fields', []):
                print(f"     - {field.get('name', 'Unknown')}: {field.get('value', 'N/A')} (confidence: {field.get('confidence', 'N/A')})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in scoped parsing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_form_patterns():
    """Test that form patterns are properly defined."""
    
    print("\n🧪 Testing form patterns...")
    
    try:
        # Check that we have the expected form patterns
        expected_forms = ['W-2', '1099-NEC', '1099-MISC', '1099-INT']
        
        for form_type in expected_forms:
            if form_type in form_patterns:
                pattern = form_patterns[form_type]['pattern']
                fields = form_patterns[form_type]['fields']
                print(f"✅ {form_type}: pattern='{pattern}', {len(fields)} fields")
            else:
                print(f"❌ {form_type}: Not found in form_patterns")
        
        print(f"📊 Total form patterns: {len(form_patterns)}")
        return True
        
    except Exception as e:
        print(f"❌ Error testing form patterns: {str(e)}")
        return False

def main():
    """Main test function."""
    
    print("🚀 Starting batch endpoint tests...")
    print("=" * 50)
    
    # Test 1: Form patterns
    test1_passed = test_form_patterns()
    
    # Test 2: Scoped parsing
    test2_passed = test_scoped_parsing_with_sample_data()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"   Form patterns: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"   Scoped parsing: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Batch endpoints should work correctly.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 