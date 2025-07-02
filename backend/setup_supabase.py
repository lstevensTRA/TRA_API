#!/usr/bin/env python3
"""
Setup script for Supabase pattern learning tables

This script creates the necessary tables in Supabase for the ML-enhanced
pattern learning system. Run this once during initial setup.
"""

import os
import sys
import logging
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.utils.supabase_client import get_supabase_client, test_supabase_connection
from app.utils.supabase_schema import get_sql_create_statements, initialize_tables

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main setup function"""
    logger.info("🚀 Starting Supabase setup for pattern learning system...")
    
    try:
        # Test Supabase connection
        logger.info("🔍 Testing Supabase connection...")
        if not test_supabase_connection():
            logger.error("❌ Failed to connect to Supabase")
            return False
        
        logger.info("✅ Supabase connection successful")
        
        # Initialize tables
        logger.info("🔧 Initializing database tables...")
        if not initialize_tables():
            logger.error("❌ Failed to initialize tables")
            return False
        
        logger.info("✅ Database tables initialized successfully")
        
        # Print SQL statements for manual execution if needed
        logger.info("📋 SQL statements for manual execution:")
        statements = get_sql_create_statements()
        for i, statement in enumerate(statements, 1):
            logger.info(f"\n--- Statement {i} ---")
            logger.info(statement.strip())
        
        logger.info("\n🎉 Supabase setup completed successfully!")
        logger.info("💡 If tables weren't created automatically, run the SQL statements above in your Supabase dashboard")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 