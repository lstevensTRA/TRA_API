"""
Database configuration for the API
Simplified database setup without Supabase dependencies
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# Create Base class
Base = declarative_base()

# Database URL - can be configured via environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tra_api.db")

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