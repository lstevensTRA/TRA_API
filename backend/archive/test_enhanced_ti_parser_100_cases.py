#!/usr/bin/env python3
"""
Enhanced TI Parser Test Script - 100 Cases Validation
Tests the enhanced TI parser against real data from logs.txt
"""

import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class TITestCase:
    """Represents a TI test case from the logs"""
    case_id: str
    filename: str
    version: Optional[str]
    total_fees: Optional[str]
    raw_text: str

class EnhancedTIParser:
    """Enhanced TI Parser with improved patterns for version detection and fee extraction"""
    
    def __init__(self):
        # Enhanced version detection patterns
        self.version_patterns = [
            r'TI\s+(\d+\.\d+)',  # TI 6.7, TI 7.2, etc.
            r'TI\s+(\d+)',       # TI 2848, etc.
            r'TI\s+Report',      # TI Report_Rozell.xlsx
            r'TI\s+SAG',         # TI SAG_JONES.pdf
        ]
        
        # Enhanced fee extraction patterns
        self.fee_patterns = [
            r'Total Resolution Fees\s*\$?([\d,]+\.?\d*)',
            r'Total Resolution Fees\s*\$?([\d,]+)',
            r'Resolution Fees\s*\$?([\d,]+\.?\d*)',
            r'Fees\s*\$?([\d,]+\.?\d*)',
        ]
        
        # Tax liability patterns
        self.tax_liability_patterns = [
            r'Current Tax Liability\s*\$?([\d,]+\.?\d*)',
            r'Current & Projected Tax Liability\s*\$?([\d,]+\.?\d*)',
            r'Tax Liability\s*\$?([\d,]+\.?\d*)',
        ]
        
        # Interest calculation patterns
        self.interest_patterns = [
            r'Interest\s*\$?([\d,]+\.?\d*)',
            r'Interest Calculation\s*\$?([\d,]+\.?\d*)',
        ]
        
        # Tax year patterns
        self.tax_year_patterns = [
            r'(\d{4})\s+(?:Filed|Unfiled|Not Req)',
            r'Tax Years.*?(\d{4})',
        ]
        
        # Resolution plan patterns
        self.resolution_patterns = [
            r'Resolution Plan Completed by:\s*([^\n]+)',
            r'Resolution Plan.*?by:\s*([^\n]+)',
        ]
    
    def extract_ti_version(self, filename: str) -> Optional[str]:
        """Extract TI version from filename"""
        if not filename:
            return None
            
        # Try version patterns
        for pattern in self.version_patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Handle special cases
        if 'Case Guide' in filename:
            return 'Case Guide'
        elif 'Report' in filename:
            return 'Report'
        elif 'SAG' in filename:
            return 'SAG'
        
        return None
    
    def extract_total_fees(self, text: str) -> Optional[str]:
        """Extract total resolution fees from text"""
        if not text:
            return None
            
        for pattern in self.fee_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extract_tax_liability(self, text: str) -> Optional[str]:
        """Extract current tax liability from text"""
        if not text:
            return None
            
        for pattern in self.tax_liability_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extract_interest_calculation(self, text: str) -> Optional[str]:
        """Extract interest calculation from text"""
        if not text:
            return None
            
        for pattern in self.interest_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extract_tax_years(self, text: str) -> List[str]:
        """Extract tax years from text"""
        if not text:
            return []
            
        years = set()
        for pattern in self.tax_year_patterns:
            matches = re.findall(pattern, text)
            years.update(matches)
        
        return sorted(list(years))
    
    def extract_resolution_plans(self, text: str) -> List[str]:
        """Extract resolution plan information from text"""
        if not text:
            return []
            
        plans = []
        for pattern in self.resolution_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            plans.extend(matches)
        
        return plans
    
    def parse_ti(self, filename: str, text: str) -> Dict:
        """Parse TI document and return structured data"""
        version = self.extract_ti_version(filename)
        total_fees = self.extract_total_fees(text)
        tax_liability = self.extract_tax_liability(text)
        interest = self.extract_interest_calculation(text)
        tax_years = self.extract_tax_years(text)
        resolution_plans = self.extract_resolution_plans(text)
        
        return {
            'filename': filename,
            'ti_version': version,
            'total_resolution_fees': total_fees,
            'current_tax_liability': tax_liability,
            'interest_calculation': interest,
            'tax_years': tax_years,
            'resolution_plans': resolution_plans,
            'raw_text_length': len(text) if text else 0
        }

def extract_test_cases_from_logs(logs_file: str) -> List[TITestCase]:
    """Extract TI test cases from logs.txt"""
    test_cases = []
    
    with open(logs_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all TI file responses - handle escaped JSON in Response Body
    ti_file_pattern = r'"Response Body":\s*"\{[^}]*"FileName":"([^"]*TI[^"]*\.pdf[^"]*)"[^}]*"case_id":"([^"]*)"'
    ti_file_matches = re.findall(ti_file_pattern, content)
    
    # Alternative pattern for different JSON structure
    ti_file_pattern2 = r'"FileName":"([^"]*TI[^"]*\.pdf[^"]*)"[^}]*"case_id":"([^"]*)"'
    ti_file_matches2 = re.findall(ti_file_pattern2, content)
    
    # Combine matches
    all_file_matches = ti_file_matches + ti_file_matches2
    
    # Find all TI raw text responses - handle escaped JSON
    ti_raw_pattern = r'"Response Body":\s*"\{[^}]*"FileName":"([^"]*TI[^"]*\.pdf[^"]*)"[^}]*"raw_text":"([^"]*)"'
    ti_raw_matches = re.findall(ti_raw_pattern, content)
    
    # Alternative pattern for raw text
    ti_raw_pattern2 = r'"FileName":"([^"]*TI[^"]*\.pdf[^"]*)"[^}]*"raw_text":"([^"]*)"'
    ti_raw_matches2 = re.findall(ti_raw_pattern2, content)
    
    # Combine raw text matches
    all_raw_matches = ti_raw_matches + ti_raw_matches2
    
    # Create lookup for raw text by filename
    raw_text_lookup = {filename: text for filename, text in all_raw_matches}
    
    # Create test cases
    for filename, case_id in all_file_matches:
        raw_text = raw_text_lookup.get(filename, "")
        test_cases.append(TITestCase(
            case_id=case_id,
            filename=filename,
            version=None,  # Will be extracted by parser
            total_fees=None,  # Will be extracted by parser
            raw_text=raw_text
        ))
    
    # Remove duplicates based on filename
    unique_cases = {}
    for case in test_cases:
        if case.filename not in unique_cases:
            unique_cases[case.filename] = case
    
    return list(unique_cases.values())

def run_comprehensive_test():
    """Run comprehensive test against all TI cases"""
    print("🔍 Enhanced TI Parser - 100 Cases Validation")
    print("=" * 60)
    
    # Extract test cases from logs
    test_cases = extract_test_cases_from_logs('logs.txt')
    print(f"📊 Found {len(test_cases)} TI test cases")
    
    if len(test_cases) == 0:
        print("❌ No TI test cases found. Check the logs.txt file and regex patterns.")
        return
    
    # Initialize parser
    parser = EnhancedTIParser()
    
    # Statistics
    stats = {
        'total_cases': len(test_cases),
        'version_detected': 0,
        'fees_detected': 0,
        'tax_liability_detected': 0,
        'interest_detected': 0,
        'tax_years_detected': 0,
        'resolution_plans_detected': 0,
        'empty_raw_text': 0,
        'successful_parses': 0
    }
    
    # Version distribution
    version_distribution = {}
    fee_distribution = {}
    
    print("\n📋 Processing test cases...")
    print("-" * 60)
    
    for i, test_case in enumerate(test_cases[:50], 1):  # Limit to first 50 for readability
        print(f"\n🔍 [{i:2d}/{len(test_cases)}] Case: {test_case.case_id}")
        print(f"📄 File: {test_case.filename}")
        
        # Parse the TI document
        result = parser.parse_ti(test_case.filename, test_case.raw_text)
        
        # Update statistics
        if result['ti_version']:
            stats['version_detected'] += 1
            version_distribution[result['ti_version']] = version_distribution.get(result['ti_version'], 0) + 1
        
        if result['total_resolution_fees']:
            stats['fees_detected'] += 1
            fee_distribution[result['total_resolution_fees']] = fee_distribution.get(result['total_resolution_fees'], 0) + 1
        
        if result['current_tax_liability']:
            stats['tax_liability_detected'] += 1
        
        if result['interest_calculation']:
            stats['interest_detected'] += 1
        
        if result['tax_years']:
            stats['tax_years_detected'] += 1
        
        if result['resolution_plans']:
            stats['resolution_plans_detected'] += 1
        
        if not test_case.raw_text:
            stats['empty_raw_text'] += 1
        
        if any([result['ti_version'], result['total_resolution_fees'], result['current_tax_liability']]):
            stats['successful_parses'] += 1
        
        # Display results
        print(f"✅ Version: {result['ti_version'] or 'Not detected'}")
        print(f"💰 Fees: {result['total_resolution_fees'] or 'Not detected'}")
        print(f"💸 Tax Liability: {result['current_tax_liability'] or 'Not detected'}")
        print(f"📅 Tax Years: {', '.join(result['tax_years']) if result['tax_years'] else 'Not detected'}")
        print(f"📝 Raw Text Length: {result['raw_text_length']} chars")
    
    # Print comprehensive statistics
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE STATISTICS")
    print("=" * 60)
    
    print(f"Total Cases Processed: {stats['total_cases']}")
    if stats['total_cases'] > 0:
        print(f"Successful Parses: {stats['successful_parses']} ({stats['successful_parses']/stats['total_cases']*100:.1f}%)")
        print(f"Empty Raw Text: {stats['empty_raw_text']} ({stats['empty_raw_text']/stats['total_cases']*100:.1f}%)")
        print()
        
        print("Detection Rates:")
        print(f"  Version Detection: {stats['version_detected']} ({stats['version_detected']/stats['total_cases']*100:.1f}%)")
        print(f"  Fee Detection: {stats['fees_detected']} ({stats['fees_detected']/stats['total_cases']*100:.1f}%)")
        print(f"  Tax Liability Detection: {stats['tax_liability_detected']} ({stats['tax_liability_detected']/stats['total_cases']*100:.1f}%)")
        print(f"  Interest Detection: {stats['interest_detected']} ({stats['interest_detected']/stats['total_cases']*100:.1f}%)")
        print(f"  Tax Years Detection: {stats['tax_years_detected']} ({stats['tax_years_detected']/stats['total_cases']*100:.1f}%)")
        print(f"  Resolution Plans Detection: {stats['resolution_plans_detected']} ({stats['resolution_plans_detected']/stats['total_cases']*100:.1f}%)")
        
        print("\nVersion Distribution:")
        for version, count in sorted(version_distribution.items(), key=lambda x: x[1], reverse=True):
            print(f"  {version}: {count} cases")
        
        print("\nFee Distribution (Top 10):")
        for fee, count in sorted(fee_distribution.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  ${fee}: {count} cases")
        
        # Identify patterns and issues
        print("\n🔍 PATTERN ANALYSIS")
        print("-" * 60)
        
        # Find cases with no version detected
        no_version_cases = [tc for tc in test_cases if not parser.extract_ti_version(tc.filename)]
        if no_version_cases:
            print(f"Cases with no version detected: {len(no_version_cases)}")
            for tc in no_version_cases[:5]:  # Show first 5
                print(f"  - {tc.filename}")
        
        # Find cases with no fees detected
        no_fees_cases = [tc for tc in test_cases if tc.raw_text and not parser.extract_total_fees(tc.raw_text)]
        if no_fees_cases:
            print(f"Cases with no fees detected: {len(no_fees_cases)}")
            for tc in no_fees_cases[:5]:  # Show first 5
                print(f"  - {tc.filename}")
    
    print("\n✅ Enhanced TI Parser validation completed!")

if __name__ == "__main__":
    run_comprehensive_test() 