"""Tests for root and health endpoints."""


async def test_root_endpoint(client):
    response = await client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "CineWise API"
    assert body["status"] == "ok"
    assert body["health"] == "/api/health"


async def test_health_endpoint(client):
    response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
