"""
rag.py — Neumann Intelligence
RAG engine: ingest documents + retrieve context.
Upgraded: persistent ChromaDB path, per-org isolation, duplicate chunk prevention.
"""

try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except (ImportError, KeyError):
    pass

import os
import hashlib
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

# ─────────────────────────────────────────────
# INIT MODELS
# ─────────────────────────────────────────────

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# IMPORTANT: Use a persistent path that survives restarts
# On HuggingFace Spaces, use /data/ — it persists between restarts
# On Railway/local, default to ./chroma_db
CHROMA_PATH = os.environ.get("CHROMA_PATH", "./chroma_db")

try:
    os.makedirs(CHROMA_PATH, exist_ok=True)
    # Test writability just in case
    test_file = os.path.join(CHROMA_PATH, "write_test.tmp")
    with open(test_file, "w") as f:
        f.write("ready")
    if os.path.exists(test_file):
        os.remove(test_file)
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
except Exception as e:
    print(f"⚠️ Chroma permission error at {CHROMA_PATH}. Fallback to /tmp/chroma_db! Error: {e}")
    CHROMA_PATH = "/tmp/chroma_db"
    os.makedirs(CHROMA_PATH, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=60
)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_collection(org_id: str):
    """Gets or creates a ChromaDB collection for this org."""
    return chroma_client.get_or_create_collection(
        name=f"org_{org_id}",
        metadata={"org_id": org_id}
    )


def chunk_id(org_id: str, filename: str, index: int) -> str:
    """
    Generates a stable unique ID for each chunk.
    Same file re-uploaded = same IDs = ChromaDB upserts instead of duplicates.
    """
    raw = f"{org_id}_{filename}_{index}"
    return hashlib.md5(raw.encode()).hexdigest()


# ─────────────────────────────────────────────
# INGEST
# ─────────────────────────────────────────────

def ingest_document(file_path: str, org_id: str) -> int:
    """Ingests a plain TXT file into ChromaDB for the given org."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    filename = os.path.basename(file_path)
    return _store_chunks(text, org_id, filename)


def ingest_pdf(file_path: str, org_id: str) -> int:
    """Ingests a PDF file into ChromaDB for the given org."""
    reader = PdfReader(file_path)
    full_text = ""

    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

    print(f"Extracted {len(full_text)} characters from PDF")
    filename = os.path.basename(file_path)
    return _store_chunks(full_text, org_id, filename)


def _store_chunks(text: str, org_id: str, filename: str) -> int:
    """
    Internal: splits text into chunks, embeds, and upserts into ChromaDB.
    Uses upsert (not add) to prevent duplicate errors on re-upload.
    """
    chunks = text_splitter.split_text(text)
    print(f"Split into {len(chunks)} chunks for org: {org_id}")

    collection = get_collection(org_id)

    # Batch upsert in groups of 50 for memory efficiency
    batch_size = 50
    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start:batch_start + batch_size]

        embeddings = [embedding_model.encode(c).tolist() for c in batch]
        ids = [chunk_id(org_id, filename, batch_start + i) for i in range(len(batch))]

        collection.upsert(
            documents=batch,
            embeddings=embeddings,
            ids=ids,
            metadatas=[{"filename": filename, "org_id": org_id} for _ in batch]
        )

    print(f"Stored {len(chunks)} chunks for org: {org_id}")
    return len(chunks)


def delete_org_documents(org_id: str):
    """Deletes all documents for an org."""
    try:
        chroma_client.delete_collection(f"org_{org_id}")
        print(f"Deleted collection for org: {org_id}")
    except Exception as e:
        print(f"Warning: Could not delete collection: {e}")


# ─────────────────────────────────────────────
# RETRIEVE
# ─────────────────────────────────────────────

def retrieve_context(query: str, org_id: str, top_k: int = 4) -> str:
    """
    Retrieves the most relevant chunks for a query from this org's collection.
    Returns joined context string.
    """
    query_embedding = embedding_model.encode(query).tolist()
    collection = get_collection(org_id)

    # Check if collection has any documents
    if collection.count() == 0:
        return ""

    # Limit top_k to available documents
    actual_k = min(top_k, collection.count())

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=actual_k
    )

    chunks = results["documents"][0]
    context = "\n\n".join(chunks)
    return context


def get_collection_stats(org_id: str) -> dict:
    """Returns stats about an org's knowledge base."""
    try:
        collection = get_collection(org_id)
        return {"org_id": org_id, "total_chunks": collection.count()}
    except Exception:
        return {"org_id": org_id, "total_chunks": 0}
