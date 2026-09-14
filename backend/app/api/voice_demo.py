import os
import uuid
import logging
from dotenv import load_dotenv
load_dotenv()
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from livekit.api import AccessToken, VideoGrants
from datetime import datetime, timezone

from app.core.dependencies import get_db
from app.models.outbound_call import OutboundCall
from app.models.campaign import Campaign
from app.models.ehr import Patient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice_demo", tags=["Voice Demo"])

@router.get("/token")
async def get_voice_demo_token(db: AsyncSession = Depends(get_db)):
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL")
    
    if not livekit_api_key or not livekit_api_secret or not livekit_url:
        logger.error("LiveKit credentials missing in environment.")
        raise HTTPException(status_code=500, detail="LiveKit credentials are not configured.")
        
    # Get a patient and campaign to mock a real call
    result_camp = await db.execute(select(Campaign).limit(1))
    campaign = result_camp.scalars().first()
    
    result_pat = await db.execute(select(Patient).limit(1))
    patient = result_pat.scalars().first()
    
    if not campaign or not patient:
        raise HTTPException(status_code=500, detail="No campaign or patient found in DB for demo.")
        
    # Create an OutboundCall
    call = OutboundCall(
        campaign_id=campaign.id,
        patient_id=patient.id,
        outcome="PENDING",
        patient_reached=False,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc) # Will be updated on completion
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)
    
    room_name = str(call.id)
    participant_identity = f"user-{uuid.uuid4().hex[:8]}"
    
    token = AccessToken(livekit_api_key, livekit_api_secret)
    token.with_identity(participant_identity)
    token.with_name("Demo Evaluator")
    token.with_grants(VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True
    ))
    
    return {
        "token": token.to_jwt(),
        "url": livekit_url,
        "room_name": room_name
    }
