"""Data models for the application."""

from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Context:
    """User context for interview preparation."""
    cv: str = ''
    company: str = ''
    position: str = ''
    custom_system_prompt: str = ''  # User-customizable system prompt


@dataclass
class HistoryEntry:
    """Single Q&A history entry."""
    question: str
    answer: str
    timestamp: str = ''

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
