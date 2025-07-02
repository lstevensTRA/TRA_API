#!/usr/bin/env python3
import requests
import time

def test_endpoint():
    base_url = "http://localhost:8000"
    results = []
    
    # Test the root endpoint first
    results.append("Testing root endpoint...")
    try:
        response = requests.get(f"{base_url}/")
        results.append(f"Root endpoint: {response.status_code} - {response.text}")
    except Exception as e:
        results.append(f"Error testing root endpoint: {e}")
    
    # Test the test endpoint
    results.append("\nTesting disposable income test endpoint...")
    try:
        response = requests.get(f"{base_url}/disposable-income/test")
        results.append(f"Test endpoint: {response.status_code} - {response.text}")
    except Exception as e:
        results.append(f"Error testing test endpoint: {e}")
    
    # Test the actual disposable income endpoint
    results.append("\nTesting disposable income endpoint...")
    try:
        response = requests.get(f"{base_url}/disposable-income/732334")
        results.append(f"Disposable income endpoint: {response.status_code} - {response.text}")
    except Exception as e:
        results.append(f"Error testing disposable income endpoint: {e}")

    # Write results to file
    with open("test_results.txt", "w") as f:
        for line in results:
            f.write(line + "\n")
    print("Test results written to test_results.txt")

if __name__ == "__main__":
    test_endpoint() 