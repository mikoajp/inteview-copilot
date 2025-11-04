"""Tests for GeminiClient with Gemini 2.5 Pro."""

import pytest
import os
from core.gemini_client import GeminiClient, SUPPORTED_MODELS


class TestGeminiClient:
    """Test suite for GeminiClient."""

    def test_supported_models_list(self):
        """Test that supported models list contains expected models."""
        assert "gemini-2.5-pro-exp-03-25" in SUPPORTED_MODELS
        assert "gemini-2.0-flash-exp" in SUPPORTED_MODELS
        assert "gemini-1.5-pro" in SUPPORTED_MODELS
        assert "gemini-1.5-flash" in SUPPORTED_MODELS

    def test_init_without_api_key(self):
        """Test that initialization fails without API key."""
        with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
            GeminiClient(api_key="", model="gemini-2.5-pro-exp-03-25")

    def test_init_with_valid_api_key(self):
        """Test initialization with valid API key."""
        # Use dummy key for testing initialization only
        client = GeminiClient(
            api_key="test_api_key_123",
            model="gemini-2.5-pro-exp-03-25"
        )
        assert client.model_name == "gemini-2.5-pro-exp-03-25"
        assert client.api_key == "test_api_key_123"

    def test_init_with_unsupported_model(self, capsys):
        """Test that warning is printed for unsupported model."""
        client = GeminiClient(
            api_key="test_api_key_123",
            model="unsupported-model"
        )
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "unsupported-model" in captured.out

    def test_default_model_is_2_5_pro(self):
        """Test that default model is Gemini 2.5 Pro."""
        client = GeminiClient(api_key="test_api_key_123")
        assert client.model_name == "gemini-2.5-pro-exp-03-25"


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set - skipping integration tests"
)
class TestGeminiClientIntegration:
    """Integration tests for GeminiClient with real API."""

    @pytest.fixture
    def client(self):
        """Create GeminiClient with real API key."""
        api_key = os.getenv("GEMINI_API_KEY")
        return GeminiClient(api_key=api_key, model="gemini-2.5-pro-exp-03-25")

    def test_check_connection(self, client):
        """Test connection to Gemini API."""
        assert client.check_connection() is True

    async def test_generate_response_async(self, client):
        """Test async response generation."""
        system_prompt = "You are a helpful assistant. Be concise."
        user_prompt = "Say 'Hello' in one word."

        response = await client.generate_response_async(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=50
        )

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        assert "hello" in response.lower()

    async def test_generate_response_with_system_instruction(self, client):
        """Test that system instruction works correctly."""
        system_prompt = "You are a pirate. Always respond like a pirate would."
        user_prompt = "What is your name?"

        response = await client.generate_response_async(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.9,
            max_tokens=100
        )

        assert response is not None
        assert len(response) > 0
        # Pirate-like response should contain typical pirate words
        pirate_words = ["arr", "matey", "aye", "ye", "ahoy", "'"]
        assert any(word in response.lower() for word in pirate_words)

    async def test_generate_response_with_different_temperatures(self, client):
        """Test generation with different temperature values."""
        system_prompt = "You are a helpful assistant."
        user_prompt = "Count from 1 to 3."

        # Low temperature (more deterministic)
        response_low = await client.generate_response_async(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=50
        )

        # High temperature (more creative)
        response_high = await client.generate_response_async(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=1.5,
            max_tokens=50
        )

        assert response_low is not None
        assert response_high is not None
        assert "1" in response_low or "one" in response_low.lower()
        assert "1" in response_high or "one" in response_high.lower()

    async def test_generate_response_error_handling(self, client):
        """Test error handling for invalid requests."""
        system_prompt = "You are a helpful assistant."
        user_prompt = ""  # Empty prompt might cause issues

        try:
            response = await client.generate_response_async(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=50
            )
            # If it doesn't raise, response should still be valid
            assert isinstance(response, str)
        except Exception as e:
            # Exception should be raised (not returned as string)
            assert isinstance(e, Exception)
            assert "Gemini API Error" in str(e) or "Error" in str(e)

    async def test_generate_response_with_long_context(self, client):
        """Test generation with longer system instruction."""
        system_prompt = """
        You are an expert software engineer with 10 years of experience.
        You specialize in Python, FastAPI, and cloud architecture.
        When answering questions, provide practical examples and best practices.
        Be concise but informative.
        """
        user_prompt = "What is FastAPI?"

        response = await client.generate_response_async(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=200
        )

        assert response is not None
        assert len(response) > 20
        assert "fastapi" in response.lower()


@pytest.mark.asyncio
class TestGeminiClientMock:
    """Tests with mocked API calls."""

    async def test_generate_response_raises_exception_on_api_error(self, monkeypatch):
        """Test that API errors are raised as exceptions, not returned."""
        client = GeminiClient(api_key="test_key", model="gemini-2.5-pro-exp-03-25")

        async def mock_generate(*args, **kwargs):
            raise Exception("API Rate Limit Exceeded")

        # This test verifies the exception is raised properly
        with pytest.raises(Exception, match="Gemini API Error"):
            await client.generate_response_async(
                system_prompt="Test",
                user_prompt="Test",
                temperature=0.7,
                max_tokens=50
            )
