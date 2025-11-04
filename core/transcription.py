"""Audio transcription using Whisper AI."""

import whisper
import numpy as np
from typing import Optional


class TranscriptionEngine:
    """Handles audio transcription using Whisper."""
    
    def __init__(self, model_name: str = "base", language: str = "pl", fp16: bool = False):
        """
        Initialize Whisper model.
        
        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
            language: Language code for transcription
            fp16: Use FP16 precision (requires GPU)
        """
        print(f"🔄 Loading Whisper model '{model_name}'...")
        self.model = whisper.load_model(model_name)
        self.language = language
        self.fp16 = fp16
        print("✅ Whisper model loaded")
    
    def transcribe(self, audio_data: np.ndarray) -> Optional[str]:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: NumPy array of audio samples
            
        Returns:
            Transcribed text or None if failed
        """
        try:
            result = self.model.transcribe(
                audio_data,
                language=self.language,
                fp16=self.fp16
            )
            text = result['text'].strip()
            return text if text else None
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return None
