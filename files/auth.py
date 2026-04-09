"""
auth.py — Neumann Intelligence
API Key authentication using FastAPI dependencies.
Every protected endpoint just adds: client = Depends(require_api_key)
"""

from fastapi import Header, HTTPException, Depends
from database import get_client_by_api_key


def require_api_key(x_api_key: str = Header(..., description="Your NeumannBot API Key")):
    """
    FastAPI dependency — validates API key from request header.
    
    Usage in any endpoint:
        @app.post("/chat")
        def chat(req: ChatRequest, client = Depends(require_api_key)):
            org_id = client["org_id"]
    
    The client sends: X-API-Key: nb_xxxxx in every request.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header."
        )

    client = get_client_by_api_key(x_api_key)

    if not client:
        raise HTTPException(
            status_code=403,
            detail="Invalid or inactive API key."
        )

    return client


def require_active_plan(client: dict, required_plan: str = None):
    """
    Optional: check if client has required plan.
    For future use when gating features by plan.
    """
    if not client["is_active"]:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive. Please contact support."
        )
    return client
