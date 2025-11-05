"""Context management for building prompts."""

from models import Context


class ContextManager:
    """Manages interview context and builds system prompts."""
    
    def __init__(self, context: Context = None):
        self.context = context or Context()

    def build_system_prompt(self, cv: str = "", company: str = "", position: str = "", custom_system_prompt: str = "") -> str:
        """Build system prompt for LLM based on provided values or stored context."""
        # Check if custom prompt is provided
        custom_prompt = custom_system_prompt or getattr(self.context, "custom_system_prompt", "")

        if custom_prompt:
            # User provided custom system prompt - use it as base
            prompt = custom_prompt
        else:
            # Use default prompt
            prompt = """Jesteś ekspertem od rozmów rekrutacyjnych.

ZASADY:
- 2-4 zdania (zwięźle!)
- Konkretne przykłady
- Pozytywny ton
- Po polsku
"""

        # Add context information
        cv_val = cv or self.context.cv
        company_val = company or getattr(self.context, "company", "")
        position_val = position or self.context.position

        if cv_val:
            prompt += f"\n\nTWOJE CV:\n{cv_val}\n"
        if company_val:
            prompt += f"\nFIRMA: {company_val}\n"
        if position_val:
            prompt += f"\nSTANOWISKO: {position_val}\n"

        return prompt
