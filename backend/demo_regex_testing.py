#!/usr/bin/env python3
"""
Demo Regex Testing Workflow

This script demonstrates the regex testing workflow without requiring interactive input.
"""

import requests
import json
import re
from typing import Dict, List, Any
from datetime import datetime

class RegexTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.authenticated = False
    
    def test_case(self, case_id: str) -> Dict[str, Any]:
        """Test a case and return comprehensive results."""
        print(f"\n🔍 Testing case {case_id}")
        print("=" * 60)
        
        results = {
            "case_id": case_id,
            "timestamp": datetime.now().isoformat(),
            "raw_text": {},
            "regex_analysis": {},
            "summary_analysis": {},
            "comparison": {}
        }
        
        # 1. Get raw text
        print("📄 Getting raw text...")
        raw_response = self.session.get(f"{self.base_url}/transcripts/raw/wi/{case_id}")
        if raw_response.status_code == 200:
            results["raw_text"] = raw_response.json()
            print(f"✅ Raw text: {len(results['raw_text'].get('raw_texts', []))} files")
        else:
            print(f"❌ Raw text failed: {raw_response.status_code}")
        
        # 2. Get regex analysis
        print("🔍 Getting regex analysis...")
        regex_response = self.session.get(f"{self.base_url}/transcripts/analysis/wi/{case_id}")
        if regex_response.status_code == 200:
            results["regex_analysis"] = regex_response.json()
            print(f"✅ Regex analysis: {len(results['regex_analysis'].get('data', []))} files")
        else:
            print(f"❌ Regex analysis failed: {regex_response.status_code}")
        
        # 3. Get summary analysis
        print("📊 Getting summary analysis...")
        summary_response = self.session.get(f"{self.base_url}/analysis/wi/{case_id}")
        if summary_response.status_code == 200:
            results["summary_analysis"] = summary_response.json()
            print(f"✅ Summary analysis: {results['summary_analysis'].get('summary', {}).get('total_years', 0)} years")
        else:
            print(f"❌ Summary analysis failed: {summary_response.status_code}")
        
        return results
    
    def print_comparison(self, results: Dict[str, Any]):
        """Print a formatted comparison of results."""
        print(f"\n📊 RESULTS FOR CASE {results['case_id']}")
        print("=" * 60)
        
        # Raw text summary
        raw_texts = results.get("raw_text", {}).get("raw_texts", [])
        if raw_texts:
            print(f"📄 RAW TEXT SUMMARY:")
            print(f"   Files: {len(raw_texts)}")
            total_chars = sum(f.get("text_length", 0) for f in raw_texts)
            print(f"   Total characters: {total_chars:,}")
            for file_data in raw_texts:
                print(f"   📁 {file_data['file_name']}: {file_data.get('text_length', 0):,} chars")
        
        # Regex analysis summary
        regex_data = results.get("regex_analysis", {}).get("data", [])
        if regex_data:
            print(f"\n🔍 REGEX ANALYSIS SUMMARY:")
            print(f"   Files processed: {len(regex_data)}")
            total_forms = 0
            total_fields = 0
            total_confidence = 0
            confidence_count = 0
            
            for file_result in regex_data:
                forms = file_result.get("forms", [])
                total_forms += len(forms)
                print(f"   📁 {file_result.get('file_name', 'Unknown')}: {len(forms)} forms")
                
                for form in forms:
                    fields = form.get("fields", [])
                    total_fields += len(fields)
                    print(f"      📋 {form.get('form_type', 'Unknown')} (confidence: {form.get('form_confidence', 0):.2f})")
                    
                    for field in fields:
                        confidence = field.get("confidence_score", 0)
                        total_confidence += confidence
                        confidence_count += 1
                        print(f"         • {field.get('name', 'Unknown')}: {field.get('value', 'Unknown')} (confidence: {confidence:.2f})")
            
            avg_confidence = total_confidence / confidence_count if confidence_count > 0 else 0
            print(f"\n   📊 OVERALL STATS:")
            print(f"      Total forms: {total_forms}")
            print(f"      Total fields: {total_fields}")
            print(f"      Average confidence: {avg_confidence:.2f}")
        
        # Summary analysis
        summary = results.get("summary_analysis", {}).get("summary", {})
        if summary:
            print(f"\n📊 SUMMARY ANALYSIS:")
            print(f"   Total years: {summary.get('total_years', 0)}")
            print(f"   Years analyzed: {', '.join(summary.get('years_analyzed', []))}")
            print(f"   Total forms: {summary.get('total_forms', 0)}")
            
            by_year = summary.get("by_year", {})
            if by_year:
                print(f"\n   📅 BY YEAR BREAKDOWN:")
                for year, data in by_year.items():
                    print(f"      {year}:")
                    print(f"         Forms: {data.get('number_of_forms', 0)}")
                    print(f"         Non-SE Income: ${data.get('non_se_income', 0):,.2f}")
                    print(f"         SE Income: ${data.get('se_income', 0):,.2f}")
                    print(f"         Total Income: ${data.get('total_income', 0):,.2f}")
                    print(f"         Withholding: ${data.get('total_withholding', 0):,.2f}")

def main():
    """Demo the regex testing workflow."""
    print("🔧 REGEX TESTING WORKFLOW DEMO")
    print("=" * 60)
    
    # Initialize tester
    tester = RegexTester()
    
    # Demo with case 54820 (we know this works)
    case_id = "54820"
    
    print(f"\n🎯 DEMO: Testing case {case_id}")
    print("This demo will show you:")
    print("1. Raw text extraction from PDFs")
    print("2. Regex pattern extraction results")
    print("3. Summary analysis with totals")
    print("4. Confidence scores and field details")
    
    # Test the case
    results = tester.test_case(case_id)
    
    if results:
        # Print comparison
        tester.print_comparison(results)
        
        print(f"\n✅ DEMO COMPLETE!")
        print("=" * 60)
        print("This shows you how the workflow works:")
        print("1. Get raw text from PDFs")
        print("2. Get regex extraction results")
        print("3. Compare and analyze")
        print("4. Review confidence scores")
        print("\nTo use interactively, run: python3 test_regex_workflow.py")
        
    else:
        print("❌ Demo failed - likely due to authentication")
        print("To run the full demo, you need to:")
        print("1. Start your server: python3 server.py")
        print("2. Authenticate with your credentials")
        print("3. Run: python3 test_regex_workflow.py")

if __name__ == "__main__":
    main() 