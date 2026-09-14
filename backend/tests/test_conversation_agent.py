import pytest
import uuid
from datetime import datetime
from typing import Dict, List

from app.schemas.conversation import (
    PatientContext, OutreachContext, ProtocolContext, 
    ConversationStage, ConversationAction, ConversationOutcome
)
from app.services.voice.stt_provider import MockSTTProvider
from app.services.voice.tts_provider import MockTTSProvider
from app.services.voice.llm_provider import MockLLMProvider
from app.services.voice.conversation_agent import ConversationAgent

@pytest.fixture
def mock_contexts():
    patient_ctx = PatientContext(
        patient_id=uuid.uuid4(),
        patient_name="John Doe",
        conditions=["Heart Failure"],
        medications=["Lisinopril"],
    )
    outreach_ctx = OutreachContext(
        call_id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        campaign_name="HF Post-Discharge",
        outreach_purpose="Check up on symptoms",
    )
    protocol_ctx = ProtocolContext(
        protocol_name="HF Standard",
        version="1.0",
        questions=[{"id": "q1", "text": "Have you noticed any swelling in your ankles?"}]
    )
    return patient_ctx, outreach_ctx, protocol_ctx

@pytest.mark.asyncio
async def test_conversation_agent_initialization(mock_contexts):
    p_ctx, o_ctx, pr_ctx = mock_contexts
    agent = ConversationAgent(MockLLMProvider(), MockSTTProvider(), MockTTSProvider(), p_ctx, o_ctx, pr_ctx)
    
    greeting, audio = await agent.start()
    
    assert agent.state.stage == ConversationStage.INTRO
    assert "John Doe" in greeting
    assert len(agent.state.transcript) == 1

@pytest.mark.asyncio
async def test_conversation_agent_normal_turn(mock_contexts):
    p_ctx, o_ctx, pr_ctx = mock_contexts
    agent = ConversationAgent(MockLLMProvider(), MockSTTProvider(), MockTTSProvider(), p_ctx, o_ctx, pr_ctx)
    await agent.start()
    
    # Process text directly
    reply, audio = await agent.process_text_turn("My ankles are a bit swollen")
    
    assert "Can you tell me more?" in reply
    assert agent.state.captured_data.responses.get("q1") == "My ankles are a bit swollen"
    assert "q1" in agent.state.completed_questions
    assert not agent.is_completed

@pytest.mark.asyncio
async def test_conversation_agent_callback_request(mock_contexts):
    p_ctx, o_ctx, pr_ctx = mock_contexts
    agent = ConversationAgent(MockLLMProvider(), MockSTTProvider(), MockTTSProvider(), p_ctx, o_ctx, pr_ctx)
    await agent.start()
    
    # Send callback
    reply, audio = await agent.process_text_turn("I am busy, can you callback later?")
    
    assert agent.state.callback_requested is True
    assert agent.state.stage == ConversationStage.CALLBACK
    assert agent.is_completed
    
    result = agent.get_result()
    assert result.outcome == ConversationOutcome.CALLBACK_REQUESTED

@pytest.mark.asyncio
async def test_conversation_agent_complete(mock_contexts):
    p_ctx, o_ctx, pr_ctx = mock_contexts
    agent = ConversationAgent(MockLLMProvider(), MockSTTProvider(), MockTTSProvider(), p_ctx, o_ctx, pr_ctx)
    await agent.start()
    
    # Send goodbye
    reply, audio = await agent.process_text_turn("That's all, goodbye.")
    
    assert agent.state.stage == ConversationStage.COMPLETE
    assert agent.is_completed
    
    result = agent.get_result()
    assert result.outcome == ConversationOutcome.COMPLETED
    assert result.patient_reached is True
