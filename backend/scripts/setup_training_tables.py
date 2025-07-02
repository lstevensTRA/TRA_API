"""
Setup script for training workflow tables in Supabase
"""

import sys
import os

# Add the parent directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from app.utils.supabase_client import get_supabase_client
from app.utils.wi_patterns import form_patterns
import logging

logger = logging.getLogger(__name__)

# SQL statements to create training workflow tables
TRAINING_TABLES_SQL = [
    """
    -- Create form_types table
    CREATE TABLE IF NOT EXISTS form_types (
        id SERIAL PRIMARY KEY,
        code VARCHAR UNIQUE NOT NULL,
        description TEXT,
        priority INTEGER DEFAULT 1
    );
    """,
    
    """
    -- Create upload_batches table
    CREATE TABLE IF NOT EXISTS upload_batches (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        method VARCHAR NOT NULL,
        description TEXT,
        status VARCHAR NOT NULL DEFAULT 'pending',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """,
    
    """
    -- Create documents table
    CREATE TABLE IF NOT EXISTS documents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        source_url TEXT,
        filename TEXT,
        upload_batch_id UUID REFERENCES upload_batches(id),
        status VARCHAR NOT NULL DEFAULT 'pending',
        error_message TEXT,
        file_size BIGINT,
        raw_text TEXT,
        processing_time_ms INTEGER,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """,
    
    """
    -- Create extractions table
    CREATE TABLE IF NOT EXISTS extractions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        document_id UUID NOT NULL REFERENCES documents(id),
        form_type_id INTEGER NOT NULL REFERENCES form_types(id),
        extraction_method VARCHAR NOT NULL,
        fields JSONB NOT NULL,
        confidence FLOAT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """,
    
    """
    -- Create users table
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email VARCHAR UNIQUE NOT NULL,
        name VARCHAR,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """,
    
    """
    -- Create annotations table
    CREATE TABLE IF NOT EXISTS annotations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        extraction_id UUID NOT NULL REFERENCES extractions(id),
        annotator_id UUID REFERENCES users(id),
        corrected_fields JSONB NOT NULL,
        status VARCHAR NOT NULL DEFAULT 'pending',
        notes TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """,
    
    """
    -- Create training_runs table
    CREATE TABLE IF NOT EXISTS training_runs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        form_type_id INTEGER NOT NULL REFERENCES form_types(id),
        started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        finished_at TIMESTAMP WITH TIME ZONE,
        status VARCHAR NOT NULL DEFAULT 'started',
        accuracy FLOAT,
        regex_baseline FLOAT,
        model_file_path TEXT,
        notes TEXT
    );
    """,
    
    """
    -- Create training_targets table
    CREATE TABLE IF NOT EXISTS training_targets (
        id SERIAL PRIMARY KEY,
        form_type_id INTEGER REFERENCES form_types(id),
        target_count INTEGER NOT NULL DEFAULT 100,
        priority INTEGER DEFAULT 1,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    
    """
    -- Create training_progress view
    CREATE OR REPLACE VIEW training_progress AS
    SELECT 
        ft.code as form_type,
        ft.description,
        COUNT(DISTINCT e.id) as total_extractions,
        COUNT(DISTINCT CASE WHEN a.id IS NOT NULL THEN e.id END) as annotated_count,
        CASE 
            WHEN COUNT(DISTINCT e.id) > 0 
            THEN ROUND((COUNT(DISTINCT CASE WHEN a.id IS NOT NULL THEN e.id END)::FLOAT / COUNT(DISTINCT e.id)::FLOAT) * 100, 2)
            ELSE NULL 
        END as completion_percentage,
        AVG(e.confidence) as avg_confidence
    FROM form_types ft
    LEFT JOIN extractions e ON ft.id = e.form_type_id
    LEFT JOIN annotations a ON e.id = a.extraction_id
    GROUP BY ft.id, ft.code, ft.description
    ORDER BY ft.priority DESC, ft.code;
    """
]

def setup_training_tables():
    """Set up training workflow tables in Supabase"""
    try:
        client = get_supabase_client()
        logger.info("✅ Connected to Supabase")
        
        # Execute SQL statements
        for i, sql in enumerate(TRAINING_TABLES_SQL, 1):
            logger.info(f"Executing SQL statement {i}/{len(TRAINING_TABLES_SQL)}")
            try:
                # Note: Supabase client doesn't support direct SQL execution
                # You'll need to run these in your Supabase dashboard
                logger.info(f"SQL Statement {i}:")
                logger.info(sql.strip())
                logger.info("-" * 50)
            except Exception as e:
                logger.error(f"Error executing statement {i}: {e}")
        
        logger.info("📋 Please run the SQL statements above in your Supabase dashboard SQL editor")
        logger.info("🔗 Go to: https://supabase.com/dashboard/project/qcoufveygmyqhxbvwjrn/sql")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to setup training tables: {e}")
        return False

def initialize_form_types():
    """Initialize form types from wi_patterns"""
    try:
        client = get_supabase_client()
        logger.info("✅ Connected to Supabase for form types initialization")
        
        for code, pattern in form_patterns.items():
            description = pattern.get('pattern', code)
            
            # Check if form type exists
            response = client.table('form_types').select('id').eq('code', code).execute()
            
            if not response.data:
                # Insert new form type
                form_type_data = {
                    'code': code,
                    'description': description,
                    'priority': 1
                }
                response = client.table('form_types').insert(form_type_data).execute()
                logger.info(f"✅ Created form type: {code}")
                
                # Create training target
                if response.data:
                    form_type_id = response.data[0]['id']
                    target_data = {
                        'form_type_id': form_type_id,
                        'target_count': 100,
                        'priority': 1
                    }
                    client.table('training_targets').insert(target_data).execute()
                    logger.info(f"✅ Created training target for: {code}")
            else:
                logger.info(f"⏭️ Form type already exists: {code}")
        
        logger.info("🎉 Form types initialization completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize form types: {e}")
        return False

def main():
    logger.info("🚀 Starting training workflow setup...")
    
    # Step 1: Test connection
    logger.info("🔍 Step 1: Testing database connection...")
    try:
        client = get_supabase_client()
        logger.info("✅ Supabase client connection successful")
    except Exception as e:
        logger.error(f"❌ Supabase client connection failed: {e}")
        return
    
    # Step 2: Setup tables
    logger.info("📋 Step 2: Setting up training tables...")
    if setup_training_tables():
        logger.info("✅ Table setup instructions provided")
    else:
        logger.error("❌ Table setup failed")
        return
    
    # Step 3: Initialize form types
    logger.info("📋 Step 3: Initializing form types...")
    if initialize_form_types():
        logger.info("✅ Form types initialization completed")
    else:
        logger.error("❌ Form types initialization failed")
        return
    
    logger.info("🎉 Training workflow setup completed successfully!")
    logger.info("🚀 You can now start the backend server and test the workflow")

if __name__ == '__main__':
    main() 