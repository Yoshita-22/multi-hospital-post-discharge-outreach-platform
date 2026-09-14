import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field

from app.models.campaign import CampaignStatus


class CampaignBase(BaseModel):
    hospital_id: uuid.UUID
    name: str = Field(..., max_length=255, min_length=1)
    description: Optional[str] = Field(None, max_length=1000)
    
    eligibility_rules: Optional[Dict[str, Any]] = None
    follow_up_window: Optional[Dict[str, Any]] = None
    calling_hours: Optional[Dict[str, Any]] = None
    priority_config: Optional[Dict[str, Any]] = None
    
    max_retries: int = Field(3, ge=0)
    calling_capacity: int = Field(10, gt=0)


class CampaignCreate(CampaignBase):
    """Schema for creating a new Campaign."""
    pass


class CampaignUpdate(BaseModel):
    """Schema for updating an existing Campaign."""
    name: Optional[str] = Field(None, max_length=255, min_length=1)
    description: Optional[str] = Field(None, max_length=1000)
    
    eligibility_rules: Optional[Dict[str, Any]] = None
    follow_up_window: Optional[Dict[str, Any]] = None
    calling_hours: Optional[Dict[str, Any]] = None
    priority_config: Optional[Dict[str, Any]] = None
    
    max_retries: Optional[int] = Field(None, ge=0)
    calling_capacity: Optional[int] = Field(None, gt=0)
    
    status: Optional[CampaignStatus] = None


class CampaignRead(CampaignBase):
    """Schema for reading a Campaign."""
    id: uuid.UUID
    status: CampaignStatus
    
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
