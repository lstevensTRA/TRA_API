from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import httpx
import logging
from ..models.response_models import CountyResponse, IRSStandardsResponse
from ..utils.cookies import cookies_exist, get_cookies
from ..utils.city_county_lookup import city_lookup
from datetime import datetime

router = APIRouter(tags=["IRS Standards"])

# Logiqs API endpoints
LOGIQS_BASE_URL = "https://tps.logiqs.com/API/CaseInterview"

def _extract_cookie_header(cookies: dict) -> str:
    """Extract cookie header string from cookies dict"""
    if not cookies:
        return None
    
    if isinstance(cookies, dict) and 'cookies' in cookies:
        return "; ".join([f"{c['name']}={c['value']}" for c in cookies['cookies']])
    elif isinstance(cookies, str):
        return cookies
    
    return None

def _get_user_agent(cookies: dict) -> str:
    """Extract user agent from cookies dict"""
    if cookies and isinstance(cookies, dict) and 'user_agent' in cookies:
        return cookies['user_agent']
    return 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

@router.get("/counties/{state}", response_model=List[CountyResponse])
async def get_counties_by_state(state: str):
    """
    Get list of counties for a given state from Logiqs API.
    
    Args:
        state: Two-letter state code (e.g., "CA", "NY", "TX")
    
    Returns:
        List of counties with their IDs and names
    """
    try:
        # Check authentication
        if not cookies_exist():
            logging.error("❌ Authentication required - no cookies found")
            raise HTTPException(status_code=401, detail="Authentication required.")
        
        # Get authenticated cookies
        cookies_data = get_cookies()
        cookie_header = _extract_cookie_header(cookies_data)
        user_agent = _get_user_agent(cookies_data)
        
        if not cookie_header:
            logging.error("❌ No valid cookies found for authentication")
            raise HTTPException(status_code=401, detail="No valid cookies found for authentication.")
        
        # Make request to Logiqs API
        url = f"{LOGIQS_BASE_URL}/GetCounties"
        params = {"state": state.upper()}
        
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": user_agent,
            "Cookie": cookie_header
        }
        
        logging.info(f"🌐 Making API request to: {url}")
        logging.info(f"📊 Request params: {params}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, 
                params=params, 
                headers=headers,
                timeout=30,
                follow_redirects=False
            )
            
            logging.info(f"📊 Response status: {response.status_code}")
            logging.info(f"📊 Response headers: {dict(response.headers)}")
            
            if response.status_code == 302:
                location = response.headers.get("Location", "").lower()
                logging.warning(f"⚠️ Received 302 redirect to: {location}")
                if "login" in location or "default.aspx" in location:
                    logging.error("❌ Redirected to login page - authentication failed")
                    raise HTTPException(status_code=401, detail="Authentication required. Please ensure cookies are valid.")
            
            if response.status_code != 200:
                logging.error(f"Logiqs API error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch counties from Logiqs")
            
            data = response.json()
            
            if data.get("Error", True):
                logging.error(f"Logiqs API returned error: {data}")
                raise HTTPException(status_code=400, detail="Logiqs API returned an error")
            
            counties = data.get("Result", [])
            logging.info(f"✅ Retrieved {len(counties)} counties for state {state}")
            
            return counties
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching counties for state {state}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/standards", response_model=IRSStandardsResponse)
async def get_irs_standards(
    family_members_under_65: int = 1,
    family_members_over_65: int = 0,
    county_id: int = 203
):
    """
    Get IRS Standards for a specific county and family composition.
    
    Args:
        family_members_under_65: Number of family members under 65
        family_members_over_65: Number of family members 65 and over
        county_id: County ID from the counties endpoint
    
    Returns:
        IRS Standards data from Logiqs
    """
    try:
        # Check authentication
        if not cookies_exist():
            logging.error("❌ Authentication required - no cookies found")
            raise HTTPException(status_code=401, detail="Authentication required.")
        
        # Get authenticated cookies
        cookies_data = get_cookies()
        cookie_header = _extract_cookie_header(cookies_data)
        user_agent = _get_user_agent(cookies_data)
        
        if not cookie_header:
            logging.error("❌ No valid cookies found for authentication")
            raise HTTPException(status_code=401, detail="No valid cookies found for authentication.")
        
        # Make request to Logiqs API
        url = f"{LOGIQS_BASE_URL}/GetIRSStandards"
        params = {
            "familyMemberUnder65": family_members_under_65,
            "familyMemberOver65": family_members_over_65,
            "countyID": county_id
        }
        
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": user_agent,
            "Cookie": cookie_header
        }
        
        logging.info(f"🌐 Making API request to: {url}")
        logging.info(f"📊 Request params: {params}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, 
                params=params, 
                headers=headers,
                timeout=30,
                follow_redirects=False
            )
            
            logging.info(f"📊 Response status: {response.status_code}")
            logging.info(f"📊 Response headers: {dict(response.headers)}")
            
            if response.status_code == 302:
                location = response.headers.get("Location", "").lower()
                logging.warning(f"⚠️ Received 302 redirect to: {location}")
                if "login" in location or "default.aspx" in location:
                    logging.error("❌ Redirected to login page - authentication failed")
                    raise HTTPException(status_code=401, detail="Authentication required. Please ensure cookies are valid.")
            
            if response.status_code != 200:
                logging.error(f"Logiqs API error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch IRS standards from Logiqs")
            
            data = response.json()
            
            if data.get("Error", True):
                logging.error(f"Logiqs API returned error: {data}")
                raise HTTPException(status_code=400, detail="Logiqs API returned an error")
            
            logging.info(f"✅ Retrieved IRS standards for county {county_id} with {family_members_under_65} under 65 and {family_members_over_65} over 65")
            
            return data
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching IRS standards: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/states", response_model=List[Dict[str, str]])
async def get_states():
    """
    Get list of all available states with their codes.
    
    Returns:
        List of states with name and value (code)
    """
    states = [
        {"stateName": "Alabama", "value": "AL"},
        {"stateName": "Alaska", "value": "AK"},
        {"stateName": "Arizona", "value": "AZ"},
        {"stateName": "Arkansas", "value": "AR"},
        {"stateName": "California", "value": "CA"},
        {"stateName": "Colorado", "value": "CO"},
        {"stateName": "Connecticut", "value": "CT"},
        {"stateName": "Delaware", "value": "DE"},
        {"stateName": "District Of Columbia", "value": "DC"},
        {"stateName": "Florida", "value": "FL"},
        {"stateName": "Georgia", "value": "GA"},
        {"stateName": "Hawaii", "value": "HI"},
        {"stateName": "Idaho", "value": "ID"},
        {"stateName": "Illinois", "value": "IL"},
        {"stateName": "Indiana", "value": "IN"},
        {"stateName": "Iowa", "value": "IA"},
        {"stateName": "Kansas", "value": "KS"},
        {"stateName": "Kentucky", "value": "KY"},
        {"stateName": "Louisiana", "value": "LA"},
        {"stateName": "Maine", "value": "ME"},
        {"stateName": "Maryland", "value": "MD"},
        {"stateName": "Massachusetts", "value": "MA"},
        {"stateName": "Michigan", "value": "MI"},
        {"stateName": "Minnesota", "value": "MN"},
        {"stateName": "Mississippi", "value": "MS"},
        {"stateName": "Missouri", "value": "MO"},
        {"stateName": "Montana", "value": "MT"},
        {"stateName": "Nebraska", "value": "NE"},
        {"stateName": "Nevada", "value": "NV"},
        {"stateName": "New Hampshire", "value": "NH"},
        {"stateName": "New Jersey", "value": "NJ"},
        {"stateName": "New Mexico", "value": "NM"},
        {"stateName": "New York", "value": "NY"},
        {"stateName": "North Carolina", "value": "NC"},
        {"stateName": "North Dakota", "value": "ND"},
        {"stateName": "Ohio", "value": "OH"},
        {"stateName": "Oklahoma", "value": "OK"},
        {"stateName": "Oregon", "value": "OR"},
        {"stateName": "Pennsylvania", "value": "PA"},
        {"stateName": "Rhode Island", "value": "RI"},
        {"stateName": "South Carolina", "value": "SC"},
        {"stateName": "South Dakota", "value": "SD"},
        {"stateName": "Tennessee", "value": "TN"},
        {"stateName": "Texas", "value": "TX"},
        {"stateName": "Utah", "value": "UT"},
        {"stateName": "Vermont", "value": "VT"},
        {"stateName": "Virginia", "value": "VA"},
        {"stateName": "Washington", "value": "WA"},
        {"stateName": "West Virginia", "value": "WV"},
        {"stateName": "Wisconsin", "value": "WI"},
        {"stateName": "Wyoming", "value": "WY"},
        {"stateName": "Puerto Rico", "value": "PR"},
        {"stateName": "Virgin Islands", "value": "VI"},
        {"stateName": "Northern Mariana Islands", "value": "MP"},
        {"stateName": "Guam", "value": "GU"},
        {"stateName": "American Samoa", "value": "AS"},
        {"stateName": "Palau", "value": "PW"}
    ]
    
    return states 

@router.get("/case/{case_id}", response_model=IRSStandardsResponse)
async def get_irs_standards_for_case(case_id: str):
    """
    Get IRS Standards for a specific case by automatically fetching client profile data.
    
    This endpoint:
    1. Gets the client profile for the case
    2. Extracts county_id, family_members_under_65, and family_members_over_65
    3. Calls IRS Standards with the correct parameters
    4. Returns the IRS Standards data
    
    Args:
        case_id: Case ID to get IRS Standards for
    
    Returns:
        IRS Standards data for the case
    """
    try:
        # Step 1: Get client profile
        logging.info(f"🔍 Getting client profile for case_id: {case_id}")
        
        # Check authentication for client profile
        if not cookies_exist():
            logging.error("❌ Authentication required - no cookies found")
            raise HTTPException(status_code=401, detail="Authentication required.")
        
        cookies_data = get_cookies()
        cookie_header = _extract_cookie_header(cookies_data)
        user_agent = _get_user_agent(cookies_data)
        
        if not cookie_header:
            logging.error("❌ No valid cookies found for authentication")
            raise HTTPException(status_code=401, detail="No valid cookies found for authentication.")
        
        # Get client profile from Logiqs API
        LOGIQS_API_KEY = "4917fa0ce4694529a9b97ead1a60c932"
        LOGIQS_API_URL = "https://tps.logiqs.com/publicapi/2020-02-22/cases/caseinfo"
        
        params = {
            "apikey": LOGIQS_API_KEY,
            "CaseID": case_id
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(LOGIQS_API_URL, params=params)
            if resp.status_code != 200:
                raise HTTPException(status_code=404, detail="Case not found")
            data = resp.json()
        
        raw = data.get("data", {})
        misc = raw.get("MiscXML", {})
        
        # Extract required data from client profile
        state = raw.get("State")
        city = raw.get("City")
        members_under_65 = _to_int(misc.get("FamilyMembersUnder65"))
        members_over_65 = _to_int(misc.get("FamilyMembersOver65"))
        household_size = _to_int(misc.get("ClientDetailHousehold"))
        
        # Use defaults only if the values are None (not if they're 0)
        if members_under_65 is None:
            members_under_65 = 1
        if members_over_65 is None:
            members_over_65 = 0
        if household_size is None:
            household_size = members_under_65 + members_over_65
        
        logging.info(f"📊 Client data - State: {state}, City: {city}, Under 65: {members_under_65}, Over 65: {members_over_65}, Household size: {household_size}")
        logging.info(f"📊 Raw MiscXML data - FamilyMembersUnder65: {misc.get('FamilyMembersUnder65')}, FamilyMembersOver65: {misc.get('FamilyMembersOver65')}, ClientDetailHousehold: {misc.get('ClientDetailHousehold')}")
        
        # Step 2: Get county information
        county_info = await _get_county_info(state, city) if state else {"county_id": None, "county_name": None}
        county_id = county_info.get("county_id")
        
        if not county_id:
            logging.warning(f"⚠️ No county ID found for case {case_id}, using default county_id=203")
            county_id = 203
        
        logging.info(f"🏛️ Using county_id: {county_id} ({county_info.get('county_name', 'Unknown')})")
        
        # Step 3: Get IRS Standards
        logging.info(f"📋 Getting IRS Standards for county {county_id} with {members_under_65} under 65, {members_over_65} over 65, household size {household_size}")
        
        url = f"{LOGIQS_BASE_URL}/GetIRSStandards"
        params = {
            "familyMemberUnder65": members_under_65,
            "familyMemberOver65": members_over_65,
            "countyID": county_id
        }
        logging.info(f"📤 IRS Standards API params: {params}")
        
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": user_agent,
            "Cookie": cookie_header
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, 
                params=params, 
                headers=headers,
                timeout=30,
                follow_redirects=False
            )
            
            if response.status_code == 302:
                location = response.headers.get("Location", "").lower()
                logging.warning(f"⚠️ Received 302 redirect to: {location}")
                if "login" in location or "default.aspx" in location:
                    logging.error("❌ Redirected to login page - authentication failed")
                    raise HTTPException(status_code=401, detail="Authentication required. Please ensure cookies are valid.")
            
            if response.status_code != 200:
                logging.error(f"Logiqs API error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch IRS standards from Logiqs")
            
            data = response.json()
            
            if data.get("Error", True):
                logging.error(f"Logiqs API returned error: {data}")
                raise HTTPException(status_code=400, detail="Logiqs API returned an error")
            
            # Add metadata about the case
            data["case_metadata"] = {
                "case_id": case_id,
                "state": state,
                "city": city,
                "county_id": county_id,
                "county_name": county_info.get("county_name"),
                "family_members_under_65": members_under_65,
                "family_members_over_65": members_over_65,
                "household_size": household_size
            }
            
            logging.info(f"✅ Successfully retrieved IRS Standards for case {case_id}")
            
            return data
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting IRS Standards for case {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def _to_int(val):
    """Convert value to integer, return None if conversion fails"""
    try:
        return int(val)
    except (TypeError, ValueError):
        return None

async def _get_county_info(state: str, city: str) -> dict:
    """Get county information based on state and city using intelligent lookup"""
    try:
        # Check if we have authentication cookies
        if not cookies_exist():
            logging.warning("No authentication cookies found, skipping county lookup")
            return {"county_id": None, "county_name": None}
        
        cookies_data = get_cookies()
        cookie_header = _extract_cookie_header(cookies_data)
        user_agent = _get_user_agent(cookies_data)
        
        if not cookie_header:
            logging.warning("No valid cookies found, skipping county lookup")
            return {"county_id": None, "county_name": None}
        
        # Get counties for the state
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": user_agent,
            "Cookie": cookie_header
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                LOGIQS_BASE_URL + "/GetCounties",
                params={"state": state.upper()},
                headers=headers,
                timeout=30,
                follow_redirects=False
            )
            
            if response.status_code != 200:
                logging.warning(f"Failed to get counties for state {state}: {response.status_code}")
                return {"county_id": None, "county_name": None}
            
            data = response.json()
            if data.get("Error", True):
                logging.warning(f"Logiqs API returned error for counties: {data}")
                return {"county_id": None, "county_name": None}
            
            counties = data.get("Result", [])
            
            # Use the intelligent city-to-county lookup
            county_info = city_lookup.get_county_for_city(city, state, counties)
            
            if county_info:
                logging.info(f"Found county for {city}, {state}: {county_info['county_name']} (ID: {county_info['county_id']})")
                return county_info
            else:
                logging.warning(f"No county found for {city}, {state}")
                return {"county_id": None, "county_name": None}
            
    except Exception as e:
        logging.warning(f"Error getting county info: {str(e)}")
        return {"county_id": None, "county_name": None}

@router.post("/validate", response_model=Dict[str, Any])
async def validate_irs_standards(
    county_id: int,
    household_sizes: List[Dict[str, int]] = [
        {"under_65": 1, "over_65": 0},
        {"under_65": 2, "over_65": 0},
        {"under_65": 1, "over_65": 1},
        {"under_65": 0, "over_65": 1}
    ]
):
    """
    Validate IRS Standards for a specific county across multiple household sizes.
    
    This endpoint tests the IRS Standards API against the direct Logiqs API
    to ensure your API is returning correct values.
    
    Args:
        county_id: County ID to test
        household_sizes: List of household configurations to test
    
    Returns:
        Validation results comparing your API vs direct Logiqs API
    """
    try:
        # Check authentication
        if not cookies_exist():
            logging.error("❌ Authentication required - no cookies found")
            raise HTTPException(status_code=401, detail="Authentication required.")
        
        cookies_data = get_cookies()
        cookie_header = _extract_cookie_header(cookies_data)
        user_agent = _get_user_agent(cookies_data)
        
        if not cookie_header:
            logging.error("❌ No valid cookies found for authentication")
            raise HTTPException(status_code=401, detail="No valid cookies found for authentication.")
        
        validation_results = {
            "county_id": county_id,
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "success_rate": 0.0
            }
        }
        
        for household in household_sizes:
            under_65 = household.get("under_65", 1)
            over_65 = household.get("over_65", 0)
            
            logging.info(f"🧪 Validating county {county_id} - {under_65} under 65, {over_65} over 65")
            
            # Test your API
            your_api_result = await _get_irs_standards_internal(
                under_65, over_65, county_id, cookie_header, user_agent
            )
            
            # Test direct Logiqs API
            direct_result = await _get_direct_irs_standards(
                under_65, over_65, county_id, cookie_header, user_agent
            )
            
            # Compare results
            comparison = _compare_irs_standards_results(your_api_result, direct_result)
            
            test_result = {
                "household": household,
                "your_api": your_api_result,
                "direct_api": direct_result,
                "comparison": comparison,
                "passed": comparison["match"]
            }
            
            validation_results["tests"].append(test_result)
            validation_results["summary"]["total_tests"] += 1
            
            if comparison["match"]:
                validation_results["summary"]["passed"] += 1
                logging.info(f"✅ PASS: County {county_id} - {under_65} under 65, {over_65} over 65")
            else:
                validation_results["summary"]["failed"] += 1
                logging.error(f"❌ FAIL: County {county_id} - {under_65} under 65, {over_65} over 65")
                logging.error(f"   Differences: {comparison['differences']}")
        
        # Calculate success rate
        total = validation_results["summary"]["total_tests"]
        passed = validation_results["summary"]["passed"]
        validation_results["summary"]["success_rate"] = (passed / total * 100) if total > 0 else 0
        
        logging.info(f"📊 Validation complete for county {county_id}: {passed}/{total} tests passed ({validation_results['summary']['success_rate']:.1f}%)")
        
        return validation_results
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error validating IRS Standards for county {county_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def _get_irs_standards_internal(under_65: int, over_65: int, county_id: int, cookie_header: str, user_agent: str) -> Dict[str, Any]:
    """Internal function to get IRS Standards from your API"""
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
            "User-Agent": user_agent,
            "Cookie": cookie_header
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, 
                params=params, 
                headers=headers,
                timeout=30,
                follow_redirects=False
            )
            
            if response.status_code != 200:
                return {"error": f"HTTP {response.status_code}", "success": False}
            
            data = response.json()
            if data.get("Error", True):
                return {"error": "API Error", "details": data, "success": False}
            
            return {"data": data.get("Result", {}), "success": True}
            
    except Exception as e:
        return {"error": str(e), "success": False}

async def _get_direct_irs_standards(under_65: int, over_65: int, county_id: int, cookie_header: str, user_agent: str) -> Dict[str, Any]:
    """Get IRS Standards directly from Logiqs API"""
    # This is the same as your API for now, but could be different if you add processing
    return await _get_irs_standards_internal(under_65, over_65, county_id, cookie_header, user_agent)

def _compare_irs_standards_results(your_result: Dict, direct_result: Dict) -> Dict[str, Any]:
    """Compare results from your API vs direct API"""
    if not your_result.get("success") or not direct_result.get("success"):
        return {
            "match": False,
            "error": "One or both APIs failed",
            "your_error": your_result.get("error"),
            "direct_error": direct_result.get("error")
        }
    
    your_data = your_result.get("data", {})
    direct_data = direct_result.get("data", {})
    
    # Compare key fields
    key_fields = ["Food", "Housing", "OperatingCostCar", "HealthOutOfPocket", "Apparel", "PersonalCare", "Misc", "PublicTrans"]
    differences = {}
    all_match = True
    
    for field in key_fields:
        your_val = your_data.get(field)
        direct_val = direct_data.get(field)
        
        if your_val != direct_val:
            differences[field] = {
                "your_api": your_val,
                "direct_api": direct_val,
                "difference": abs(your_val - direct_val) if your_val and direct_val else None
            }
            all_match = False
    
    return {
        "match": all_match,
        "differences": differences,
        "your_data": your_data,
        "direct_data": direct_data
    } 