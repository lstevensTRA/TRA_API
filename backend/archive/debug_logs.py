#!/usr/bin/env python3
"""
Debug script to examine logs.txt structure
"""

import re

def debug_logs():
    with open('logs.txt', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("🔍 Debugging logs.txt structure")
    print("=" * 50)
    
    # Look for TI filenames
    ti_filename_matches = re.findall(r'TI[^"]*\.pdf', content)
    print(f"Found {len(ti_filename_matches)} TI PDF filenames:")
    for i, filename in enumerate(ti_filename_matches[:10]):
        print(f"  {i+1}. {filename}")
    
    print("\n" + "=" * 50)
    
    # Look for lines containing both TI and Response Body
    ti_response_pattern = r'[^"]*"Response Body":[^"]*TI[^"]*\.pdf[^"]*'
    ti_response_matches = re.findall(ti_response_pattern, content)
    print(f"Found {len(ti_response_matches)} lines with TI and Response Body")
    
    if ti_response_matches:
        print("\nFirst TI Response Body line:")
        print(ti_response_matches[0][:300] + "...")
    
    print("\n" + "=" * 50)
    
    # Look for lines containing raw_text
    raw_text_pattern = r'[^"]*"raw_text":[^"]*'
    raw_text_matches = re.findall(raw_text_pattern, content)
    print(f"Found {len(raw_text_matches)} lines with raw_text")
    
    if raw_text_matches:
        print("\nFirst raw_text line:")
        print(raw_text_matches[0][:300] + "...")
    
    print("\n" + "=" * 50)
    
    # Look for specific patterns around TI files
    ti_context_pattern = r'([^"]*"FileName":"TI[^"]*\.pdf"[^"]*"case_id":"[^"]*"[^"]*)'
    ti_context_matches = re.findall(ti_context_pattern, content)
    print(f"Found {len(ti_context_matches)} TI file contexts")
    
    if ti_context_matches:
        print("\nFirst TI context:")
        print(ti_context_matches[0][:300] + "...")

if __name__ == "__main__":
    debug_logs() 