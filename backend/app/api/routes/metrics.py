"""FastAPI router for evaluation metrics endpoint.

Endpoints:
- GET /api/metrics — Return precomputed evaluation metrics (Precision@10, NDCG@10)
"""
from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("")
async def get_metrics(request: Request):
    """Return evaluation metrics loaded at startup from metrics.json.

    Returns 404 if metrics have not been computed yet (metrics.json absent at startup).
    """
    metrics = getattr(request.app.state, "metrics", None)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Metrics not yet computed")
    return metrics
