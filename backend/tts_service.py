"""TTS service - placeholder implementation."""
import hashlib
from pathlib import Path
from typing import Optional

from config import settings


class TTSService:
    """Text-to-Speech service.
    
    Currently a placeholder that returns None for all requests.
    Ready for integration with Azure TTS, Google Cloud TTS, or Edge TTS.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir or settings.audio_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, text: str, language: str, voice: str) -> Path:
        hash_val = hashlib.md5(f"{text}:{language}:{voice}".encode("utf-8")).hexdigest()
        return self.output_dir / f"{hash_val}.mp3"

    async def generate_audio(self, text: str, language: str, voice: Optional[str] = None) -> Optional[Path]:
        """Generate TTS audio for given text.
        
        Returns:
            Path to audio file if successful, None if not available (placeholder).
            
        Note:
            This is a placeholder implementation. To enable TTS:
            1. Install a TTS SDK (azure-cognitiveservices-speech, google-cloud-texttospeech, etc.)
            2. Configure API credentials in environment variables
            3. Replace this method with actual TTS generation logic
        """
        # Placeholder: no runtime TTS engine bundled.
        # Returns None to indicate TTS is not available.
        return None


tts_service = TTSService()
