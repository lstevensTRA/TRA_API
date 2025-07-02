#!/usr/bin/env python3
"""
Export documents and extractions from Supabase to Label Studio format for annotation.

Usage:
    python export_to_labelstudio.py [--output tasks.json] [--push]

- Requires SUPABASE_URL, SUPABASE_KEY, and (optionally) LABEL_STUDIO_URL, LABEL_STUDIO_API_KEY in env or .env file.
- By default, saves output to tasks.json. Use --push to send tasks to Label Studio via API.
"""
import os
import json
import logging
import argparse
from supabase import create_client, Client
from dotenv import load_dotenv

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

parser = argparse.ArgumentParser(description="Export Supabase data to Label Studio format.")
parser.add_argument('--output', type=str, default='tasks.json', help='Output file for Label Studio tasks')
parser.add_argument('--push', action='store_true', help='Push tasks to Label Studio project via API')
parser.add_argument('--ls_project', type=int, help='Label Studio project ID (required if --push)')
args = parser.parse_args()

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_documents_and_extractions(supabase: Client):
    docs = supabase.table('documents').select('*').execute().data
    extractions = supabase.table('extractions').select('*').execute().data
    return docs, extractions

def build_labelstudio_tasks(docs, extractions):
    # Map extractions by document_id
    extraction_map = {}
    for ext in extractions:
        doc_id = ext['document_id']
        if doc_id not in extraction_map:
            extraction_map[doc_id] = []
        extraction_map[doc_id].append(ext)
    tasks = []
    for doc in docs:
        doc_id = doc['id']
        task = {
            "data": {
                "document_id": doc_id,
                "filename": doc['filename'],
                "raw_text": doc['raw_text'],
                "extractions": extraction_map.get(doc_id, [])
            }
        }
        tasks.append(task)
    return tasks

def push_to_labelstudio(tasks, project_id):
    if not LSClient:
        raise ImportError("label_studio_sdk is not installed.")
    assert LABEL_STUDIO_URL and LABEL_STUDIO_API_KEY, "Label Studio credentials required."
    ls_client = LSClient(LABEL_STUDIO_URL, LABEL_STUDIO_API_KEY)
    project = ls_client.get_project(project_id)
    response = project.import_tasks(tasks)
    logging.info(f"Pushed {len(tasks)} tasks to Label Studio project {project_id}.")
    return response

def main():
    supabase = get_supabase_client()
    docs, extractions = fetch_documents_and_extractions(supabase)
    tasks = build_labelstudio_tasks(docs, extractions)
    with open(args.output, 'w') as f:
        json.dump(tasks, f, indent=2)
    logging.info(f"Exported {len(tasks)} tasks to {args.output}")
    if args.push:
        assert args.ls_project, "--ls_project is required when using --push."
        push_to_labelstudio(tasks, args.ls_project)

if __name__ == "__main__":
    main() 