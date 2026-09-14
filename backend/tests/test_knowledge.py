"""
Test 6 — Knowledge isolation: H001 search only returns H001 knowledge.
"""

import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _create_doc(client, hospital_id, token, title="Clinical Guidelines", content="test content"):
    resp = await client.post(
        f"/api/v1/hospitals/{hospital_id}/knowledge",
        json={"title": title, "content": content},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# --------------------------------------------------------------------------- #
# Test 6: Knowledge isolation                                                  #
# --------------------------------------------------------------------------- #


async def test_knowledge_search_returns_only_own_hospital_docs(
    client: AsyncClient,
    hospital_a_token: str,
    hospital_b_token: str,
    hospital_a,
    hospital_b,
) -> None:
    """
    Hospital A's knowledge search must NEVER return Hospital B's documents.
    """
    unique_keyword = f"UNIQUE_KEYWORD_{uuid.uuid4().hex}"

    # Create a document in Hospital B with the unique keyword
    b_doc = await _create_doc(
        client,
        hospital_b.id,
        hospital_b_token,
        title=f"Hospital B Doc {unique_keyword}",
        content=f"This document belongs to Hospital B. {unique_keyword}",
    )

    # Search in Hospital A with the same keyword — must return nothing
    resp = await client.post(
        f"/api/v1/hospitals/{hospital_a.id}/knowledge/search",
        json={"query": unique_keyword},
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert resp.status_code == 200, resp.text
    results = resp.json()

    result_ids = [r["id"] for r in results]
    assert b_doc["id"] not in result_ids, (
        "CRITICAL ISOLATION FAILURE: Hospital A's search returned Hospital B's document!"
    )


async def test_hospital_a_cannot_list_hospital_b_knowledge(
    client: AsyncClient,
    hospital_a_token: str,
    hospital_b,
) -> None:
    """Hospital A admin must receive 403 when listing Hospital B's knowledge."""
    resp = await client.get(
        f"/api/v1/hospitals/{hospital_b.id}/knowledge",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert resp.status_code == 403, resp.text


async def test_knowledge_list_returns_only_own_docs(
    client: AsyncClient,
    hospital_a_token: str,
    hospital_b_token: str,
    hospital_a,
    hospital_b,
) -> None:
    """All documents in the list response must belong to the requesting hospital."""
    # Create doc in Hospital A
    a_doc = await _create_doc(
        client,
        hospital_a.id,
        hospital_a_token,
        title=f"Hospital A exclusive doc {uuid.uuid4().hex[:8]}",
    )

    # Create doc in Hospital B
    b_doc = await _create_doc(
        client,
        hospital_b.id,
        hospital_b_token,
        title=f"Hospital B exclusive doc {uuid.uuid4().hex[:8]}",
    )

    # List Hospital A's docs
    resp = await client.get(
        f"/api/v1/hospitals/{hospital_a.id}/knowledge",
        headers={"Authorization": f"Bearer {hospital_a_token}"},
    )
    assert resp.status_code == 200, resp.text
    docs = resp.json()

    # Every returned doc must belong to Hospital A
    for doc in docs:
        assert doc["hospital_id"] == str(hospital_a.id), (
            f"Document {doc['id']} belongs to {doc['hospital_id']}, not Hospital A!"
        )

    # Hospital B's doc must NOT appear
    result_ids = [d["id"] for d in docs]
    assert b_doc["id"] not in result_ids
