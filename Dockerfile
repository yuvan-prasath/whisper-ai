FROM python:3.11

# HuggingFace Spaces requires user 1000
RUN useradd -m -u 1000 user 

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR $HOME/app

# Install dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Pre-download sentence-transformer model
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy all app files
COPY --chown=user . .

# Set persistent paths into the writable home directory
ENV CHROMA_PATH=$HOME/app/chroma_db \
    DB_PATH=$HOME/app/neumannbot.db

# Ensure folder exists inside the container (they will be owned by 'user')
RUN mkdir -p $HOME/app/chroma_db $HOME/app/uploads

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--log-level", "info"]
