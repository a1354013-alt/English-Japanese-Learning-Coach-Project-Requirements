"""TTS service."""
import hashlib
from pathlib import Path
from typing import Optional

from config import settings


class TTSService:
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir or settings.audio_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, text: str, language: str, voice: str) -> Path:
        hash_val = hashlib.md5(f"{text}:{language}:{voice}".encode("utf-8")).hexdigest()
        return self.output_dir / f"{hash_val}.mp3"

    async def generate_audio(self, text: str, language: str, voice: Optional[str] = None) -> Optional[Path]:
        cache_path = self._get_cache_path(text, language, voice or "default")
        if cache_path.exists():
            return cache_path

        # Placeholder: no runtime TTS engine bundled.
        return None


tts_service = TTSService()
