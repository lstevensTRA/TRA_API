import logging
import re
import json
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
import requests
from datetime import datetime
from ..utils.cookies import cookies_exist, get_cookies

logger = logging.getLogger(__name__)

router = APIRouter()

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
    """Get user agent from cookies dict or return default"""
    if isinstance(cookies, dict) and 'user_agent' in cookies:
        return cookies['user_agent']
    return 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# --- Helper functions ---
def extract_case_data(response_text: str) -> List[Dict[str, Any]]:
    """
    Extract the storeCase_Data array from the Logiqs Case.aspx HTML/JS response.
    Enhanced to handle different response formats and provide better error handling.
    """
    try:
        import re
        
        # DEBUG: Log response length and first 500 chars
        logger.info(f"Response length: {len(response_text)} characters")
        logger.info(f"Response preview: {response_text[:500]}...")
        
        # Use regex to find the exact pattern from the user's example
        # Looking for: this.storeCase_Data=[{...}];
        pattern = r'this\.storeCase_Data\s*=\s*(\[.*?\]);'
        match = re.search(pattern, response_text, re.DOTALL)
        
        if match:
            logger.info("✅ Found this.storeCase_Data pattern!")
            json_string = match.group(1)
            logger.info(f"JSON string length: {len(json_string)} characters")
            logger.info(f"JSON preview: {json_string[:200]}...")
            
            try:
                case_data = json.loads(json_string)
                logger.info(f"✅ Successfully parsed JSON with {len(case_data)} records")
                return case_data
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON decode error: {e}")
                logger.error(f"JSON string preview: {json_string[:200]}...")
                return []
        
        # Fallback: Try other patterns
        patterns = [
            'this.storeCase_Data=[',
            'storeCase_Data=[',
            'var storeCase_Data=[',
            'window.storeCase_Data=[',
            'caseData=[',
            'this.caseData=[',
            'this.storeCase_Data = [',
            'storeCase_Data = [',
            'var storeCase_Data = [',
            'window.storeCase_Data = ['
        ]
        
        data_start = -1
        pattern_used = None
        
        for pattern in patterns:
            data_start = response_text.find(pattern)
            if data_start != -1:
                pattern_used = pattern
                logger.info(f"✅ Found pattern: {pattern}")
                break
        
        if data_start == -1:
            logger.warning("❌ No case data patterns found in response")
            # Look for any JSON-like structures
            json_patterns = [
                r'\[.*\{.*"CaseID".*\}.*\]',  # Array with CaseID
                r'\{.*"CaseID".*\}',          # Object with CaseID
                r'\[.*\{.*"caseId".*\}.*\]',  # Array with caseId
                r'\{.*"caseId".*\}',          # Object with caseId
            ]
            
            for json_pattern in json_patterns:
                matches = re.findall(json_pattern, response_text, re.DOTALL)
                if matches:
                    logger.info(f"✅ Found JSON pattern: {json_pattern}")
                    try:
                        case_data = json.loads(matches[0])
                        if isinstance(case_data, list):
                            logger.info(f"Successfully extracted case data using JSON pattern")
                            return case_data
                        elif isinstance(case_data, dict):
                            logger.info(f"Successfully extracted single case using JSON pattern")
                            return [case_data]
                    except json.JSONDecodeError:
                        continue
            
            logger.warning("❌ Could not extract case data, returning empty structure")
            return []
        
        # Find the end of the array (look for the closing bracket followed by semicolon)
        data_end = data_start + len(pattern_used)
        bracket_count = 1
        in_string = False
        escape_next = False
        
        for i in range(data_start + len(pattern_used), len(response_text)):
            char = response_text[i]
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if char == '[' or char == '{':
                    bracket_count += 1
                elif char == ']' or char == '}':
                    bracket_count -= 1
                    if bracket_count == 0:
                        data_end = i + 1
                        break
        
        if bracket_count != 0:
            logger.warning("Bracket count mismatch, attempting to find end of data")
            # Try to find the end more conservatively
            for i in range(data_start + len(pattern_used), min(data_start + len(pattern_used) + 10000, len(response_text))):
                if response_text[i:i+2] == '];':
                    data_end = i + 2
                    break
        
        json_string = response_text[data_start + len(pattern_used):data_end]
        
        # Clean up the JSON string
        json_string = json_string.strip()
        if json_string.endswith(';'):
            json_string = json_string[:-1]
        
        case_data = json.loads(json_string)
        logger.info(f"Successfully extracted case data using pattern: {pattern_used}")
        return case_data
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in extract_case_data: {e}")
        logger.error(f"JSON string preview: {json_string[:200] if 'json_string' in locals() else 'N/A'}")
        # Return empty array instead of raising
        return []
    except Exception as e:
        logger.error(f"Error extracting case data: {e}")
        # Return empty array instead of raising
        return []

def flatten_case_data(case_array: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Flatten nested objects and parse MiscXML fields.
    """
    result = []
    for case_item in case_array:
        flattened = dict(case_item)
        misc_xml = flattened.get('MiscXML')
        if misc_xml:
            try:
                misc_data = json.loads(misc_xml)
                for k, v in misc_data.items():
                    flattened[f"Misc_{k}"] = v
            except Exception as e:
                logger.warning(f"Error parsing MiscXML: {e}")
        result.append(flattened)
    return result

# --- Endpoints ---
@router.get("/api/case/{case_id}", tags=["Case Data"], summary="Get complete case data", description="Fetch and parse case data from Logiqs Case.aspx, flatten MiscXML, and return as JSON.")
def get_case_data(case_id: str, product_id: int = Query(1, description="ProductID for Logiqs")):
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    # Get authenticated cookies and user-agent from the login flow
    cookies_data = get_cookies()
    cookie_header = _extract_cookie_header(cookies_data)
    user_agent = _get_user_agent(cookies_data)
    
    if not cookie_header:
        logger.error("❌ No valid cookies found for authentication")
        raise HTTPException(status_code=401, detail="No valid cookies found for authentication.")
    
    api_url = f"https://tps.logiqs.com/Cases/Case.aspx?CaseID={case_id}&ProductID={product_id}"
    logger.info(f"Fetching case data from: {api_url}")
    try:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'user-agent': user_agent,
            'referer': 'https://tps.logiqs.com/Default.aspx',
            'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'iframe',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'priority': 'u=0, i',
            'cookie': cookie_header
        }
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"HTTP {response.status_code} error from Logiqs API")
            raise HTTPException(status_code=response.status_code, detail=f"Logiqs API returned status {response.status_code}")
        
        # Log response preview for debugging
        response_preview = response.text[:500] if response.text else "Empty response"
        logger.debug(f"Logiqs response preview: {response_preview}")
        case_data = extract_case_data(response.text)
        if not case_data:
            logger.warning(f"No case data found for case_id: {case_id}")
            return {
                "success": False,
                "caseId": case_id,
                "productId": product_id,
                "totalRecords": 0,
                "data": [],
                "message": "No case data found in response"
            }
        processed_data = flatten_case_data(case_data)
        return {
            "success": True,
            "caseId": case_id,
            "productId": product_id,
            "totalRecords": len(processed_data),
            "data": processed_data
        }
    except Exception as e:
        logger.error(f"Error fetching case data: {e}")
        raise HTTPException(status_code=500, detail={
            "success": False,
            "error": "Failed to fetch case data",
            "message": str(e)
        })

@router.get("/api/case/{case_id}/fields", tags=["Case Data"], summary="Get specific fields from a case", description="Fetch and parse case data, return only requested fields.")
def get_case_fields(case_id: str, product_id: int = Query(1), fields: Optional[str] = Query(None, description="Comma-separated list of fields to return")):
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    # Get authenticated cookies and user-agent from the login flow
    cookies_data = get_cookies()
    cookie_header = _extract_cookie_header(cookies_data)
    user_agent = _get_user_agent(cookies_data)
    
    if not cookie_header:
        logger.error("❌ No valid cookies found for authentication")
        raise HTTPException(status_code=401, detail="No valid cookies found for authentication.")
    
    api_url = f"https://tps.logiqs.com/Cases/Case.aspx?CaseID={case_id}&ProductID={product_id}"
    try:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'user-agent': user_agent,
            'referer': 'https://tps.logiqs.com/Default.aspx',
            'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'iframe',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'priority': 'u=0, i',
            'cookie': cookie_header
        }
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"HTTP {response.status_code} error from Logiqs API")
            raise HTTPException(status_code=response.status_code, detail=f"Logiqs API returned status {response.status_code}")
        
        # Log response preview for debugging
        response_preview = response.text[:500] if response.text else "Empty response"
        logger.debug(f"Logiqs response preview: {response_preview}")
        case_data = extract_case_data(response.text)
        if not case_data:
            logger.warning(f"No case data found for case_id: {case_id}")
            return {
                "success": False,
                "caseId": case_id,
                "requestedFields": [f.strip() for f in fields.split(',')] if fields else None,
                "data": [],
                "message": "No case data found in response"
            }
        processed_data = flatten_case_data(case_data)
        requested_fields = [f.strip() for f in fields.split(',')] if fields else None
        filtered_data = processed_data
        if requested_fields:
            filtered_data = [
                {k: v for k, v in item.items() if k in requested_fields}
                for item in processed_data
            ]
        return {
            "success": True,
            "caseId": case_id,
            "requestedFields": requested_fields,
            "data": filtered_data
        }
    except Exception as e:
        logger.error(f"Error fetching case fields: {e}")
        raise HTTPException(status_code=500, detail={
            "success": False,
            "error": "Failed to fetch case fields",
            "message": str(e)
        })

@router.get("/api/case/{case_id}/schema", tags=["Case Data"], summary="Get all available field names", description="Return all unique field names for a case.")
def get_case_schema(case_id: str, product_id: int = Query(1)):
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    # Get authenticated cookies and user-agent from the login flow
    cookies_data = get_cookies()
    cookie_header = _extract_cookie_header(cookies_data)
    user_agent = _get_user_agent(cookies_data)
    
    if not cookie_header:
        logger.error("❌ No valid cookies found for authentication")
        raise HTTPException(status_code=401, detail="No valid cookies found for authentication.")
    
    api_url = f"https://tps.logiqs.com/Cases/Case.aspx?CaseID={case_id}&ProductID={product_id}"
    try:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'user-agent': user_agent,
            'referer': 'https://tps.logiqs.com/Default.aspx',
            'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'iframe',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'priority': 'u=0, i',
            'cookie': cookie_header
        }
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"HTTP {response.status_code} error from Logiqs API")
            raise HTTPException(status_code=response.status_code, detail=f"Logiqs API returned status {response.status_code}")
        
        # Log response preview for debugging
        response_preview = response.text[:500] if response.text else "Empty response"
        logger.debug(f"Logiqs response preview: {response_preview}")
        case_data = extract_case_data(response.text)
        if not case_data:
            logger.warning(f"No case data found for case_id: {case_id}")
            return {
                "success": False,
                "caseId": case_id,
                "totalFields": 0,
                "fields": [],
                "message": "No case data found in response"
            }
        processed_data = flatten_case_data(case_data)
        field_names = set()
        for item in processed_data:
            field_names.update(item.keys())
        sorted_fields = sorted(field_names)
        return {
            "success": True,
            "caseId": case_id,
            "totalFields": len(sorted_fields),
            "fields": sorted_fields
        }
    except Exception as e:
        logger.error(f"Error fetching case schema: {e}")
        raise HTTPException(status_code=500, detail={
            "success": False,
            "error": "Failed to fetch case schema",
            "message": str(e)
        })

@router.get("/health", tags=["Case Data"], summary="Health check", description="Health check endpoint.")
def health_check():
    return {"status": "OK", "timestamp": datetime.now().isoformat()}

@router.get("/api/case/search", tags=["Case Data"], summary="Search cases by query string", description="Search Logiqs cases using the Search.aspx page and return results.")
def search_cases(query: str = Query(..., description="Search string for Logiqs case search")):
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    # Get authenticated cookies and user-agent from the login flow
    cookies_data = get_cookies()
    cookie_header = _extract_cookie_header(cookies_data)
    user_agent = _get_user_agent(cookies_data)
    
    if not cookie_header:
        logger.error("❌ No valid cookies found for authentication")
        raise HTTPException(status_code=401, detail="No valid cookies found for authentication.")
    
    search_url = f"https://tps.logiqs.com/Cases/Search.aspx?search={query}"
    logger.info(f"Searching Logiqs cases with query: {query}")
    try:
        response = requests.get(search_url, headers={
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cookie': cookie_header
        }, timeout=30)
        html = response.text
        # Optionally, try to parse results if the HTML contains a table of cases
        # For now, just return the raw HTML
        return {
            "success": True,
            "query": query,
            "searchUrl": search_url,
            "rawHtml": html
        }
    except Exception as e:
        logger.error(f"Error searching Logiqs cases: {e}")
        raise HTTPException(status_code=500, detail={
            "success": False,
            "error": "Failed to search Logiqs cases",
            "message": str(e)
        })

@router.get("/api/case/{case_id}/connected", tags=["Case Data"], summary="Get connected cases", description="Fetch connected cases for a given caseId from Logiqs API.")
def get_connected_cases(case_id: str):
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    # Get authenticated cookies and user-agent from the login flow
    cookies_data = get_cookies()
    cookie_header = _extract_cookie_header(cookies_data)
    user_agent = _get_user_agent(cookies_data)
    
    if not cookie_header:
        logger.error("❌ No valid cookies found for authentication")
        raise HTTPException(status_code=401, detail="No valid cookies found for authentication.")
    
    api_url = f"https://tps.logiqs.com/API/Case/GetConnectedCases?caseId={case_id}"
    logger.info(f"Fetching connected cases from: {api_url}")
    try:
        response = requests.get(api_url, headers={
            'User-Agent': user_agent,
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'X-Requested-With': 'XMLHttpRequest',
            'Cookie': cookie_header
        }, timeout=30)
        # Try to parse as JSON
        try:
            data = response.json()
        except Exception as e:
            logger.error(f"Error parsing connected cases JSON: {e}")
            data = {"raw": response.text}
        return {
            "success": True,
            "caseId": case_id,
            "data": data
        }
    except Exception as e:
        logger.error(f"Error fetching connected cases: {e}")
        raise HTTPException(status_code=500, detail={
            "success": False,
            "error": "Failed to fetch connected cases",
            "message": str(e)
        }) 