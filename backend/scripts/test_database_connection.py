"""
Test database connection and verify training workflow tables
"""

import sys
import os

# Add the parent directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from app.db import engine, SessionLocal
from app.models import Base
from app.utils.supabase_client import get_supabase_client
import logging

logger = logging.getLogger(__name__)

def test_sqlalchemy_connection():
    """Test SQLAlchemy connection to Supabase PostgreSQL"""
    try:
        # Test connection
        with engine.connect() as connection:
            result = connection.execute("SELECT 1")
            logger.info("✅ SQLAlchemy connection successful")
            return True
    except Exception as e:
        logger.error(f"❌ SQLAlchemy connection failed: {e}")
        return False

def test_supabase_client():
    """Test Supabase client connection"""
    try:
        client = get_supabase_client()
        # Try a simple query
        response = client.table('form_types').select('count').limit(1).execute()
        logger.info("✅ Supabase client connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Supabase client connection failed: {e}")
        return False

def verify_tables():
    """Verify all training workflow tables exist"""
    required_tables = [
        'form_types',
        'upload_batches', 
        'documents',
        'extractions',
        'users',
        'annotations',
        'training_runs',
        'training_targets'
    ]
    
    try:
        client = get_supabase_client()
        missing_tables = []
        
        for table in required_tables:
            try:
                response = client.table(table).select('count').limit(1).execute()
                logger.info(f"✅ Table '{table}' exists")
            except Exception as e:
                logger.error(f"❌ Table '{table}' missing: {e}")
                missing_tables.append(table)
        
        if missing_tables:
            logger.error(f"❌ Missing tables: {missing_tables}")
            return False
        else:
            logger.info("✅ All required tables exist")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error verifying tables: {e}")
        return False

def test_form_types_data():
    """Test if form types have been populated"""
    try:
        client = get_supabase_client()
        response = client.table('form_types').select('*').execute()
        
        if response.data:
            logger.info(f"✅ Found {len(response.data)} form types")
            for form_type in response.data:
                logger.info(f"  - {form_type['code']}: {form_type['description']}")
            return True
        else:
            logger.warning("⚠️ No form types found - run the setup script to populate them")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error checking form types: {e}")
        return False

def main():
    logger.info("🔍 Testing database connections and tables...")
    
    # Test SQLAlchemy connection
    logger.info("📋 Step 1: Testing SQLAlchemy connection...")
    if not test_sqlalchemy_connection():
        return
    
    # Test Supabase client
    logger.info("📋 Step 2: Testing Supabase client...")
    if not test_supabase_client():
        return
    
    # Verify tables
    logger.info("📋 Step 3: Verifying tables...")
    if not verify_tables():
        logger.error("❌ Some tables are missing. Please run the SQL script in Supabase first.")
        return
    
    # Test form types data
    logger.info("📋 Step 4: Checking form types data...")
    test_form_types_data()
    
    logger.info("🎉 Database connection and table verification completed!")
    logger.info("🚀 Your backend is ready to start!")

if __name__ == '__main__':
    main() 