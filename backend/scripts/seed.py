"""
Seed script — creates the initial PLATFORM_ADMIN user.

Usage:
    cd backend
    python scripts/seed.py

The script is idempotent: running it twice will not create duplicate users.
"""

import asyncio
import os
import sys

# Ensure the backend directory is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.core.security import hash_password
from app.db.database import AsyncSessionLocal
from app.models import User, UserRole, UserStatus  # ensures all models registered

PLATFORM_ADMIN_EMAIL = "admin@platform.com"
PLATFORM_ADMIN_PASSWORD = "PlatformAdmin@2026"
PLATFORM_ADMIN_NAME = "Platform Administrator"


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # Check if already exists
        result = await db.execute(select(User).where(User.email == PLATFORM_ADMIN_EMAIL))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"[seed] PLATFORM_ADMIN already exists: {PLATFORM_ADMIN_EMAIL}")
            return

        import uuid

        admin = User(
            id=uuid.uuid4(),
            hospital_id=None,  # Platform admin has no hospital
            name=PLATFORM_ADMIN_NAME,
            email=PLATFORM_ADMIN_EMAIL,
            password_hash=hash_password(PLATFORM_ADMIN_PASSWORD),
            role=UserRole.PLATFORM_ADMIN,
            status=UserStatus.ACTIVE,
        )
        db.add(admin)
        await db.commit()
        print(f"[seed] Created PLATFORM_ADMIN: {PLATFORM_ADMIN_EMAIL}")
        print(f"[seed] Temporary password: {PLATFORM_ADMIN_PASSWORD}")
        print("[seed] IMPORTANT: Change this password immediately in production!")


if __name__ == "__main__":
    asyncio.run(seed())
