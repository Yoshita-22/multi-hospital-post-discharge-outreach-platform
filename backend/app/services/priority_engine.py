import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func

from app.core.tenant_context import TenantContext
from app.models.campaign import Campaign, CampaignValidationStatus
from app.models.campaign_patient import CampaignPatient
from app.models.ehr import Patient, Discharge
from app.schemas.campaign_prioritization import PrioritizationResult
from app.services.audit_service import audit_service


class PriorityEngine:
    DEFAULT_WEIGHTS = {
        "clinical_risk": 0.40,
        "follow_up_urgency": 0.25,
        "time_since_discharge": 0.15,
        "callback_request": 0.10,
        "outreach_history": 0.05,
        "campaign_priority": 0.05
    }
    
    DEFAULT_THRESHOLDS = {
        "high": 0.75,
        "medium": 0.50
    }

    async def prioritize_campaign(self, db: AsyncSession, campaign_id: uuid.UUID, tenant: TenantContext) -> PrioritizationResult:
        # 1. Load campaign
        res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = res.scalar_one_or_none()
        
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
            
        # 2. Tenant isolation checks
        if not tenant.can_access_hospital(campaign.hospital_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to the specified hospital.")
            
        # 3. Campaign validation prerequisite
        if campaign.validation_status != CampaignValidationStatus.VALID:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Campaign must be successfully validated before prioritization."
            )
            
        # 4. Config validation
        weights = self.DEFAULT_WEIGHTS.copy()
        thresholds = self.DEFAULT_THRESHOLDS.copy()
        campaign_priority_base = 0.5 # default moderate baseline

        if campaign.priority_config:
            if "weights" in campaign.priority_config:
                w = campaign.priority_config["weights"]
                if not isinstance(w, dict):
                    raise HTTPException(status_code=400, detail="Invalid priority weights configuration")
                if sum(w.values()) < 0.99 or sum(w.values()) > 1.01:
                    raise HTTPException(status_code=400, detail="Priority weights must sum to 1.0")
                for k, v in w.items():
                    if v < 0:
                        raise HTTPException(status_code=400, detail="Priority weights cannot be negative")
                weights.update(w)
                
            if "thresholds" in campaign.priority_config:
                thresholds.update(campaign.priority_config["thresholds"])
                
            if "campaign_priority" in campaign.priority_config:
                campaign_priority_base = float(campaign.priority_config["campaign_priority"])
            
        # 5. Fetch ELIGIBLE patients
        # We need Discharge information to calculate clinical risk, urgency, and discharge time.
        stmt = select(CampaignPatient, Discharge).join(
            Patient, Patient.id == CampaignPatient.patient_id
        ).outerjoin(
            Discharge, Discharge.patient_id == Patient.id
        ).where(
            CampaignPatient.campaign_id == campaign.id,
            CampaignPatient.eligibility_status == "ELIGIBLE",
            Patient.hospital_id == campaign.hospital_id
        )
        
        result = await db.execute(stmt)
        rows = result.all()
        
        if not rows:
            return await self._empty_result(db, campaign, tenant.user_id)
            
        # 6. Calculate factors
        now = datetime.now(timezone.utc)
        scored_patients = []
        
        for cp, discharge in rows:
            clinical_risk_score = 0.0
            follow_up_urgency_score = 0.0
            time_since_discharge_score = 0.0
            
            if discharge:
                # Clinical Risk
                risk = discharge.risk_level
                if risk:
                    r = risk.lower()
                    if r == "high": clinical_risk_score = 1.0
                    elif r == "medium": clinical_risk_score = 0.6
                    elif r == "low": clinical_risk_score = 0.2
                    
                # Follow up urgency
                if discharge.follow_up_deadline:
                    delta = (discharge.follow_up_deadline - now).total_seconds() / 86400.0
                    if delta <= 0: follow_up_urgency_score = 1.0
                    elif delta <= 1: follow_up_urgency_score = 0.9
                    elif delta <= 3: follow_up_urgency_score = 0.75
                    elif delta <= 7: follow_up_urgency_score = 0.5
                    else: follow_up_urgency_score = 0.25
                    
                # Time since discharge
                if discharge.discharge_timestamp:
                    days_since = (now - discharge.discharge_timestamp).total_seconds() / 86400.0
                    if days_since < 0: days_since = 0
                    if days_since > 30: days_since = 30
                    # closer to 0 or closer to end of window? 
                    # Assuming older is less urgent but maybe it's just normalized to 0..30 days -> 1..0
                    time_since_discharge_score = 1.0 - (days_since / 30.0)
                    
            callback_request = 0.0
            outreach_history = 0.0
            
            priority_score = (
                clinical_risk_score * weights.get("clinical_risk", 0) +
                follow_up_urgency_score * weights.get("follow_up_urgency", 0) +
                time_since_discharge_score * weights.get("time_since_discharge", 0) +
                callback_request * weights.get("callback_request", 0) +
                outreach_history * weights.get("outreach_history", 0) +
                campaign_priority_base * weights.get("campaign_priority", 0)
            )
            
            level = "LOW"
            if priority_score >= thresholds.get("high", 0.75):
                level = "HIGH"
            elif priority_score >= thresholds.get("medium", 0.50):
                level = "MEDIUM"
                
            factors = {
                "clinical_risk": clinical_risk_score,
                "follow_up_urgency": follow_up_urgency_score,
                "time_since_discharge": time_since_discharge_score,
                "callback_request": callback_request,
                "outreach_history": outreach_history,
                "campaign_priority": campaign_priority_base
            }
            
            scored_patients.append({
                "cp": cp,
                "score": priority_score,
                "level": level,
                "factors": factors,
                "urgency": follow_up_urgency_score,
                "risk": clinical_risk_score,
                "discharge_time": discharge.discharge_timestamp if discharge else datetime.min
            })
            
        # 7. Sort
        # Sort descending by: priority_score, follow-up urgency, clinical risk, discharge timestamp
        scored_patients.sort(
            key=lambda x: (
                x["score"],
                x["urgency"],
                x["risk"],
                x["discharge_time"]
            ),
            reverse=True
        )
        
        # 8. Persist results
        high_count = 0
        med_count = 0
        low_count = 0
        
        for rank, p in enumerate(scored_patients, start=1):
            cp = p["cp"]
            cp.priority_score = p["score"]
            cp.priority_level = p["level"]
            cp.priority_rank = rank
            cp.prioritized_at = now
            cp.priority_factors = p["factors"]
            
            if cp.priority_level == "HIGH":
                high_count += 1
            elif cp.priority_level == "MEDIUM":
                med_count += 1
            else:
                low_count += 1
                
            # By modifying the instances loaded within this session, SQLAlchemy tracks changes 
            # and issues updates efficiently on commit. 
            # (Assuming the number of eligible patients isn't in the millions. For 500 patients, this is very fast.)
            
        # 9. Audit log
        await audit_service.log_event(
            db=db,
            action="CAMPAIGN_PATIENTS_PRIORITIZED",
            actor_user_id=tenant.user_id,
            hospital_id=campaign.hospital_id,
            resource_type="CAMPAIGN",
            resource_id=campaign.id,
            metadata={
                "prioritized_count": len(scored_patients),
                "high_priority_count": high_count,
                "medium_priority_count": med_count,
                "low_priority_count": low_count
            }
        )
        
        await db.commit()
        
        return PrioritizationResult(
            campaign_id=campaign.id,
            prioritized_count=len(scored_patients),
            high_priority_count=high_count,
            medium_priority_count=med_count,
            low_priority_count=low_count,
            prioritized_at=now.isoformat()
        )

    async def _empty_result(self, db: AsyncSession, campaign: Campaign, user_id: uuid.UUID) -> PrioritizationResult:
        now = datetime.now(timezone.utc)
        await audit_service.log_event(
            db=db,
            action="CAMPAIGN_PATIENTS_PRIORITIZED",
            actor_user_id=user_id,
            hospital_id=campaign.hospital_id,
            resource_type="CAMPAIGN",
            resource_id=campaign.id,
            metadata={
                "prioritized_count": 0,
                "high_priority_count": 0,
                "medium_priority_count": 0,
                "low_priority_count": 0
            }
        )
        await db.commit()
        return PrioritizationResult(
            campaign_id=campaign.id,
            prioritized_count=0,
            high_priority_count=0,
            medium_priority_count=0,
            low_priority_count=0,
            prioritized_at=now.isoformat()
        )

priority_engine = PriorityEngine()
