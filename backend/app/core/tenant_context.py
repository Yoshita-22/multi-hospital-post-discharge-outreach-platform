from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum


class UserRole(str, Enum):
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    HOSPITAL_ADMIN = "HOSPITAL_ADMIN"
    CAMPAIGN_MANAGER = "CAMPAIGN_MANAGER"
    CLINICAL_REVIEWER = "CLINICAL_REVIEWER"


@dataclass(frozen=True)
class TenantContext:
    """
    Immutable object attached to every authenticated request.

    Answers three questions:
        WHO   → user_id
        WHERE → hospital_id  (None for PLATFORM_ADMIN)
        WHAT  → role
    """

    user_id: uuid.UUID
    hospital_id: uuid.UUID | None
    role: UserRole

    @property
    def is_platform_admin(self) -> bool:
        return self.role == UserRole.PLATFORM_ADMIN

    @property
    def is_hospital_admin(self) -> bool:
        return self.role == UserRole.HOSPITAL_ADMIN

    def can_access_hospital(self, hospital_id: uuid.UUID) -> bool:
        """Check if this tenant context has access to a given hospital."""
        if self.is_platform_admin:
            return True
        return self.hospital_id == hospital_id
