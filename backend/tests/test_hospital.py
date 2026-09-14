"""
Test 1 — Platform Admin creates hospital → 201
Test 2 — Hospital Admin tries to create hospital → 403
Test 3 — Hospital Admin can access own hospital → 200
Test 4 — Hospital Admin cannot access another hospital → 403
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------- #
# Test 1: Platform Admin creates hospital → 201                              #
# --------------------------------------------------------------------------- #


async def test_platform_admin_can_create_hospital(
    client: AsyncClient,
    platform_admin_token: str,
) -> None:
    """PLATFORM_ADMIN should be able to create a hospital and get 201."""
    response = await client.post(
        "/api/v1/hospitals",
        json={
            "name": "Test Apollo Hospital",
            "contact_email": "apollo@test.com",
            "contact_phone": "+91-9876543210",
            "timezone": "Asia/Kolkata",
        },
        headers={"Authorization": f"Bearer {platform_admin_token}"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "Test Apollo Hospital"
    assert data["status"] == "ONBOARDING"
    assert "id" in data


# --------------------------------------------------------------------------- #
# Test 2: Hospital Admin cannot create hospital → 403                        #
# --------------------------------------------------------------------------- #


async def test_hospital_admin_cannot_create_hospital(
    client: AsyncClient,
    hospital_a_token: str,
) -> None:
    """HOSPITAL_ADMIN must receive 403 when attempting to create a hospital."""
    response = await client.post(
        "/api/v1/hospitals",
        json={
            "name": "Unauthorized Hospital",
            "contact_email": "unauthorized@test.com",
            "timezone": "UTC",
        },
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert response.status_code == 403, response.text


# --------------------------------------------------------------------------- #
# Test 3: Hospital Admin can access own hospital → 200                       #
# --------------------------------------------------------------------------- #


async def test_hospital_admin_can_access_own_hospital(
    client: AsyncClient,
    hospital_a_token: str,
    hospital_a,
) -> None:
    """HOSPITAL_ADMIN must be able to GET their own hospital details."""
    response = await client.get(
        f"/api/v1/hospitals/{hospital_a.id}",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(hospital_a.id)


# --------------------------------------------------------------------------- #
# Test 4: Hospital Admin cannot access another hospital → 403               #
# --------------------------------------------------------------------------- #


async def test_hospital_admin_cannot_access_other_hospital(
    client: AsyncClient,
    hospital_a_token: str,
    hospital_b,
) -> None:
    """Hospital A admin must receive 403 when accessing Hospital B."""
    response = await client.get(
        f"/api/v1/hospitals/{hospital_b.id}",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert response.status_code == 403, response.text


# --------------------------------------------------------------------------- #
# Additional: Unauthenticated request → 401                                  #
# --------------------------------------------------------------------------- #


async def test_unauthenticated_request_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/hospitals")
    assert response.status_code == 401


# --------------------------------------------------------------------------- #
# Additional: Platform Admin can access any hospital                         #
# --------------------------------------------------------------------------- #


async def test_platform_admin_can_access_any_hospital(
    client: AsyncClient,
    platform_admin_token: str,
    hospital_a,
    hospital_b,
) -> None:
    for hospital in (hospital_a, hospital_b):
        response = await client.get(
            f"/api/v1/hospitals/{hospital.id}",
            headers={"Authorization": f"Bearer {platform_admin_token}"},
        )
        assert response.status_code == 200, response.text
