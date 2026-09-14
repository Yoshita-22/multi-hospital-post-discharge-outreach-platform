"""
Direct-ID manipulation attack tests (Step 24).

These are the most critical security tests in Phase 1.

Scenario:
    Hospital A = hospital_a
    Hospital B = hospital_b
    Protocol A = belongs to hospital_a
    Protocol B = belongs to hospital_b

    Hospital A Admin tries GET /protocols/<protocol_b_id>
    → Must receive 403, even though they guessed the correct UUID.

The backend does:
    1. Fetch protocol by ID
    2. Compare protocol.hospital_id with tenant.hospital_id
    3. DENY if mismatch
"""

import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------- #
# Helpers (inline to keep tests self-contained)                           #
# ---------------------------------------------------------------------- #


async def _create_protocol_for(client, hospital_id, token, name_prefix="Attack_Test"):
    name = f"{name_prefix}_{uuid.uuid4().hex[:6]}"
    resp = await client.post(
        f"/api/v1/hospitals/{hospital_id}/protocols",
        json={
            "name": name,
            "version": "1.0",
            "content": {"questions": ["test?"], "red_flags": ["pain"]},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# --------------------------------------------------------------------------- #
# Direct-ID attack: Protocol                                                   #
# --------------------------------------------------------------------------- #


async def test_hospital_a_cannot_access_hospital_b_protocol_by_id(
    client: AsyncClient,
    hospital_a_token: str,
    hospital_b_token: str,
    hospital_a,
    hospital_b,
) -> None:
    """
    Hospital A admin tries to access Hospital B's protocol by raw UUID.
    Must receive 403 — not the protocol data.
    """
    # Create a protocol in Hospital B
    b_protocol = await _create_protocol_for(client, hospital_b.id, hospital_b_token)

    # Hospital A admin tries to access it via Hospital A's URL path
    response = await client.get(
        f"/api/v1/hospitals/{hospital_a.id}/protocols/{b_protocol['id']}",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert response.status_code == 403, (
        f"SECURITY FAILURE: Hospital A accessed Hospital B's protocol! "
        f"Status: {response.status_code}, Body: {response.text}"
    )


async def test_hospital_b_cannot_access_hospital_a_protocol_by_id(
    client: AsyncClient,
    hospital_a_token: str,
    hospital_b_token: str,
    hospital_a,
    hospital_b,
) -> None:
    """Mirror test — Hospital B cannot access Hospital A's protocol."""
    a_protocol = await _create_protocol_for(client, hospital_a.id, hospital_a_token)

    response = await client.get(
        f"/api/v1/hospitals/{hospital_b.id}/protocols/{a_protocol['id']}",
        headers={"Authorization": f"Bearer {hospital_b_token}"},
    )
    assert response.status_code == 403, (
        f"SECURITY FAILURE: Hospital B accessed Hospital A's protocol!"
    )


# --------------------------------------------------------------------------- #
# Direct-ID attack: Knowledge Document                                         #
# --------------------------------------------------------------------------- #


async def test_hospital_a_cannot_access_hospital_b_knowledge_doc_by_id(
    client: AsyncClient,
    hospital_a_token: str,
    hospital_b_token: str,
    hospital_a,
    hospital_b,
) -> None:
    """Hospital A cannot access Hospital B's knowledge document by raw UUID."""
    # Create document in Hospital B
    b_doc_resp = await client.post(
        f"/api/v1/hospitals/{hospital_b.id}/knowledge",
        json={"title": "B Secret Doc", "content": "Confidential Hospital B data"},
        headers={"Authorization": f"Bearer {hospital_b_token}"},
    )
    assert b_doc_resp.status_code == 201
    b_doc = b_doc_resp.json()

    # Hospital A admin tries to access it
    response = await client.get(
        f"/api/v1/hospitals/{hospital_a.id}/knowledge/{b_doc['id']}",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert response.status_code == 403, (
        f"SECURITY FAILURE: Hospital A accessed Hospital B's knowledge document!"
    )


# --------------------------------------------------------------------------- #
# Cross-hospital configuration update                                         #
# --------------------------------------------------------------------------- #


async def test_hospital_a_admin_cannot_update_hospital_b_configuration(
    client: AsyncClient,
    hospital_a_token: str,
    hospital_b,
) -> None:
    """Hospital A admin cannot update Hospital B's configuration."""
    response = await client.put(
        f"/api/v1/hospitals/{hospital_b.id}/configuration",
        json={"max_calling_capacity": 999},
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert response.status_code == 403, (
        f"SECURITY FAILURE: Hospital A updated Hospital B's configuration!"
    )


# --------------------------------------------------------------------------- #
# Cross-hospital user creation                                                 #
# --------------------------------------------------------------------------- #


async def test_hospital_a_admin_cannot_create_user_in_hospital_b(
    client: AsyncClient,
    hospital_a_token: str,
    hospital_b,
) -> None:
    """Hospital A admin cannot create a user in Hospital B."""
    response = await client.post(
        f"/api/v1/hospitals/{hospital_b.id}/users",
        json={
            "name": "Malicious User",
            "email": f"malicious_{uuid.uuid4().hex[:8]}@test.com",
            "password": "Test@123",
            "role": "HOSPITAL_ADMIN",
        },
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert response.status_code == 403, (
        f"SECURITY FAILURE: Hospital A created a user in Hospital B!"
    )
