import httpx
import os
import base64
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_BASE_URL = "https://api.sarvam.ai"

async def speech_to_text(audio_bytes: bytes, language_code: str = "unknown") -> dict:
    """Convert voice input to text using Saarika Flash (fastest model)"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SARVAM_BASE_URL}/speech-to-text",
            headers={"api-subscription-key": SARVAM_API_KEY},
            files={"file": ("audio.wav", audio_bytes, "audio/x-wav")},
            data={
                "model": "saarika:v2.5",
                "language_code": language_code,
                "with_timestamps": "false"
            },
            timeout=30
        )
        result = response.json()
        print("STT response:", result)
        return result

async def text_to_speech(text: str, language_code: str = "en-IN") -> bytes:
    """Convert text to natural voice using Bulbul v2"""
    voice_map = {
        "ta-IN": "anushka",
        "hi-IN": "abhilash",
        "te-IN": "anushka",
        "kn-IN": "karun",
        "en-IN": "anushka",
        "ml-IN": "anushka",
        "bn-IN": "anushka",
    }
    speaker = voice_map.get(language_code, "anushka")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SARVAM_BASE_URL}/text-to-speech",
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "inputs": [text],
                "target_language_code": language_code,
                "speaker": speaker,
                "model": "bulbul:v2",
                "enable_preprocessing": True
            },
            timeout=30
        )
        result = response.json()
        print("TTS response keys:", result.keys())

        if "audios" in result:
            return base64.b64decode(result["audios"][0])
        elif "audio" in result:
            return base64.b64decode(result["audio"])
        else:
            print("❌ Unexpected TTS response:", result)
            raise ValueError(f"Unexpected TTS response: {result}")
