import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from rag import ingest_document, ingest_pdf

router = APIRouter()

# Response model
class IngestResponse(BaseModel):
    message: str
    org_id: str
    chunks_stored: int
    filename: str


@router.post("/upload", response_model=IngestResponse)
async def upload_document(
    org_id: str = Form(...),       # which organisation
    file: UploadFile = File(...)   # the uploaded file
):
    """
    Accepts a PDF or TXT file upload.
    Ingests it into ChromaDB for the given org_id.
    """

    # Step 1 - Validate file type
    allowed_types = ["application/pdf", "text/plain"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported"
        )

    # Step 2 - Save file to uploads folder
    file_path = f"uploads/{org_id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print(f"File saved: {file_path}")

    # Step 3 - Ingest based on file type
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

    # Step 4 - Clean up saved file after ingestion
    os.remove(file_path)

    return IngestResponse(
        message="Document ingested successfully",
        org_id=org_id,
        chunks_stored=chunks,
        filename=file.filename
    )