from datetime import datetime, timezone
import uuid
from typing import Tuple, Optional

from app.schemas.conversation import (
    PatientContext,
    OutreachContext,
    ProtocolContext,
    ConversationState,
    ConversationResult,
    ConversationStage,
    ConversationAction,
    ConversationOutcome
)
from app.services.voice.stt_provider import STTProvider
from app.services.voice.tts_provider import TTSProvider
from app.services.voice.llm_provider import LLMProvider

class ConversationAgent:
    def __init__(
        self,
        llm_provider: LLMProvider,
        stt_provider: STTProvider,
        tts_provider: TTSProvider,
        patient_ctx: PatientContext,
        outreach_ctx: OutreachContext,
        protocol_ctx: ProtocolContext
    ):
        self.llm = llm_provider
        self.stt = stt_provider
        self.tts = tts_provider
        self.patient_ctx = patient_ctx
        self.outreach_ctx = outreach_ctx
        self.protocol_ctx = protocol_ctx
        
        self.state = ConversationState()
        self.started_at = datetime.now(timezone.utc)
        self.is_completed = False

    async def start(self) -> Tuple[str, bytes]:
        """
        Starts the conversation and returns the initial greeting.
        """
        self.state.stage = ConversationStage.INTRO
        greeting_text = f"Hello, am I speaking with {self.patient_ctx.patient_name}?"
        
        self.state.transcript.append({"role": "agent", "text": greeting_text})
        audio = await self.tts.synthesize(greeting_text)
        return greeting_text, audio

    async def process_audio_turn(self, audio_bytes: bytes) -> Tuple[str, bytes]:
        """
        Takes patient audio, runs STT, generates next response via LLM, and returns TTS audio.
        """
        if self.is_completed:
            return "", b""

        patient_text = await self.stt.transcribe(audio_bytes)
        
        if not patient_text.strip():
            # Handle empty transcript (no answer / noise)
            response_text = "I'm sorry, I didn't quite catch that. Could you please repeat?"
            self.state.transcript.append({"role": "agent", "text": response_text})
            audio = await self.tts.synthesize(response_text)
            return response_text, audio

        return await self.process_text_turn(patient_text)

    async def process_text_turn(self, patient_text: str) -> Tuple[str, bytes]:
        """
        Processes text directly (useful for testing or if STT is already done).
        """
        if self.is_completed:
            return "", b""

        self.state.transcript.append({"role": "patient", "text": patient_text})

        # Call LLM
        output = await self.llm.generate_response(
            patient_input=patient_text,
            state=self.state,
            patient_ctx=self.patient_ctx,
            outreach_ctx=self.outreach_ctx,
            protocol_ctx=self.protocol_ctx
        )

        # Update State
        self._update_state(output)

        self.state.transcript.append({"role": "agent", "text": output.response})
        
        # Determine if we should terminate
        if output.action in [
            ConversationAction.COMPLETE, 
            ConversationAction.DECLINED, 
            ConversationAction.REQUEST_CALLBACK, 
            ConversationAction.INTERRUPTED, 
            ConversationAction.TRANSFER
        ]:
            self.is_completed = True

        audio = await self.tts.synthesize(output.response)
        return output.response, audio

    def _update_state(self, output):
        # Update stage
        self.state.stage = output.conversation.next_stage
        if output.conversation.current_question_id:
            self.state.current_question_id = output.conversation.current_question_id

        # Merge captured information
        if output.captured_information:
            # Responses
            for k, v in output.captured_information.responses.items():
                self.state.captured_data.responses[k] = v
                if k not in self.state.completed_questions:
                    self.state.completed_questions.append(k)

            # Symptoms
            for s in output.captured_information.symptoms:
                self.state.captured_data.symptoms.append(s)

            # Meds, follow up, etc (just simple overwrite or merge)
            self.state.captured_data.medication_information.update(output.captured_information.medication_information)
            self.state.captured_data.follow_up_information.update(output.captured_information.follow_up_information)
            
            for c in output.captured_information.concerns:
                if c not in self.state.captured_data.concerns:
                    self.state.captured_data.concerns.append(c)

        if output.callback.requested:
            self.state.callback_requested = True
            self.state.callback_time = output.callback.requested_time

    def get_result(self) -> ConversationResult:
        """
        Compiles the current state into the final ConversationResult.
        """
        outcome = ConversationOutcome.COMPLETED
        if self.state.callback_requested:
            outcome = ConversationOutcome.CALLBACK_REQUESTED
        elif self.state.stage == ConversationStage.DECLINED:
            outcome = ConversationOutcome.PATIENT_DECLINED
        elif self.state.stage == ConversationStage.INTERRUPTED:
            outcome = ConversationOutcome.INTERRUPTED
        elif self.state.stage == ConversationStage.TRANSFER:
            outcome = ConversationOutcome.TRANSFERRED

        # patient_reached is true if they said something
        patient_reached = any(t['role'] == 'patient' for t in self.state.transcript)

        return ConversationResult(
            call_id=self.outreach_ctx.call_id,
            patient_id=self.patient_ctx.patient_id,
            campaign_id=self.outreach_ctx.campaign_id,
            outcome=outcome,
            patient_reached=patient_reached,
            responses=self.state.captured_data.responses,
            symptoms_reported=self.state.captured_data.symptoms,
            uncertainties=[],
            callback_requested=self.state.callback_requested,
            callback_time=self.state.callback_time,
            transcript=self.state.transcript,
            summary="Automated summary not yet implemented in mock.",
            started_at=self.started_at,
            completed_at=datetime.now(timezone.utc)
        )
