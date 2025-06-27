#!/usr/bin/env python3
"""
TRA API Complete Workflow Test

This script tests the complete workflow of TRA API endpoints in the correct dependency order.
It ensures that endpoints that depend on other endpoints are called after their dependencies are satisfied.

Usage:
    python test_complete_workflow.py --case-id 54820
    python test_complete_workflow.py --case-id 54820 --save-results
"""

import asyncio
import httpx
import json
import logging
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@dataclass
class EndpointTest:
    """Represents a single endpoint test"""
    name: str
    method: str
    url: str
    description: str
    dependencies: List[str]
    required: bool = True
    expected_status: int = 200

@dataclass
class TestResult:
    """Represents the result of a single endpoint test"""
    endpoint: EndpointTest
    status_code: int
    success: bool
    response_time: float
    error_message: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None
    dependencies_met: bool = True

@dataclass
class WorkflowTestResult:
    """Represents the complete workflow test result"""
    case_id: str
    start_time: str
    end_time: str
    total_duration: float
    results: List[TestResult]
    overall_success: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    dependency_errors: List[str]
    phase_summary: Dict[str, Any]

class CompleteWorkflowTester:
    """Tests the complete TRA API workflow in proper dependency order"""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self.results: List[TestResult] = []
        self.dependency_errors: List[str] = []
        self.case_document_ids: Dict[str, List[str]] = {"wi": [], "at": []}
        
        # Define the complete workflow with dependencies
        self.workflow = self._define_workflow()
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _define_workflow(self) -> List[EndpointTest]:
        """Define the complete workflow with proper dependencies"""
        return [
            # Phase 1: Authentication & Health
            EndpointTest(
                name="Health Check",
                method="GET",
                url="/health",
                description="Verify API is running",
                dependencies=[],
                required=True
            ),
            EndpointTest(
                name="Authentication",
                method="GET",
                url="/auth/login",
                description="Authenticate with the API",
                dependencies=[],
                required=True
            ),
            
            # Phase 2: Client Profile (Required for county info)
            EndpointTest(
                name="Client Profile",
                method="GET",
                url="/client_profile/{case_id}",
                description="Get client profile and county information",
                dependencies=["Authentication"],
                required=True
            ),
            
            # Phase 3: Transcript Discovery
            EndpointTest(
                name="WI Transcript Discovery",
                method="GET",
                url="/transcripts/wi/{case_id}",
                description="Discover available WI transcript files",
                dependencies=["Authentication"],
                required=True
            ),
            EndpointTest(
                name="AT Transcript Discovery",
                method="GET",
                url="/transcripts/at/{case_id}",
                description="Discover available AT transcript files",
                dependencies=["Authentication"],
                required=True
            ),
            
            # Phase 4: Data Processing
            EndpointTest(
                name="WI Raw Data",
                method="GET",
                url="/transcripts/raw/wi/{case_id}",
                description="Parse WI transcript data",
                dependencies=["WI Transcript Discovery"],
                required=True
            ),
            EndpointTest(
                name="AT Raw Data",
                method="GET",
                url="/transcripts/raw/at/{case_id}",
                description="Parse AT transcript data",
                dependencies=["AT Transcript Discovery"],
                required=True
            ),
            EndpointTest(
                name="IRS Standards",
                method="GET",
                url="/irs-standards/case/{case_id}",
                description="Get IRS Standards for client's county",
                dependencies=["Client Profile"],
                required=True
            ),
            
            # Phase 5: Analysis & Calculations
            EndpointTest(
                name="WI Analysis",
                method="GET",
                url="/analysis/wi/{case_id}",
                description="Perform WI analysis with summary",
                dependencies=["WI Raw Data"],
                required=True
            ),
            EndpointTest(
                name="AT Analysis",
                method="GET",
                url="/analysis/at/{case_id}",
                description="Perform AT analysis with summary",
                dependencies=["AT Raw Data"],
                required=True
            ),
            EndpointTest(
                name="Disposable Income",
                method="GET",
                url="/disposable-income/case/{case_id}",
                description="Calculate disposable income",
                dependencies=["Client Profile", "IRS Standards"],
                required=True
            ),
            EndpointTest(
                name="Income Comparison",
                method="GET",
                url="/income-comparison/{case_id}",
                description="Compare income from different sources",
                dependencies=["WI Raw Data", "AT Raw Data"],
                required=False
            ),
            
            # Phase 6: Document Generation
            EndpointTest(
                name="Closing Letters",
                method="GET",
                url="/closing-letters/{case_id}",
                description="Get closing letters for the case",
                dependencies=["WI Raw Data", "AT Raw Data"],
                required=False
            ),
            EndpointTest(
                name="Case Activities",
                method="GET",
                url="/case-management/activities/{case_id}",
                description="Get case management activities",
                dependencies=["Authentication"],
                required=False
            ),
            EndpointTest(
                name="Tax Investigation Client",
                method="GET",
                url="/tax-investigation/client/{case_id}",
                description="Get tax investigation client info",
                dependencies=["Authentication"],
                required=False
            ),
        ]
    
    def check_dependencies(self, endpoint: EndpointTest) -> bool:
        """Check if all dependencies for an endpoint are met"""
        if not endpoint.dependencies:
            return True
        
        for dep in endpoint.dependencies:
            # Find a successful result for this dependency
            dep_success = any(
                r.success and r.endpoint.name == dep 
                for r in self.results
            )
            
            if not dep_success:
                error_msg = f"Endpoint '{endpoint.name}' missing dependency: {dep}"
                self.dependency_errors.append(error_msg)
                logger.error(f"❌ {error_msg}")
                return False
        
        return True
    
    async def test_endpoint(self, endpoint: EndpointTest, case_id: str) -> TestResult:
        """Test a single endpoint"""
        start_time = datetime.now()
        full_url = f"{self.base_url}{endpoint.url.format(case_id=case_id)}"
        
        try:
            logger.info(f"Testing {endpoint.name}: {endpoint.method} {full_url}")
            
            if endpoint.method.upper() == "GET":
                response = await self.client.get(full_url)
            elif endpoint.method.upper() == "POST":
                response = await self.client.post(full_url)
            else:
                raise ValueError(f"Unsupported HTTP method: {endpoint.method}")
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            success = response.status_code == endpoint.expected_status
            response_data = None
            
            if success and response.headers.get("content-type", "").startswith("application/json"):
                try:
                    response_data = response.json()
                except:
                    response_data = {"raw_response": str(response.content)}
            
            # Extract file IDs for download tests
            if endpoint.name in ["WI Transcript Discovery", "AT Transcript Discovery"] and success and response_data:
                if "files" in response_data:
                    file_type = "wi" if "WI" in endpoint.name else "at"
                    self.case_document_ids[file_type] = [
                        file.get("case_document_id") for file in response_data["files"]
                        if file.get("case_document_id")
                    ]
            
            result = TestResult(
                endpoint=endpoint,
                status_code=response.status_code,
                success=success,
                response_time=response_time,
                error_message=None if success else f"HTTP {response.status_code}",
                response_data=response_data
            )
            
            if success:
                logger.info(f"✅ {endpoint.name} - {response.status_code} ({response_time:.2f}s)")
            else:
                logger.error(f"❌ {endpoint.name} - {response.status_code} ({response_time:.2f}s)")
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            logger.error(f"❌ {endpoint.name} - Exception: {str(e)} ({response_time:.2f}s)")
            
            return TestResult(
                endpoint=endpoint,
                status_code=0,
                success=False,
                response_time=response_time,
                error_message=str(e)
            )
    
    async def test_workflow(self, case_id: str) -> WorkflowTestResult:
        """Test the complete workflow in proper dependency order"""
        logger.info(f"🚀 Starting complete workflow test for case_id: {case_id}")
        start_time = datetime.now()
        
        try:
            # Test each endpoint in order, checking dependencies
            for endpoint in self.workflow:
                # Check dependencies
                dependencies_met = self.check_dependencies(endpoint)
                
                if not dependencies_met and endpoint.required:
                    logger.warning(f"⚠️ Skipping required endpoint '{endpoint.name}' due to missing dependencies")
                    continue
                
                # Test the endpoint
                result = await self.test_endpoint(endpoint, case_id)
                result.dependencies_met = dependencies_met
                self.results.append(result)
                
                # If this is a required endpoint and it failed, we might want to stop
                if endpoint.required and not result.success:
                    logger.warning(f"⚠️ Required endpoint '{endpoint.name}' failed, but continuing...")
            
            # Add download tests if we have file IDs
            await self._test_downloads(case_id)
            
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            # Calculate summary
            total_tests = len(self.results)
            passed_tests = sum(1 for r in self.results if r.success)
            failed_tests = total_tests - passed_tests
            
            # Create phase summary
            phase_summary = self._create_phase_summary()
            
            result = WorkflowTestResult(
                case_id=case_id,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                total_duration=total_duration,
                results=self.results,
                overall_success=failed_tests == 0,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                dependency_errors=self.dependency_errors,
                phase_summary=phase_summary
            )
            
            # Log summary
            self._log_summary(result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Workflow test failed: {str(e)}")
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            return WorkflowTestResult(
                case_id=case_id,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                total_duration=total_duration,
                results=self.results,
                overall_success=False,
                total_tests=len(self.results),
                passed_tests=sum(1 for r in self.results if r.success),
                failed_tests=len(self.results) - sum(1 for r in self.results if r.success),
                dependency_errors=[str(e)],
                phase_summary={}
            )
    
    async def _test_downloads(self, case_id: str):
        """Test document downloads if we have file IDs"""
        # Test WI downloads
        for doc_id in self.case_document_ids["wi"][:1]:  # Limit to 1 file
            endpoint = EndpointTest(
                name=f"WI Download {doc_id}",
                method="GET",
                url=f"/transcripts/download/wi/{{case_id}}/{doc_id}",
                description=f"Download WI file {doc_id}",
                dependencies=["WI Raw Data"],
                required=False
            )
            
            result = await self.test_endpoint(endpoint, case_id)
            self.results.append(result)
        
        # Test AT downloads
        for doc_id in self.case_document_ids["at"][:1]:  # Limit to 1 file
            endpoint = EndpointTest(
                name=f"AT Download {doc_id}",
                method="GET",
                url=f"/transcripts/download/at/{{case_id}}/{doc_id}",
                description=f"Download AT file {doc_id}",
                dependencies=["AT Raw Data"],
                required=False
            )
            
            result = await self.test_endpoint(endpoint, case_id)
            self.results.append(result)
    
    def _create_phase_summary(self) -> Dict[str, Any]:
        """Create a summary of results by phase"""
        phases = {
            "Authentication": [],
            "Client Profile": [],
            "Transcript Discovery": [],
            "Data Processing": [],
            "Analysis": [],
            "Documents": []
        }
        
        for result in self.results:
            endpoint_name = result.endpoint.name
            
            if "Health" in endpoint_name or "Auth" in endpoint_name:
                phases["Authentication"].append(result)
            elif "Client Profile" in endpoint_name:
                phases["Client Profile"].append(result)
            elif "Discovery" in endpoint_name:
                phases["Transcript Discovery"].append(result)
            elif "Raw" in endpoint_name or "IRS Standards" in endpoint_name:
                phases["Data Processing"].append(result)
            elif "Analysis" in endpoint_name or "Income" in endpoint_name or "Disposable" in endpoint_name:
                phases["Analysis"].append(result)
            else:
                phases["Documents"].append(result)
        
        # Calculate phase statistics
        phase_stats = {}
        for phase_name, phase_results in phases.items():
            if phase_results:
                total = len(phase_results)
                passed = sum(1 for r in phase_results if r.success)
                failed = total - passed
                avg_time = sum(r.response_time for r in phase_results) / total
                
                phase_stats[phase_name] = {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "success_rate": (passed / total) * 100 if total > 0 else 0,
                    "avg_response_time": avg_time
                }
        
        return phase_stats
    
    def _log_summary(self, result: WorkflowTestResult):
        """Log a comprehensive summary of the test results"""
        logger.info(f"📊 Complete Workflow Test Summary:")
        logger.info(f"   Total Duration: {result.total_duration:.2f}s")
        logger.info(f"   Overall Success: {'✅' if result.overall_success else '❌'}")
        logger.info(f"   Endpoints Tested: {result.total_tests}")
        logger.info(f"   Endpoints Passed: {result.passed_tests}")
        logger.info(f"   Endpoints Failed: {result.failed_tests}")
        logger.info(f"   Dependency Errors: {len(result.dependency_errors)}")
        
        logger.info(f"\n📋 Phase Summary:")
        for phase_name, stats in result.phase_summary.items():
            status = "✅" if stats["failed"] == 0 else "⚠️"
            logger.info(f"   {status} {phase_name}: {stats['passed']}/{stats['total']} passed ({stats['success_rate']:.1f}%) - {stats['avg_response_time']:.2f}s avg")

def save_results(result: WorkflowTestResult, filename: str = None):
    """Save workflow results to a JSON file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"complete_workflow_test_{result.case_id}_{timestamp}.json"
    
    # Convert dataclass to dict for JSON serialization
    result_dict = asdict(result)
    
    with open(filename, 'w') as f:
        json.dump(result_dict, f, indent=2, default=str)
    
    logger.info(f"💾 Results saved to: {filename}")
    return filename

async def main():
    """Main function to run the complete workflow test"""
    parser = argparse.ArgumentParser(description="TRA API Complete Workflow Test")
    parser.add_argument("--case-id", required=True, help="Case ID to test")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--save-results", action="store_true", help="Save results to JSON file")
    parser.add_argument("--output-file", help="Output file name for results")
    
    args = parser.parse_args()
    
    logger.info(f"🔧 Configuration:")
    logger.info(f"   Case ID: {args.case_id}")
    logger.info(f"   Base URL: {args.base_url}")
    logger.info(f"   Timeout: {args.timeout}s")
    logger.info(f"   Save Results: {args.save_results}")
    
    async with CompleteWorkflowTester(args.base_url, args.timeout) as tester:
        result = await tester.test_workflow(args.case_id)
        
        if args.save_results:
            filename = save_results(result, args.output_file)
            print(f"\n📄 Detailed results saved to: {filename}")
        
        # Print summary to console
        print(f"\n{'='*60}")
        print(f"TRA API COMPLETE WORKFLOW TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Case ID: {result.case_id}")
        print(f"Duration: {result.total_duration:.2f}s")
        print(f"Overall Success: {'✅ PASSED' if result.overall_success else '❌ FAILED'}")
        print(f"Endpoints: {result.passed_tests}/{result.total_tests} passed")
        print(f"Dependency Errors: {len(result.dependency_errors)}")
        
        if result.dependency_errors:
            print(f"\n❌ Dependency Errors:")
            for error in result.dependency_errors:
                print(f"   • {error}")
        
        print(f"\n📊 Phase Results:")
        for phase_name, stats in result.phase_summary.items():
            status = "✅" if stats["failed"] == 0 else "⚠️"
            print(f"   {status} {phase_name}: {stats['passed']}/{stats['total']} passed ({stats['success_rate']:.1f}%)")
        
        print(f"{'='*60}")
        
        # Exit with appropriate code
        exit(0 if result.overall_success else 1)

if __name__ == "__main__":
    asyncio.run(main()) 