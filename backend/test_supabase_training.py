#!/usr/bin/env python3
"""
Test script for Supabase training workflow
Tests connectivity and basic operations
"""

import sys
import os
import logging
import uuid
from datetime import datetime

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.supabase_client import get_supabase_client, test_supabase_connection

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_supabase_connectivity():
    """Test basic Supabase connectivity"""
    logger.info("🔍 Testing Supabase connectivity...")
    
    try:
        supabase = get_supabase_client()
        # Test with a table we know exists
        result = supabase.table("documents").select("count", count="exact").limit(1).execute()
        logger.info("✅ Supabase connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Supabase connection failed: {str(e)}")
        return False

def test_form_types_table():
    """Test form_types table access"""
    logger.info("🔍 Testing form_types table...")
    
    try:
        supabase = get_supabase_client()
        result = supabase.table("form_types").select("*").limit(5).execute()
        
        if result.data:
            logger.info(f"✅ Found {len(result.data)} form types")
            for form_type in result.data:
                logger.info(f"  - {form_type['code']}: {form_type['description']}")
        else:
            logger.warning("⚠️ No form types found in database")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to access form_types table: {str(e)}")
        return False

def test_documents_table():
    """Test documents table access"""
    logger.info("🔍 Testing documents table...")
    
    try:
        supabase = get_supabase_client()
        result = supabase.table("documents").select("*").limit(5).execute()
        
        logger.info(f"✅ Found {len(result.data)} documents")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to access documents table: {str(e)}")
        return False

def test_extractions_table():
    """Test extractions table access"""
    logger.info("🔍 Testing extractions table...")
    
    try:
        supabase = get_supabase_client()
        result = supabase.table("extractions").select("*").limit(5).execute()
        
        logger.info(f"✅ Found {len(result.data)} extractions")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to access extractions table: {str(e)}")
        return False

def test_annotations_table():
    """Test annotations table access"""
    logger.info("🔍 Testing annotations table...")
    
    try:
        supabase = get_supabase_client()
        result = supabase.table("annotations").select("*").limit(5).execute()
        
        logger.info(f"✅ Found {len(result.data)} annotations")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to access annotations table: {str(e)}")
        return False

def test_training_runs_table():
    """Test training_runs table access"""
    logger.info("🔍 Testing training_runs table...")
    
    try:
        supabase = get_supabase_client()
        result = supabase.table("training_runs").select("*").limit(5).execute()
        
        logger.info(f"✅ Found {len(result.data)} training runs")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to access training_runs table: {str(e)}")
        return False

def test_insert_document():
    """Test inserting a test document"""
    logger.info("🔍 Testing document insertion...")
    
    try:
        supabase = get_supabase_client()
        
        # Create test document data with proper UUID
        test_doc = {
            "id": str(uuid.uuid4()),
            "filename": "test_document.pdf",
            "status": "processed",
            "raw_text": "This is a test document for training workflow testing.",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        result = supabase.table("documents").insert(test_doc).execute()
        logger.info(f"✅ Test document inserted: {result.data[0]['id']}")
        
        # Clean up - delete the test document
        supabase.table("documents").delete().eq("id", test_doc["id"]).execute()
        logger.info("✅ Test document cleaned up")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to insert test document: {str(e)}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting Supabase training workflow tests...")
    
    tests = [
        ("Connectivity", test_supabase_connectivity),
        ("Form Types Table", test_form_types_table),
        ("Documents Table", test_documents_table),
        ("Extractions Table", test_extractions_table),
        ("Annotations Table", test_annotations_table),
        ("Training Runs Table", test_training_runs_table),
        ("Document Insertion", test_insert_document),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running test: {test_name}")
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} passed")
            else:
                logger.error(f"❌ {test_name} failed")
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {str(e)}")
    
    logger.info(f"\n🎉 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("✅ All tests passed! Supabase training workflow is ready.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main()) 