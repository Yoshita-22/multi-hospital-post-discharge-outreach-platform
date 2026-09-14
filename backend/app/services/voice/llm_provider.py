from abc import ABC, abstractmethod
import json
import google.generativeai as genai
from pydantic import TypeAdapter
from app.schemas.conversation import (
    StructuredAgentOutput, 
    ConversationState,
    PatientContext,
    OutreachContext,
    ProtocolContext
)

class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(
        self, 
        patient_input: str, 
        state: ConversationState,
        patient_ctx: PatientContext,
        outreach_ctx: OutreachContext,
        protocol_ctx: ProtocolContext
    ) -> StructuredAgentOutput:
        pass

class MockLLMProvider(LLMProvider):
    async def generate_response(
        self, 
        patient_input: str, 
        state: ConversationState,
        patient_ctx: PatientContext,
        outreach_ctx: OutreachContext,
        protocol_ctx: ProtocolContext
    ) -> StructuredAgentOutput:
        # Deterministic mock response for testing state transitions
        import random
        from app.schemas.conversation import ConversationAction, ConversationStage, ConversationStateUpdate
        
        # Super simple deterministic logic based on the input text
        if "callback" in patient_input.lower():
            return StructuredAgentOutput(
                response="I will schedule a callback for you. What time works best?",
                action=ConversationAction.REQUEST_CALLBACK,
                captured_information={"responses": {}, "symptoms": [], "medication_information": {}, "follow_up_information": {}, "concerns": []},
                callback={"requested": True, "requested_time": None},
                conversation=ConversationStateUpdate(next_stage=ConversationStage.CALLBACK)
            )
        elif "goodbye" in patient_input.lower():
            return StructuredAgentOutput(
                response="Thank you for your time. Goodbye.",
                action=ConversationAction.COMPLETE,
                captured_information={"responses": {}, "symptoms": [], "medication_information": {}, "follow_up_information": {}, "concerns": []},
                conversation=ConversationStateUpdate(next_stage=ConversationStage.COMPLETE)
            )
            
        return StructuredAgentOutput(
            response="I understand. Can you tell me more?",
            action=ConversationAction.ASK_FOLLOWUP,
            captured_information={"responses": {"q1": patient_input}, "symptoms": [], "medication_information": {}, "follow_up_information": {}, "concerns": []},
            conversation=ConversationStateUpdate(next_stage=state.stage, current_question_id=state.current_question_id)
        )

class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro')

    async def generate_response(
        self, 
        patient_input: str, 
        state: ConversationState,
        patient_ctx: PatientContext,
        outreach_ctx: OutreachContext,
        protocol_ctx: ProtocolContext
    ) -> StructuredAgentOutput:
        
        # Build prompt
        system_prompt = f"""
You are an AI Conversation Agent for a post-discharge healthcare outreach platform.
Your job is to talk to the patient and gather information according to the protocol.
Do NOT perform triage, diagnosis, risk assessment, or escalation.

Patient: {patient_ctx.patient_name}
Conditions: {', '.join(patient_ctx.conditions)}
Campaign: {outreach_ctx.campaign_name}
Purpose: {outreach_ctx.outreach_purpose}

Protocol Questions:
{json.dumps(protocol_ctx.questions, indent=2)}

Current Conversation Stage: {state.stage.value}
Transcript History:
{json.dumps(state.transcript[-5:], indent=2)}

You MUST output ONLY valid JSON matching the exact schema required. Do not include markdown formatting.
"""

        prompt = f"Patient just said: {patient_input}\nGenerate the next response and extract information."
        
        response = await self.model.generate_content_async(
            contents=[
                {"role": "user", "parts": [system_prompt]},
                {"role": "user", "parts": [prompt]}
            ],
            # Use structured output feature in Gemini if available, or just instruct
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                # Gemini currently supports JSON schema but it's best to rely on Pydantic's JSON schema feature
                response_schema=StructuredAgentOutput.model_json_schema()
            )
        )
        
        json_data = response.text
        adapter = TypeAdapter(StructuredAgentOutput)
        return adapter.validate_json(json_data)
