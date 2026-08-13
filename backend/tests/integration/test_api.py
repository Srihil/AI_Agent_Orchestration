"""
Integration tests for the FastAPI endpoints.
Requires a running PostgreSQL database configured via TEST_DATABASE_URL.
Skip gracefully when DB is not available.
"""
import pytest
from httpx import AsyncClient, ASGITransport

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def client():
    import os
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL not set — skipping integration tests")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _register_and_login(client: AsyncClient) -> str:
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@test.com"
    password = "testpassword123"

    await client.post("/api/auth/register", json={"email": email, "password": password})
    res = await client.post("/api/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


class TestAuth:
    async def test_register_and_login(self, client):
        import uuid
        email = f"test_{uuid.uuid4().hex[:8]}@test.com"

        reg = await client.post("/api/auth/register", json={"email": email, "password": "password123"})
        assert reg.status_code == 201

        login = await client.post("/api/auth/login", json={"email": email, "password": "password123"})
        assert login.status_code == 200
        assert "access_token" in login.json()

    async def test_invalid_login_fails(self, client):
        res = await client.post("/api/auth/login", json={"email": "nobody@test.com", "password": "wrong"})
        assert res.status_code == 401

    async def test_me_requires_auth(self, client):
        res = await client.get("/api/auth/me")
        assert res.status_code == 403


class TestWorkflows:
    async def test_create_workflow(self, client):
        token = await _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.post("/api/workflows", json={"task": "Test task"}, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert "id" in data
        assert data["status"] == "pending"
        assert data["task"] == "Test task"

    async def test_list_workflows(self, client):
        token = await _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        await client.post("/api/workflows", json={"task": "Task 1"}, headers=headers)
        res = await client.get("/api/workflows", headers=headers)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    async def test_get_workflow(self, client):
        token = await _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        create = await client.post("/api/workflows", json={"task": "Test"}, headers=headers)
        workflow_id = create.json()["id"]

        res = await client.get(f"/api/workflows/{workflow_id}", headers=headers)
        assert res.status_code == 200
        assert res.json()["id"] == workflow_id

    async def test_other_user_cannot_access_workflow(self, client):
        token1 = await _register_and_login(client)
        token2 = await _register_and_login(client)

        create = await client.post("/api/workflows", json={"task": "Private task"},
                                    headers={"Authorization": f"Bearer {token1}"})
        workflow_id = create.json()["id"]

        res = await client.get(f"/api/workflows/{workflow_id}",
                               headers={"Authorization": f"Bearer {token2}"})
        assert res.status_code == 404


class TestMemory:
    async def test_create_memory(self, client):
        token = await _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.post("/api/memory",
                                json={"content": "I prefer bullet points", "memory_type": "preference"},
                                headers=headers)
        assert res.status_code == 201
        assert res.json()["content"] == "I prefer bullet points"

    async def test_list_memories(self, client):
        token = await _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        await client.post("/api/memory", json={"content": "Test memory"}, headers=headers)
        res = await client.get("/api/memory", headers=headers)
        assert res.status_code == 200
        assert len(res.json()) >= 1

    async def test_delete_memory(self, client):
        token = await _register_and_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        create = await client.post("/api/memory", json={"content": "To delete"}, headers=headers)
        memory_id = create.json()["id"]

        del_res = await client.delete(f"/api/memory/{memory_id}", headers=headers)
        assert del_res.status_code == 204

        memories = await client.get("/api/memory", headers=headers)
        ids = [m["id"] for m in memories.json()]
        assert memory_id not in ids

    async def test_other_user_cannot_delete_memory(self, client):
        token1 = await _register_and_login(client)
        token2 = await _register_and_login(client)

        create = await client.post("/api/memory", json={"content": "User1 memory"},
                                    headers={"Authorization": f"Bearer {token1}"})
        memory_id = create.json()["id"]

        del_res = await client.delete(f"/api/memory/{memory_id}",
                                       headers={"Authorization": f"Bearer {token2}"})
        assert del_res.status_code == 404


class TestHealth:
    async def test_health(self, client):
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
