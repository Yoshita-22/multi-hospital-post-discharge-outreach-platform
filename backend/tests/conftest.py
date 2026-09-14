"""
Pytest fixtures for all Phase 1 tests.

Strategy:
    - Use the real Supabase DB, isolated by unique emails/names per test run
    - Function-scoped fixtures to avoid asyncio event loop cross-contamination
    - Helper functions (not fixtures) for creating test data
"""

import uuid
from typing import AsyncGenerator

import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole, UserStatus
from app.models.hospital import Hospital, HospitalStatus
from app.models.configuration import HospitalConfiguration


# ---------------------------------------------------------------------- #
# HTTP client — function scoped                                           #
# ---------------------------------------------------------------------- #


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------- #
# Database session — function scoped                                      #
# ---------------------------------------------------------------------- #


@pytest_asyncio.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------- #
# Helper functions (not fixtures — called directly inside tests/fixtures) #
# ---------------------------------------------------------------------- #


async def _create_hospital_in_db(db, name: str, timezone: str = "Asia/Kolkata") -> Hospital:
    slug = name.lower().replace(" ", "").replace("_", "")
    hospital = Hospital(
        id=uuid.uuid4(),
        name=name,
        contact_email=f"contact@{slug}.com",
        contact_phone="+91-9999999999",
        timezone=timezone,
        status=HospitalStatus.ONBOARDING,
    )
    db.add(hospital)
    await db.flush()

    config = HospitalConfiguration(
        id=uuid.uuid4(),
        hospital_id=hospital.id,
        calling_start_time="09:00",
        calling_end_time="18:00",
        max_calling_capacity=10,
        max_retries=3,
    )
    db.add(config)
    await db.commit()
    await db.refresh(hospital)
    return hospital


async def _create_user_in_db(
    db,
    email: str,
    role: UserRole,
    hospital_id: uuid.UUID | None = None,
    password: str = "TestPass@123",
) -> User:
    user = User(
        id=uuid.uuid4(),
        hospital_id=hospital_id,
        name=f"Test {role.value}",
        email=email,
        password_hash=hash_password(password),
        role=role,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _get_token(client: AsyncClient, email: str, password: str = "TestPass@123") -> str:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200, f"Login failed for {email!r}: {response.text}"
    return response.json()["access_token"]


# ---------------------------------------------------------------------- #
# Convenience fixtures — use these in test modules                        #
# Each creates fresh data so tests are independent                        #
# ---------------------------------------------------------------------- #


@pytest_asyncio.fixture
async def platform_admin(db) -> User:
    email = f"platform_admin_{uuid.uuid4().hex[:8]}@test.com"
    return await _create_user_in_db(db, email, UserRole.PLATFORM_ADMIN, hospital_id=None)


@pytest_asyncio.fixture
async def platform_admin_token(client, platform_admin) -> str:
    return await _get_token(client, platform_admin.email)


@pytest_asyncio.fixture
async def hospital_a(db) -> Hospital:
    return await _create_hospital_in_db(db, f"Hospital_A_{uuid.uuid4().hex[:6]}")


@pytest_asyncio.fixture
async def hospital_b(db) -> Hospital:
    return await _create_hospital_in_db(db, f"Hospital_B_{uuid.uuid4().hex[:6]}")


@pytest_asyncio.fixture
async def hospital_a_admin(db, hospital_a) -> User:
    email = f"admin_a_{uuid.uuid4().hex[:8]}@test.com"
    return await _create_user_in_db(db, email, UserRole.HOSPITAL_ADMIN, hospital_a.id)


@pytest_asyncio.fixture
async def hospital_b_admin(db, hospital_b) -> User:
    email = f"admin_b_{uuid.uuid4().hex[:8]}@test.com"
    return await _create_user_in_db(db, email, UserRole.HOSPITAL_ADMIN, hospital_b.id)


@pytest_asyncio.fixture
async def hospital_a_token(client, hospital_a_admin) -> str:
    return await _get_token(client, hospital_a_admin.email)


@pytest_asyncio.fixture
async def hospital_b_token(client, hospital_b_admin) -> str:
    return await _get_token(client, hospital_b_admin.email)
