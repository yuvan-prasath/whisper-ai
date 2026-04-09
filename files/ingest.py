"""
ingest.py — Neumann Intelligence
Document upload endpoint.
Upgraded: API key auth, plan-based PDF limits, document tracking.
"""

import os
import shutil
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from pydantic import BaseModel
from auth import require_api_key
from database import (
    get_plan_limits, get_document_count,
    log_document, get_documents
)
from rag import ingest_document, ingest_pdf

router = APIRouter()


class IngestResponse(BaseModel):
    message: str
    org_id: str
    chunks_stored: int
    filename: str


class DocumentListResponse(BaseModel):
    org_id: str
    documents: list
    total: int


@router.post("/upload", response_model=IngestResponse)
async def upload_document(
    file: UploadFile = File(...),
    client: dict = Depends(require_api_key)   # Auth happens here
):
    """
    Upload a PDF or TXT file.
    Requires X-API-Key header.
    Enforces plan-based PDF upload limits.
    """
    org_id = client["org_id"]
    plan = client["plan"]

    # Check plan limits
    limits = get_plan_limits(plan)
    current_count = get_document_count(org_id)

    if current_count >= limits["pdfs"]:
        raise HTTPException(
            status_code=403,
            detail=f"Your '{plan}' plan allows {limits['pdfs']} document(s). "
                   f"You have {current_count}. Upgrade your plan to upload more."
        )

    # Validate file type
    allowed_types = ["application/pdf", "text/plain"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported."
        )

    # Save file temporarily
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{org_id}_{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print(f"File saved: {file_path}")

    # Ingest into ChromaDB
    try:
        if file.content_type == "application/pdf":
            chunks = ingest_pdf(file_path, org_id)
        else:
            chunks = ingest_document(file_path, org_id)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )
    finally:
        # Always clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)

    # Log document to database
    log_document(org_id, file.filename, chunks)

    return IngestResponse(
        message="Document ingested successfully",
        org_id=org_id,
        chunks_stored=chunks,
        filename=file.filename
    )


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(client: dict = Depends(require_api_key)):
    """Returns all documents uploaded by this client."""
    org_id = client["org_id"]
    docs = get_documents(org_id)

    return DocumentListResponse(
        org_id=org_id,
        documents=docs,
        total=len(docs)
    )
