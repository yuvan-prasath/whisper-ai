import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from rag import retrieve_context
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from ingest import router as ingest_router
from analytics import log_message, get_analytics, detect_escalation




app = FastAPI(title="Whisper API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Then routers
app.include_router(ingest_router, prefix="/api/ingest", tags=["Ingest"])

# 4. Then everything else
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class ChatRequest(BaseModel):
    session_id: str
    message: str
    org_id: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    sources_used: str
    escalate: bool

sessions = {}



# Serve the chatbot at the root URL
app.mount("/animation1", StaticFiles(directory="animation1"), name="animation1")
app.mount("/animation2", StaticFiles(directory="animation2"), name="animation2")
app.mount("/animation3", StaticFiles(directory="animation3"), name="animation3")
app.mount("/animation4", StaticFiles(directory="animation4"), name="animation4")
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/whisper")
def serve_ui():
    return FileResponse("whisper.html")


@app.get("/")
def home():
    return {"message": "Whisper API is running!"}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        escalate = detect_escalation(req.message)
        context = retrieve_context(req.message, org_id=req.org_id)

        system_prompt = f"""You are Whisper, a helpful AI assistant.
Answer using ONLY the context below.
If the answer is not in the context, say:
'I dont have that information. Please contact support.'
Never make up answers.

Context:
{context}
"""
        if req.session_id not in sessions:
            sessions[req.session_id] = []

        sessions[req.session_id].append({
            "role": "user",
            "content": req.message
        })

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt}
            ] + sessions[req.session_id]
        )

        reply = response.choices[0].message.content

        sessions[req.session_id].append({
            "role": "assistant",
            "content": reply
        })

        log_message(
            session_id=req.session_id,
            org_id=req.org_id,
            message=req.message,
            reply=reply,
            escalate=escalate
        )

        return ChatResponse(
            session_id=req.session_id,
            reply=reply,
            sources_used=context[:200] + "...",
            escalate=escalate
        )

    except Exception as e:
        print(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/{org_id}")
def analytics(org_id: str):
    return get_analytics(org_id)
