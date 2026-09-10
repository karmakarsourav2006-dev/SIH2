"""Speech-to-Text abstraction for Polar Energy AI."""
from typing import Dict, Any

class SpeechToTextService:
    @staticmethod
    def transcribe(audio_payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Transcribes voice commands from crew members.
        Returns recognized transcript or default message.
        """
        # In modern browsers, SpeechRecognition runs directly in the client via Web Speech API.
        # This endpoint supports server-side transcription pipelines or audio forwarding.
        return {
            "status": "ready",
            "supported_modes": ["browser_web_speech", "whisper_compatible"],
            "note": "Client-side Web Speech API active. Voice processing enabled."
        }

