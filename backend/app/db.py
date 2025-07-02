"""
Database configuration for the training workflow
Uses Supabase as the database backend
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from app.utils.supabase_client import SUPABASE_URL, SUPABASE_ANON_KEY
from supabase import create_client

# Create Base class
Base = declarative_base()

# Supabase PostgreSQL direct connection string (without db. prefix)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:2TOOdW7hB60tNZj9@qcoufveygmyqhxbvwjrn.supabase.co:5432/postgres")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Test database connection
def test_db_connection():
    """Test if we can connect to the database"""
    try:
        with engine.connect() as connection:
            result = connection.execute("SELECT 1")
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

SUPABASE_URL = "https://qcoufveygmyqhxbvwjrn.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFjb3VmdmV5Z215cWh4YnZ3anJuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTEzMjgyMDQsImV4cCI6MjA2NjkwNDIwNH0.3nAaffQFST4U0kX4MJA6dF-UI5t_OIqoeWHYksQrT_8"

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY) 