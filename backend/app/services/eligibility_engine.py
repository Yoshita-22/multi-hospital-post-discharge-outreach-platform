import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, text, and_, or_, not_
from sqlalchemy.dialects.postgresql import insert

from app.core.tenant_context import TenantContext
from app.models.campaign import Campaign, CampaignValidationStatus
from app.models.campaign_patient import CampaignPatient
from app.models.ehr import Patient, Discharge, Encounter, Condition, Medication, Observation
from app.schemas.campaign_evaluation import EligibilityResult, EligiblePatientDetail
from app.services.audit_service import audit_service


class EligibilityEngine:
    
    async def evaluate_campaign(self, db: AsyncSession, campaign_id: uuid.UUID, tenant: TenantContext) -> EligibilityResult:
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
                detail="Campaign must be successfully validated before eligibility evaluation."
            )
            
        rules = campaign.eligibility_rules
        if not rules:
            return await self._empty_result(db, campaign, tenant.user_id)

        # 4. Construct SQL logic
        # We start by querying all patients for the hospital
        base_query = select(
            Patient.id, 
            Patient.external_patient_id, 
            Discharge.risk_level
        ).outerjoin(
            Discharge, (Discharge.patient_id == Patient.id)
        ).where(Patient.hospital_id == campaign.hospital_id)
        
        # 5. Parse rules and add filters
        expressions, explanations_map = self._parse_rule_group(rules, "AND")
        if expressions:
            base_query = base_query.where(and_(*expressions))
            
        # 6. Execute evaluation
        result = await db.execute(base_query)
        rows = result.all()
        
        # Determine total evaluated count (all patients in hospital)
        count_res = await db.execute(select(func.count(Patient.id)).where(Patient.hospital_id == campaign.hospital_id))
        evaluated_count = count_res.scalar_one()
        
        patients_list = []
        patient_upserts = []
        now = datetime.now(timezone.utc)
        
        for row in rows:
            # Reconstruct the explanation strings per patient based on the rules we have
            # Since this is a boolean match per patient, the logic itself matched.
            # We provide the explanations_map list.
            patients_list.append(EligiblePatientDetail(
                patient_id=row.id,
                external_patient_id=row.external_patient_id,
                risk_level=row.risk_level,
                matched_rules=explanations_map
            ))
            
            patient_upserts.append({
                "campaign_id": campaign.id,
                "patient_id": row.id,
                "eligibility_status": "ELIGIBLE",
                "eligibility_reason": ", ".join(explanations_map),
                "evaluated_at": now
            })
            
        # 7. Upsert campaign_patients
        if patient_upserts:
            stmt = insert(CampaignPatient).values(patient_upserts)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_campaign_patient",
                set_={
                    "eligibility_status": stmt.excluded.eligibility_status,
                    "eligibility_reason": stmt.excluded.eligibility_reason,
                    "evaluated_at": stmt.excluded.evaluated_at
                }
            )
            await db.execute(stmt)
            
        # Optional: update non-eligible patients if they were previously eligible
        # (For idempotency on re-evaluation)
        eligible_ids = [p["patient_id"] for p in patient_upserts]
        if eligible_ids:
            # We don't have to do it if none were evaluated, but good practice
            pass 

        await audit_service.log_event(
            db=db,
            action="CAMPAIGN_ELIGIBILITY_EVALUATED",
            actor_user_id=tenant.user_id,
            hospital_id=campaign.hospital_id,
            resource_type="CAMPAIGN",
            resource_id=campaign.id,
            metadata={"evaluated_count": evaluated_count, "eligible_count": len(patients_list)}
        )
        
        await db.commit()
        
        return EligibilityResult(
            campaign_id=campaign.id,
            evaluated_count=evaluated_count,
            eligible_count=len(patients_list),
            evaluation_timestamp=now.isoformat(),
            patients=patients_list
        )
        
    async def _empty_result(self, db, campaign, user_id) -> EligibilityResult:
        count_res = await db.execute(select(func.count(Patient.id)).where(Patient.hospital_id == campaign.hospital_id))
        evaluated_count = count_res.scalar_one()
        
        await audit_service.log_event(
            db=db,
            action="CAMPAIGN_ELIGIBILITY_EVALUATED",
            actor_user_id=user_id,
            hospital_id=campaign.hospital_id,
            resource_type="CAMPAIGN",
            resource_id=campaign.id,
            metadata={"evaluated_count": evaluated_count, "eligible_count": 0}
        )
        await db.commit()
        return EligibilityResult(
            campaign_id=campaign.id,
            evaluated_count=evaluated_count,
            eligible_count=0,
            evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
            patients=[]
        )

    def _parse_rule_group(self, rules: Dict[str, Any], logic: str) -> Tuple[List[Any], List[str]]:
        exprs = []
        explanations = []
        
        if "all" in rules:
            for r in rules["all"]:
                sub_exprs, sub_expl = self._parse_rule_group(r, "AND")
                exprs.append(and_(*sub_exprs))
                explanations.extend(sub_expl)
        elif "any" in rules:
            any_exprs = []
            for r in rules["any"]:
                sub_exprs, sub_expl = self._parse_rule_group(r, "OR")
                if sub_exprs:
                    any_exprs.append(and_(*sub_exprs))
                explanations.extend(sub_expl)
            if any_exprs:
                exprs.append(or_(*any_exprs))
        else:
            # Base rule
            e, expl = self._build_expression(rules)
            if e is not None:
                exprs.append(e)
                explanations.append(expl)
                
        return exprs, explanations

    def _build_expression(self, rule: Dict[str, Any]) -> Tuple[Any, str]:
        field = rule["field"]
        operator = rule["operator"]
        value = rule["value"]
        
        col = None
        is_subquery = False
        
        if field == "age":
            # Extract year from DOB
            col = datetime.now(timezone.utc).year - func.extract('year', Patient.date_of_birth)
        elif field == "gender":
            col = Patient.gender
        elif field == "preferred_contact_method":
            col = Patient.preferred_contact_method
        elif field == "risk_level":
            col = Discharge.risk_level
        elif field == "follow_up_required":
            col = Discharge.follow_up_required
        elif field == "discharge_status":
            col = Discharge.discharge_status
        elif field == "discharged_within_days":
            # difference in days between now and discharge
            # Discharge.discharge_timestamp >= now - days
            cutoff = datetime.now(timezone.utc) - timedelta(days=value)
            return (Discharge.discharge_timestamp >= cutoff, f"Discharged within {value} days")
        elif field == "days_until_follow_up_deadline":
            cutoff = datetime.now(timezone.utc) + timedelta(days=value)
            return (Discharge.follow_up_deadline <= cutoff, f"Follow-up deadline within {value} days")
        elif field == "encounter_type":
            col = select(Encounter.encounter_type).where(Encounter.patient_id == Patient.id).scalar_subquery()
            is_subquery = True
        elif field == "care_setting":
            col = select(Encounter.care_setting).where(Encounter.patient_id == Patient.id).scalar_subquery()
            is_subquery = True
        elif field == "condition":
            # Exists query
            subq = select(1).where(and_(Condition.patient_id == Patient.id, Condition.code == value))
            return (subq.exists(), f"Condition equals {value}")
        elif field == "condition_count":
            col = select(func.count(Condition.id)).where(Condition.patient_id == Patient.id).scalar_subquery()
        elif field == "medication":
            subq = select(1).where(and_(Medication.patient_id == Patient.id, Medication.name == value))
            return (subq.exists(), f"Medication equals {value}")
        elif field == "medication_count":
            col = select(func.count(Medication.id)).where(Medication.patient_id == Patient.id).scalar_subquery()
        elif field == "observation":
            subq = select(1).where(and_(Observation.patient_id == Patient.id, Observation.code == value))
            return (subq.exists(), f"Observation equals {value}")
        elif field == "observation_value":
            subq = select(1).where(and_(Observation.patient_id == Patient.id, Observation.value == value))
            return (subq.exists(), f"Observation value equals {value}")

        if col is None:
            return None, ""
            
        expr = None
        if operator == "equals":
            expr = col == value
        elif operator == "not_equals":
            expr = col != value
        elif operator == "greater_than":
            expr = col > value
        elif operator == "greater_than_or_equal":
            expr = col >= value
        elif operator == "less_than":
            expr = col < value
        elif operator == "less_than_or_equal":
            expr = col <= value
        elif operator == "in":
            expr = col.in_(value)
        elif operator == "not_in":
            expr = col.notin_(value)
            
        explanation = f"{field.replace('_', ' ').capitalize()} {operator.replace('_', ' ')} {value}"
        return expr, explanation

eligibility_engine = EligibilityEngine()
