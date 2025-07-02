#!/usr/bin/env python3
import requests
import json

def test_disposable_income_endpoint():
    base_url = "http://localhost:8000"
    
    # Test the test endpoint first
    print("Testing disposable income test endpoint...")
    try:
        response = requests.get(f"{base_url}/disposable-income/test")
        print(f"Test endpoint status: {response.status_code}")
        print(f"Test endpoint response: {response.text}")
    except Exception as e:
        print(f"Error testing endpoint: {e}")
        return
    
    # Test the actual endpoint with case ID 54820
    print("\nTesting disposable income endpoint with case ID 54820...")
    try:
        response = requests.get(f"{base_url}/disposable-income/case/54820")
        print(f"Endpoint status: {response.status_code}")
        print(f"Endpoint response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Success! Disposable income calculated: ${data.get('monthly_disposable_income', 0):.2f}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_disposable_income_endpoint() 