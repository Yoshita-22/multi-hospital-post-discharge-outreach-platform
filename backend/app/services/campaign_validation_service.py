import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.campaign import Campaign, CampaignValidationStatus
from app.schemas.campaign_evaluation import ValidationResult, ValidationErrorDetail
from app.services.audit_service import audit_service


class CampaignValidationService:
    SUPPORTED_FIELDS = {
        "age": {"type": "integer"},
        "gender": {"type": "string", "enum": ["male", "female", "other"]},
        "preferred_contact_method": {"type": "string", "enum": ["phone", "sms", "email"]},
        "risk_level": {"type": "string", "enum": ["Low", "Medium", "High"]},
        "follow_up_required": {"type": "boolean"},
        "discharge_status": {"type": "string"},
        "discharged_within_days": {"type": "integer"},
        "days_until_follow_up_deadline": {"type": "integer"},
        "encounter_type": {"type": "string"},
        "care_setting": {"type": "string"},
        "condition": {"type": "string"},
        "condition_count": {"type": "integer"},
        "medication": {"type": "string"},
        "medication_count": {"type": "integer"},
        "observation": {"type": "string"},
        "observation_value": {"type": "string"}
    }

    SUPPORTED_OPERATORS = {
        "string": {"equals", "not_equals", "in", "not_in"},
        "integer": {"equals", "greater_than", "greater_than_or_equal", "less_than", "less_than_or_equal"},
        "boolean": {"equals", "not_equals"}
    }

    async def validate_campaign(self, db: AsyncSession, campaign: Campaign, user_id: Any) -> ValidationResult:
        errors = []
        
        # 1. Basic validation
        if not campaign.name or len(campaign.name.strip()) == 0:
            errors.append(ValidationErrorDetail(field="name", message="Campaign name must not be empty."))
        
        if campaign.max_retries < 0:
            errors.append(ValidationErrorDetail(field="max_retries", message="max_retries must be >= 0."))
            
        if campaign.calling_capacity <= 0:
            errors.append(ValidationErrorDetail(field="calling_capacity", message="calling_capacity must be > 0."))
            
        if campaign.start_at and campaign.end_at and campaign.end_at <= campaign.start_at:
            errors.append(ValidationErrorDetail(field="end_at", message="end_at must be after start_at."))

        
            
        # 3. Calling hours validation
        if campaign.calling_hours:
            self._validate_calling_hours(campaign.calling_hours, errors)
            
        # 4. DSL Rules validation
        if campaign.eligibility_rules:
            self._validate_dsl(campaign.eligibility_rules, errors, path="eligibility_rules")
            
        valid = len(errors) == 0
        campaign.validation_status = CampaignValidationStatus.VALID if valid else CampaignValidationStatus.INVALID
        
        await audit_service.log_event(
            db=db,
            action="CAMPAIGN_VALIDATED" if valid else "CAMPAIGN_VALIDATION_FAILED",
            actor_user_id=user_id,
            hospital_id=campaign.hospital_id,
            resource_type="CAMPAIGN",
            resource_id=campaign.id,
            metadata={"errors": [e.dict() for e in errors]}
        )
        
        await db.commit()
        await db.refresh(campaign)
        
        return ValidationResult(
            campaign_id=campaign.id,
            valid=valid,
            errors=errors
        )

    

    def _validate_calling_hours(self, hours: Dict[str, Any], errors: List[ValidationErrorDetail]):
        start = hours.get("start")
        end = hours.get("end")
        time_pattern = re.compile(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
        if not start or not time_pattern.match(str(start)):
            errors.append(ValidationErrorDetail(field="calling_hours.start", message="Invalid time format. Use HH:MM."))
        if not end or not time_pattern.match(str(end)):
            errors.append(ValidationErrorDetail(field="calling_hours.end", message="Invalid time format. Use HH:MM."))
        if start and end and time_pattern.match(str(start)) and time_pattern.match(str(end)):
            if end <= start:
                errors.append(ValidationErrorDetail(field="calling_hours.end", message="end time must be after start time."))

    def _validate_dsl(self, rules: Dict[str, Any], errors: List[ValidationErrorDetail], path: str):
        if not isinstance(rules, dict):
            errors.append(ValidationErrorDetail(field=path, message="Rules must be an object."))
            return
            
        if "all" in rules:
            if not isinstance(rules["all"], list):
                errors.append(ValidationErrorDetail(field=f"{path}.all", message="Expected a list of rules."))
            else:
                for i, r in enumerate(rules["all"]):
                    self._validate_dsl(r, errors, f"{path}.all[{i}]")
            return
            
        if "any" in rules:
            if not isinstance(rules["any"], list):
                errors.append(ValidationErrorDetail(field=f"{path}.any", message="Expected a list of rules."))
            else:
                for i, r in enumerate(rules["any"]):
                    self._validate_dsl(r, errors, f"{path}.any[{i}]")
            return
            
        # Base rule
        field = rules.get("field")
        operator = rules.get("operator")
        value = rules.get("value")
        
        if not field or not operator or "value" not in rules:
            errors.append(ValidationErrorDetail(field=path, message="Rule must contain field, operator, and value."))
            return
            
        if field not in self.SUPPORTED_FIELDS:
            errors.append(ValidationErrorDetail(field=f"{path}.field", message=f"Unsupported field: {field}"))
            return
            
        field_config = self.SUPPORTED_FIELDS[field]
        expected_type = field_config["type"]
        
        if operator not in self.SUPPORTED_OPERATORS[expected_type]:
            errors.append(ValidationErrorDetail(field=f"{path}.operator", message=f"Unsupported operator '{operator}' for type {expected_type}."))
            return
            
        # Value validation
        if expected_type == "integer" and not isinstance(value, int) and not isinstance(value, float):
            errors.append(ValidationErrorDetail(field=f"{path}.value", message="Value must be a number."))
        elif expected_type == "boolean" and not isinstance(value, bool):
            errors.append(ValidationErrorDetail(field=f"{path}.value", message="Value must be a boolean."))
        elif expected_type == "string":
            if operator in {"in", "not_in"} and not isinstance(value, list):
                errors.append(ValidationErrorDetail(field=f"{path}.value", message="Value must be a list for 'in' operators."))
            elif operator not in {"in", "not_in"} and not isinstance(value, str):
                errors.append(ValidationErrorDetail(field=f"{path}.value", message="Value must be a string."))

campaign_validation_service = CampaignValidationService()
