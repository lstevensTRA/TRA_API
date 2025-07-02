#!/usr/bin/env python3
"""
Script to create pending annotations for existing extractions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.supabase_client import get_supabase_client
from datetime import datetime
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_system_user():
    """Create a system user for annotations"""
    supabase = get_supabase_client()
    
    try:
        # Check if system user already exists
        result = supabase.table("users").select("id").eq("email", "system@training.local").execute()
        if result.data:
            logger.info("System user already exists")
            return result.data[0]["id"]
        
        # Create system user
        user_data = {
            "id": str(uuid.uuid4()),
            "email": "system@training.local",
            "name": "System Annotator",
            "created_at": datetime.now().isoformat()
        }
        
        result = supabase.table("users").insert(user_data).execute()
        logger.info(f"Created system user: {result.data[0]['id']}")
        return result.data[0]["id"]
        
    except Exception as e:
        logger.error(f"Failed to create system user: {str(e)}")
        return None

def create_annotations_for_extractions():
    """Create pending annotations for all extractions that don't have annotations"""
    supabase = get_supabase_client()
    
    try:
        # Get all extractions
        extractions_result = supabase.table("extractions").select("*").execute()
        extractions = extractions_result.data
        logger.info(f"Found {len(extractions)} extractions")
        
        # Get existing annotations to avoid duplicates
        annotations_result = supabase.table("annotations").select("extraction_id").execute()
        existing_annotation_extraction_ids = {ann["extraction_id"] for ann in annotations_result.data}
        logger.info(f"Found {len(existing_annotation_extraction_ids)} existing annotations")
        
        # Create system user if needed
        system_user_id = create_system_user()
        
        # Create annotations for extractions that don't have them
        new_annotations = []
        for extraction in extractions:
            if extraction["id"] not in existing_annotation_extraction_ids:
                annotation_data = {
                    "extraction_id": extraction["id"],
                    "corrected_fields": {},  # Empty initially
                    "status": "pending",
                    "notes": "Auto-generated for annotation workflow",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                new_annotations.append(annotation_data)
        
        if new_annotations:
            # Insert all new annotations
            result = supabase.table("annotations").insert(new_annotations).execute()
            logger.info(f"Created {len(result.data)} new annotations")
            return result.data
        else:
            logger.info("No new annotations needed")
            return []
            
    except Exception as e:
        logger.error(f"Failed to create annotations: {str(e)}")
        raise

if __name__ == "__main__":
    create_annotations_for_extractions() 