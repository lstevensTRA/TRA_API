#!/usr/bin/env python3
"""
Import completed annotations from Label Studio API and save to Supabase.

Usage:
    python import_from_labelstudio.py --ls_project <project_id>

- Requires SUPABASE_URL, SUPABASE_KEY, LABEL_STUDIO_URL, LABEL_STUDIO_API_KEY in env or .env file.
"""
import os
import logging
import argparse
from dotenv import load_dotenv
from supabase import create_client, Client

try:
    from label_studio_sdk import Client as LSClient
except ImportError:
    LSClient = None

logging.basicConfig(level=logging.INFO)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
LABEL_STUDIO_URL = os.getenv("LABEL_STUDIO_URL")
LABEL_STUDIO_API_KEY = os.getenv("LABEL_STUDIO_API_KEY")

assert SUPABASE_URL and SUPABASE_KEY, "Supabase credentials are required."
assert LABEL_STUDIO_URL and LABEL_STUDIO_API_KEY, "Label Studio credentials are required."

parser = argparse.ArgumentParser(description="Import annotations from Label Studio to Supabase.")
parser.add_argument('--ls_project', type=int, required=True, help='Label Studio project ID')
args = parser.parse_args()

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_labelstudio_client():
    if not LSClient:
        raise ImportError("label_studio_sdk is not installed.")
    return LSClient(LABEL_STUDIO_URL, LABEL_STUDIO_API_KEY)

def fetch_completed_annotations(ls_client, project_id):
    project = ls_client.get_project(project_id)
    tasks = project.get_tasks()
    completed = [t for t in tasks if t.get('is_labeled')]
    return completed

def save_annotations_to_supabase(supabase: Client, completed_tasks):
    for task in completed_tasks:
        data = task['data']
        for annotation in task.get('annotations', []):
            extraction_id = data.get('extractions', [{}])[0].get('id') if data.get('extractions') else None
            annotation_record = {
                'extraction_id': extraction_id,
                'corrected_fields': annotation.get('result', []),
                'status': 'completed',
                'notes': annotation.get('comment', '')
            }
            # Upsert by extraction_id
            if extraction_id:
                supabase.table('annotations').upsert(annotation_record, on_conflict=['extraction_id']).execute()
                logging.info(f"Saved annotation for extraction_id {extraction_id}")

def main():
    supabase = get_supabase_client()
    ls_client = get_labelstudio_client()
    completed_tasks = fetch_completed_annotations(ls_client, args.ls_project)
    logging.info(f"Fetched {len(completed_tasks)} completed tasks from Label Studio.")
    save_annotations_to_supabase(supabase, completed_tasks)
    logging.info("Import complete.")

if __name__ == "__main__":
    main() 