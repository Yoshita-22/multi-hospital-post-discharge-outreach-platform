import logging
import json
import os
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.schemas.conversation import ConversationResult
from app.models.triage import TriageResult
from app.models.campaign import Campaign
from app.models.ehr import Patient
from app.models.protocol import Protocol

logger = logging.getLogger(__name__)

async def call_gemini(system_prompt: str, user_prompt: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
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
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        try:
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(content)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            return {}

class TriageService:
    @staticmethod
    async def process(result: ConversationResult, db: AsyncSession):
        logger.info(f"Starting Multi-Agent Triage for Call ID {result.call_id}")
        
        # 1. Fetch Context
        stmt = select(Patient).where(Patient.id == result.patient_id)
        pat_res = await db.execute(stmt)
        patient = pat_res.scalars().first()
        
        stmt_camp = select(Campaign).options(selectinload(Campaign.protocol)).where(Campaign.id == result.campaign_id)
        camp_res = await db.execute(stmt_camp)
        campaign = camp_res.scalars().first()
        
        protocol = campaign.protocol
        protocol_questions = protocol.questions if protocol else []
        
        # Format transcript for prompts
        transcript_text = "\n".join([f"{t.get('role', 'unknown').upper()}: {t.get('text', '')}" for t in result.transcript])
        
        # 2. FINDINGS AGENT
        findings_prompt_sys = "You are the Findings Agent. Extract all medical findings, reported symptoms, and uncertainties from the conversation transcript. Output JSON: {\"findings\": [\"...\"], \"symptoms\": [\"...\"], \"uncertainties\": [\"...\"]}"
        findings_prompt_user = f"Patient: {patient.first_name} {patient.last_name}\nTranscript:\n{transcript_text}"
        findings_result = await call_gemini(findings_prompt_sys, findings_prompt_user)
        
        # 3. PROTOCOL AGENT
        protocol_prompt_sys = "You are the Protocol Agent. Assess the patient findings against the protocol rules. Identify matched rules. Output JSON: {\"matched_rules\": [\"...\"], \"assessment\": \"...\"}"
        protocol_prompt_user = f"Findings:\n{json.dumps(findings_result, indent=2)}\nProtocol Questions:\n{json.dumps(protocol_questions, indent=2)}"
        protocol_result = await call_gemini(protocol_prompt_sys, protocol_prompt_user)
        
        # 4. SAFETY AGENT
        safety_prompt_sys = "You are the Safety Agent. Identify any medical red flags or dangerous situations reported. DO NOT invent symptoms. Output JSON: {\"red_flags\": [\"...\"], \"requires_human_review\": true/false, \"risk_level\": \"URGENT|ATTENTION|ROUTINE\"}"
        safety_prompt_user = f"Findings:\n{json.dumps(findings_result, indent=2)}\nProtocol matched rules:\n{json.dumps(protocol_result, indent=2)}\nTranscript:\n{transcript_text}"
        safety_result = await call_gemini(safety_prompt_sys, safety_prompt_user)
        
        # 5. DETERMINISTIC CONSENSUS
        red_flags = safety_result.get("red_flags", [])
        requires_review = safety_result.get("requires_human_review", False)
        safety_risk = safety_result.get("risk_level", "ROUTINE").upper()
        
        if red_flags or safety_risk == "URGENT":
            triage_level = "URGENT"
            recommended_action = "IMMEDIATE_CLINICIAN_REVIEW"
            requires_review = True
        elif requires_review or safety_risk == "ATTENTION":
            triage_level = "ATTENTION"
            recommended_action = "CLINICIAN_REVIEW"
        else:
            triage_level = "ROUTINE"
            recommended_action = "NO_ACTION_REQUIRED"
            
        reasoning = f"Protocol Assessment: {protocol_result.get('assessment', 'N/A')} | Safety Risk: {safety_risk}"
        
        # 6. PERSIST TO DB
        triage_record = TriageResult(
            call_id=result.call_id,
            patient_id=result.patient_id,
            campaign_id=result.campaign_id,
            triage_level=triage_level,
            recommended_action=recommended_action,
            findings=findings_result.get("findings", []),
            red_flags=red_flags,
            matched_protocol_rules=protocol_result.get("matched_rules", []),
            reasoning_summary=reasoning,
            agent_assessments=[
                {"agent": "findings", "result": findings_result},
                {"agent": "protocol", "result": protocol_result},
                {"agent": "safety", "result": safety_result}
            ],
            requires_human_review=requires_review,
            protocol_name=protocol.name if protocol else "Default",
            protocol_version="1.0"
        )
        
        db.add(triage_record)
        await db.commit()
        
        logger.info(f"Triage completed for Call {result.call_id} -> {triage_level}")
        return triage_level
