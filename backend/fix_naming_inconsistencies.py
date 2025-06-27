#!/usr/bin/env python3
"""
TRA API Naming Inconsistency Fixer

This script identifies and fixes naming inconsistencies in the API endpoints,
standardizing them to kebab-case format.

Usage:
    python fix_naming_inconsistencies.py --check-only
    python fix_naming_inconsistencies.py --fix
"""

import re
import os
import argparse
from typing import List, Dict, Tuple
from pathlib import Path

class NamingInconsistencyFixer:
    """Identifies and fixes naming inconsistencies in API endpoints"""
    
    def __init__(self, routes_dir: str = "app/routes"):
        self.routes_dir = Path(routes_dir)
        self.inconsistencies = []
        self.fixes_made = []
        
    def find_inconsistencies(self) -> List[Dict]:
        """Find all naming inconsistencies in route files"""
        inconsistencies = []
        
        # Check server.py for route prefixes
        server_file = Path("server.py")
        if server_file.exists():
            with open(server_file, 'r') as f:
                content = f.read()
                
            # Find route prefixes that use snake_case instead of kebab-case
            route_pattern = r'app\.include_router\((\w+)\.router,\s+prefix="([^"]+)"'
            matches = re.findall(route_pattern, content)
            
            for module_name, prefix in matches:
                if '_' in prefix and not prefix.startswith('/'):
                    inconsistencies.append({
                        'file': 'server.py',
                        'type': 'route_prefix',
                        'current': prefix,
                        'suggested': prefix.replace('_', '-'),
                        'line': self._find_line_number(content, prefix)
                    })
        
        # Check individual route files
        for route_file in self.routes_dir.glob("*.py"):
            if route_file.name == "__init__.py":
                continue
                
            with open(route_file, 'r') as f:
                content = f.read()
                
            # Find route decorators with snake_case paths
            route_pattern = r'@router\.(get|post|put|delete|patch)\("([^"]+)"'
            matches = re.findall(route_pattern, content)
            
            for method, path in matches:
                if '_' in path and not path.startswith('/'):
                    inconsistencies.append({
                        'file': str(route_file),
                        'type': 'route_path',
                        'current': path,
                        'suggested': path.replace('_', '-'),
                        'line': self._find_line_number(content, path)
                    })
        
        self.inconsistencies = inconsistencies
        return inconsistencies
    
    def _find_line_number(self, content: str, search_text: str) -> int:
        """Find the line number where text appears"""
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if search_text in line:
                return i
        return 0
    
    def fix_inconsistencies(self) -> List[Dict]:
        """Fix all identified naming inconsistencies"""
        fixes_made = []
        
        # Fix server.py route prefixes
        server_file = Path("server.py")
        if server_file.exists():
            with open(server_file, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Fix route prefixes
            for inconsistency in self.inconsistencies:
                if inconsistency['file'] == 'server.py' and inconsistency['type'] == 'route_prefix':
                    content = content.replace(
                        f'prefix="{inconsistency["current"]}"',
                        f'prefix="{inconsistency["suggested"]}"'
                    )
                    fixes_made.append(inconsistency)
            
            # Write back if changes were made
            if content != original_content:
                with open(server_file, 'w') as f:
                    f.write(content)
                print(f"✅ Fixed route prefixes in server.py")
        
        # Fix individual route files
        for route_file in self.routes_dir.glob("*.py"):
            if route_file.name == "__init__.py":
                continue
                
            with open(route_file, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Fix route paths in this file
            for inconsistency in self.inconsistencies:
                if inconsistency['file'] == str(route_file) and inconsistency['type'] == 'route_path':
                    content = content.replace(
                        f'"{inconsistency["current"]}"',
                        f'"{inconsistency["suggested"]}"'
                    )
                    fixes_made.append(inconsistency)
            
            # Write back if changes were made
            if content != original_content:
                with open(route_file, 'w') as f:
                    f.write(content)
                print(f"✅ Fixed route paths in {route_file.name}")
        
        self.fixes_made = fixes_made
        return fixes_made
    
    def print_report(self):
        """Print a detailed report of inconsistencies and fixes"""
        print(f"\n{'='*60}")
        print(f"TRA API NAMING INCONSISTENCY REPORT")
        print(f"{'='*60}")
        
        if not self.inconsistencies:
            print("✅ No naming inconsistencies found!")
            return
        
        print(f"\n📊 Found {len(self.inconsistencies)} inconsistencies:")
        
        for i, inconsistency in enumerate(self.inconsistencies, 1):
            print(f"\n{i}. {inconsistency['file']} (line {inconsistency['line']})")
            print(f"   Type: {inconsistency['type']}")
            print(f"   Current: {inconsistency['current']}")
            print(f"   Suggested: {inconsistency['suggested']}")
        
        if self.fixes_made:
            print(f"\n🔧 Fixed {len(self.fixes_made)} inconsistencies:")
            for fix in self.fixes_made:
                print(f"   ✅ {fix['file']}: {fix['current']} → {fix['suggested']}")
        
        print(f"\n📋 Summary:")
        print(f"   Total inconsistencies: {len(self.inconsistencies)}")
        print(f"   Fixed: {len(self.fixes_made)}")
        print(f"   Remaining: {len(self.inconsistencies) - len(self.fixes_made)}")
        
        print(f"{'='*60}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="TRA API Naming Inconsistency Fixer")
    parser.add_argument("--check-only", action="store_true", help="Only check for inconsistencies, don't fix")
    parser.add_argument("--fix", action="store_true", help="Fix identified inconsistencies")
    parser.add_argument("--routes-dir", default="app/routes", help="Routes directory path")
    
    args = parser.parse_args()
    
    if not args.check_only and not args.fix:
        print("Please specify either --check-only or --fix")
        return
    
    fixer = NamingInconsistencyFixer(args.routes_dir)
    
    print("🔍 Scanning for naming inconsistencies...")
    inconsistencies = fixer.find_inconsistencies()
    
    if args.check_only:
        fixer.print_report()
    elif args.fix:
        print("🔧 Fixing naming inconsistencies...")
        fixes = fixer.fix_inconsistencies()
        fixer.print_report()
        
        if fixes:
            print(f"\n⚠️  IMPORTANT: After fixing naming inconsistencies, you may need to:")
            print(f"   1. Update any hardcoded API calls in your frontend/client code")
            print(f"   2. Update API documentation")
            print(f"   3. Update any test scripts that use the old endpoint names")
            print(f"   4. Restart your FastAPI server")

if __name__ == "__main__":
    main() 