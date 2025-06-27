#!/usr/bin/env python3
"""
County Database Builder

This script fetches all counties for every state from the Logiqs API
and creates a comprehensive database for validation and testing.
"""

import asyncio
import json
import httpx
import logging
from typing import Dict, List, Any
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# States list (from your existing states endpoint)
STATES = [
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

# Logiqs API configuration
LOGIQS_BASE_URL = "https://tps.logiqs.com/API/CaseInterview"

# You'll need to provide authentication cookies
# This should be set up before running the script
COOKIE_HEADER = None  # Set this to your cookie header
USER_AGENT = None     # Set this to your user agent

async def get_counties_for_state(state_code: str) -> List[Dict[str, Any]]:
    """Fetch counties for a specific state"""
    try:
        url = f"{LOGIQS_BASE_URL}/GetCounties"
        params = {"state": state_code.upper()}
        
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
                logger.error(f"Failed to get counties for {state_code}: {response.status_code}")
                return []
            
            data = response.json()
            if data.get("Error", True):
                logger.error(f"Logiqs API error for {state_code}: {data}")
                return []
            
            counties = data.get("Result", [])
            logger.info(f"✅ Retrieved {len(counties)} counties for {state_code}")
            return counties
            
    except Exception as e:
        logger.error(f"Error fetching counties for {state_code}: {str(e)}")
        return []

async def get_irs_standards_sample(county_id: int, state_code: str) -> Dict[str, Any]:
    """Get a sample IRS Standards response for validation"""
    try:
        url = f"{LOGIQS_BASE_URL}/GetIRSStandards"
        params = {
            "familyMemberUnder65": 1,
            "familyMemberOver65": 0,
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
                return {"error": f"HTTP {response.status_code}"}
            
            data = response.json()
            if data.get("Error", True):
                return {"error": "API Error", "details": data}
            
            return data.get("Result", {})
            
    except Exception as e:
        return {"error": str(e)}

async def build_county_database():
    """Build comprehensive county database"""
    logger.info("🚀 Starting county database build...")
    
    all_counties = {}
    validation_samples = {}
    
    # Process each state
    for state in STATES:
        state_code = state["value"]
        state_name = state["stateName"]
        
        logger.info(f"📊 Processing {state_name} ({state_code})...")
        
        counties = await get_counties_for_state(state_code)
        
        if counties:
            all_counties[state_code] = {
                "state_name": state_name,
                "counties": counties,
                "count": len(counties)
            }
            
            # Get validation sample for first county
            if counties:
                first_county = counties[0]
                county_id = first_county.get("CountyId")
                county_name = first_county.get("CountyName")
                
                logger.info(f"🔍 Getting validation sample for {county_name} (ID: {county_id})")
                sample = await get_irs_standards_sample(county_id, state_code)
                
                validation_samples[state_code] = {
                    "county_id": county_id,
                    "county_name": county_name,
                    "sample_data": sample
                }
                
                # Add delay to avoid overwhelming the API
                await asyncio.sleep(1)
    
    # Save the database
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    
    # Save counties database
    counties_file = output_dir / "counties_database.json"
    with open(counties_file, 'w') as f:
        json.dump(all_counties, f, indent=2)
    
    # Save validation samples
    validation_file = output_dir / "validation_samples.json"
    with open(validation_file, 'w') as f:
        json.dump(validation_samples, f, indent=2)
    
    # Generate summary
    total_counties = sum(state_data["count"] for state_data in all_counties.values())
    logger.info(f"✅ Database build complete!")
    logger.info(f"📊 Total states processed: {len(all_counties)}")
    logger.info(f"📊 Total counties: {total_counties}")
    logger.info(f"📁 Counties database saved to: {counties_file}")
    logger.info(f"📁 Validation samples saved to: {validation_file}")
    
    return all_counties, validation_samples

def generate_city_county_mapping(counties_data: Dict) -> Dict[str, Dict]:
    """Generate city-to-county mapping suggestions"""
    logger.info("🗺️ Generating city-to-county mapping suggestions...")
    
    # This would need to be enhanced with actual city data
    # For now, we'll create a structure for manual population
    mapping_structure = {}
    
    for state_code, state_data in counties_data.items():
        mapping_structure[state_code] = {
            "state_name": state_data["state_name"],
            "counties": {},
            "major_cities": {}  # To be populated manually
        }
        
        for county in state_data["counties"]:
            county_id = county.get("CountyId")
            county_name = county.get("CountyName")
            
            mapping_structure[state_code]["counties"][county_name] = {
                "county_id": county_id,
                "cities": []  # To be populated
            }
    
    # Save mapping structure
    output_dir = Path("data")
    mapping_file = output_dir / "city_county_mapping_structure.json"
    with open(mapping_file, 'w') as f:
        json.dump(mapping_structure, f, indent=2)
    
    logger.info(f"📁 Mapping structure saved to: {mapping_file}")
    return mapping_structure

if __name__ == "__main__":
    # Check if authentication is set up
    if not COOKIE_HEADER or not USER_AGENT:
        logger.error("❌ Please set COOKIE_HEADER and USER_AGENT before running this script")
        logger.info("💡 You can get these from your browser's developer tools or from your existing API calls")
        exit(1)
    
    # Run the database build
    asyncio.run(build_county_database()) 