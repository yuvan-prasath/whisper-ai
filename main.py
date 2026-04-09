"""
main.py — Neumann Intelligence | NeumannBot
Industrial-grade RAG chatbot API.

Endpoints:
  POST /api/register          — Register new client (get org_id + api_key)
  POST /api/ingest/upload     — Upload PDF/TXT (requires X-API-Key)
  GET  /api/ingest/documents  — List uploaded docs (requires X-API-Key)
  POST /chat                  — Chat with the bot (requires X-API-Key)
  GET  /api/analytics/{org_id}— Analytics (requires X-API-Key)
  PUT  /api/settings          — Update bot name, color, prompt (requires X-API-Key)
  GET  /api/me                — Get client profile (requires X-API-Key)
  GET  /api/embed-code        — Get embeddable widget snippet (requires X-API-Key)
  GET  /whisper               — Serve the chatbot UI
"""

import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, EmailStr
from groq import Groq

from database import init_db, create_client, update_client_settings
from auth import require_api_key
from rag import retrieve_context, get_collection_stats
from ingest import router as ingest_router
from analytics import log_message, get_analytics, detect_escalation

# ─────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────

# Initialize database tables on startup
init_db()

# Create uploads directory
os.makedirs("uploads", exist_ok=True)

# ─────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────

app = FastAPI(
    title="NeumannBot API",
    description="Enterprise RAG Chatbot by Neumann Intelligence",
    version="2.0.0"
)

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


# In-memory session store (session history per session_id)
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
    """Serves the chatbot HTML interface."""
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
    """
    Update bot customization settings.
    - bot_name: What the bot calls itself (e.g. "Aria", "Max")
    - bot_color: Hex color for the widget (e.g. "#6366f1")
    - system_prompt: Custom instructions for the bot's behavior
    """
    update_client_settings(
        org_id=client["org_id"],
        bot_name=req.bot_name,
        bot_color=req.bot_color,
        system_prompt=req.system_prompt
    )
    return {"message": "Settings updated successfully."}


@app.get("/api/embed-code", tags=["Client"])
def get_embed_code(client: dict = Depends(require_api_key)):
    """
    Returns the embeddable widget snippet for this client.
    Client pastes this into their website's <body> tag.
    """
    base_url = os.getenv("BASE_URL", "https://your-deployment-url.com")
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
    """
    Main chat endpoint.
    Uses client's custom system_prompt and knowledge base.
    Requires X-API-Key header.
    """
    if not groq_client:
        raise HTTPException(status_code=503, detail="Chat service unavailable.")

    org_id = client["org_id"]
    bot_name = client["bot_name"]
    custom_prompt = client["system_prompt"]

    escalate = detect_escalation(req.message)

    # Retrieve relevant context from this org's knowledge base
    context = retrieve_context(req.message, org_id=org_id)

    # Build system prompt with client's custom instructions
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
        system_prompt = f"""{custom_prompt}

You are {bot_name}, an AI assistant for {client['business_name']}.
No knowledge base documents have been uploaded yet.
Politely inform the user and suggest they contact support.
"""

    # Maintain session history
    if req.session_id not in sessions:
        sessions[req.session_id] = []

    sessions[req.session_id].append({
        "role": "user",
        "content": req.message
    })

    # Keep session to last 10 messages to avoid token overflow
    recent_history = sessions[req.session_id][-10:]

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt}
            ] + recent_history,
            max_tokens=512,
            temperature=0.3
        )

        reply = response.choices[0].message.content

        sessions[req.session_id].append({
            "role": "assistant",
            "content": reply
        })

        # Log to persistent DB
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
    """
    Returns analytics for an org.
    Client can only access their own analytics.
    """
    if client["org_id"] != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only access your own analytics."
        )
    return get_analytics(org_id)
