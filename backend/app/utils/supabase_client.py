"""
Supabase client configuration for pattern learning system
"""

import os
from supabase import create_client, Client
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = "https://qcoufveygmyqhxbvwjrn.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFjb3VmdmV5Z215cWh4YnZ3anJuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTEzMjgyMDQsImV4cCI6MjA2NjkwNDIwNH0.3nAaffQFST4U0kX4MJA6dF-UI5t_OIqoeWHYksQrT_8"

# Environment variable overrides (for production)
SUPABASE_URL = os.getenv('SUPABASE_URL', SUPABASE_URL)
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', SUPABASE_ANON_KEY)

# Global Supabase client instance
_supabase_client: Optional[Client] = None

def get_supabase_client() -> Client:
    """
    Get or create the Supabase client instance.
    
    Returns:
        Supabase client instance
    """
    global _supabase_client
    
    if _supabase_client is None:
        try:
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            logger.info("✅ Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {e}")
            raise
    
    return _supabase_client

def test_supabase_connection() -> bool:
    """
    Test the Supabase connection.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        client = get_supabase_client()
        # Try a simple query to test connection
        response = client.table('pattern_performance').select('count').limit(1).execute()
        logger.info("✅ Supabase connection test successful")
        return True
    except Exception as e:
        logger.error(f"❌ Supabase connection test failed: {e}")
        return False

# Initialize client on module import
try:
    get_supabase_client()
except Exception as e:
    logger.warning(f"⚠️ Supabase client initialization failed: {e}") 