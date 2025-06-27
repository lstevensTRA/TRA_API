#!/usr/bin/env python3
"""
Endpoint Synchronization Check Script

This script ensures that all backend endpoints are properly represented
in the frontend UI. It scans backend routes and compares them with
the frontend endpointConfig object.

Usage:
    python scripts/endpoint_sync_check.py
"""

import os
import re
import json
import ast
from pathlib import Path
from typing import List, Dict, Set, Tuple

def extract_backend_endpoints() -> Dict[str, List[Dict]]:
    """Extract all endpoints from backend route files."""
    routes_dir = Path("app/routes")
    endpoints = {}
    
    for route_file in routes_dir.glob("*.py"):
        if route_file.name == "__init__.py":
            continue
            
        category = route_file.stem.replace("_routes", "").replace("_", "")
        endpoints[category] = []
        
        with open(route_file, 'r') as f:
            content = f.read()
            
        # Find all @router.get and @router.post decorators
        pattern = r'@router\.(get|post)\(["\']([^"\']+)["\']'
        matches = re.findall(pattern, content)
        
        for method, path in matches:
            endpoints[category].append({
                "method": method.upper(),
                "path": path,
                "name": f"{method.upper()} {path}"
            })
    
    return endpoints

def extract_frontend_endpoints() -> Dict[str, List[Dict]]:
    """Extract endpoints from frontend App.js file."""
    frontend_file = Path("frontend-testing-tool/src/App.js")
    
    if not frontend_file.exists():
        return {}
    
    with open(frontend_file, 'r') as f:
        content = f.read()
    
    # Find endpointConfig object
    pattern = r'endpointConfig\s*=\s*{([^}]+)}'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        return {}
    
    # This is a simplified parser - in production you might want a more robust solution
    endpoints = {}
    
    # Look for category patterns
    category_pattern = r'(\w+):\s*{[^}]*name:\s*[\'"]([^\'"]+)[\'"][^}]*endpoints:\s*\[([^\]]+)\]'
    category_matches = re.findall(category_pattern, content, re.DOTALL)
    
    for category_key, category_name, endpoints_str in category_matches:
        endpoints[category_key] = []
        
        # Extract individual endpoints
        endpoint_pattern = r'{\s*path:\s*[\'"]([^\'"]+)[\'"][^}]*method:\s*[\'"]([^\'"]+)[\'"][^}]*name:\s*[\'"]([^\'"]+)[\'"]'
        endpoint_matches = re.findall(endpoint_pattern, endpoints_str)
        
        for path, method, name in endpoint_matches:
            endpoints[category_key].append({
                "method": method.upper(),
                "path": path,
                "name": name
            })
    
    return endpoints

def compare_endpoints(backend: Dict, frontend: Dict) -> Tuple[Set, Set, Set]:
    """Compare backend and frontend endpoints."""
    backend_endpoints = set()
    frontend_endpoints = set()
    
    # Collect all backend endpoints
    for category, endpoints in backend.items():
        for endpoint in endpoints:
            backend_endpoints.add(f"{endpoint['method']} {endpoint['path']}")
    
    # Collect all frontend endpoints
    for category, endpoints in frontend.items():
        for endpoint in endpoints:
            frontend_endpoints.add(f"{endpoint['method']} {endpoint['path']}")
    
    missing_in_frontend = backend_endpoints - frontend_endpoints
    missing_in_backend = frontend_endpoints - backend_endpoints
    matching = backend_endpoints & frontend_endpoints
    
    return missing_in_frontend, missing_in_backend, matching

def main():
    """Main function to run the synchronization check."""
    print("🔍 Endpoint Synchronization Check")
    print("=" * 50)
    
    # Change to backend directory
    os.chdir("backend")
    
    backend_endpoints = extract_backend_endpoints()
    frontend_endpoints = extract_frontend_endpoints()
    
    missing_in_frontend, missing_in_backend, matching = compare_endpoints(
        backend_endpoints, frontend_endpoints
    )
    
    print(f"\n📊 Summary:")
    print(f"Backend endpoints: {sum(len(eps) for eps in backend_endpoints.values())}")
    print(f"Frontend endpoints: {sum(len(eps) for eps in frontend_endpoints.values())}")
    print(f"Matching endpoints: {len(matching)}")
    print(f"Missing in frontend: {len(missing_in_frontend)}")
    print(f"Missing in backend: {len(missing_in_backend)}")
    
    if missing_in_frontend:
        print(f"\n❌ Missing in Frontend:")
        for endpoint in sorted(missing_in_frontend):
            print(f"  - {endpoint}")
    
    if missing_in_backend:
        print(f"\n❌ Missing in Backend:")
        for endpoint in sorted(missing_in_backend):
            print(f"  - {endpoint}")
    
    if matching:
        print(f"\n✅ Matching Endpoints:")
        for endpoint in sorted(matching):
            print(f"  - {endpoint}")
    
    if not missing_in_frontend and not missing_in_backend:
        print(f"\n🎉 All endpoints are synchronized!")
        return 0
    else:
        print(f"\n⚠️  Endpoint synchronization issues found!")
        return 1

if __name__ == "__main__":
    exit(main()) 