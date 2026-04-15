"""
auth.py — Neumann Intelligence
API Key authentication using FastAPI dependencies.
"""

from fastapi import Request, HTTPException
from database import get_client_by_api_key


def require_api_key(request: Request):
    """
    Reads X-API-Key from request headers (case-insensitive).
    Works with both 'x-api-key' and 'X-API-Key' header names.
    """
    # FastAPI/Starlette stores headers lowercase internally
    api_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include X-API-Key header."
        )

    client = get_client_by_api_key(api_key)

    if not client:
        raise HTTPException(
            status_code=403,
            detail="Invalid or inactive API key."
        )

    return client
