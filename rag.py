import os
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


chroma_client = chromadb.PersistentClient(
    path=os.environ.get("CHROMA_PATH", "./chroma_db")
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,   
    chunk_overlap=50  
)


def ingest_document(file_path: str, org_id: str):

    with open(file_path, "r") as f:
        text = f.read()

    # Step 2 - Split into chunks
    chunks = text_splitter.split_text(text)
    print(f"Document split into {len(chunks)} chunks")

    # Step 3 - Get or create a collection for this organisation
    collection = chroma_client.get_or_create_collection(name=f"org_{org_id}")

    # Step 4 - Embed each chunk and store
    for i, chunk in enumerate(chunks):
        embedding = embedding_model.encode(chunk).tolist()

        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"chunk_{i}"]
        )

    print(f"Stored {len(chunks)} chunks for org: {org_id}")
    return len(chunks)


def retrieve_context(query: str, org_id: str, top_k: int = 3):
    
    query_embedding = embedding_model.encode(query).tolist()

    # Step 2 - Search ChromaDB for similar chunks
    collection = chroma_client.get_or_create_collection(name=f"org_{org_id}")

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    # Step 3 - Join the found chunks into one context string
    chunks = results["documents"][0]
    context = "\n\n".join(chunks)

    return context


def ingest_pdf(file_path: str, org_id: str):
    """
    Reads a PDF file, extracts all text,
    splits into chunks, stores in ChromaDB
    """

    # Step 1 - Extract text from every page
    reader = PdfReader(file_path)
    full_text = ""

    for page in reader.pages:
        text = page.extract_text()
        if text:  # some pages might be empty
            full_text += text + "\n"

    print(f"Extracted {len(full_text)} characters from PDF")

    # Step 2 - Split into chunks
    chunks = text_splitter.split_text(full_text)
    print(f"Split into {len(chunks)} chunks")

    # Step 3 - Get collection for this org
    collection = chroma_client.get_or_create_collection(name=f"org_{org_id}")

    # Step 4 - Embed and store each chunk
    for i, chunk in enumerate(chunks):
        embedding = embedding_model.encode(chunk).tolist()

        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"pdf_chunk_{i}_{org_id}"]
        )

    print(f"Stored {len(chunks)} chunks for org: {org_id}")
    return len(chunks)