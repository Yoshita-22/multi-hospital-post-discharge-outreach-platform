from __future__ import annotations

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.configuration import HospitalConfiguration
from app.models.hospital import Hospital, HospitalStatus
from app.models.protocol import Protocol, ProtocolStatus
from app.models.user import User, UserRole, UserStatus
from app.schemas.hospital import ReadinessCheck, ReadinessReport


class ReadinessService:
    """
    Evaluates whether a hospital has completed all onboarding requirements
    and is ready to transition from ONBOARDING → READY.

    Checks:
        1. Name exists
        2. Contact email exists
        3. Timezone configured
        4. Configuration record exists
        5. Calling hours configured
        6. Max calling capacity > 0
        7. Retry policy configured
        8. At least one ACTIVE HOSPITAL_ADMIN exists
        9. At least one ACTIVE protocol exists
    """

    async def check_readiness(
        self,
        db: AsyncSession,
        hospital_id: uuid.UUID,
    ) -> ReadinessReport:
        # Load hospital
        hospital_result = await db.execute(
            select(Hospital).where(Hospital.id == hospital_id)
        )
        hospital = hospital_result.scalar_one_or_none()
        if not hospital:
            return ReadinessReport(
                hospital_id=hospital_id,
                ready=False,
                checks=[ReadinessCheck(name="hospital_exists", passed=False, message="Hospital not found.")],
            )

        # Load configuration
        config_result = await db.execute(
            select(HospitalConfiguration).where(
                HospitalConfiguration.hospital_id == hospital_id
            )
        )
        config = config_result.scalar_one_or_none()

        # Count hospital admins
        admin_count_result = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.hospital_id == hospital_id,
                    User.role == UserRole.HOSPITAL_ADMIN,
                    User.status == UserStatus.ACTIVE,
                )
            )
        )
        admin_count = admin_count_result.scalar_one()

        # Count active protocols
        protocol_count_result = await db.execute(
            select(func.count(Protocol.id)).where(
                and_(
                    Protocol.hospital_id == hospital_id,
                    Protocol.status == ProtocolStatus.ACTIVE,
                )
            )
        )
        protocol_count = protocol_count_result.scalar_one()

        checks: list[ReadinessCheck] = []

        def chk(name: str, passed: bool, msg_pass: str, msg_fail: str) -> None:
            checks.append(
                ReadinessCheck(name=name, passed=passed, message=msg_pass if passed else msg_fail)
            )

        chk("name", bool(hospital.name and hospital.name.strip()), "Name is set.", "Hospital name is missing.")
        chk("contact_email", bool(hospital.contact_email), "Contact email is set.", "Contact email is missing.")
        chk("timezone", bool(hospital.timezone), "Timezone is configured.", "Timezone is not configured.")
        chk("configuration_exists", config is not None, "Configuration record exists.", "No configuration record found.")
        chk(
            "calling_hours",
            config is not None and bool(config.calling_start_time) and bool(config.calling_end_time),
            "Calling hours are configured.",
            "Calling hours are not configured.",
        )
        chk(
            "max_calling_capacity",
            config is not None and config.max_calling_capacity > 0,
            f"Max calling capacity is {config.max_calling_capacity if config else 0}.",
            "Max calling capacity must be > 0.",
        )
        chk(
            "retry_policy",
            config is not None and config.max_retries > 0,
            f"Retry policy is {config.max_retries if config else 0} retries.",
            "Max retries must be > 0.",
        )
        chk(
            "hospital_admin",
            admin_count > 0,
            f"{admin_count} active Hospital Admin(s) found.",
            "At least one active HOSPITAL_ADMIN is required.",
        )
        chk(
            "active_protocol",
            protocol_count > 0,
            f"{protocol_count} active protocol(s) found.",
            "At least one ACTIVE protocol is required.",
        )

        all_passed = all(c.passed for c in checks)
        return ReadinessReport(hospital_id=hospital_id, ready=all_passed, checks=checks)

    async def transition_to_ready(
        self,
        db: AsyncSession,
        hospital_id: uuid.UUID,
    ) -> tuple[bool, ReadinessReport]:
        """
        Run readiness check; if all pass, transition status to READY.
        Returns (transitioned: bool, report: ReadinessReport).
        """
        report = await self.check_readiness(db, hospital_id)
        if not report.ready:
            return False, report

        hospital_result = await db.execute(
            select(Hospital).where(Hospital.id == hospital_id)
        )
        hospital = hospital_result.scalar_one()

        if hospital.status == HospitalStatus.ONBOARDING:
            hospital.status = HospitalStatus.READY
            await db.flush()
            await db.commit()

        return True, report


readiness_service = ReadinessService()
