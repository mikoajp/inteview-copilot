"""Data models for the application."""

from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


@dataclass
class Context:
    """User context for interview preparation."""
    cv: str = ''
    company_name: str = ''
    position: str = ''
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Context':
        """Create from dictionary."""
        return cls(**data)
    
    def is_empty(self) -> bool:
        """Check if context is empty."""
        return not any([self.cv.strip(), self.company_name.strip(), self.position.strip()])
    
    def filled_count(self) -> int:
        """Count filled fields."""
        return sum(1 for v in [self.cv, self.company_name, self.position] if v.strip())


@dataclass
class HistoryEntry:
    """Single Q&A history entry."""
    question: str
    answer: str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'HistoryEntry':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class AudioDevice:
    """Audio device information."""
    index: int
    name: str
    max_input_channels: int
    
    @property
    def display_name(self) -> str:
        """Get formatted display name."""
        return f"[{self.index}] {self.name}"
    
    def is_virtual(self, virtual_names: list[str]) -> bool:
        """Check if this is a virtual audio device."""
        return any(virtual.lower() in self.name.lower() for virtual in virtual_names)


@dataclass
class LLMModel:
    """LLM model information."""
    id: str
    object: str = "model"
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LLMModel':
        """Create from API response."""
        return cls(id=data['id'], object=data.get('object', 'model'))
    
    def is_embedding_model(self) -> bool:
        """Check if this is an embedding model."""
        return 'embedding' in self.id.lower()
