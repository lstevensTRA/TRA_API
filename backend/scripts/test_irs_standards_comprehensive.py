#!/usr/bin/env python3
"""
Comprehensive IRS Standards Testing Suite

This script tests IRS Standards across different household sizes and counties
to ensure the API works correctly for all scenarios.
"""

import asyncio
import json
import httpx
import logging
from typing import Dict, List, Any, Tuple
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configurations
HOUSEHOLD_SIZES = [
    {"under_65": 1, "over_65": 0, "description": "Single person under 65"},
    {"under_65": 2, "over_65": 0, "description": "Two people under 65"},
    {"under_65": 1, "over_65": 1, "description": "One under 65, one over 65"},
    {"under_65": 2, "over_65": 1, "description": "Two under 65, one over 65"},
    {"under_65": 0, "over_65": 1, "description": "Single person over 65"},
    {"under_65": 0, "over_65": 2, "description": "Two people over 65"},
]

# Sample counties to test (major counties from different states)
SAMPLE_COUNTIES = [
    {"state": "CA", "county_id": 187, "county_name": "Los Angeles County"},
    {"state": "NY", "county_id": 1001, "county_name": "New York County"},
    {"state": "TX", "county_id": 2001, "county_name": "Harris County"},
    {"state": "FL", "county_id": 3001, "county_name": "Miami-Dade County"},
    {"state": "IL", "county_id": 708, "county_name": "Cook County"},
    {"state": "WI", "county_id": 3111, "county_name": "Milwaukee County"},
    {"state": "OH", "county_id": 4001, "county_name": "Cuyahoga County"},
    {"state": "PA", "county_id": 5001, "county_name": "Philadelphia County"},
]

# API configuration
API_BASE_URL = "http://localhost:8000"
LOGIQS_BASE_URL = "https://tps.logiqs.com/API/CaseInterview"

# Authentication (set these before running)
COOKIE_HEADER = None
USER_AGENT = None

class IRSStandardsTester:
    def __init__(self):
        self.results = []
        self.errors = []
        self.test_count = 0
        self.pass_count = 0
        self.fail_count = 0
    
    async def test_irs_standards_direct(self, county_id: int, under_65: int, over_65: int) -> Dict[str, Any]:
        """Test direct IRS Standards API call"""
        try:
            url = f"{LOGIQS_BASE_URL}/GetIRSStandards"
            params = {
                "familyMemberUnder65": under_65,
                "familyMemberOver65": over_65,
                "countyID": county_id
            }
            
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "User-Agent": USER_AGENT,
                "Cookie": COOKIE_HEADER
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, 
                    params=params, 
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code != 200:
                    return {"error": f"HTTP {response.status_code}", "success": False}
                
                data = response.json()
                if data.get("Error", True):
                    return {"error": "API Error", "details": data, "success": False}
                
                return {"data": data.get("Result", {}), "success": True}
                
        except Exception as e:
            return {"error": str(e), "success": False}
    
    async def test_irs_standards_api(self, county_id: int, under_65: int, over_65: int) -> Dict[str, Any]:
        """Test your API's IRS Standards endpoint"""
        try:
            url = f"{API_BASE_URL}/irs-standards/standards"
            params = {
                "family_members_under_65": under_65,
                "family_members_over_65": over_65,
                "county_id": county_id
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=30)
                
                if response.status_code != 200:
                    return {"error": f"HTTP {response.status_code}", "success": False}
                
                data = response.json()
                if data.get("Error", True):
                    return {"error": "API Error", "details": data, "success": False}
                
                return {"data": data.get("Result", {}), "success": True}
                
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def compare_results(self, direct_result: Dict, api_result: Dict) -> Dict[str, Any]:
        """Compare results from direct API vs your API"""
        if not direct_result.get("success") or not api_result.get("success"):
            return {
                "match": False,
                "error": "One or both APIs failed",
                "direct_error": direct_result.get("error"),
                "api_error": api_result.get("error")
            }
        
        direct_data = direct_result.get("data", {})
        api_data = api_result.get("data", {})
        
        # Compare key fields
        key_fields = ["Food", "Housing", "OperatingCostCar", "HealthOutOfPocket"]
        differences = {}
        all_match = True
        
        for field in key_fields:
            direct_val = direct_data.get(field)
            api_val = api_data.get(field)
            
            if direct_val != api_val:
                differences[field] = {
                    "direct": direct_val,
                    "api": api_val,
                    "difference": abs(direct_val - api_val) if direct_val and api_val else None
                }
                all_match = False
        
        return {
            "match": all_match,
            "differences": differences,
            "direct_data": direct_data,
            "api_data": api_data
        }
    
    async def run_single_test(self, county: Dict, household: Dict) -> Dict[str, Any]:
        """Run a single test case"""
        county_id = county["county_id"]
        under_65 = household["under_65"]
        over_65 = household["over_65"]
        
        test_info = {
            "county": county,
            "household": household,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"🧪 Testing {county['county_name']} ({county['state']}) - {household['description']}")
        
        # Test direct API
        direct_result = await self.test_irs_standards_direct(county_id, under_65, over_65)
        
        # Test your API
        api_result = await self.test_irs_standards_api(county_id, under_65, over_65)
        
        # Compare results
        comparison = self.compare_results(direct_result, api_result)
        
        test_result = {
            **test_info,
            "direct_result": direct_result,
            "api_result": api_result,
            "comparison": comparison,
            "passed": comparison["match"]
        }
        
        self.test_count += 1
        if comparison["match"]:
            self.pass_count += 1
            logger.info(f"✅ PASS: {county['county_name']} - {household['description']}")
        else:
            self.fail_count += 1
            logger.error(f"❌ FAIL: {county['county_name']} - {household['description']}")
            logger.error(f"   Differences: {comparison['differences']}")
        
        return test_result
    
    async def run_comprehensive_test(self):
        """Run comprehensive testing across all configurations"""
        logger.info("🚀 Starting comprehensive IRS Standards testing...")
        logger.info(f"📊 Testing {len(SAMPLE_COUNTIES)} counties × {len(HOUSEHOLD_SIZES)} household sizes = {len(SAMPLE_COUNTIES) * len(HOUSEHOLD_SIZES)} total tests")
        
        for county in SAMPLE_COUNTIES:
            for household in HOUSEHOLD_SIZES:
                result = await self.run_single_test(county, household)
                self.results.append(result)
                
                # Add delay to avoid overwhelming APIs
                await asyncio.sleep(0.5)
        
        # Generate summary
        self.generate_summary()
        
        # Save results
        self.save_results()
    
    def generate_summary(self):
        """Generate test summary"""
        logger.info("\n" + "="*60)
        logger.info("📊 TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"Total tests: {self.test_count}")
        logger.info(f"Passed: {self.pass_count}")
        logger.info(f"Failed: {self.fail_count}")
        logger.info(f"Success rate: {(self.pass_count/self.test_count)*100:.1f}%")
        
        if self.fail_count > 0:
            logger.info("\n❌ FAILED TESTS:")
            for result in self.results:
                if not result["passed"]:
                    county = result["county"]
                    household = result["household"]
                    logger.info(f"  - {county['county_name']} ({county['state']}) - {household['description']}")
                    if result["comparison"]["differences"]:
                        for field, diff in result["comparison"]["differences"].items():
                            logger.info(f"    {field}: Direct={diff['direct']}, API={diff['api']}")
    
    def save_results(self):
        """Save test results to file"""
        output_dir = Path("test_results")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = output_dir / f"irs_standards_test_results_{timestamp}.json"
        
        summary = {
            "test_summary": {
                "total_tests": self.test_count,
                "passed": self.pass_count,
                "failed": self.fail_count,
                "success_rate": (self.pass_count/self.test_count)*100 if self.test_count > 0 else 0
            },
            "test_configuration": {
                "household_sizes": HOUSEHOLD_SIZES,
                "sample_counties": SAMPLE_COUNTIES
            },
            "detailed_results": self.results
        }
        
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"📁 Test results saved to: {results_file}")

async def test_specific_cases():
    """Test specific problematic cases"""
    logger.info("🔍 Testing specific problematic cases...")
    
    # Test the Chicago case that was failing
    chicago_test = {
        "county": {"state": "IL", "county_id": 708, "county_name": "Cook County"},
        "household": {"under_65": 1, "over_65": 0, "description": "Single person under 65"}
    }
    
    tester = IRSStandardsTester()
    result = await tester.run_single_test(chicago_test["county"], chicago_test["household"])
    
    logger.info(f"Chicago test result: {'PASS' if result['passed'] else 'FAIL'}")
    if not result["passed"]:
        logger.error(f"Chicago test differences: {result['comparison']['differences']}")

if __name__ == "__main__":
    # Check authentication
    if not COOKIE_HEADER or not USER_AGENT:
        logger.error("❌ Please set COOKIE_HEADER and USER_AGENT before running this script")
        logger.info("💡 You can get these from your browser's developer tools or from your existing API calls")
        exit(1)
    
    # Run tests
    tester = IRSStandardsTester()
    asyncio.run(tester.run_comprehensive_test())
    
    # Test specific cases
    asyncio.run(test_specific_cases()) 