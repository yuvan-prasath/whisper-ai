FROM python:3.11

WORKDIR /app

# HuggingFace Spaces requires user 1000
RUN useradd -m -u 1000 user && \
    mkdir -p /app/uploads && \
    mkdir -p /app/static && \
    mkdir -p /data/chroma_db && \
    chown -R user:user /app && \
    chown -R user:user /data

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    CHROMA_PATH=/data/chroma_db \
    DB_PATH=/data/neumannbot.db

# Install dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Pre-download sentence-transformer model
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy all app files
COPY --chown=user . .

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--log-level", "info"]
