"""
main.py — Neumann Intelligence | NeumannBot
Industrial-grade RAG chatbot API.
"""

import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from groq import Groq

from database import init_db, create_client, update_client_settings
from auth import require_api_key
from rag import retrieve_context, get_collection_stats
from ingest import router as ingest_router
from analytics import log_message, get_analytics, detect_escalation

# ─────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────
init_db()

try:
    os.makedirs("uploads", exist_ok=True)
    # Test writability
    test_file = os.path.join("uploads", "write_test.tmp")
    with open(test_file, "w") as f:
        f.write("ready")
    if os.path.exists(test_file):
        os.remove(test_file)
except Exception as e:
    print(f"⚠️ Uploads permission error. Fallback to /tmp/uploads! Error: {e}")
    os.environ["UPLOAD_DIR"] = "/tmp/uploads"
    os.makedirs("/tmp/uploads", exist_ok=True)

# ─────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────
app = FastAPI(
    title="NeumannBot API",
    description="Enterprise RAG Chatbot by Neumann Intelligence",
    version="2.0.0"
)

# Add Authorize button to Swagger UI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    schema["security"] = [{"APIKeyHeader": []}]
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("WARNING: GROQ_API_KEY not set. Chat will fail.")
    groq_client = None
else:
    groq_client = Groq(api_key=api_key)

# ─────────────────────────────────────────────
# ROUTERS
# ─────────────────────────────────────────────
app.include_router(ingest_router, prefix="/api/ingest", tags=["Documents"])

# ─────────────────────────────────────────────
# STATIC FILES
# ─────────────────────────────────────────────
for folder in ["animation1", "animation2", "animation3", "animation4"]:
    if os.path.exists(folder):
        app.mount(f"/{folder}", StaticFiles(directory=folder), name=folder)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ─────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────
class RegisterRequest(BaseModel):
    business_name: str
    email: str

class RegisterResponse(BaseModel):
    message: str
    org_id: str
    api_key: str
    business_name: str
    note: str

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    escalate: bool
    bot_name: str

class SettingsRequest(BaseModel):
    bot_name: str = None
    bot_color: str = None
    system_prompt: str = None

# In-memory session store
sessions = {}

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.get("/")
def home():
    return {
        "service": "NeumannBot API",
        "version": "2.0.0",
        "company": "Neumann Intelligence",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/whisper", response_class=FileResponse)
def serve_ui():
    return FileResponse("whisper.html")

@app.post("/api/register", response_model=RegisterResponse, tags=["Auth"])
def register_client(req: RegisterRequest):
    """
    Register a new client business.
    Returns org_id and api_key — save these, they won't be shown again.
    """
    try:
        client = create_client(
            business_name=req.business_name,
            email=req.email
        )
        return RegisterResponse(
            message="Registration successful!",
            org_id=client["org_id"],
            api_key=client["api_key"],
            business_name=client["business_name"],
            note="Save your API key securely. Use it in X-API-Key header for all requests."
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/me", tags=["Client"])
def get_my_profile(client: dict = Depends(require_api_key)):
    """Returns the authenticated client's profile."""
    stats = get_collection_stats(client["org_id"])
    return {
        "org_id": client["org_id"],
        "business_name": client["business_name"],
        "email": client["email"],
        "bot_name": client["bot_name"],
        "bot_color": client["bot_color"],
        "plan": client["plan"],
        "is_active": client["is_active"],
        "knowledge_base": stats
    }

@app.put("/api/settings", tags=["Client"])
def update_settings(req: SettingsRequest, client: dict = Depends(require_api_key)):
    """Update bot name, color, and system prompt."""
    update_client_settings(
        org_id=client["org_id"],
        bot_name=req.bot_name,
        bot_color=req.bot_color,
        system_prompt=req.system_prompt
    )
    return {"message": "Settings updated successfully."}

@app.get("/api/embed-code", tags=["Client"])
def get_embed_code(client: dict = Depends(require_api_key)):
    """Returns the embeddable widget snippet for this client."""
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    org_id = client["org_id"]
    api_key_val = client["api_key"]
    bot_name = client["bot_name"]
    bot_color = client["bot_color"]

    snippet = f"""<!-- NeumannBot Widget — paste before </body> -->
<script>
  window.NeumannBotConfig = {{
    apiKey: "{api_key_val}",
    orgId: "{org_id}",
    botName: "{bot_name}",
    color: "{bot_color}",
    apiBase: "{base_url}"
  }};
</script>
<script src="{base_url}/static/widget.js" defer></script>"""

    return {
        "org_id": org_id,
        "embed_snippet": snippet,
        "instructions": "Paste this snippet just before the </body> tag on your website."
    }

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(req: ChatRequest, client: dict = Depends(require_api_key)):
    """Main chat endpoint. Requires X-API-Key header."""
    if not groq_client:
        raise HTTPException(status_code=503, detail="Chat service unavailable. GROQ_API_KEY not set.")

    org_id = client["org_id"]
    bot_name = client["bot_name"]
    custom_prompt = client["system_prompt"]

    escalate = detect_escalation(req.message)
    context = retrieve_context(req.message, org_id=org_id)

    if context:
        system_prompt = f"""{custom_prompt}

You are {bot_name}, an AI assistant for {client['business_name']}.
Answer using ONLY the context provided below.
If the answer is not in the context, say: 'I don't have that information. Please contact our support team.'
Never make up answers. Be concise and helpful.

Context:
{context}
"""
    else:
        system_prompt = f"""You are {bot_name}, an AI assistant for {client['business_name']}.
No documents have been uploaded yet. Politely inform the user and suggest they contact support."""

    if req.session_id not in sessions:
        sessions[req.session_id] = []

    sessions[req.session_id].append({"role": "user", "content": req.message})

    # Keep last 10 messages only
    recent_history = sessions[req.session_id][-10:]

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}] + recent_history,
            max_tokens=512,
            temperature=0.3
        )

        reply = response.choices[0].message.content
        sessions[req.session_id].append({"role": "assistant", "content": reply})

        log_message(
            session_id=req.session_id,
            org_id=org_id,
            message=req.message,
            reply=reply,
            escalate=escalate
        )

        return ChatResponse(
            session_id=req.session_id,
            reply=reply,
            escalate=escalate,
            bot_name=bot_name
        )

    except Exception as e:
        print(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/{org_id}", tags=["Analytics"])
def analytics(org_id: str, client: dict = Depends(require_api_key)):
    """Returns analytics for an org. Clients can only access their own."""
    if client["org_id"] != org_id:
        raise HTTPException(status_code=403, detail="You can only access your own analytics.")
    return get_analytics(org_id)
