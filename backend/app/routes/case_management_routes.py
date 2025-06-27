import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from app.utils.cookies import cookies_exist, get_cookies
from app.models.response_models import (
    CaseClosingNotesResponse, CaseActivitiesResponse, ResolutionSummary
)
import requests
import re
from datetime import datetime

# Create logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()

def fetch_case_activity(case_id: str, cookies: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fetch case activity from Logiqs API.
    """
    logger.info(f"📋 Fetching case activity for case_id: {case_id}")
    
    try:
        # This would make an actual API call to Logiqs
        # For now, return mock data
        return []
    except Exception as e:
        logger.error(f"❌ Error fetching case activity: {str(e)}")
        raise Exception(f"Error fetching case activity: {str(e)}")

@router.get("/case-closing-notes/{case_id}", tags=["Case Management"], 
           summary="Get Case Closing Notes",
           description="Get case closing notes and resolution details from Logiqs.",
           response_model=CaseClosingNotesResponse)
def get_case_closing_notes(case_id: str):
    """
    Get case closing notes and resolution details from Logiqs.
    """
    logger.info(f"🔍 Received case closing notes request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch case activity
        logger.info(f"📋 Fetching case activity for case_id: {case_id}")
        activity_data = fetch_case_activity(case_id, cookies)
        
        # Extract closing notes
        logger.info(f"🔍 Extracting closing notes from activity data")
        closing_notes = []
        for activity in activity_data:
            if activity.get('subject', '').lower() in ['closing notes', 'resolution', 'case closed']:
                closing_notes.append({
                    "activity_id": activity.get('activity_id'),
                    "subject": activity.get('subject'),
                    "description": activity.get('description'),
                    "created_date": activity.get('created_date'),
                    "created_by": activity.get('created_by')
                })
        
        logger.info(f"✅ Extracted {len(closing_notes)} closing notes")
        
        # Parse resolution details from closing notes
        logger.info(f"🔍 Parsing resolution details from closing notes")
        resolution_details = None
        if closing_notes:
            # This would parse the closing notes to extract resolution details
            # For now, return a default structure
            resolution_details = ResolutionSummary()
        
        logger.info(f"✅ Parsed resolution details: {resolution_details}")
        
        logger.info(f"✅ Successfully retrieved case closing notes for case_id: {case_id}")
        
        return CaseClosingNotesResponse(
            case_id=case_id,
            total_activities=len(activity_data),
            closing_notes=closing_notes,
            resolution_details=resolution_details or ResolutionSummary()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting case closing notes for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/activities/{case_id}", tags=["Case Management"], 
           summary="Get Case Activities",
           description="Get case activities with optional filtering.",
           response_model=CaseActivitiesResponse)
def get_case_activities(
    case_id: str,
    subject_filter: Optional[str] = Query(None, title="Subject Filter"),
    activity_id: Optional[int] = Query(None, title="Activity Id")
):
    """
    Get case activities with optional filtering.
    """
    logger.info(f"🔍 Received case activities request for case_id: {case_id}")
    if subject_filter:
        logger.info(f"🔍 Subject filter: {subject_filter}")
    if activity_id:
        logger.info(f"🔍 Activity ID filter: {activity_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch case activity
        logger.info(f"📋 Fetching case activity for case_id: {case_id}")
        activity_data = fetch_case_activity(case_id, cookies)
        
        # Apply filters
        filtered_activities = []
        for activity in activity_data:
            include_activity = True
            
            if subject_filter:
                subject = activity.get('subject', '').lower()
                if subject_filter.lower() not in subject:
                    include_activity = False
            
            if activity_id and activity.get('activity_id') != activity_id:
                include_activity = False
            
            if include_activity:
                filtered_activities.append({
                    "activity_id": activity.get('activity_id'),
                    "subject": activity.get('subject'),
                    "description": activity.get('description'),
                    "created_date": activity.get('created_date'),
                    "created_by": activity.get('created_by'),
                    "activity_type": activity.get('activity_type')
                })
        
        logger.info(f"✅ Successfully retrieved case activities for case_id: {case_id}")
        
        return CaseActivitiesResponse(
            case_id=case_id,
            total_activities=len(activity_data),
            filtered_activities=len(filtered_activities),
            activities=filtered_activities,
            filters_applied={
                "subject_filter": subject_filter,
                "activity_id": activity_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting case activities for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 