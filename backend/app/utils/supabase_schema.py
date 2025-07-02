"""
Supabase table schema definitions for pattern learning system
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# Table schemas for pattern learning system
PATTERN_PERFORMANCE_SCHEMA = {
    "table_name": "pattern_performance",
    "columns": {
        "id": "bigint primary key generated always as identity",
        "pattern_id": "text not null",
        "pattern_name": "text not null",
        "parser_type": "text not null default 'wi'",
        "success_count": "integer not null default 0",
        "failure_count": "integer not null default 0",
        "total_extractions": "integer not null default 0",
        "average_confidence": "numeric(5,4) not null default 0.0",
        "last_used": "timestamp with time zone",
        "created_at": "timestamp with time zone default now()",
        "updated_at": "timestamp with time zone default now()"
    },
    "indexes": [
        "CREATE INDEX IF NOT EXISTS idx_pattern_performance_pattern_id ON pattern_performance(pattern_id)",
        "CREATE INDEX IF NOT EXISTS idx_pattern_performance_parser_type ON pattern_performance(parser_type)",
        "CREATE INDEX IF NOT EXISTS idx_pattern_performance_confidence ON pattern_performance(average_confidence DESC)"
    ]
}

EXTRACTION_FEEDBACK_SCHEMA = {
    "table_name": "extraction_feedback",
    "columns": {
        "id": "bigint primary key generated always as identity",
        "case_id": "text not null",
        "pattern_id": "text not null",
        "parser_type": "text not null default 'wi'",
        "extraction_result": "jsonb not null",
        "user_feedback": "jsonb",
        "confidence_score": "numeric(5,4) not null",
        "is_correct": "boolean",
        "feedback_notes": "text",
        "created_at": "timestamp with time zone default now()",
        "updated_at": "timestamp with time zone default now()"
    },
    "indexes": [
        "CREATE INDEX IF NOT EXISTS idx_extraction_feedback_case_id ON extraction_feedback(case_id)",
        "CREATE INDEX IF NOT EXISTS idx_extraction_feedback_pattern_id ON extraction_feedback(pattern_id)",
        "CREATE INDEX IF NOT EXISTS idx_extraction_feedback_parser_type ON extraction_feedback(parser_type)",
        "CREATE INDEX IF NOT EXISTS idx_extraction_feedback_created_at ON extraction_feedback(created_at DESC)"
    ]
}

PATTERN_SUGGESTIONS_SCHEMA = {
    "table_name": "pattern_suggestions",
    "columns": {
        "id": "bigint primary key generated always as identity",
        "pattern_id": "text not null",
        "parser_type": "text not null default 'wi'",
        "suggested_pattern": "text not null",
        "confidence_boost": "numeric(5,4) not null",
        "reasoning": "text",
        "status": "text not null default 'pending' check (status in ('pending', 'approved', 'rejected'))",
        "created_at": "timestamp with time zone default now()",
        "updated_at": "timestamp with time zone default now()"
    },
    "indexes": [
        "CREATE INDEX IF NOT EXISTS idx_pattern_suggestions_pattern_id ON pattern_suggestions(pattern_id)",
        "CREATE INDEX IF NOT EXISTS idx_pattern_suggestions_status ON pattern_suggestions(status)",
        "CREATE INDEX IF NOT EXISTS idx_pattern_suggestions_parser_type ON pattern_suggestions(parser_type)"
    ]
}

def get_table_schemas() -> Dict[str, Dict[str, Any]]:
    """
    Get all table schemas for the pattern learning system.
    
    Returns:
        Dictionary of table schemas
    """
    return {
        "pattern_performance": PATTERN_PERFORMANCE_SCHEMA,
        "extraction_feedback": EXTRACTION_FEEDBACK_SCHEMA,
        "pattern_suggestions": PATTERN_SUGGESTIONS_SCHEMA
    }

def get_sql_create_statements() -> List[str]:
    """
    Get SQL CREATE statements for all tables.
    
    Returns:
        List of SQL CREATE statements
    """
    schemas = get_table_schemas()
    statements = []
    
    for table_name, schema in schemas.items():
        columns = []
        for col_name, col_def in schema["columns"].items():
            columns.append(f"{col_name} {col_def}")
        
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {', '.join(columns)}
        );
        """
        statements.append(create_sql)
        
        # Add indexes
        for index_sql in schema.get("indexes", []):
            statements.append(index_sql)
    
    return statements

def initialize_tables():
    """
    Initialize all tables in Supabase.
    This should be called once during setup.
    """
    from .supabase_client import get_supabase_client
    
    try:
        client = get_supabase_client()
        statements = get_sql_create_statements()
        
        for statement in statements:
            # Note: Supabase doesn't support direct SQL execution via client
            # This would need to be run via Supabase dashboard or migrations
            logger.info(f"Table creation statement: {statement}")
        
        logger.info("✅ Table schema definitions ready for Supabase")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize tables: {e}")
        return False 