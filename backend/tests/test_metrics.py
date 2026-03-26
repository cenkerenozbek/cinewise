"""Tests for GET /api/metrics endpoint — Phase 4."""
import pytest


@pytest.mark.asyncio
async def test_metrics_returns_200(client):
    """GET /api/metrics returns 200 with metrics data when metrics are loaded."""
    from app.main import app
    app.state.metrics = {
        "precision_at_10": 0.42,
        "ndcg_at_10": 0.55,
        "eval_date": "2026-03-26",
        "n_users": 100,
    }
    response = await client.get("/api/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["precision_at_10"] == 0.42
    assert body["ndcg_at_10"] == 0.55
    assert body["eval_date"] == "2026-03-26"
    assert body["n_users"] == 100


@pytest.mark.asyncio
async def test_metrics_returns_404(client):
    """GET /api/metrics returns 404 when no metrics.json was loaded."""
    from app.main import app
    app.state.metrics = None
    response = await client.get("/api/metrics")
    assert response.status_code == 404
    assert "not yet computed" in response.json()["detail"]
