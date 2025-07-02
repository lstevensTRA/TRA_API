#!/usr/bin/env python3
"""
Simple verification script for enhanced system
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.utils.supabase_client import get_supabase_client

def main():
    print("🔍 Verifying enhanced system...")
    
    try:
        supabase = get_supabase_client()
        
        # Check enhanced data
        result = supabase.table("form_types").select(
            "code, category, form_pattern, field_definitions, calculation_rules"
        ).limit(3).execute()
        
        print(f"✅ Found {len(result.data)} enhanced form types")
        
        for form in result.data:
            print(f"  - {form['code']}: category={form.get('category')}, has_pattern={bool(form.get('form_pattern'))}, has_fields={bool(form.get('field_definitions'))}")
            if form.get('calculation_rules'):
                print(f"    * Has calculation rules: {len(form['calculation_rules'])} rules")
        
        print("✅ Enhanced system verification complete!")
        return 0
        
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main()) 