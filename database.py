"""Database configuration and session management."""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from config import config

# Create database engine
engine = create_engine(
    config.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database (create tables)."""
    from db_models import User, InterviewContext, InterviewHistory
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")


def check_db_connection() -> bool:
    """Check if database connection is working."""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
