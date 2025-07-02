#!/usr/bin/env python3
"""
Inspect annotation, extraction, document, and form_type links for debugging annotation queue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.supabase_client import get_supabase_client
import pprint

pp = pprint.PrettyPrinter(indent=2)

supabase = get_supabase_client()

# Get all pending annotations
annotations = supabase.table("annotations").select("*").eq("status", "pending").execute().data
print(f"Found {len(annotations)} pending annotations\n")

for ann in annotations:
    extraction_id = ann["extraction_id"]
    print(f"Annotation ID: {ann['id']} | Extraction ID: {extraction_id}")
    extraction = supabase.table("extractions").select("*").eq("id", extraction_id).execute().data
    if extraction:
        extraction = extraction[0]
        print(f"  Extraction found. Document ID: {extraction['document_id']}, Form Type ID: {extraction['form_type_id']}")
        document = supabase.table("documents").select("*").eq("id", extraction["document_id"]).execute().data
        form_type = supabase.table("form_types").select("*").eq("id", extraction["form_type_id"]).execute().data
        print(f"    Document exists: {bool(document)} | Form Type exists: {bool(form_type)}")
        if document:
            print(f"    Document filename: {document[0].get('filename')}")
        if form_type:
            print(f"    Form Type code: {form_type[0].get('code')}")
    else:
        print("  Extraction NOT found!")
    print() 