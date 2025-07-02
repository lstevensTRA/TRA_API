#!/usr/bin/env python3
"""
Debug script to test form extraction with real transcript data.
"""

import sys
import os
import re
sys.path.append('.')

print('=== DEBUG SCRIPT STARTED ===')
sys.stdout.flush()

from app.services.wi_service import extract_form_blocks, parse_transcript_scoped
from app.utils.wi_patterns import form_patterns

def test_form_extraction():
    """Test form extraction with real transcript data."""
    
    # Real transcript text from case 884562
    real_text = """IRS Logo
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
Social Security Tips: $0.00
Allocated Tips: $0.00
Dependent Care Benefits: $0.00
Deferred Compensation: $0.00
Code "Q" Nontaxable Combat Pay: $0.00
Code "W" Employer Contributions to a Health Savings Account: $0.00
Code "Y" Deferrals under a section 409A nonqualifi
ed Deferred Compensation
plan:
$0.00
Code "Z" Income under section 409A on a nonqualified Deferred Compensation
plan:
$0.00
Code "R" Employer's Contribution to MSA: $0.00
Code "S" Employer's Contribution to Simple Account: $0.00
Code "T" Expenses Incurred for Qualified Adoptions: $0.00
Code "V" Income from exercise of non-statutory stock options: $0.00
Code "AA" Designated Roth Contributions under a Section 401(k) Plan:$0.00
Code "BB" Designated Roth Contributions under a Section 403(b) Plan:$0.00
Code "DD" Cost of Employer-Sponsored Health Coverage: $0.00
Code "EE" Designated ROTH Contributions Under a Governmental Section 457(b)
Plan:
$0.00
Code "FF" Permitted benefits under a qualified small employer health
reimbursement arrangement:
$0.00
Code "GG" Income from Qualified Equity Grants Under Section 83(i): $0.00
Code "HH" Aggregate Deferrals Under Section 83(i)"""
    
    print("🔍 Testing form extraction with real transcript data...")
    sys.stdout.flush()
    print(f"📝 Text length: {len(real_text)} characters")
    sys.stdout.flush()
    print(f"📝 First 200 chars: {real_text[:200]}")
    sys.stdout.flush()
    print()
    sys.stdout.flush()
    
    # Test form block extraction
    print("🔍 Extracting form blocks...")
    sys.stdout.flush()
    blocks = extract_form_blocks(real_text)
    print(f"📊 Found {len(blocks)} form blocks")
    sys.stdout.flush()
    
    for i, block in enumerate(blocks):
        print(f"\n📄 Block {i+1}:")
        sys.stdout.flush()
        print(f"   Form Type: {block['form_type']}")
        sys.stdout.flush()
        print(f"   Original Header: {block['original_header']}")
        sys.stdout.flush()
        print(f"   Content Length: {len(block['content'])}")
        sys.stdout.flush()
        print(f"   Content Preview: {block['content'][:200]}...")
        sys.stdout.flush()
        
        # Debug field extraction for this block
        print(f"\n🔍 Debugging field extraction for {block['form_type']}...")
        sys.stdout.flush()
        
        # Find the canonical form name in form_patterns
        canonical_form = None
        for k, v in form_patterns.items():
            if re.search(v['pattern'], block['form_type'], re.IGNORECASE):
                canonical_form = k
                break
        
        print(f"   Canonical form: {canonical_form}")
        sys.stdout.flush()
        
        if canonical_form:
            pattern_info = form_patterns[canonical_form]
            field_patterns = pattern_info.get('fields', {})
            print(f"   Field patterns available: {list(field_patterns.keys())}")
            sys.stdout.flush()
            
            # Test each field pattern
            block_lines = block['content'].splitlines()
            for field_name, regex in field_patterns.items():
                if not regex:
                    continue
                print(f"\n   Testing field: {field_name}")
                sys.stdout.flush()
                print(f"   Regex: {regex}")
                sys.stdout.flush()
                
                found = False
                for line_num, line in enumerate(block_lines):
                    m = re.search(regex, line, re.IGNORECASE)
                    if m:
                        value = m.group(1).replace(',', '').replace('$', '').strip()
                        print(f"   ✅ MATCH on line {line_num}: '{line.strip()}' -> '{value}'")
                        sys.stdout.flush()
                        found = True
                        break
                
                if not found:
                    print(f"   ❌ NO MATCH for {field_name}")
                    sys.stdout.flush()
                    # Show a few sample lines to help debug
                    print(f"   Sample lines from content:")
                    sys.stdout.flush()
                    for j, line in enumerate(block_lines[:5]):
                        print(f"     Line {j}: '{line}'")
                        sys.stdout.flush()
    
    # Test full scoped parsing
    print("\n🔍 Testing full scoped parsing...")
    sys.stdout.flush()
    result = parse_transcript_scoped(real_text, "test_file.pdf")
    print(f"📊 Parsing result:")
    sys.stdout.flush()
    print(f"   File: {result['file_name']}")
    sys.stdout.flush()
    print(f"   Tracking Number: {result['tracking_number']}")
    sys.stdout.flush()
    print(f"   Tax Year: {result['tax_year']}")
    sys.stdout.flush()
    print(f"   Forms Found: {result['parsing_metadata']['total_forms_found']}")
    sys.stdout.flush()
    print(f"   Successful Extractions: {result['parsing_metadata']['successful_extractions']}")
    sys.stdout.flush()
    print(f"   Overall Confidence: {result['parsing_metadata']['overall_confidence']}")
    sys.stdout.flush()
    
    if result['forms']:
        for i, form in enumerate(result['forms']):
            print(f"\n📄 Form {i+1}: {form['form_type']}")
            sys.stdout.flush()
            print(f"   Confidence: {form['form_confidence']}")
            sys.stdout.flush()
            print(f"   Fields: {len(form['fields'])}")
            sys.stdout.flush()
            for field in form['fields']:
                print(f"     {field['name']}: {field['value']} (confidence: {field['confidence_score']})")
                sys.stdout.flush()

if __name__ == "__main__":
    try:
        test_form_extraction()
    except Exception as e:
        print(f"[EXCEPTION] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        import sys
        sys.exit(1) 