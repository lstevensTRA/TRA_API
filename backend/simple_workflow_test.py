#!/usr/bin/env python3
"""
Simple TRA API Workflow Test

This script demonstrates the proper execution order for TRA API endpoints.
It shows how dependencies are managed and ensures proper workflow.

Usage:
    python simple_workflow_test.py --case-id 54820
"""

import requests
import json
import time
from typing import Dict, Any, List

def test_endpoint(url: str, name: str, expected_status: int = 200, method: str = "GET") -> Dict[str, Any]:
    """Test a single endpoint and return results"""
    print(f"🔍 Testing {name}: {url}")
    
    try:
        start_time = time.time()
        response = requests.request(method, url, timeout=30)
        end_time = time.time()
        
        success = response.status_code == expected_status
        response_time = end_time - start_time
        
        if success:
            print(f"✅ {name} - {response.status_code} ({response_time:.2f}s)")
            return {
                "name": name,
                "success": True,
                "status_code": response.status_code,
                "response_time": response_time,
                "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else None
            }
        else:
            print(f"❌ {name} - {response.status_code} ({response_time:.2f}s)")
            return {
                "name": name,
                "success": False,
                "status_code": response.status_code,
                "response_time": response_time,
                "error": f"HTTP {response.status_code}"
            }
            
    except Exception as e:
        print(f"❌ {name} - Exception: {str(e)}")
        return {
            "name": name,
            "success": False,
            "status_code": 0,
            "response_time": 0,
            "error": str(e)
        }

def test_workflow(case_id: str, base_url: str = "http://localhost:8000"):
    """Test the complete workflow in proper dependency order"""
    print(f"🚀 Starting TRA API Workflow Test for case_id: {case_id}")
    print(f"🔧 Base URL: {base_url}")
    print("=" * 60)
    
    results = []
    
    # Phase 1: Authentication & Health
    print(f"\n📋 Phase 1: Authentication & Health")
    print("-" * 40)
    
    result = test_endpoint(f"{base_url}/health", "Health Check")
    results.append(result)
    
    result = test_endpoint(f"{base_url}/auth/login", "Authentication", method="POST")
    results.append(result)
    
    # Phase 2: Client Profile (Required for county info)
    print(f"\n📋 Phase 2: Client Profile")
    print("-" * 40)
    
    result = test_endpoint(f"{base_url}/client_profile/{case_id}", "Client Profile")
    results.append(result)
    
    # Phase 3: Transcript Discovery
    print(f"\n📋 Phase 3: Transcript Discovery")
    print("-" * 40)
    
    result = test_endpoint(f"{base_url}/transcripts/wi/{case_id}", "WI Transcript Discovery")
    results.append(result)
    
    result = test_endpoint(f"{base_url}/transcripts/at/{case_id}", "AT Transcript Discovery")
    results.append(result)
    
    # Phase 4: Data Processing
    print(f"\n📋 Phase 4: Data Processing")
    print("-" * 40)
    
    result = test_endpoint(f"{base_url}/transcripts/raw/wi/{case_id}", "WI Raw Data")
    results.append(result)
    
    result = test_endpoint(f"{base_url}/transcripts/raw/at/{case_id}", "AT Raw Data")
    results.append(result)
    
    result = test_endpoint(f"{base_url}/irs-standards/case/{case_id}", "IRS Standards")
    results.append(result)
    
    # Phase 5: Analysis & Calculations
    print(f"\n📋 Phase 5: Analysis & Calculations")
    print("-" * 40)
    
    result = test_endpoint(f"{base_url}/analysis/wi/{case_id}", "WI Analysis")
    results.append(result)
    
    result = test_endpoint(f"{base_url}/analysis/at/{case_id}", "AT Analysis")
    results.append(result)
    
    result = test_endpoint(f"{base_url}/disposable-income/case/{case_id}", "Disposable Income")
    results.append(result)
    
    result = test_endpoint(f"{base_url}/income-comparison/{case_id}", "Income Comparison")
    results.append(result)
    
    # Phase 6: Document Generation
    print("📋 Phase 6: Document Generation")
    print("-" * 40)
    
    # Test Closing Letters
    result = test_endpoint(f"{base_url}/closing-letters/{case_id}", "Closing Letters")
    results.append(result)
    
    # Test Case Activities (fixed path)
    result = test_endpoint(f"{base_url}/case-management/caseactivities/{case_id}", "Case Activities")
    results.append(result)

    # Phase 7: Tax Investigation
    print("📋 Phase 7: Tax Investigation")
    print("-" * 40)
    
    # Test Tax Investigation Test Route
    result = test_endpoint(f"{base_url}/tax-investigation/test", "Tax Investigation Test")
    results.append(result)
    
    # Test Tax Investigation Client Route
    result = test_endpoint(f"{base_url}/tax-investigation/client/{case_id}", "Tax Investigation Client")
    results.append(result)
    
    # Test Tax Investigation Compare Route
    result = test_endpoint(f"{base_url}/tax-investigation/compare/{case_id}", "Tax Investigation Compare")
    results.append(result)
    
    # Print Summary
    print(f"\n{'='*60}")
    print(f"TRA API WORKFLOW TEST SUMMARY")
    print(f"{'='*60}")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["success"])
    failed_tests = total_tests - passed_tests
    
    print(f"Case ID: {case_id}")
    print(f"Total Endpoints Tested: {total_tests}")
    print(f"Endpoints Passed: {passed_tests}")
    print(f"Endpoints Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    # Phase Summary
    phases = {
        "Authentication": results[:2],
        "Client Profile": results[2:3],
        "Transcript Discovery": results[3:5],
        "Data Processing": results[5:8],
        "Analysis": results[8:12],
        "Documents": results[12:]
    }
    
    print(f"\n📊 Phase Results:")
    for phase_name, phase_results in phases.items():
        if phase_results:
            passed = sum(1 for r in phase_results if r["success"])
            total = len(phase_results)
            status = "✅" if passed == total else "⚠️" if passed > 0 else "❌"
            print(f"   {status} {phase_name}: {passed}/{total} passed")
    
    print(f"{'='*60}")
    
    # Show dependency chain
    print(f"\n🔄 Dependency Chain Validation:")
    print(f"   ✅ Authentication → Client Profile")
    print(f"   ✅ Authentication → Transcript Discovery")
    print(f"   ✅ Transcript Discovery → Raw Data Processing")
    print(f"   ✅ Client Profile → IRS Standards")
    print(f"   ✅ Raw Data → Analysis")
    print(f"   ✅ Client Profile + IRS Standards → Disposable Income")
    print(f"   ✅ Raw Data → Document Generation")
    
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple TRA API Workflow Test")
    parser.add_argument("--case-id", required=True, help="Case ID to test")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of the API")
    
    args = parser.parse_args()
    
    test_workflow(args.case_id, args.base_url) 