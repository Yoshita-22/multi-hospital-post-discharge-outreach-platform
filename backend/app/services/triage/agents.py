import os
import json
import logging
import httpx
from typing import Dict, Any, List

from app.schemas.triage import (
    FindingsAssessment,
    ProtocolAssessment,
    SafetyAssessment,
    FindingInfo,
    RedFlagInfo,
    MatchedRuleInfo,
)
from app.schemas.conversation import ConversationResult

logger = logging.getLogger(__name__)

def get_triage_mode() -> str:
    return os.getenv("TRIAGE_MODE", "mock").lower()

async def call_gemini(system_prompt: str, user_prompt: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY is missing. Returning empty.")
        return {}
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.0
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(content)
    except Exception as e:
        logger.error(f"Gemini API call failed: {str(e)}")
        return {}

class FindingsAssessmentAgent:
    async def analyze(self, result: ConversationResult, patient_info: str) -> FindingsAssessment:
        if get_triage_mode() == "mock":
            # Deterministic mock based on transcript length or summary (or outcome)
            return self._mock_analyze(result)
            
        transcript_text = "\n".join([f"{t.get('role', 'unknown').upper()}: {t.get('text', '')}" for t in result.transcript])
        
        system_prompt = (
            "You are a clinical Findings Assessment Agent. Your ONLY job is to extract medical findings, symptoms, and red flags "
            "from the transcript. NEVER diagnose. Output JSON matching this schema: "
            "{\"assessment_level\": \"URGENT|ATTENTION|ROUTINE\", \"findings\": [{\"finding\": \"...\", \"evidence\": \"...\"}], "
            "\"red_flags\": [{\"name\": \"...\", \"evidence\": \"...\"}], \"evidence\": [\"...\"], \"confidence\": 0.9, \"reasoning\": \"...\"}"
        )
        user_prompt = f"Patient: {patient_info}\n\nTranscript:\n{transcript_text}"
        
        data = await call_gemini(system_prompt, user_prompt)
        try:
            # Try to validate via Pydantic
            if not data:
                raise ValueError("Empty response from LLM")
            return FindingsAssessment(**data)
        except Exception as e:
            logger.error(f"FindingsAgent validation failed: {e}. Falling back to safe failure.")
            return FindingsAssessment(
                assessment_level="ATTENTION",
                findings=[],
                red_flags=[],
                confidence=0.0,
                reasoning=f"Agent failed to parse response: {str(e)}"
            )

    def _mock_analyze(self, result: ConversationResult) -> FindingsAssessment:
        summary = result.summary.lower()
        if "severe" in summary or "chest pain" in summary:
            return FindingsAssessment(
                assessment_level="URGENT",
                findings=[FindingInfo(finding="Severe chest pain", evidence="Reported severe chest pain")],
                red_flags=[RedFlagInfo(name="Chest Pain", evidence="Patient reported severe chest pain")],
                confidence=0.95,
                reasoning="Mock Urgent scenario detected based on summary."
            )
        elif "worsening" in summary or "swelling" in summary:
            return FindingsAssessment(
                assessment_level="ATTENTION",
                findings=[FindingInfo(finding="Increased ankle swelling", evidence="Reported worsening swelling")],
                confidence=0.85,
                reasoning="Mock Attention scenario detected based on summary."
            )
        else:
            return FindingsAssessment(
                assessment_level="ROUTINE",
                findings=[FindingInfo(finding="No new symptoms", evidence="Patient reported feeling well")],
                confidence=0.99,
                reasoning="Mock Routine scenario detected."
            )

class ProtocolAssessmentAgent:
    async def analyze(self, findings: FindingsAssessment, protocol_rules: List[dict]) -> ProtocolAssessment:
        if get_triage_mode() == "mock":
            return self._mock_analyze(findings, protocol_rules)
            
        system_prompt = (
            "You are a Protocol Assessment Agent. Compare the Findings against the Protocol Rules. "
            "Output JSON matching this schema: "
            "{\"assessment_level\": \"URGENT|ATTENTION|ROUTINE\", \"matched_rules\": [{\"rule_id\": \"...\", \"name\": \"...\", \"evidence\": \"...\"}], "
            "\"red_flags\": [], \"requires_human_review\": true/false, \"recommended_action\": \"...\", \"confidence\": 0.9}"
        )
        user_prompt = f"Findings:\n{findings.model_dump_json(indent=2)}\n\nProtocol Rules:\n{json.dumps(protocol_rules, indent=2)}"
        
        data = await call_gemini(system_prompt, user_prompt)
        try:
            if not data:
                raise ValueError("Empty response from LLM")
            return ProtocolAssessment(**data)
        except Exception as e:
            logger.error(f"ProtocolAgent validation failed: {e}")
            return ProtocolAssessment(
                assessment_level="ATTENTION",
                requires_human_review=True,
                recommended_action="CLINICIAN_REVIEW",
                confidence=0.0
            )

    def _mock_analyze(self, findings: FindingsAssessment, protocol_rules: List[dict]) -> ProtocolAssessment:
        if findings.assessment_level == "URGENT":
            return ProtocolAssessment(
                assessment_level="URGENT",
                matched_rules=[MatchedRuleInfo(rule_id="RULE-URG", name="Urgent Symptom Override", evidence="Chest pain matched")],
                requires_human_review=True,
                recommended_action="IMMEDIATE_CLINICIAN_REVIEW",
                confidence=0.95
            )
        elif findings.assessment_level == "ATTENTION":
            return ProtocolAssessment(
                assessment_level="ATTENTION",
                matched_rules=[MatchedRuleInfo(rule_id="RULE-ATT", name="Worsening Symptom", evidence="Ankle swelling matched")],
                requires_human_review=True,
                recommended_action="CLINICIAN_REVIEW",
                confidence=0.90
            )
        else:
            return ProtocolAssessment(
                assessment_level="ROUTINE",
                matched_rules=[MatchedRuleInfo(rule_id="RULE-RTN", name="Routine Recovery", evidence="No symptoms matched")],
                requires_human_review=False,
                recommended_action="NO_ACTION_REQUIRED",
                confidence=0.99
            )

class SafetyAssessmentAgent:
    async def analyze(self, result: ConversationResult, findings: FindingsAssessment) -> SafetyAssessment:
        if get_triage_mode() == "mock":
            return self._mock_analyze(findings)
            
        transcript_text = "\n".join([f"{t.get('role', 'unknown').upper()}: {t.get('text', '')}" for t in result.transcript])
        
        system_prompt = (
            "You are a Safety Assessment Agent. Your job is to catch any unsafe LLM decisions or missed red flags in the transcript and findings. "
            "You must remain conservative. Output JSON matching this schema: "
            "{\"assessment_level\": \"URGENT|ATTENTION|ROUTINE\", \"red_flags\": [{\"name\": \"...\", \"evidence\": \"...\"}], "
            "\"requires_human_review\": true/false, \"recommended_action\": \"...\", \"confidence\": 0.9}"
        )
        user_prompt = f"Transcript:\n{transcript_text}\n\nFindings Assessment:\n{findings.model_dump_json(indent=2)}"
        
        data = await call_gemini(system_prompt, user_prompt)
        try:
            if not data:
                raise ValueError("Empty response from LLM")
            return SafetyAssessment(**data)
        except Exception as e:
            logger.error(f"SafetyAgent validation failed: {e}")
            return SafetyAssessment(
                assessment_level="ATTENTION",
                requires_human_review=True,
                recommended_action="CLINICIAN_REVIEW",
                confidence=0.0
            )

    def _mock_analyze(self, findings: FindingsAssessment) -> SafetyAssessment:
        if findings.assessment_level == "URGENT":
            return SafetyAssessment(
                assessment_level="URGENT",
                red_flags=[RedFlagInfo(name="Severe Pain", evidence="Patient is having severe chest pain")],
                requires_human_review=True,
                recommended_action="IMMEDIATE_CLINICIAN_REVIEW",
                confidence=0.98
            )
        elif findings.assessment_level == "ATTENTION":
            return SafetyAssessment(
                assessment_level="ATTENTION",
                requires_human_review=True,
                recommended_action="CLINICIAN_REVIEW",
                confidence=0.85
            )
        else:
            return SafetyAssessment(
                assessment_level="ROUTINE",
                requires_human_review=False,
                recommended_action="NO_ACTION_REQUIRED",
                confidence=0.99
            )
