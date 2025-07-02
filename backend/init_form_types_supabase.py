#!/usr/bin/env python3
"""
Initialize form_types and training_targets tables in Supabase from wi_patterns.py
Enhanced version to store complete wi_patterns data
"""

import sys
import os
import logging
import json
import inspect
import re

# Add backend/app to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.utils.supabase_client import get_supabase_client
from app.utils.wi_patterns import form_patterns

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_TARGET = 100

def is_json_serializable(obj):
    """Check if an object is JSON serializable"""
    try:
        json.dumps(obj)
        return True
    except (TypeError, ValueError):
        return False

def convert_lambda_to_config(lambda_func):
    """Convert a lambda function to a JSON-serializable configuration"""
    if lambda_func is None:
        return None
    
    # Get the source code of the lambda function
    try:
        source = inspect.getsource(lambda_func)
        # Extract the lambda expression part
        lambda_match = re.search(r'lambda\s+fields:\s*(.+)', source, re.DOTALL)
        if lambda_match:
            lambda_body = lambda_match.group(1).strip()
            # Remove trailing comma and comments
            lambda_body = re.sub(r',\s*#.*$', '', lambda_body, flags=re.MULTILINE)
            return {
                "type": "lambda",
                "body": lambda_body
            }
    except Exception as e:
        logger.warning(f"Could not convert lambda function: {str(e)}")
    
    return None

def sanitize_for_json(data):
    """Convert data to be JSON serializable"""
    if data is None:
        return None
    
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if callable(value):
                # Convert lambda functions to configuration objects
                sanitized[key] = convert_lambda_to_config(value)
            elif isinstance(value, (dict, list)):
                sanitized[key] = sanitize_for_json(value)
            else:
                sanitized[key] = value
        return sanitized
    
    elif isinstance(data, list):
        return [sanitize_for_json(item) for item in data]
    
    elif callable(data):
        return convert_lambda_to_config(data)
    
    else:
        return data

def validate_form_data(form_data):
    """Validate that form data is JSON serializable"""
    try:
        json.dumps(form_data)
        return True
    except (TypeError, ValueError) as e:
        logger.error(f"Data not JSON serializable: {str(e)}")
        return False

def main():
    logger.info("🚀 Initializing enhanced form_types and training_targets in Supabase...")
    supabase = get_supabase_client()
    
    for form_code, pattern in form_patterns.items():
        description = pattern.get('description', form_code)
        logger.info(f"Processing form type: {form_code} - {description}")
        
        # Check if form_type already exists
        exists = supabase.table("form_types").select("id").eq("code", form_code).execute()
        if exists.data:
            form_type_id = exists.data[0]['id']
            logger.info(f"Form type '{form_code}' already exists (id={form_type_id}), updating with enhanced data...")
            
            # Prepare enhanced data with proper sanitization
            enhanced_data = {
                "category": pattern.get('category'),
                "form_pattern": pattern.get('pattern'),
                "field_definitions": sanitize_for_json(pattern.get('fields')),
                "calculation_rules": sanitize_for_json(pattern.get('calculation')),
                "identifiers": sanitize_for_json(pattern.get('identifiers'))
            }
            
            # Validate data before sending to database
            if not validate_form_data(enhanced_data):
                logger.error(f"Skipping update for '{form_code}' due to JSON serialization issues")
                continue
            
            try:
                supabase.table("form_types").update(enhanced_data).eq("id", form_type_id).execute()
                logger.info(f"Updated form type '{form_code}' with enhanced data")
            except Exception as e:
                logger.error(f"Failed to update form type '{form_code}': {str(e)}")
                continue
        else:
            # Insert new form_type with complete data
            form_type_data = {
                "code": form_code,
                "description": description,
                "priority": 1,
                "category": pattern.get('category'),
                "form_pattern": pattern.get('pattern'),
                "field_definitions": sanitize_for_json(pattern.get('fields')),
                "calculation_rules": sanitize_for_json(pattern.get('calculation')),
                "identifiers": sanitize_for_json(pattern.get('identifiers'))
            }
            
            # Validate data before sending to database
            if not validate_form_data(form_type_data):
                logger.error(f"Skipping insert for '{form_code}' due to JSON serialization issues")
                continue
            
            try:
                result = supabase.table("form_types").insert(form_type_data).execute()
                form_type_id = result.data[0]['id']
                logger.info(f"Inserted form type '{form_code}' (id={form_type_id}) with enhanced data")
            except Exception as e:
                logger.error(f"Failed to insert form type '{form_code}': {str(e)}")
                continue
        
        # Check if training_target already exists
        target_exists = supabase.table("training_targets").select("id").eq("form_type_id", form_type_id).execute()
        if target_exists.data:
            logger.info(f"Training target for form_type_id={form_type_id} already exists, skipping insert.")
        else:
            # Insert training_target with only existing columns
            target_data = {
                "form_type_id": form_type_id,
                "target_count": DEFAULT_TARGET,
                "priority": 1
            }
            try:
                supabase.table("training_targets").insert(target_data).execute()
                logger.info(f"Inserted training target for form_type_id={form_type_id} (target={DEFAULT_TARGET})")
            except Exception as e:
                logger.error(f"Failed to insert training target for form_type_id={form_type_id}: {str(e)}")
                continue
    
    logger.info("✅ Enhanced initialization complete!")
    
    # Verify the data
    logger.info("🔍 Verifying enhanced data...")
    try:
        result = supabase.table("form_types").select("code, category, form_pattern, field_definitions").limit(5).execute()
        logger.info(f"Sample enhanced form types:")
        for form in result.data:
            has_pattern = bool(form.get('form_pattern'))
            has_fields = bool(form.get('field_definitions'))
            category = form.get('category', 'None')
            logger.info(f"  - {form['code']}: category={category}, has_pattern={has_pattern}, has_fields={has_fields}")
            
            # Show sample field definitions if available
            if has_fields and form.get('field_definitions'):
                field_count = len(form['field_definitions'])
                logger.info(f"    * Field count: {field_count}")
    except Exception as e:
        logger.error(f"Failed to verify data: {str(e)}")

if __name__ == "__main__":
    main() 