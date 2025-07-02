#!/usr/bin/env python3
"""
Test Routes Registration

This script tests that all routes are properly registered in the FastAPI app.
"""

import requests
import json

def test_route_registration():
    """Test that all expected routes are registered"""
    
    base_url = "http://localhost:8000"
    
    # Get the OpenAPI spec
    try:
        response = requests.get(f"{base_url}/openapi.json")
        if response.status_code != 200:
            print(f"❌ Failed to get OpenAPI spec: {response.status_code}")
            return
        
        openapi_spec = response.json()
        paths = openapi_spec.get("paths", {})
        
        print("🔍 Checking route registration...")
        print("=" * 60)
        
        # Expected routes to check
        expected_routes = [
            "/health",
            "/auth/login",
            "/client_profile/{case_id}",
            "/transcripts/wi/{case_id}",
            "/transcripts/at/{case_id}",
            "/transcripts/raw/wi/{case_id}",
            "/transcripts/raw/at/{case_id}",
            "/irs-standards/case/{case_id}",
            "/analysis/wi/{case_id}",
            "/analysis/at/{case_id}",
            "/disposable-income/case/{case_id}",
            "/income-comparison/{case_id}",
            "/closing-letters/{case_id}",
            "/case-management/activities/{case_id}",
            "/tax-investigation/client/{case_id}"
        ]
        
        found_routes = []
        missing_routes = []
        
        for route in expected_routes:
            if route in paths:
                found_routes.append(route)
                print(f"✅ {route}")
            else:
                missing_routes.append(route)
                print(f"❌ {route}")
        
        print("=" * 60)
        print(f"📊 Route Registration Summary:")
        print(f"   Found: {len(found_routes)}/{len(expected_routes)}")
        print(f"   Missing: {len(missing_routes)}")
        
        if missing_routes:
            print(f"\n❌ Missing Routes:")
            for route in missing_routes:
                print(f"   • {route}")
        
        # Check for similar routes that might exist
        print(f"\n🔍 Checking for similar routes...")
        all_paths = list(paths.keys())
        
        for missing_route in missing_routes:
            print(f"\nLooking for routes similar to: {missing_route}")
            for path in all_paths:
                if any(part in path for part in missing_route.split('/')):
                    print(f"   Found similar: {path}")
        
        return found_routes, missing_routes
        
    except Exception as e:
        print(f"❌ Error testing route registration: {str(e)}")
        return [], []

if __name__ == "__main__":
    test_route_registration() 