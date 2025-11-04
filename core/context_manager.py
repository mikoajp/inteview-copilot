"""Context management for building prompts."""

from ..data.models import Context


class ContextManager:
    """Manages interview context and builds system prompts."""
    
    def __init__(self, context: Context = None):
        """Initialize with context."""
        self.context = context or Context()
    
    def update_context(self, context: Context):
        """Update the context."""
        self.context = context
    
    def build_system_prompt(self) -> str:
        """
        Build system prompt for LLM based on context.
        
        Returns:
            Complete system prompt string
        """
        prompt = """Jesteś ekspertem od rozmów rekrutacyjnych.

ZASADY:
- 2-4 zdania (zwięźle!)
- Konkretne przykłady
- Pozytywny ton
- Po polsku
"""
        
        if self.context.cv:
            prompt += f"\n\nTWOJE CV:\n{self.context.cv}\n"
        
        if self.context.company_name:
            prompt += f"\nFIRMA: {self.context.company_name}\n"
        
        if self.context.position:
            prompt += f"\nSTANOWISKO: {self.context.position}\n"
        
        return prompt
    
    def build_user_prompt(self, question: str) -> str:
        """
        Build user prompt for a specific question.
        
        Args:
            question: The recruiter's question
            
        Returns:
            Formatted user prompt
        """
        return f"Pytanie rekrutera: {question}\n\nWygeneruj profesjonalną odpowiedź:"
