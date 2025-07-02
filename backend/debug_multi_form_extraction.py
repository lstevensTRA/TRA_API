#!/usr/bin/env python3
"""
Debug script to test form extraction with multiple forms per file.
"""

import sys
import os
import re
sys.path.append('.')

from app.services.wi_service import extract_form_blocks, parse_transcript_scoped
from app.utils.wi_patterns import form_patterns

def test_multi_form_extraction():
    """Test form extraction with multiple forms per file."""
    
    # Test case 1: Multiple W-2 forms (case 884562)
    w2_text = """IRS Logo
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
Form W-2 Wage and Tax Statement
Employer:
Employer Identification Number (EIN):123456789
ANOTHER EMPLOYER LLC
123 MAIN ST
DES MOINES, IA 50314-0000
Employee:
Employee's Social Security Number: 485-39-3214
CANDANO R OKEE
926 OAKRIDGE DR
DES MOINES, IA 50314-0000
Submission Type: Original document
Wages, Tips and Other Compensation: $25,000.00
Federal Income Tax Withheld: $500.00"""
    
    # Test case 2: 1099-NEC form (case 909511)
    nec_text = """IRS Logo
This Product Contains Sensitive Taxpayer Data
Wage and Income Transcript
Request Date: 10-23-2024
Response Date: 10-23-2024
Tracking Number:106794058469
SSN Provided: XXX-XX-3226
Tax Period Requested:December, 2022
Form 1099-NEC Nonemployee Compensation
Issuer/Provider:
Issuer's/Provider's Federal ID No.:XXXXX5871
A1 P
PO BOX
Recipient:
Recipient's ID No.: XXX-XX-3226
JAME MAY
1541 H
Submission Type: Original document
Second Notice Indicator: No Second Notice
Federal Income Tax Withheld: $0.00
Non-Employee Compensation:: $64,185.00
Direct Sales Indicator: No direct sales"""
    
    print("🔍 Testing multi-form extraction...")
    print("=" * 50)
    
    # Test W-2 multiple forms
    print("\n📄 Test Case 1: Multiple W-2 forms")
    print("-" * 30)
    blocks = extract_form_blocks(w2_text)
    print(f"📊 Found {len(blocks)} form blocks")
    
    for i, block in enumerate(blocks):
        print(f"\n📄 Block {i+1}:")
        print(f"   Form Type: {block['form_type']}")
        print(f"   Original Header: {block['original_header']}")
        print(f"   Content Length: {len(block['content'])}")
        print(f"   Content Preview: {block['content'][:100]}...")
        
        # Test field extraction
        canonical_form = None
        for k, v in form_patterns.items():
            if re.search(v['pattern'], block['form_type'], re.IGNORECASE):
                canonical_form = k
                break
        
        print(f"   Canonical form: {canonical_form}")
        
        if canonical_form:
            pattern_info = form_patterns[canonical_form]
            field_patterns = pattern_info.get('fields', {})
            
            block_lines = block['content'].splitlines()
            for field_name, regex in field_patterns.items():
                if not regex:
                    continue
                
                found = False
                for line_num, line in enumerate(block_lines):
                    m = re.search(regex, line, re.IGNORECASE)
                    if m:
                        value = m.group(1).replace(',', '').replace('$', '').strip()
                        print(f"   ✅ {field_name}: {value} (line {line_num})")
                        found = True
                        break
                
                if not found:
                    print(f"   ❌ {field_name}: NO MATCH")
    
    # Test 1099-NEC form
    print("\n📄 Test Case 2: 1099-NEC form")
    print("-" * 30)
    blocks = extract_form_blocks(nec_text)
    print(f"📊 Found {len(blocks)} form blocks")
    
    for i, block in enumerate(blocks):
        print(f"\n📄 Block {i+1}:")
        print(f"   Form Type: {block['form_type']}")
        print(f"   Original Header: {block['original_header']}")
        print(f"   Content Length: {len(block['content'])}")
        print(f"   Content Preview: {block['content'][:100]}...")
        
        # Test field extraction
        canonical_form = None
        for k, v in form_patterns.items():
            if re.search(v['pattern'], block['form_type'], re.IGNORECASE):
                canonical_form = k
                break
        
        print(f"   Canonical form: {canonical_form}")
        
        if canonical_form:
            pattern_info = form_patterns[canonical_form]
            field_patterns = pattern_info.get('fields', {})
            
            block_lines = block['content'].splitlines()
            for field_name, regex in field_patterns.items():
                if not regex:
                    continue
                
                found = False
                for line_num, line in enumerate(block_lines):
                    m = re.search(regex, line, re.IGNORECASE)
                    if m:
                        value = m.group(1).replace(',', '').replace('$', '').strip()
                        print(f"   ✅ {field_name}: {value} (line {line_num})")
                        found = True
                        break
                
                if not found:
                    print(f"   ❌ {field_name}: NO MATCH")
    
    # Test full parsing
    print("\n🔍 Testing full scoped parsing...")
    print("=" * 50)
    
    print("\n📄 W-2 Multiple Forms Result:")
    result = parse_transcript_scoped(w2_text, "w2_test.pdf")
    print(f"   Forms Found: {result['parsing_metadata']['total_forms_found']}")
    print(f"   Successful Extractions: {result['parsing_metadata']['successful_extractions']}")
    for i, form in enumerate(result['forms']):
        print(f"   Form {i+1}: {form['form_type']} ({len(form['fields'])} fields)")
    
    print("\n📄 1099-NEC Result:")
    result = parse_transcript_scoped(nec_text, "nec_test.pdf")
    print(f"   Forms Found: {result['parsing_metadata']['total_forms_found']}")
    print(f"   Successful Extractions: {result['parsing_metadata']['successful_extractions']}")
    for i, form in enumerate(result['forms']):
        print(f"   Form {i+1}: {form['form_type']} ({len(form['fields'])} fields)")

if __name__ == "__main__":
    test_multi_form_extraction() 