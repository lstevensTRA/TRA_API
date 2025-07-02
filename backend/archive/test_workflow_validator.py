#!/usr/bin/env python3
"""
TRA API Workflow Validator

This script validates the complete workflow of TRA API endpoints in the correct dependency order.
It ensures that endpoints that depend on other endpoints are called after their dependencies are satisfied.

Usage:
    python test_workflow_validator.py --case-id 54820
    python test_workflow_validator.py --case-id 54820 --base-url http://localhost:8000
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
class TestResult:
    """Represents the result of a single endpoint test"""
    endpoint: str
    method: str
    status_code: int
    success: bool
    response_time: float
    error_message: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None
    dependencies_met: bool = True

@dataclass
class PhaseResult:
    """Represents the result of a complete phase"""
    phase_name: str
    tests: List[TestResult]
    success: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    phase_duration: float

@dataclass
class WorkflowResult:
    """Represents the complete workflow validation result"""
    case_id: str
    start_time: str
    end_time: str
    total_duration: float
    phases: List[PhaseResult]
    overall_success: bool
    total_endpoints_tested: int
    total_endpoints_passed: int
    total_endpoints_failed: int
    dependency_errors: List[str]

class WorkflowValidator:
    """Validates the complete TRA API workflow in proper dependency order"""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self.results: List[TestResult] = []
        self.dependency_errors: List[str] = []
        self.case_document_ids: Dict[str, List[str]] = {"wi": [], "at": []}
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def test_endpoint(self, method: str, endpoint: str, **kwargs) -> TestResult:
        """Test a single endpoint and return the result"""
        start_time = datetime.now()
        full_url = f"{self.base_url}{endpoint}"
        
        try:
            logger.info(f"Testing {method} {full_url}")
            
            if method.upper() == "GET":
                response = await self.client.get(full_url, **kwargs)
            elif method.upper() == "POST":
                response = await self.client.post(full_url, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            success = response.status_code < 400
            response_data = None
            
            if success and response.headers.get("content-type", "").startswith("application/json"):
                try:
                    response_data = response.json()
                except:
                    response_data = {"raw_response": str(response.content)}
            
            result = TestResult(
                endpoint=endpoint,
                method=method,
                status_code=response.status_code,
                success=success,
                response_time=response_time,
                error_message=None if success else f"HTTP {response.status_code}",
                response_data=response_data
            )
            
            if success:
                logger.info(f"✅ {method} {endpoint} - {response.status_code} ({response_time:.2f}s)")
            else:
                logger.error(f"❌ {method} {endpoint} - {response.status_code} ({response_time:.2f}s)")
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            logger.error(f"❌ {method} {endpoint} - Exception: {str(e)} ({response_time:.2f}s)")
            
            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                success=False,
                response_time=response_time,
                error_message=str(e)
            )
    
    def check_dependencies(self, phase_name: str, required_data: Dict[str, Any]) -> bool:
        """Check if required dependencies are met for a phase"""
        missing_deps = []
        
        for dep_name, dep_required in required_data.items():
            if dep_required and not any(r.success and r.endpoint.endswith(dep_name) for r in self.results):
                missing_deps.append(dep_name)
        
        if missing_deps:
            error_msg = f"Phase '{phase_name}' missing dependencies: {', '.join(missing_deps)}"
            self.dependency_errors.append(error_msg)
            logger.error(f"❌ {error_msg}")
            return False
        
        return True
    
    async def validate_discovery_phase(self, case_id: str) -> PhaseResult:
        """Phase 1: Data Discovery - Authenticate and discover available data"""
        logger.info("🔍 Starting Phase 1: Data Discovery")
        phase_start = datetime.now()
        phase_tests = []
        
        # 1. Health Check
        result = await self.test_endpoint("GET", "/health")
        phase_tests.append(result)
        self.results.append(result)
        
        # 2. Authentication
        result = await self.test_endpoint("GET", "/auth/login")
        phase_tests.append(result)
        self.results.append(result)
        
        # 3. Client Profile (Required for county info)
        result = await self.test_endpoint("GET", f"/client_profile/{case_id}")
        phase_tests.append(result)
        self.results.append(result)
        
        # 4. Transcript Discovery
        result = await self.test_endpoint("GET", f"/transcripts/wi/{case_id}")
        phase_tests.append(result)
        self.results.append(result)
        
        # Extract WI file IDs for later use
        if result.success and result.response_data:
            if "files" in result.response_data:
                self.case_document_ids["wi"] = [
                    file.get("case_document_id") for file in result.response_data["files"]
                    if file.get("case_document_id")
                ]
        
        result = await self.test_endpoint("GET", f"/transcripts/at/{case_id}")
        phase_tests.append(result)
        self.results.append(result)
        
        # Extract AT file IDs for later use
        if result.success and result.response_data:
            if "files" in result.response_data:
                self.case_document_ids["at"] = [
                    file.get("case_document_id") for file in result.response_data["files"]
                    if file.get("case_document_id")
                ]
        
        phase_end = datetime.now()
        phase_duration = (phase_end - phase_start).total_seconds()
        
        passed_tests = sum(1 for t in phase_tests if t.success)
        failed_tests = len(phase_tests) - passed_tests
        
        return PhaseResult(
            phase_name="Data Discovery",
            tests=phase_tests,
            success=failed_tests == 0,
            total_tests=len(phase_tests),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            phase_duration=phase_duration
        )
    
    async def validate_processing_phase(self, case_id: str) -> PhaseResult:
        """Phase 2: Data Processing - Parse transcript data and get IRS Standards"""
        logger.info("🔍 Starting Phase 2: Data Processing")
        phase_start = datetime.now()
        phase_tests = []
        
        # Check dependencies
        required_deps = {
            "client_profile": True,
            "transcripts/wi": True,
            "transcripts/at": True
        }
        
        if not self.check_dependencies("Data Processing", required_deps):
            # Return failed phase result
            phase_end = datetime.now()
            return PhaseResult(
                phase_name="Data Processing",
                tests=[],
                success=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                phase_duration=(phase_end - phase_start).total_seconds()
            )
        
        # 5. Parse WI Data
        result = await self.test_endpoint("GET", f"/transcripts/raw/wi/{case_id}")
        phase_tests.append(result)
        self.results.append(result)
        
        # 6. Parse AT Data
        result = await self.test_endpoint("GET", f"/transcripts/raw/at/{case_id}")
        phase_tests.append(result)
        self.results.append(result)
        
        # 7. IRS Standards (Depends on client profile for county info)
        result = await self.test_endpoint("GET", f"/irs-standards/case/{case_id}")
        phase_tests.append(result)
        self.results.append(result)
        
        phase_end = datetime.now()
        phase_duration = (phase_end - phase_start).total_seconds()
        
        passed_tests = sum(1 for t in phase_tests if t.success)
        failed_tests = len(phase_tests) - passed_tests
        
        return PhaseResult(
            phase_name="Data Processing",
            tests=phase_tests,
            success=failed_tests == 0,
            total_tests=len(phase_tests),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            phase_duration=phase_duration
        )
    
    async def validate_analysis_phase(self, case_id: str) -> PhaseResult:
        """Phase 3: Analysis & Calculations - Perform analysis and calculations"""
        logger.info("🔍 Starting Phase 3: Analysis & Calculations")
        phase_start = datetime.now()
        phase_tests = []
        
        # Check dependencies
        required_deps = {
            "transcripts/raw/wi": True,
            "transcripts/raw/at": True,
            "irs-standards/case": True
        }
        
        if not self.check_dependencies("Analysis & Calculations", required_deps):
            phase_end = datetime.now()
            return PhaseResult(
                phase_name="Analysis & Calculations",
                tests=[],
                success=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                phase_duration=(phase_end - phase_start).total_seconds()
            )
        
        # 8. WI Analysis
        result = await self.test_endpoint("GET", f"/analysis/wi/{case_id}")
        phase_tests.append(result)
        self.results.append(result)
        
        # 9. AT Analysis
        result = await self.test_endpoint("GET", f"/analysis/at/{case_id}")
        phase_tests.append(result)
        self.results.append(result)
        
        # 10. Disposable Income (Depends on client profile + IRS Standards)
        result = await self.test_endpoint("GET", f"/disposable-income/case/{case_id}")
        phase_tests.append(result)
        self.results.append(result)
        
        # 11. Income Comparison
        result = await self.test_endpoint("GET", f"/income-comparison/{case_id}")
        phase_tests.append(result)
        self.results.append(result)
        
        phase_end = datetime.now()
        phase_duration = (phase_end - phase_start).total_seconds()
        
        passed_tests = sum(1 for t in phase_tests if t.success)
        failed_tests = len(phase_tests) - passed_tests
        
        return PhaseResult(
            phase_name="Analysis & Calculations",
            tests=phase_tests,
            success=failed_tests == 0,
            total_tests=len(phase_tests),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            phase_duration=phase_duration
        )
    
    async def validate_document_phase(self, case_id: str) -> PhaseResult:
        """Phase 4: Document Generation - Download files and generate documents"""
        logger.info("🔍 Starting Phase 4: Document Generation")
        phase_start = datetime.now()
        phase_tests = []
        
        # Check dependencies
        required_deps = {
            "transcripts/raw/wi": True,
            "transcripts/raw/at": True
        }
        
        if not self.check_dependencies("Document Generation", required_deps):
            phase_end = datetime.now()
            return PhaseResult(
                phase_name="Document Generation",
                tests=[],
                success=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                phase_duration=(phase_end - phase_start).total_seconds()
            )
        
        # 12. Download WI Files (if available)
        for doc_id in self.case_document_ids["wi"][:2]:  # Limit to first 2 files
            result = await self.test_endpoint("GET", f"/transcripts/download/wi/{case_id}/{doc_id}")
            phase_tests.append(result)
            self.results.append(result)
        
        # 13. Download AT Files (if available)
        for doc_id in self.case_document_ids["at"][:2]:  # Limit to first 2 files
            result = await self.test_endpoint("GET", f"/transcripts/download/at/{case_id}/{doc_id}")
            phase_tests.append(result)
            self.results.append(result)
        
        # 14. Closing Letters
        result = await self.test_endpoint("GET", f"/closing-letters/{case_id}")
        phase_tests.append(result)
        self.results.append(result)
        
        # 15. Case Activities
        result = await self.test_endpoint("GET", f"/case-management/activities/{case_id}")
        phase_tests.append(result)
        self.results.append(result)
        
        phase_end = datetime.now()
        phase_duration = (phase_end - phase_start).total_seconds()
        
        passed_tests = sum(1 for t in phase_tests if t.success)
        failed_tests = len(phase_tests) - passed_tests
        
        return PhaseResult(
            phase_name="Document Generation",
            tests=phase_tests,
            success=failed_tests == 0,
            total_tests=len(phase_tests),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            phase_duration=phase_duration
        )
    
    async def validate_workflow(self, case_id: str) -> WorkflowResult:
        """Validate the complete workflow in proper dependency order"""
        logger.info(f"🚀 Starting workflow validation for case_id: {case_id}")
        start_time = datetime.now()
        
        try:
            # Phase 1: Data Discovery
            phase1 = await self.validate_discovery_phase(case_id)
            
            # Phase 2: Data Processing
            phase2 = await self.validate_processing_phase(case_id)
            
            # Phase 3: Analysis & Calculations
            phase3 = await self.validate_analysis_phase(case_id)
            
            # Phase 4: Document Generation
            phase4 = await self.validate_document_phase(case_id)
            
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            phases = [phase1, phase2, phase3, phase4]
            overall_success = all(phase.success for phase in phases)
            
            total_endpoints_tested = sum(phase.total_tests for phase in phases)
            total_endpoints_passed = sum(phase.passed_tests for phase in phases)
            total_endpoints_failed = sum(phase.failed_tests for phase in phases)
            
            result = WorkflowResult(
                case_id=case_id,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                total_duration=total_duration,
                phases=phases,
                overall_success=overall_success,
                total_endpoints_tested=total_endpoints_tested,
                total_endpoints_passed=total_endpoints_passed,
                total_endpoints_failed=total_endpoints_failed,
                dependency_errors=self.dependency_errors
            )
            
            # Log summary
            logger.info(f"📊 Workflow Validation Summary:")
            logger.info(f"   Total Duration: {total_duration:.2f}s")
            logger.info(f"   Overall Success: {'✅' if overall_success else '❌'}")
            logger.info(f"   Endpoints Tested: {total_endpoints_tested}")
            logger.info(f"   Endpoints Passed: {total_endpoints_passed}")
            logger.info(f"   Endpoints Failed: {total_endpoints_failed}")
            logger.info(f"   Dependency Errors: {len(self.dependency_errors)}")
            
            for phase in phases:
                status = "✅" if phase.success else "❌"
                logger.info(f"   {status} {phase.phase_name}: {phase.passed_tests}/{phase.total_tests} passed ({phase.phase_duration:.2f}s)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Workflow validation failed: {str(e)}")
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            return WorkflowResult(
                case_id=case_id,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                total_duration=total_duration,
                phases=[],
                overall_success=False,
                total_endpoints_tested=0,
                total_endpoints_passed=0,
                total_endpoints_failed=0,
                dependency_errors=[str(e)]
            )

def save_results(result: WorkflowResult, filename: str = None):
    """Save workflow results to a JSON file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"workflow_validation_{result.case_id}_{timestamp}.json"
    
    # Convert dataclass to dict for JSON serialization
    result_dict = asdict(result)
    
    with open(filename, 'w') as f:
        json.dump(result_dict, f, indent=2, default=str)
    
    logger.info(f"💾 Results saved to: {filename}")
    return filename

async def main():
    """Main function to run the workflow validator"""
    parser = argparse.ArgumentParser(description="TRA API Workflow Validator")
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
    
    async with WorkflowValidator(args.base_url, args.timeout) as validator:
        result = await validator.validate_workflow(args.case_id)
        
        if args.save_results:
            filename = save_results(result, args.output_file)
            print(f"\n📄 Detailed results saved to: {filename}")
        
        # Print summary to console
        print(f"\n{'='*60}")
        print(f"TRA API WORKFLOW VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"Case ID: {result.case_id}")
        print(f"Duration: {result.total_duration:.2f}s")
        print(f"Overall Success: {'✅ PASSED' if result.overall_success else '❌ FAILED'}")
        print(f"Endpoints: {result.total_endpoints_passed}/{result.total_endpoints_tested} passed")
        print(f"Dependency Errors: {len(result.dependency_errors)}")
        
        if result.dependency_errors:
            print(f"\n❌ Dependency Errors:")
            for error in result.dependency_errors:
                print(f"   • {error}")
        
        print(f"\n📊 Phase Results:")
        for phase in result.phases:
            status = "✅" if phase.success else "❌"
            print(f"   {status} {phase.phase_name}: {phase.passed_tests}/{phase.total_tests} passed ({phase.phase_duration:.2f}s)")
        
        print(f"{'='*60}")
        
        # Exit with appropriate code
        exit(0 if result.overall_success else 1)

if __name__ == "__main__":
    asyncio.run(main()) 