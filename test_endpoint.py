#!/usr/bin/env python3
import requests
import time

def test_endpoint():
    base_url = "http://localhost:8000"
    
    # Test the root endpoint first
    print("Testing root endpoint...")
    try:
        response = requests.get(f"{base_url}/")
        print(f"Root endpoint: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error testing root endpoint: {e}")
    
    # Test the test endpoint
    print("\nTesting disposable income test endpoint...")
    try:
        response = requests.get(f"{base_url}/disposable-income/test")
        print(f"Test endpoint: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error testing test endpoint: {e}")
    
    # Test the actual disposable income endpoint
    print("\nTesting disposable income endpoint...")
    try:
        response = requests.get(f"{base_url}/disposable-income/732334")
        print(f"Disposable income endpoint: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error testing disposable income endpoint: {e}")

if __name__ == "__main__":
    test_endpoint() 