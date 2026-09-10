from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.voice.tts import TextToSpeechService
from backend.voice.stt import SpeechToTextService

router = APIRouter(prefix="/api/voice", tags=["Voice Engine"])

class TTSRequest(BaseModel):
    text: str

@router.get("/status")
def voice_status():
    return {
        "ok": True,
        "stt": SpeechToTextService.transcribe(),
        "tts_available": True
    }

@router.post("/synthesize")
def synthesize_speech(payload: TTSRequest):
    packet = TextToSpeechService.synthesize_script(payload.text)
    return {"ok": True, "packet": packet}

