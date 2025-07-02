#!/usr/bin/env python3
"""
Practical Regex Testing Workflow

This script provides a hands-on way to test and improve regex patterns
by comparing raw text with extraction results.
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
    
    def login(self, username: str, password: str) -> bool:
        """Login to the API."""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                self.authenticated = True
                print("✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def test_case(self, case_id: str) -> Dict[str, Any]:
        """Test a case and return comprehensive results."""
        if not self.authenticated:
            print("❌ Please login first")
            return {}
        
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
        
        # 4. Compare results
        results["comparison"] = self._compare_results(results)
        
        return results
    
    def _compare_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare raw text with regex extraction results."""
        comparison = {
            "file_comparisons": [],
            "overall_stats": {},
            "issues": [],
            "suggestions": []
        }
        
        raw_texts = results.get("raw_text", {}).get("raw_texts", [])
        regex_data = results.get("regex_analysis", {}).get("data", [])
        
        # Create file mapping
        raw_files = {f["file_name"]: f for f in raw_texts}
        regex_files = {f["file_name"]: f for f in regex_data}
        
        total_fields = 0
        total_confidence = 0
        confidence_count = 0
        
        for file_name in raw_files.keys():
            raw_file = raw_files.get(file_name, {})
            regex_file = regex_files.get(file_name, {})
            
            file_comparison = {
                "file_name": file_name,
                "raw_text_length": raw_file.get("text_length", 0),
                "forms_found": len(regex_file.get("forms", [])),
                "fields_extracted": 0,
                "average_confidence": 0,
                "form_details": []
            }
            
            # Analyze forms and fields
            for form in regex_file.get("forms", []):
                form_detail = {
                    "form_type": form.get("form_type", ""),
                    "confidence": form.get("form_confidence", 0),
                    "fields": []
                }
                
                for field in form.get("fields", []):
                    field_detail = {
                        "name": field.get("name", ""),
                        "value": field.get("value", ""),
                        "confidence": field.get("confidence_score", 0),
                        "source_line": field.get("source_line", ""),
                        "pattern_used": field.get("pattern_used", "")
                    }
                    form_detail["fields"].append(field_detail)
                    total_fields += 1
                    total_confidence += field.get("confidence_score", 0)
                    confidence_count += 1
                
                file_comparison["form_details"].append(form_detail)
                file_comparison["fields_extracted"] += len(form.get("fields", []))
            
            if file_comparison["fields_extracted"] > 0:
                file_comparison["average_confidence"] = total_confidence / confidence_count if confidence_count > 0 else 0
            
            comparison["file_comparisons"].append(file_comparison)
        
        # Overall stats
        comparison["overall_stats"] = {
            "total_files": len(raw_files),
            "total_forms": sum(f["forms_found"] for f in comparison["file_comparisons"]),
            "total_fields": total_fields,
            "average_confidence": total_confidence / confidence_count if confidence_count > 0 else 0,
            "total_raw_characters": sum(f["raw_text_length"] for f in comparison["file_comparisons"])
        }
        
        # Identify issues
        if comparison["overall_stats"]["total_fields"] == 0:
            comparison["issues"].append("No fields extracted - check regex patterns")
        
        if comparison["overall_stats"]["average_confidence"] < 0.7:
            comparison["issues"].append("Low average confidence - review pattern accuracy")
        
        if comparison["overall_stats"]["total_raw_characters"] > 10000 and comparison["overall_stats"]["total_fields"] < 5:
            comparison["issues"].append("Low field extraction rate - consider improving patterns")
        
        # Generate suggestions
        if comparison["overall_stats"]["total_fields"] == 0:
            comparison["suggestions"].append("Check if form patterns are matching the actual text")
            comparison["suggestions"].append("Verify that the raw text contains expected form types")
        
        if comparison["overall_stats"]["average_confidence"] < 0.7:
            comparison["suggestions"].append("Review patterns with low confidence scores")
            comparison["suggestions"].append("Check source lines to see what was actually matched")
        
        return comparison
    
    def print_comparison(self, results: Dict[str, Any]):
        """Print a formatted comparison of results."""
        comparison = results.get("comparison", {})
        
        print(f"\n📊 COMPARISON RESULTS FOR CASE {results['case_id']}")
        print("=" * 60)
        
        # Overall stats
        stats = comparison.get("overall_stats", {})
        print(f"📁 Files processed: {stats.get('total_files', 0)}")
        print(f"📋 Forms found: {stats.get('total_forms', 0)}")
        print(f"🔢 Fields extracted: {stats.get('total_fields', 0)}")
        print(f"📈 Average confidence: {stats.get('average_confidence', 0):.2f}")
        print(f"📝 Total characters: {stats.get('total_raw_characters', 0):,}")
        
        # Issues and suggestions
        issues = comparison.get("issues", [])
        if issues:
            print(f"\n⚠️ ISSUES FOUND:")
            for issue in issues:
                print(f"   • {issue}")
        
        suggestions = comparison.get("suggestions", [])
        if suggestions:
            print(f"\n💡 SUGGESTIONS:")
            for suggestion in suggestions:
                print(f"   • {suggestion}")
        
        # File details
        print(f"\n📄 FILE DETAILS:")
        for file_comp in comparison.get("file_comparisons", []):
            print(f"\n   📁 {file_comp['file_name']}")
            print(f"      Raw text: {file_comp['raw_text_length']:,} characters")
            print(f"      Forms: {file_comp['forms_found']}")
            print(f"      Fields: {file_comp['fields_extracted']}")
            print(f"      Avg confidence: {file_comp['average_confidence']:.2f}")
            
            for form in file_comp.get("form_details", []):
                print(f"         📋 {form['form_type']} (confidence: {form['confidence']:.2f})")
                for field in form.get("fields", []):
                    print(f"            • {field['name']}: {field['value']} (confidence: {field['confidence']:.2f})")
    
    def test_specific_pattern(self, case_id: str, pattern: str, field_name: str = "Test Pattern"):
        """Test a specific regex pattern against raw text."""
        if not self.authenticated:
            print("❌ Please login first")
            return
        
        print(f"\n🧪 Testing pattern: {field_name}")
        print(f"Pattern: {pattern}")
        print("=" * 60)
        
        # Get raw text
        raw_response = self.session.get(f"{self.base_url}/transcripts/raw/wi/{case_id}")
        if raw_response.status_code != 200:
            print("❌ Failed to get raw text")
            return
        
        raw_data = raw_response.json()
        
        total_matches = 0
        for file_data in raw_data.get("raw_texts", []):
            text = file_data["raw_text"]
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            if matches:
                print(f"\n📄 {file_data['file_name']}: {len(matches)} matches")
                for i, match in enumerate(matches[:5]):  # Show first 5 matches
                    print(f"   Match {i+1}: {match}")
                if len(matches) > 5:
                    print(f"   ... and {len(matches) - 5} more matches")
                
                total_matches += len(matches)
            else:
                print(f"\n📄 {file_data['file_name']}: No matches")
        
        print(f"\n📊 Total matches across all files: {total_matches}")
        
        if total_matches == 0:
            print("💡 Suggestion: Pattern may need adjustment - check the raw text format")

def main():
    """Main function with example usage."""
    print("🔧 REGEX TESTING WORKFLOW")
    print("=" * 60)
    
    # Initialize tester
    tester = RegexTester()
    
    # Example usage
    print("""
Example usage:

1. Login:
   tester.login("your_username", "your_password")

2. Test a case:
   results = tester.test_case("54820")
   tester.print_comparison(results)

3. Test specific patterns:
   tester.test_specific_pattern("54820", r'Wages[,\s]*tips[,\s]*and[,\s]*other[,\s]*compensation[:\s]*\$?([\d,\.]+)', "Wages Pattern")

4. Interactive mode:
   case_id = input("Enter case ID: ")
   results = tester.test_case(case_id)
   tester.print_comparison(results)
""")
    
    # Interactive mode
    try:
        username = input("\nEnter username (or press Enter to skip): ").strip()
        if username:
            password = input("Enter password: ").strip()
            if tester.login(username, password):
                while True:
                    case_id = input("\nEnter case ID to test (or 'quit' to exit): ").strip()
                    if case_id.lower() == 'quit':
                        break
                    
                    results = tester.test_case(case_id)
                    if results:
                        tester.print_comparison(results)
                        
                        # Option to test specific patterns
                        test_pattern = input("\nTest specific pattern? (y/n): ").strip().lower()
                        if test_pattern == 'y':
                            pattern = input("Enter regex pattern: ").strip()
                            field_name = input("Enter field name: ").strip()
                            tester.test_specific_pattern(case_id, pattern, field_name)
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")

if __name__ == "__main__":
    main() 