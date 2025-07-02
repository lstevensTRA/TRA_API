#!/usr/bin/env python3
"""
Test Tax Investigation Routes

This script tests the tax investigation routes to verify they are working.
"""

import requests
import json

def test_tax_investigation_routes():
    """Test tax investigation routes"""
    
    base_url = "http://localhost:8000"
    
    print("🔍 Testing Tax Investigation Routes...")
    print("=" * 50)
    
    # Test the test route
    try:
        response = requests.get(f"{base_url}/tax-investigation/test")
        print(f"Test Route: {response.status_code} - {response.text[:100]}")
    except Exception as e:
        print(f"Test Route Error: {e}")
    
    # Test the client route
    try:
        response = requests.get(f"{base_url}/tax-investigation/client/54820")
        print(f"Client Route: {response.status_code} - {response.text[:100]}")
    except Exception as e:
        print(f"Client Route Error: {e}")
    
    # Test the compare route
    try:
        response = requests.get(f"{base_url}/tax-investigation/compare/54820")
        print(f"Compare Route: {response.status_code} - {response.text[:100]}")
    except Exception as e:
        print(f"Compare Route Error: {e}")
    
    # Check OpenAPI spec
    try:
        response = requests.get(f"{base_url}/openapi.json")
        if response.status_code == 200:
            openapi_spec = response.json()
            paths = openapi_spec.get("paths", {})
            
            print("\n📋 Routes in OpenAPI spec:")
            tax_routes = [path for path in paths.keys() if "tax-investigation" in path]
            for route in tax_routes:
                print(f"  - {route}")
        else:
            print(f"Failed to get OpenAPI spec: {response.status_code}")
    except Exception as e:
        print(f"OpenAPI Error: {e}")

if __name__ == "__main__":
    test_tax_investigation_routes() 