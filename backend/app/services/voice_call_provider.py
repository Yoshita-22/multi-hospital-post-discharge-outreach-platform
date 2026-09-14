import abc
import asyncio
import logging
from app.schemas.conversation import (
    PatientContext,
    OutreachContext,
    ProtocolContext,
    ConversationResult
)
from app.services.voice.conversation_agent import ConversationAgent
import os
from app.services.voice.stt_provider import DeepgramSTTProvider, MockSTTProvider
from app.services.voice.tts_provider import DeepgramTTSProvider, MockTTSProvider
from app.services.voice.llm_provider import GeminiLLMProvider, MockLLMProvider

logger = logging.getLogger(__name__)

class VoiceCallProvider(abc.ABC):
    @abc.abstractmethod
    async def start_call(self, patient_ctx: PatientContext, outreach_ctx: OutreachContext, protocol_ctx: ProtocolContext) -> ConversationResult:
        """
        Starts a voice call and returns the resulting ConversationResult.
        """
        pass

class MockVoiceCallProvider(VoiceCallProvider):
    async def start_call(self, patient_ctx: PatientContext, outreach_ctx: OutreachContext, protocol_ctx: ProtocolContext) -> ConversationResult:
        # Simulate connecting the call
        await asyncio.sleep(1.0)
        
        logger.info(f"Mock Call connected for {patient_ctx.patient_name}")
        
        deepgram_key = os.getenv("DEEPGRAM_API_KEY", "dummy_key")
        gemini_key = os.getenv("GEMINI_API_KEY", "dummy_key")

        # Instantiate Agent with real AI components (or fallback to Mock if keys are dummy for deterministic test runs)
        if deepgram_key != "dummy_key" and gemini_key != "dummy_key":
            stt = DeepgramSTTProvider(api_key=deepgram_key)
            tts = DeepgramTTSProvider(api_key=deepgram_key)
            llm = GeminiLLMProvider(api_key=gemini_key)
        else:
            stt = MockSTTProvider()
            tts = MockTTSProvider()
            llm = MockLLMProvider()

        agent = ConversationAgent(
            llm_provider=llm,
            stt_provider=stt,
            tts_provider=tts,
            patient_ctx=patient_ctx,
            outreach_ctx=outreach_ctx,
            protocol_ctx=protocol_ctx
        )
        
        # Start conversation
        await agent.start()
        
        # Simulate patient conversational loop (text based to avoid needing raw audio simulation)
        simulated_patient_responses = [
            "Yes, speaking.",
            "I have had some swelling in my ankles.",
            "That's all, goodbye."
        ]
        
        for response in simulated_patient_responses:
            if agent.is_completed:
                break
                
            await asyncio.sleep(0.5) # Simulate processing/speaking time
            await agent.process_text_turn(response)
            
        # Ensure completion if loop didn't hit it
        if not agent.is_completed:
            await agent.process_text_turn("goodbye")
            
        logger.info(f"Mock Call completed for {patient_ctx.patient_name}")
        
        return agent.get_result()

