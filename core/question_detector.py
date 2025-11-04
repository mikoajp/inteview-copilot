"""Question detection logic."""

QUESTION_MARKERS = [
    "what", "why", "how", "when", "where", "who", "which", "can you", "could you", "would you",
    "jak", "dlaczego", "kiedy", "gdzie", "kto", "który", "czy", "możesz", "mógłbyś"
]
MIN_QUESTION_LENGTH = 8


class QuestionDetector:
    """Detects if transcribed text is a question."""
    
    def __init__(self, markers: list[str] = None, min_length: int = None):
        """
        Initialize detector.
        
        Args:
            markers: List of question marker words
            min_length: Minimum text length to consider
        """
        self.markers = markers or QUESTION_MARKERS
        self.min_length = min_length or MIN_QUESTION_LENGTH
    
    def is_question(self, text: str) -> bool:
        """
        Check if text is a question.
        
        Args:
            text: Transcribed text to analyze
            
        Returns:
            True if text appears to be a question
        """
        if not text or len(text) < self.min_length:
            return False
        
        text_lower = text.lower()
        return any(marker in text_lower for marker in self.markers)
    
    def is_valid_length(self, text: str) -> bool:
        """Check if text meets minimum length requirement."""
        return len(text) >= self.min_length
