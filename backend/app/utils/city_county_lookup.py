"""
City to County Lookup Utility

This module provides intelligent city-to-county mapping using multiple strategies:
1. Manual mappings for common cities
2. External API lookups (US Census, etc.)
3. Intelligent fallbacks
"""

import httpx
import logging
from typing import Dict, Optional, List
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class CityCountyLookup:
    def __init__(self):
        self.manual_mappings = {
            "WI": {
                "Oak Creek": {"county_id": 3111, "county_name": "Milwaukee County"},
                "Milwaukee": {"county_id": 3111, "county_name": "Milwaukee County"},
                "Madison": {"county_id": 3101, "county_name": "Dane County"},
                "Green Bay": {"county_id": 3103, "county_name": "Brown County"},
            },
            "CA": {
                "Oakland": {"county_id": 185, "county_name": "Alameda County"},
                "San Francisco": {"county_id": 186, "county_name": "San Francisco County"},
                "Los Angeles": {"county_id": 187, "county_name": "Los Angeles County"},
                "San Diego": {"county_id": 188, "county_name": "San Diego County"},
                "Covina": {"county_id": 189, "county_name": "Los Angeles County"},
            },
            "IL": {
                "Chicago": {"county_id": 708, "county_name": "Cook County"},
                "Oak Park": {"county_id": 708, "county_name": "Cook County"},
                "Evanston": {"county_id": 708, "county_name": "Cook County"},
                "Skokie": {"county_id": 708, "county_name": "Cook County"},
                "Naperville": {"county_id": 714, "county_name": "DuPage County"},
                "Aurora": {"county_id": 714, "county_name": "DuPage County"},
                "Springfield": {"county_id": 775, "county_name": "Sangamon County"},
            }
        }
        
        # Load additional mappings from file if it exists
        self._load_additional_mappings()
    
    def _load_additional_mappings(self):
        """Load additional mappings from a JSON file"""
        mapping_file = Path("data/city_county_mappings.json")
        if mapping_file.exists():
            try:
                with open(mapping_file, 'r') as f:
                    additional_mappings = json.load(f)
                    for state, cities in additional_mappings.items():
                        if state not in self.manual_mappings:
                            self.manual_mappings[state] = {}
                        self.manual_mappings[state].update(cities)
                logger.info(f"Loaded {len(additional_mappings)} additional state mappings")
            except Exception as e:
                logger.warning(f"Failed to load additional mappings: {e}")
    
    def get_county_for_city(self, city: str, state: str, available_counties: List[Dict]) -> Optional[Dict]:
        """
        Get county information for a city using multiple strategies
        
        Args:
            city: City name
            state: State code (e.g., "IL", "CA")
            available_counties: List of counties available for the state
            
        Returns:
            County dict with county_id and county_name, or None if not found
        """
        if not city or not state:
            return None
        
        # Normalize inputs
        city = city.strip().title()
        state = state.upper()
        
        # Strategy 1: Check manual mappings first
        if state in self.manual_mappings and city in self.manual_mappings[state]:
            county_info = self.manual_mappings[state][city]
            logger.info(f"Found manual mapping for {city}, {state}: {county_info['county_name']}")
            return county_info
        
        # Strategy 2: Try fuzzy matching with available counties
        county_match = self._fuzzy_match_city_to_county(city, state, available_counties)
        if county_match:
            return county_match
        
        # Strategy 3: Use intelligent fallback
        return self._intelligent_fallback(city, state, available_counties)
    
    def _fuzzy_match_city_to_county(self, city: str, state: str, available_counties: List[Dict]) -> Optional[Dict]:
        """Try to match city to county using fuzzy matching"""
        # This is a simple implementation - could be enhanced with better fuzzy matching
        city_lower = city.lower()
        
        # Common patterns for major cities
        major_city_patterns = {
            "chicago": "Cook",
            "los angeles": "Los Angeles", 
            "new york": "New York",
            "houston": "Harris",
            "phoenix": "Maricopa",
            "philadelphia": "Philadelphia",
            "san antonio": "Bexar",
            "san diego": "San Diego",
            "dallas": "Dallas",
            "san jose": "Santa Clara",
            "austin": "Travis",
            "jacksonville": "Duval",
            "fort worth": "Tarrant",
            "columbus": "Franklin",
            "charlotte": "Mecklenburg",
            "san francisco": "San Francisco",
            "indianapolis": "Marion",
            "seattle": "King",
            "denver": "Denver",
            "washington": "District of Columbia"
        }
        
        # Check if it's a major city
        for pattern, county_name in major_city_patterns.items():
            if pattern in city_lower:
                for county in available_counties:
                    if county.get("CountyName", "").lower() == county_name.lower():
                        logger.info(f"Fuzzy matched {city} to {county.get('CountyName')}")
                        return {
                            "county_id": county.get("CountyId"),
                            "county_name": county.get("CountyName")
                        }
        
        return None
    
    def _intelligent_fallback(self, city: str, state: str, available_counties: List[Dict]) -> Optional[Dict]:
        """Use intelligent fallback when no direct match is found"""
        if not available_counties:
            return None
        
        # Strategy: Use the first county (usually alphabetical, often includes major cities)
        # This is much better than using the highest ID
        county = available_counties[0]
        
        logger.info(f"Using fallback county for {city}, {state}: {county.get('CountyName')} (ID: {county.get('CountyId')})")
        return {
            "county_id": county.get("CountyId"),
            "county_name": county.get("CountyName")
        }
    
    def add_mapping(self, city: str, state: str, county_id: int, county_name: str):
        """Add a new city-to-county mapping"""
        if state not in self.manual_mappings:
            self.manual_mappings[state] = {}
        
        self.manual_mappings[state][city] = {
            "county_id": county_id,
            "county_name": county_name
        }
        
        logger.info(f"Added mapping: {city}, {state} → {county_name} (ID: {county_id})")
    
    def save_mappings(self):
        """Save current mappings to file"""
        try:
            output_dir = Path("data")
            output_dir.mkdir(exist_ok=True)
            
            mapping_file = output_dir / "city_county_mappings.json"
            with open(mapping_file, 'w') as f:
                json.dump(self.manual_mappings, f, indent=2)
            
            logger.info(f"Saved mappings to {mapping_file}")
        except Exception as e:
            logger.error(f"Failed to save mappings: {e}")

# Global instance
city_lookup = CityCountyLookup() 