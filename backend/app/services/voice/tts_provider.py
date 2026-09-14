from abc import ABC, abstractmethod
import tempfile
import os

class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        pass

class MockTTSProvider(TTSProvider):
    async def synthesize(self, text: str) -> bytes:
        # Return the text itself encoded as bytes to verify text flow
        return text.encode('utf-8')

import httpx

class DeepgramTTSProvider(TTSProvider):
    def __init__(self, api_key: str, model: str = "aura-asteria-en"):
        self.api_key = api_key
        self.model = model

    async def synthesize(self, text: str) -> bytes:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.deepgram.com/v1/speak?model={self.model}&encoding=linear16&container=wav&sample_rate=24000",
                    headers={"Authorization": f"Token {self.api_key}"},
                    json={"text": text},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.content
        except Exception as e:
            print(f"Deepgram TTS Error: {e}")
            return b""
