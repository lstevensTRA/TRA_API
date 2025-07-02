import logging
import re
import json
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Helper functions ---
def extract_case_data(response_text: str) -> List[Dict[str, Any]]:
    """
    Extract the storeCase_Data array from the Logiqs Case.aspx HTML/JS response.
    """
    try:
        data_start = response_text.find('this.storeCase_Data=[')
        if data_start == -1:
            raise ValueError('storeCase_Data not found in response')
        # Find the end of the array (look for the closing bracket followed by semicolon)
        data_end = data_start + 21
        bracket_count = 1
        in_string = False
        escape_next = False
        for i in range(data_start + 21, len(response_text)):
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
        json_string = response_text[data_start + 20:data_end]
        case_data = json.loads(json_string)
        return case_data
    except Exception as e:
        logger.error(f"Error extracting case data: {e}")
        raise

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
    api_url = f"https://tps.logiqs.com/Cases/Case.aspx?CaseID={case_id}&ProductID={product_id}"
    logger.info(f"Fetching case data from: {api_url}")
    try:
        response = requests.get(api_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }, timeout=30)
        case_data = extract_case_data(response.text)
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
    api_url = f"https://tps.logiqs.com/Cases/Case.aspx?CaseID={case_id}&ProductID={product_id}"
    try:
        response = requests.get(api_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }, timeout=30)
        case_data = extract_case_data(response.text)
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
    api_url = f"https://tps.logiqs.com/Cases/Case.aspx?CaseID={case_id}&ProductID={product_id}"
    try:
        response = requests.get(api_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }, timeout=30)
        case_data = extract_case_data(response.text)
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