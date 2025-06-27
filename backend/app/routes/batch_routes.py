import logging
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional, Dict, Any, List
from app.utils.cookies import cookies_exist, get_cookies
import requests
import json
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.models.response_models import (
    BatchStatusResponse, CompletedCasesResponse, BatchAnalysisResponse, 
    CSVExportResponse, ErrorResponse
)

# Create logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/income-comparison", tags=["Batch Processing"])
async def batch_income_comparison(
    case_ids: List[str],
    background_tasks: BackgroundTasks
):
    """
    Perform income comparison analysis on multiple cases in batch.
    """
    logger.info(f"🔍 Received batch income comparison request for {len(case_ids)} cases")
    
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    if len(case_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 cases allowed per batch request")
    
    cookies = get_cookies()
    
    try:
        # Start batch processing in background
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Add background task
        background_tasks.add_task(process_batch_income_comparison, batch_id, case_ids, cookies)
        
        result = {
            "batch_id": batch_id,
            "total_cases": len(case_ids),
            "status": "processing",
            "message": f"Batch processing started for {len(case_ids)} cases",
            "started_at": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Started batch income comparison with batch_id: {batch_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error starting batch income comparison: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/completed-cases", tags=["Batch Processing"], response_model=CompletedCasesResponse)
def get_completed_cases():
    """
    Get all completed cases from Logiqs API.
    Returns list of case IDs that have status 349 (completed).
    """
    logger.info("🔍 Fetching all completed cases from Logiqs API")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        completed_cases = fetch_completed_cases(cookies)
        
        logger.info(f"✅ Successfully fetched {len(completed_cases)} completed cases")
        return CompletedCasesResponse(
            total_completed_cases=len(completed_cases),
            case_ids=[int(case_id) for case_id in completed_cases]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching completed cases: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{batch_id}/status", tags=["Batch Processing"], response_model=BatchStatusResponse)
def get_batch_status(batch_id: str):
    """
    Get the status of a batch processing job.
    """
    logger.info(f"🔍 Received batch status request for batch_id: {batch_id}")
    
    # This would typically check a database or cache for batch status
    # For now, return a mock status
    result = BatchStatusResponse(
        batch_id=batch_id,
        status="completed",
        total_cases=10,
        processed_cases=10,
        successful_cases=8,
        failed_cases=2,
        started_at=datetime.now().isoformat(),
        completed_at=datetime.now().isoformat(),
        errors=["Case 123456: No data found", "Case 789012: Authentication failed"]
    )
    
    logger.info(f"✅ Retrieved batch status for batch_id: {batch_id}")
    return result

@router.post("/transcript-analysis", tags=["Batch Processing"])
async def batch_transcript_analysis(
    case_ids: List[str],
    background_tasks: BackgroundTasks,
    transcript_types: List[str] = Query(["WI", "AT"], description="Types of transcripts to analyze")
):
    """
    Perform transcript analysis on multiple cases in batch.
    """
    logger.info(f"🔍 Received batch transcript analysis request for {len(case_ids)} cases")
    
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    if len(case_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 cases allowed per batch request")
    
    cookies = get_cookies()
    
    try:
        # Start batch processing in background
        batch_id = f"transcript_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Add background task
        background_tasks.add_task(process_batch_transcript_analysis, batch_id, case_ids, transcript_types, cookies)
        
        result = {
            "batch_id": batch_id,
            "total_cases": len(case_ids),
            "transcript_types": transcript_types,
            "status": "processing",
            "message": f"Batch transcript analysis started for {len(case_ids)} cases",
            "started_at": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Started batch transcript analysis with batch_id: {batch_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error starting batch transcript analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/case-summary", tags=["Batch Processing"])
async def batch_case_summary(
    case_ids: List[str],
    background_tasks: BackgroundTasks,
    include_activities: bool = Query(True, description="Include case activities in summary"),
    include_resolution: bool = Query(True, description="Include resolution details in summary")
):
    """
    Generate case summaries for multiple cases in batch.
    """
    logger.info(f"🔍 Received batch case summary request for {len(case_ids)} cases")
    
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    if len(case_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 cases allowed per batch request")
    
    cookies = get_cookies()
    
    try:
        # Start batch processing in background
        batch_id = f"summary_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Add background task
        background_tasks.add_task(process_batch_case_summary, batch_id, case_ids, include_activities, include_resolution, cookies)
        
        result = {
            "batch_id": batch_id,
            "total_cases": len(case_ids),
            "include_activities": include_activities,
            "include_resolution": include_resolution,
            "status": "processing",
            "message": f"Batch case summary started for {len(case_ids)} cases",
            "started_at": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Started batch case summary with batch_id: {batch_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error starting batch case summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/cases/by_status/{status_id}", tags=["Batch Processing"])
def get_cases_by_status(status_id: int):
    """
    Get all case IDs with the given status_id from Logiqs API.
    """
    import requests
    LOGIQS_API_KEY = "4917fa0ce4694529a9b97ead1a60c932"
    LOGIQS_URL = "https://tps.logiqs.com/publicapi/2020-02-22/cases/GetCasesByStatus"
    logger.info(f"🔍 Fetching all cases with status_id={status_id} from Logiqs API")
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        params = {
            "apikey": LOGIQS_API_KEY,
            "StatusID": status_id
        }
        response = requests.get(LOGIQS_URL, params=params, timeout=30)
        if response.status_code != 200:
            logger.error(f"Logiqs API error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch cases from Logiqs")
        data = response.json()
        # Expecting a list of cases, each with a CaseID field
        case_ids = [case["CaseID"] for case in data if "CaseID" in case]
        logger.info(f"✅ Successfully fetched {len(case_ids)} cases with status_id={status_id}")
        return {"status_id": status_id, "case_ids": case_ids, "total_cases": len(case_ids)}
    except Exception as e:
        logger.error(f"❌ Error fetching cases by status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def process_batch_income_comparison(batch_id: str, case_ids: List[str], cookies: dict):
    """
    Process batch income comparison in background.
    """
    logger.info(f"🔄 Starting batch income comparison processing for batch_id: {batch_id}")
    
    results = []
    errors = []
    
    # Process cases in parallel with limited concurrency
    with ThreadPoolExecutor(max_workers=5) as executor:
        loop = asyncio.get_event_loop()
        
        # Create tasks for each case
        tasks = []
        for case_id in case_ids:
            task = loop.run_in_executor(executor, process_single_income_comparison, case_id, cookies)
            tasks.append(task)
        
        # Wait for all tasks to complete
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(completed_results):
            case_id = case_ids[i]
            if isinstance(result, Exception):
                errors.append({
                    "case_id": case_id,
                    "error": str(result)
                })
                logger.error(f"❌ Error processing case {case_id}: {str(result)}")
            else:
                results.append({
                    "case_id": case_id,
                    "result": result
                })
                logger.info(f"✅ Successfully processed case {case_id}")
    
    # Store results (in a real implementation, this would be stored in a database)
    batch_results = {
        "batch_id": batch_id,
        "total_cases": len(case_ids),
        "successful_cases": len(results),
        "failed_cases": len(errors),
        "results": results,
        "errors": errors,
        "completed_at": datetime.now().isoformat()
    }
    
    logger.info(f"✅ Completed batch income comparison for batch_id: {batch_id}")
    return batch_results

def process_single_income_comparison(case_id: str, cookies: dict) -> Dict[str, Any]:
    """
    Process income comparison for a single case.
    """
    try:
        # Fetch case data
        case_data = fetch_case_data(case_id, cookies)
        
        # Extract client information
        from app.utils.client_info import extract_client_info
        client_info = extract_client_info(case_data)
        
        # Fetch WI data
        wi_data = fetch_wi_data(case_id, cookies)
        
        # Fetch AT data
        at_data = fetch_at_data(case_id, cookies)
        
        # Perform income comparison
        comparison_result = compare_income_data(client_info, wi_data, at_data)
        
        return {
            "case_id": case_id,
            "client_info": client_info,
            "wi_data": wi_data,
            "at_data": at_data,
            "comparison": comparison_result
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing income comparison for case {case_id}: {str(e)}")
        raise

async def process_batch_transcript_analysis(batch_id: str, case_ids: List[str], transcript_types: List[str], cookies: dict):
    """
    Process batch transcript analysis in background.
    """
    logger.info(f"🔄 Starting batch transcript analysis processing for batch_id: {batch_id}")
    
    results = []
    errors = []
    
    # Process cases in parallel with limited concurrency
    with ThreadPoolExecutor(max_workers=5) as executor:
        loop = asyncio.get_event_loop()
        
        # Create tasks for each case
        tasks = []
        for case_id in case_ids:
            task = loop.run_in_executor(executor, process_single_transcript_analysis, case_id, transcript_types, cookies)
            tasks.append(task)
        
        # Wait for all tasks to complete
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(completed_results):
            case_id = case_ids[i]
            if isinstance(result, Exception):
                errors.append({
                    "case_id": case_id,
                    "error": str(result)
                })
                logger.error(f"❌ Error processing case {case_id}: {str(result)}")
            else:
                results.append({
                    "case_id": case_id,
                    "result": result
                })
                logger.info(f"✅ Successfully processed case {case_id}")
    
    # Store results
    batch_results = {
        "batch_id": batch_id,
        "total_cases": len(case_ids),
        "transcript_types": transcript_types,
        "successful_cases": len(results),
        "failed_cases": len(errors),
        "results": results,
        "errors": errors,
        "completed_at": datetime.now().isoformat()
    }
    
    logger.info(f"✅ Completed batch transcript analysis for batch_id: {batch_id}")
    return batch_results

def process_single_transcript_analysis(case_id: str, transcript_types: List[str], cookies: dict) -> Dict[str, Any]:
    """
    Process transcript analysis for a single case.
    """
    try:
        result = {
            "case_id": case_id,
            "transcript_types": transcript_types,
            "analysis": {}
        }
        
        for transcript_type in transcript_types:
            if transcript_type.upper() == "WI":
                wi_data = fetch_wi_data(case_id, cookies)
                result["analysis"]["WI"] = analyze_wi_data(wi_data)
            elif transcript_type.upper() == "AT":
                at_data = fetch_at_data(case_id, cookies)
                result["analysis"]["AT"] = analyze_at_data(at_data)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error processing transcript analysis for case {case_id}: {str(e)}")
        raise

async def process_batch_case_summary(batch_id: str, case_ids: List[str], include_activities: bool, include_resolution: bool, cookies: dict):
    """
    Process batch case summary in background.
    """
    logger.info(f"🔄 Starting batch case summary processing for batch_id: {batch_id}")
    
    results = []
    errors = []
    
    # Process cases in parallel with limited concurrency
    with ThreadPoolExecutor(max_workers=5) as executor:
        loop = asyncio.get_event_loop()
        
        # Create tasks for each case
        tasks = []
        for case_id in case_ids:
            task = loop.run_in_executor(executor, process_single_case_summary, case_id, include_activities, include_resolution, cookies)
            tasks.append(task)
        
        # Wait for all tasks to complete
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(completed_results):
            case_id = case_ids[i]
            if isinstance(result, Exception):
                errors.append({
                    "case_id": case_id,
                    "error": str(result)
                })
                logger.error(f"❌ Error processing case {case_id}: {str(result)}")
            else:
                results.append({
                    "case_id": case_id,
                    "result": result
                })
                logger.info(f"✅ Successfully processed case {case_id}")
    
    # Store results
    batch_results = {
        "batch_id": batch_id,
        "total_cases": len(case_ids),
        "include_activities": include_activities,
        "include_resolution": include_resolution,
        "successful_cases": len(results),
        "failed_cases": len(errors),
        "results": results,
        "errors": errors,
        "completed_at": datetime.now().isoformat()
    }
    
    logger.info(f"✅ Completed batch case summary for batch_id: {batch_id}")
    return batch_results

def process_single_case_summary(case_id: str, include_activities: bool, include_resolution: bool, cookies: dict) -> Dict[str, Any]:
    """
    Process case summary for a single case.
    """
    try:
        # Fetch case data
        case_data = fetch_case_data(case_id, cookies)
        
        # Extract client information
        from app.utils.client_info import extract_client_info
        client_info = extract_client_info(case_data)
        
        result = {
            "case_id": case_id,
            "client_info": client_info,
            "case_data": case_data
        }
        
        if include_activities:
            # Fetch case activities
            activities = fetch_case_activities(case_id, cookies)
            result["activities"] = activities
        
        if include_resolution:
            # Extract resolution details
            resolution_details = extract_resolution_details(case_data)
            result["resolution"] = resolution_details
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error processing case summary for case {case_id}: {str(e)}")
        raise

# Helper functions (these would be imported from other modules in a real implementation)
def fetch_case_data(case_id: str, cookies: dict) -> Dict[str, Any]:
    """Fetch case data from Logiqs."""
    # Implementation would be similar to other modules
    return {}

def fetch_wi_data(case_id: str, cookies: dict) -> Dict[str, Any]:
    """Fetch WI data from Logiqs."""
    # Implementation would be similar to other modules
    return {}

def fetch_at_data(case_id: str, cookies: dict) -> Dict[str, Any]:
    """Fetch AT data from Logiqs."""
    # Implementation would be similar to other modules
    return {}

def fetch_case_activities(case_id: str, cookies: dict) -> List[Dict[str, Any]]:
    """Fetch case activities from Logiqs."""
    # Implementation would be similar to other modules
    return []

def compare_income_data(client_info: Dict[str, Any], wi_data: Dict[str, Any], at_data: Dict[str, Any]) -> Dict[str, Any]:
    """Compare income data from different sources."""
    # Implementation would be similar to income comparison module
    return {}

def analyze_wi_data(wi_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze WI data."""
    # Implementation would be similar to analysis module
    return {}

def analyze_at_data(at_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze AT data."""
    # Implementation would be similar to analysis module
    return {}

def extract_resolution_details(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract resolution details from case data."""
    # Implementation would be similar to case management module
    return {}

def fetch_completed_cases(cookies: Dict[str, Any]) -> List[str]:
    """
    Fetch all completed cases from Logiqs API.
    Returns list of case IDs that have status 349 (completed).
    """
    logger.info("🔍 Fetching completed cases from Logiqs API")
    
    try:
        # This would typically make an API call to Logiqs
        # For now, return mock data
        completed_cases = ["54820", "697391", "123456", "789012", "345678"]
        logger.info(f"✅ Found {len(completed_cases)} completed cases")
        return completed_cases
    except Exception as e:
        logger.error(f"❌ Error fetching completed cases: {str(e)}")
        raise Exception(f"Error fetching completed cases: {str(e)}") 