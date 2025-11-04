"""Gemini AI client for generating responses."""

import google.generativeai as genai
from typing import Optional
import asyncio
from functools import partial


# Supported Gemini models
SUPPORTED_MODELS = [
    "gemini-2.5-pro-exp-03-25",  # Gemini 2.5 Pro (Experimental, March 2025)
    "gemini-2.0-flash-exp",       # Gemini 2.0 Flash (Experimental)
    "gemini-1.5-pro",             # Gemini 1.5 Pro (Stable)
    "gemini-1.5-flash",           # Gemini 1.5 Flash (Stable)
    "gemini-pro",                 # Legacy Gemini Pro
]


class GeminiClient:
    """Client for Google Gemini API with native system instruction support."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-pro-exp-03-25"):
        """
        Initialize Gemini client.

        Args:
            api_key: Google API key
            model: Gemini model name

        Raises:
            ValueError: If API key is missing
        """
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")

        # Validate model
        if model not in SUPPORTED_MODELS:
            print(f"⚠️  WARNING: Model '{model}' is not in the supported models list.")
            print(f"   Supported models: {', '.join(SUPPORTED_MODELS)}")
            print(f"   Continuing anyway, but API calls may fail.")

        genai.configure(api_key=api_key)
        self.model_name = model
        self.api_key = api_key
        print(f"✅ Gemini client initialized with model: {model}")
    
    def check_connection(self) -> bool:
        """
        Check if Gemini API is accessible.

        Returns:
            True if connection successful
        """
        try:
            # Simple test generation
            test_model = genai.GenerativeModel(self.model_name)
            response = test_model.generate_content("Hello")
            return bool(response.text)
        except Exception as e:
            print(f"❌ Gemini connection error: {e}")
            return False
    
    async def generate_response_async(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """
        Generate response using Gemini with native system instruction support (async).

        Args:
            system_prompt: System context prompt (used as native system_instruction)
            user_prompt: User question/prompt
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response text

        Raises:
            Exception: If generation fails
        """
        try:
            print(f"🤖 Generating with Gemini: {self.model_name}")

            # Create model with native system instruction support
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_prompt  # Native system instruction
            )

            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                top_p=0.95,      # Nucleus sampling
                top_k=40,        # Top-k sampling
            )

            # Run sync method in executor to make it async
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                partial(
                    model.generate_content,
                    user_prompt,  # Only user prompt (system instruction is separate)
                    generation_config=generation_config
                )
            )

            # Extract text from response
            answer = response.text.strip()
            print(f"✅ Response generated ({len(answer)} chars)")
            return answer

        except Exception as e:
            error_msg = f"Gemini API Error: {str(e)}"
            print(f"❌ {error_msg}")
            # Re-raise exception instead of returning error as text
            raise Exception(error_msg) from e
    
