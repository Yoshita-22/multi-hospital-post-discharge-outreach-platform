"""
Test 5 — Protocol isolation (H001 Admin cannot see H002 protocols)
Test 7 — Protocol versioning (v1 archived, v2 active)
Test 8 — Audit log created on protocol creation
"""

import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------- #
# Helpers                                                                  #
# ---------------------------------------------------------------------- #


async def _create_protocol(client, hospital_id, token, name="Cardiac", version="1.0"):
    resp = await client.post(
        f"/api/v1/hospitals/{hospital_id}/protocols",
        json={
            "name": name,
            "version": version,
            "content": {
                "questions": ["How are you feeling?"],
                "red_flags": ["chest pain"],
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# --------------------------------------------------------------------------- #
# Test 5: Protocol isolation                                                   #
# --------------------------------------------------------------------------- #


async def test_hospital_a_admin_can_list_own_protocols(
    client: AsyncClient,
    hospital_a_token: str,
    hospital_a,
) -> None:
    """H001 Admin → H001 protocols → 200 OK."""
    await _create_protocol(client, hospital_a.id, hospital_a_token, name="Cardiac_A")
    response = await client.get(
        f"/api/v1/hospitals/{hospital_a.id}/protocols",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert response.status_code == 200, response.text


async def test_hospital_a_admin_cannot_list_hospital_b_protocols(
    client: AsyncClient,
    hospital_a_token: str,
    hospital_b,
) -> None:
    """H001 Admin → H002 protocols → 403."""
    response = await client.get(
        f"/api/v1/hospitals/{hospital_b.id}/protocols",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert response.status_code == 403, response.text


# --------------------------------------------------------------------------- #
# Test 7: Protocol versioning                                                  #
# --------------------------------------------------------------------------- #


async def test_protocol_versioning(
    client: AsyncClient,
    hospital_a_token: str,
    hospital_a,
) -> None:
    """
    v1 created and activated → v2 created and activated →
    v1 must be ARCHIVED, v2 must be ACTIVE.
    """
    proto_name = f"Versioning_Test_{uuid.uuid4().hex[:6]}"

    # Create v1
    v1 = await _create_protocol(client, hospital_a.id, hospital_a_token, name=proto_name, version="1.0")
    assert v1["status"] == "DRAFT"

    # Activate v1
    resp = await client.post(
        f"/api/v1/hospitals/{hospital_a.id}/protocols/{v1['id']}/activate",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ACTIVE"

    # Create v2
    v2 = await _create_protocol(client, hospital_a.id, hospital_a_token, name=proto_name, version="2.0")
    assert v2["status"] == "DRAFT"

    # Activate v2 → should archive v1 automatically
    resp = await client.post(
        f"/api/v1/hospitals/{hospital_a.id}/protocols/{v2['id']}/activate",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ACTIVE"

    # Verify v1 is now ARCHIVED
    resp_v1 = await client.get(
        f"/api/v1/hospitals/{hospital_a.id}/protocols/{v1['id']}",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert resp_v1.status_code == 200
    assert resp_v1.json()["status"] == "ARCHIVED", (
        f"Expected v1 to be ARCHIVED, got {resp_v1.json()['status']}"
    )


# --------------------------------------------------------------------------- #
# Test 8: Audit log created on protocol creation                              #
# --------------------------------------------------------------------------- #


async def test_audit_log_created_for_protocol(
    client: AsyncClient,
    hospital_a_token: str,
    platform_admin_token: str,
    hospital_a,
) -> None:
    """Creating a protocol must produce a PROTOCOL_CREATED audit log entry."""
    proto = await _create_protocol(
        client,
        hospital_a.id,
        hospital_a_token,
        name=f"Audit_Test_{uuid.uuid4().hex[:6]}",
    )
    proto_id = proto["id"]

    # Fetch audit logs
    resp = await client.get(
        f"/api/v1/hospitals/{hospital_a.id}/audit-logs",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert resp.status_code == 200, resp.text

    logs = resp.json()
    matching = [
        log for log in logs
        if log["action"] == "PROTOCOL_CREATED" and log["resource_id"] == proto_id
    ]
    assert matching, (
        f"No PROTOCOL_CREATED audit log found for protocol {proto_id}. "
        f"Logs: {[l['action'] for l in logs[:5]]}"
    )

    log = matching[0]
    assert log["hospital_id"] == str(hospital_a.id)
    assert log["resource_type"] == "PROTOCOL"
