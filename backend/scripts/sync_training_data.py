#!/usr/bin/env python3
"""
Sync training data between Supabase and Label Studio.

Usage:
    python sync_training_data.py --ls_project <project_id>

- Requires SUPABASE_URL, SUPABASE_KEY, LABEL_STUDIO_URL, LABEL_STUDIO_API_KEY in env or .env file.
- Pushes new/updated documents and extractions to Label Studio
- Pulls new/updated annotations from Label Studio to Supabase
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

import export_to_labelstudio
import import_from_labelstudio

logging.basicConfig(level=logging.INFO)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
LABEL_STUDIO_URL = os.getenv("LABEL_STUDIO_URL")
LABEL_STUDIO_API_KEY = os.getenv("LABEL_STUDIO_API_KEY")

assert SUPABASE_URL and SUPABASE_KEY, "Supabase credentials are required."
assert LABEL_STUDIO_URL and LABEL_STUDIO_API_KEY, "Label Studio credentials are required."

parser = argparse.ArgumentParser(description="Sync training data between Supabase and Label Studio.")
parser.add_argument('--ls_project', type=int, required=True, help='Label Studio project ID')
args = parser.parse_args()

def main():
    # Export new/updated docs/extractions to Label Studio
    logging.info("Exporting new/updated documents and extractions to Label Studio...")
    export_to_labelstudio.main()
    # Import new/updated annotations from Label Studio
    logging.info("Importing new/updated annotations from Label Studio to Supabase...")
    import_from_labelstudio.main()
    logging.info("Sync complete.")

if __name__ == "__main__":
    main() 