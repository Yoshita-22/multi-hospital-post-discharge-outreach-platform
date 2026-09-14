import abc
from fastapi import WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)

class AudioTransport(abc.ABC):
    @abc.abstractmethod
    async def send_audio(self, audio_bytes: bytes) -> None:
        """Sends audio bytes out through the transport."""
        pass
        
    @abc.abstractmethod
    async def receive_audio(self) -> bytes:
        """Waits for and receives audio bytes from the transport."""
        pass
        
    @abc.abstractmethod
    async def send_json(self, data: dict) -> None:
        """Sends JSON metadata out through the transport (e.g. state changes)."""
        pass


class BrowserAudioTransport(AudioTransport):
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        
    async def send_audio(self, audio_bytes: bytes) -> None:
        try:
            await self.ws.send_bytes(audio_bytes)
        except WebSocketDisconnect:
            logger.warning("WebSocket disconnected while sending audio.")
            raise
            
    async def receive_audio(self) -> bytes:
        try:
            # We expect the frontend to send complete binary chunks (e.g. WAV or WebM blob)
            data = await self.ws.receive_bytes()
            return data
        except WebSocketDisconnect:
            logger.warning("WebSocket disconnected while receiving audio.")
            raise

    async def send_json(self, data: dict) -> None:
        try:
            await self.ws.send_json(data)
        except WebSocketDisconnect:
            logger.warning("WebSocket disconnected while sending JSON.")
            raise
