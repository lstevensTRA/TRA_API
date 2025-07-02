#!/usr/bin/env python3
"""
Comprehensive Endpoint Analysis and Regex Testing Workflow

This script provides:
1. Complete analysis of all backend endpoints
2. Workflow for comparing raw text with regex extraction results
3. Tools for testing and improving regex patterns
"""

import os
import re
import json
import ast
from pathlib import Path
from typing import List, Dict, Set, Tuple, Any
from datetime import datetime
import requests
import base64

class EndpointAnalyzer:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.endpoints = {}
        self.categories = {}
        
    def extract_all_endpoints(self) -> Dict[str, List[Dict]]:
        """Extract all endpoints from all route files."""
        routes_dir = Path("app/routes")
        
        for route_file in routes_dir.glob("*.py"):
            if route_file.name in ["__init__.py", "test_routes.py"]:
                continue
                
            category = route_file.stem.replace("_routes", "").replace("_", " ")
            self.categories[category] = []
            
            with open(route_file, 'r') as f:
                content = f.read()
            
            # Find all @router decorators
            pattern = r'@router\.(get|post|put|delete)\(["\']([^"\']+)["\']'
            matches = re.findall(pattern, content)
            
            for method, path in matches:
                # Extract tags and description if available
                tag_match = re.search(r'tags=\[([^\]]+)\]', content)
                tags = tag_match.group(1).replace('"', '').replace("'", "").split(', ') if tag_match else []
                
                # Extract summary if available
                summary_match = re.search(r'summary=["\']([^"\']+)["\']', content)
                summary = summary_match.group(1) if summary_match else ""
                
                endpoint_info = {
                    "method": method.upper(),
                    "path": path,
                    "full_path": f"{self.base_url}{path}",
                    "tags": tags,
                    "summary": summary,
                    "file": route_file.name,
                    "category": category
                }
                
                self.categories[category].append(endpoint_info)
                self.endpoints[f"{method.upper()} {path}"] = endpoint_info
        
        return self.categories
    
    def get_wi_endpoints(self) -> List[Dict]:
        """Get all WI-related endpoints."""
        wi_endpoints = []
        for category, endpoints in self.categories.items():
            for endpoint in endpoints:
                if any(term in endpoint["path"].lower() for term in ["wi", "wage", "income"]):
                    wi_endpoints.append(endpoint)
        return wi_endpoints
    
    def get_regex_testing_endpoints(self) -> List[Dict]:
        """Get endpoints useful for regex testing."""
        regex_endpoints = []
        for category, endpoints in self.categories.items():
            for endpoint in endpoints:
                if any(term in endpoint["path"].lower() for term in ["raw", "analysis", "regex", "pattern"]):
                    regex_endpoints.append(endpoint)
        return regex_endpoints

class RegexTestingWorkflow:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with the API."""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"username": username, "password": password}
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False
    
    def get_raw_text(self, case_id: str) -> Dict[str, Any]:
        """Get raw text from WI transcripts."""
        try:
            response = self.session.get(f"{self.base_url}/transcripts/raw/wi/{case_id}")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get raw text: {response.status_code}")
                return {}
        except Exception as e:
            print(f"Error getting raw text: {e}")
            return {}
    
    def get_regex_analysis(self, case_id: str) -> Dict[str, Any]:
        """Get regex analysis results."""
        try:
            response = self.session.get(f"{self.base_url}/transcripts/analysis/wi/{case_id}")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get regex analysis: {response.status_code}")
                return {}
        except Exception as e:
            print(f"Error getting regex analysis: {e}")
            return {}
    
    def get_summary_analysis(self, case_id: str) -> Dict[str, Any]:
        """Get summary analysis with totals."""
        try:
            response = self.session.get(f"{self.base_url}/analysis/wi/{case_id}")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get summary analysis: {response.status_code}")
                return {}
        except Exception as e:
            print(f"Error getting summary analysis: {e}")
            return {}
    
    def compare_raw_vs_regex(self, case_id: str) -> Dict[str, Any]:
        """Compare raw text with regex extraction results."""
        print(f"🔍 Comparing raw text vs regex extraction for case {case_id}")
        
        # Get raw text
        raw_data = self.get_raw_text(case_id)
        if not raw_data:
            return {"error": "Failed to get raw text"}
        
        # Get regex analysis
        regex_data = self.get_regex_analysis(case_id)
        if not regex_data:
            return {"error": "Failed to get regex analysis"}
        
        comparison = {
            "case_id": case_id,
            "timestamp": datetime.now().isoformat(),
            "raw_text_summary": {},
            "regex_extraction_summary": {},
            "comparison_results": {},
            "suggestions": []
        }
        
        # Analyze raw text
        if "raw_texts" in raw_data:
            comparison["raw_text_summary"] = {
                "total_files": len(raw_data["raw_texts"]),
                "total_characters": sum(f["text_length"] for f in raw_data["raw_texts"]),
                "files": [{"name": f["file_name"], "length": f["text_length"]} for f in raw_data["raw_texts"]]
            }
        
        # Analyze regex extraction
        if "data" in regex_data:
            total_forms = 0
            total_fields = 0
            total_confidence = 0
            confidence_count = 0
            
            for file_result in regex_data["data"]:
                forms = file_result.get("forms", [])
                total_forms += len(forms)
                
                for form in forms:
                    fields = form.get("fields", [])
                    total_fields += len(fields)
                    
                    for field in fields:
                        confidence = field.get("confidence_score", 0)
                        total_confidence += confidence
                        confidence_count += 1
            
            comparison["regex_extraction_summary"] = {
                "total_files": len(regex_data["data"]),
                "total_forms": total_forms,
                "total_fields": total_fields,
                "average_confidence": total_confidence / confidence_count if confidence_count > 0 else 0
            }
        
        # Generate suggestions
        if comparison["raw_text_summary"] and comparison["regex_extraction_summary"]:
            raw_chars = comparison["raw_text_summary"]["total_characters"]
            extracted_fields = comparison["regex_extraction_summary"]["total_fields"]
            
            if raw_chars > 0 and extracted_fields == 0:
                comparison["suggestions"].append("No fields extracted - check regex patterns")
            elif raw_chars > 10000 and extracted_fields < 5:
                comparison["suggestions"].append("Low field extraction rate - consider improving patterns")
            
            avg_confidence = comparison["regex_extraction_summary"]["average_confidence"]
            if avg_confidence < 0.7:
                comparison["suggestions"].append("Low confidence scores - review pattern accuracy")
        
        return comparison
    
    def test_specific_patterns(self, case_id: str, patterns: List[str]) -> Dict[str, Any]:
        """Test specific regex patterns against raw text."""
        raw_data = self.get_raw_text(case_id)
        if not raw_data:
            return {"error": "Failed to get raw text"}
        
        results = {
            "case_id": case_id,
            "patterns_tested": patterns,
            "results": {}
        }
        
        for pattern in patterns:
            pattern_results = []
            
            for file_data in raw_data.get("raw_texts", []):
                text = file_data["raw_text"]
                matches = re.findall(pattern, text, re.IGNORECASE)
                
                pattern_results.append({
                    "file": file_data["file_name"],
                    "matches": matches,
                    "match_count": len(matches)
                })
            
            results["results"][pattern] = pattern_results
        
        return results

def print_endpoint_analysis():
    """Print comprehensive endpoint analysis."""
    analyzer = EndpointAnalyzer()
    categories = analyzer.extract_all_endpoints()
    
    print("=" * 80)
    print("🔍 COMPREHENSIVE ENDPOINT ANALYSIS")
    print("=" * 80)
    
    total_endpoints = 0
    for category, endpoints in categories.items():
        print(f"\n📁 {category.upper()} ({len(endpoints)} endpoints)")
        print("-" * 50)
        
        for endpoint in endpoints:
            total_endpoints += 1
            tags_str = ", ".join(endpoint["tags"]) if endpoint["tags"] else "No tags"
            summary = endpoint["summary"][:50] + "..." if len(endpoint["summary"]) > 50 else endpoint["summary"]
            
            print(f"  {endpoint['method']} {endpoint['path']}")
            print(f"    Tags: {tags_str}")
            if summary:
                print(f"    Summary: {summary}")
            print()
    
    print(f"\n📊 TOTAL ENDPOINTS: {total_endpoints}")
    
    # WI-specific endpoints
    wi_endpoints = analyzer.get_wi_endpoints()
    print(f"\n🎯 WI-RELATED ENDPOINTS ({len(wi_endpoints)}):")
    for endpoint in wi_endpoints:
        print(f"  {endpoint['method']} {endpoint['path']} - {endpoint['summary']}")
    
    # Regex testing endpoints
    regex_endpoints = analyzer.get_regex_testing_endpoints()
    print(f"\n🔧 REGEX TESTING ENDPOINTS ({len(regex_endpoints)}):")
    for endpoint in regex_endpoints:
        print(f"  {endpoint['method']} {endpoint['path']} - {endpoint['summary']}")

def print_regex_workflow():
    """Print regex testing workflow."""
    print("\n" + "=" * 80)
    print("🔧 REGEX TESTING WORKFLOW")
    print("=" * 80)
    
    print("""
📋 WORKFLOW FOR COMPARING RAW TEXT WITH REGEX EXTRACTION:

1. 🔐 AUTHENTICATION
   curl -X POST "http://localhost:8000/auth/login" \\
     -H "Content-Type: application/json" \\
     -d '{"username": "your_username", "password": "your_password"}'

2. 📄 GET RAW TEXT
   curl -X GET "http://localhost:8000/transcripts/raw/wi/{case_id}"
   
   This gives you the actual text content from PDFs for manual inspection.

3. 🔍 GET REGEX ANALYSIS
   curl -X GET "http://localhost:8000/transcripts/analysis/wi/{case_id}"
   
   This shows what the regex patterns extracted with confidence scores.

4. 📊 GET SUMMARY ANALYSIS
   curl -X GET "http://localhost:8000/analysis/wi/{case_id}"
   
   This gives you calculated totals and breakdowns.

5. 🔄 COMPARISON WORKFLOW:
   
   a) Look at raw text to see what's actually in the PDF
   b) Check regex analysis to see what was extracted
   c) Compare source lines with raw text
   d) Identify patterns that need improvement
   e) Update regex patterns in wi_patterns.py
   f) Test again with the same case

6. 🛠️ TOOLS FOR IMPROVEMENT:
   
   - Use /transcripts/analysis/wi/{case_id} to see confidence scores
   - Use /pattern-learning/regex-review/wi/{case_id} for detailed analysis
   - Use /batch/regex-review/wi for batch testing
   - Check source lines in regex analysis to see exact matches

7. 📝 PATTERN IMPROVEMENT PROCESS:
   
   a) Find low-confidence extractions in regex analysis
   b) Look at the source_line to see what was matched
   c) Check raw text to see what should have been matched
   d) Update the pattern in wi_patterns.py
   e) Test with multiple cases to ensure it works broadly
   f) Monitor confidence scores to validate improvements

8. 🎯 KEY ENDPOINTS FOR TESTING:
   
   Raw Text:     /transcripts/raw/wi/{case_id}
   Regex Analysis: /transcripts/analysis/wi/{case_id}
   Summary:      /analysis/wi/{case_id}
   Pattern Review: /pattern-learning/regex-review/wi/{case_id}
   Batch Testing: /batch/regex-review/wi

9. 📊 METRICS TO MONITOR:
   
   - Field extraction rate (fields found / expected fields)
   - Confidence scores (should be > 0.7 for good patterns)
   - Source line accuracy (extracted text matches raw text)
   - Pattern coverage (all expected form types detected)
""")

def main():
    """Main function to run the analysis."""
    print_endpoint_analysis()
    print_regex_workflow()
    
    # Example usage
    print("\n" + "=" * 80)
    print("💡 EXAMPLE USAGE")
    print("=" * 80)
    
    print("""
# Example: Test case 54820
workflow = RegexTestingWorkflow()

# 1. Authenticate
workflow.authenticate("username", "password")

# 2. Compare raw vs regex
comparison = workflow.compare_raw_vs_regex("54820")
print(json.dumps(comparison, indent=2))

# 3. Test specific patterns
patterns = [
    r'Wages[,\s]*tips[,\s]*and[,\s]*other[,\s]*compensation[:\s]*\$?([\d,\.]+)',
    r'Federal[,\s]*income[,\s]*tax[,\s]*withheld[:\s]*\$?([\d,\.]+)'
]
results = workflow.test_specific_patterns("54820", patterns)
print(json.dumps(results, indent=2))
""")

if __name__ == "__main__":
    main() 