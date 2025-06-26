#!/usr/bin/env python3
"""
Test script for enhanced TI parser
"""

import sys
import os
sys.path.append('backend')

from app.utils.ti_parser import EnhancedTIParser

def test_ti_version_extraction():
    """Test TI version extraction from filenames"""
    print("🔍 Testing TI Version Extraction...")
    
    test_filenames = [
        "TI 6.7 - David & Paula.pdf",
        "TI 6.9 - Emmanuel.pdf", 
        "TI 6.9 - Salvatore & Barbara.pdf",
        "TI 7.2 - Sanderson.pdf",
        "TI 6.7 - Marc.pdf"
    ]
    
    for filename in test_filenames:
        version = EnhancedTIParser.extract_ti_version_from_filename(filename)
        print(f"   📄 {filename} -> Version: {version}")

def test_fee_extraction():
    """Test fee extraction from TI text"""
    print("\n💰 Testing Fee Extraction...")
    
    # Sample TI text from logs
    sample_text = """
    Tax Investigation Results
    CLIENT INFO:
    Opening InvestigatorSoledad Dimas Resolution Plan Completed by:Matthew BenitezCase # 798555 Current Tax Liability$4,808.08 Date RESO Plan Completed: 6/28/20248Client NameDavid & Paula FItzgeraldCurrent & Projected Tax Liability$4,808.08 Settlement Officer:New RepDate TI Completed6/24/2024 Total Resolution Fees$2,050.00 TRA Code: M21
    """
    
    fees = EnhancedTIParser.extract_total_resolution_fees(sample_text)
    current_liability = EnhancedTIParser.extract_current_tax_liability(sample_text)
    projected_liability = EnhancedTIParser.extract_current_and_projected_liability(sample_text)
    
    print(f"   💵 Total Resolution Fees: ${fees}")
    print(f"   💰 Current Tax Liability: ${current_liability}")
    print(f"   📊 Current & Projected Tax Liability: ${projected_liability}")

def test_interest_extraction():
    """Test interest calculation extraction"""
    print("\n📈 Testing Interest Extraction...")
    
    sample_text = """
    For every day that the client does not resolve their tax issues, the IRS is assessing additional interest. Based on the information provided by the IRS, the following amount of interest is being assessed:Daily:  $0.74Monthly: $22.13Yearly: $269.25
    """
    
    interest = EnhancedTIParser.extract_interest_calculations(sample_text)
    print(f"   📅 Daily Interest: ${interest.get('daily_interest')}")
    print(f"   📅 Monthly Interest: ${interest.get('monthly_interest')}")
    print(f"   📅 Yearly Interest: ${interest.get('yearly_interest')}")

def test_full_parsing():
    """Test full TI parsing with sample data"""
    print("\n🔍 Testing Full TI Parsing...")
    
    sample_text = """
    Tax Investigation Results
    CLIENT INFO:
    Opening InvestigatorSoledad Dimas Resolution Plan Completed by:Matthew BenitezCase # 798555 Current Tax Liability$4,808.08 Date RESO Plan Completed: 6/28/20248Client NameDavid & Paula FItzgeraldCurrent & Projected Tax Liability$4,808.08 Settlement Officer:New RepDate TI Completed6/24/2024 Total Resolution Fees$2,050.00 TRA Code: M21
    Tax YearsReturn FiledFiling StatusCurrent BalanceCSED DateReason StatusLegal ActionProjected Balance Wage Information Notes
    2023 Filed MFJ PWR $0.00 W-2 1099-S SSA 1099-R g div
    2022 Filed MFJ Refund $0.00 W-2 1099-NECSSA 1099-R$2,058 W2 $102 1099DIV $388 1099R2021 Filed MFJ $4,808.084/23/2034Closed AUR $0.00 W-2 1099-NECSSA 1099-R
    2020 Filed MFJ Refund $0.00 W-2 1099-NECSSA 1099-R
    2019 Filed MFJ Refund $0.00 W-2 1099-MISCSSA 1099-R
    2018 Filed MFJ Refund $0.00 W-2 1099-MISCSSA 1099-R
    2017 Filed MFJ Refund $0.00 W-2 1099-MISCSSA 1099-R
    Total Individual Balance:$4,808.08 Projected Unfiled Balances:$0.00
    """
    
    filename = "TI 6.7 - David & Paula.pdf"
    result = EnhancedTIParser.parse_ti_text_enhanced(sample_text, filename)
    
    print(f"   📋 TI Version: {result.get('case_metadata', {}).get('file_info', {}).get('ti_version')}")
    print(f"   💰 Total Resolution Fees: ${result.get('tax_liability_summary', {}).get('total_resolution_fees')}")
    print(f"   📊 Current Tax Liability: ${result.get('tax_liability_summary', {}).get('current_tax_liability')}")
    print(f"   📅 Tax Years Found: {len(result.get('tax_years', []))}")
    print(f"   📋 Resolution Steps: {len(result.get('resolution_plan', {}).get('steps', []))}")

if __name__ == "__main__":
    print("🧪 Enhanced TI Parser Test Suite")
    print("=" * 50)
    
    try:
        test_ti_version_extraction()
        test_fee_extraction()
        test_interest_extraction()
        test_full_parsing()
        print("\n✅ All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 