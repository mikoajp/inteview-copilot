"""Gemini AI client for generating responses."""

import google.generativeai as genai
from typing import Optional
import asyncio
from functools import partial


class GeminiClient:
    """Client for Google Gemini API."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google API key
            model: Gemini model name
        """
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        
        genai.configure(api_key=api_key)
        self.model_name = model
        self.model = genai.GenerativeModel(model)
        print(f"✅ Gemini client initialized with model: {model}")
    
    def check_connection(self) -> bool:
        """
        Check if Gemini API is accessible.
        
        Returns:
            True if connection successful
        """
        try:
            # Simple test generation
            response = self.model.generate_content("Hello")
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
    ) -> Optional[str]:
        """
        Generate response using Gemini (async).
        
        Args:
            system_prompt: System context prompt
            user_prompt: User question/prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response text or None if failed
        """
        try:
            print(f"🤖 Generating with Gemini: {self.model_name}")
            
            # Combine system and user prompts
            full_prompt = f"{system_prompt}\n\nUser Question: {user_prompt}\n\nYour Answer:"
            
            # Configure generation
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            # Run sync method in executor to make it async
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                partial(
                    self.model.generate_content,
                    full_prompt,
                    generation_config=generation_config
                )
            )
            
            answer = response.text.strip()
            print(f"✅ Response generated ({len(answer)} chars)")
            return answer
        
        except Exception as e:
            error_msg = f"❌ Gemini Error: {str(e)}"
            print(error_msg)
            return error_msg
    
    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """
        Generate response using Gemini (sync version).
        
        Args:
            system_prompt: System context prompt
            user_prompt: User question/prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response text or None if failed
        """
        try:
            print(f"🤖 Generating with Gemini: {self.model_name}")
            
            # Combine system and user prompts
            full_prompt = f"{system_prompt}\n\nUser Question: {user_prompt}\n\nYour Answer:"
            
            # Configure generation
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            answer = response.text.strip()
            print(f"✅ Response generated ({len(answer)} chars)")
            return answer
        
        except Exception as e:
            error_msg = f"❌ Gemini Error: {str(e)}"
            print(error_msg)
            return error_msg
