"""Database operations for Interview Copilot."""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from datetime import datetime
from db_models import User, InterviewContext, InterviewHistory
from models import Context


def create_user_db(db: Session, user_id: str, email: str, hashed_password: str, full_name: Optional[str] = None) -> User:
    """Create user in database."""
    db_user = User(
        id=user_id,
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_context(user_id: str, db: Session) -> Optional[Context]:
    """Get interview context for user."""
    db_context = db.query(InterviewContext).filter(
        InterviewContext.user_id == user_id
    ).order_by(InterviewContext.updated_at.desc()).first()

    if db_context:
        return Context(
            cv=db_context.cv,
            company=db_context.company,
            position=db_context.position
        )

    return Context()


def update_context(user_id: str, context: Context, db: Session) -> InterviewContext:
    """Update or create interview context for user."""
    db_context = db.query(InterviewContext).filter(
        InterviewContext.user_id == user_id
    ).order_by(InterviewContext.updated_at.desc()).first()

    if db_context:
        # Update existing context
        db_context.cv = context.cv
        db_context.company = context.company
        db_context.position = context.position
        db_context.updated_at = datetime.utcnow()
    else:
        # Create new context
        db_context = InterviewContext(
            user_id=user_id,
            cv=context.cv,
            company=context.company,
            position=context.position,
            created_at=datetime.utcnow()
        )
        db.add(db_context)

    db.commit()
    db.refresh(db_context)
    return db_context


def add_history_entry(user_id: str, question: str, answer: str, db: Session) -> InterviewHistory:
    """Add history entry for user."""
    db_history = InterviewHistory(
        user_id=user_id,
        question=question,
        answer=answer,
        created_at=datetime.utcnow()
    )
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    return db_history


def get_history(user_id: str, db: Session, limit: int = 100) -> List[Dict]:
    """Get interview history for user."""
    db_history = db.query(InterviewHistory).filter(
        InterviewHistory.user_id == user_id
    ).order_by(InterviewHistory.created_at.desc()).limit(limit).all()

    return [
        {
            "question": entry.question,
            "answer": entry.answer,
            "timestamp": entry.created_at.isoformat()
        }
        for entry in db_history
    ]


def clear_history(db: Session, user_id: str) -> int:
    """Clear all history for user."""
    count = db.query(InterviewHistory).filter(
        InterviewHistory.user_id == user_id
    ).delete()
    db.commit()
    return count
