from abc import ABC, abstractmethod
import asyncio
import os
import tempfile

class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> str:
        pass

class MockSTTProvider(STTProvider):
    async def transcribe(self, audio_bytes: bytes) -> str:
        # For testing, we could treat audio_bytes as straight text
        try:
            return audio_bytes.decode('utf-8')
        except:
            return "This is a mocked transcription of what the patient said."

import httpx

class DeepgramSTTProvider(STTProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def transcribe(self, audio_bytes: bytes) -> str:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true",
                    headers={"Authorization": f"Token {self.api_key}", "Content-Type": "audio/wav"},
                    content=audio_bytes,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data["results"]["channels"][0]["alternatives"][0]["transcript"]
        except Exception as e:
            print(f"Deepgram STT Error: {e}")
            return ""
