# NeumannBot v2.0 — Upgrade Notes
## Neumann Intelligence

---

## What Changed

| File | Change |
|---|---|
| `database.py` | NEW — SQLite client registry, persistent analytics, document tracking |
| `auth.py` | NEW — API key authentication middleware |
| `rag.py` | UPGRADED — upsert instead of add, batch processing, persistent ChromaDB |
| `ingest.py` | UPGRADED — auth protected, plan limits enforced, document logging |
| `analytics.py` | UPGRADED — now writes to SQLite, not in-memory list |
| `main.py` | UPGRADED — register, settings, embed-code, me endpoints added |
| `static/widget.js` | NEW — embeddable popup widget for client websites |
| `requirements.txt` | UPGRADED — added email-validator |

---

## New API Endpoints

### 1. Register a new client
```
POST /api/register
Body: { "business_name": "ABC Corp", "email": "admin@abc.com" }
Response: { "org_id": "org_xxx", "api_key": "nb_xxx" }
```
Save the api_key — it won't be shown again.

### 2. Upload a document
```
POST /api/ingest/upload
Header: X-API-Key: nb_xxx
Body: multipart form — file (PDF or TXT)
```

### 3. Chat
```
POST /chat
Header: X-API-Key: nb_xxx
Body: { "session_id": "any_string", "message": "Hello" }
```

### 4. Update bot settings
```
PUT /api/settings
Header: X-API-Key: nb_xxx
Body: { "bot_name": "Aria", "bot_color": "#ff6b6b", "system_prompt": "You are Aria..." }
```

### 5. Get embed code
```
GET /api/embed-code
Header: X-API-Key: nb_xxx
Response: { "embed_snippet": "<script>...</script>" }
```

### 6. Analytics
```
GET /api/analytics/{org_id}
Header: X-API-Key: nb_xxx
```

---

## Widget Integration (for clients)

Client pastes this into their website before `</body>`:

```html
<script>
  window.NeumannBotConfig = {
    apiKey: "nb_their_api_key",
    orgId: "org_their_org_id",
    botName: "Aria",
    color: "#6366f1",
    apiBase: "https://your-deployment-url.com"
  };
</script>
<script src="https://your-deployment-url.com/static/widget.js" defer></script>
```

---

## HuggingFace Spaces — Persistent Storage Fix

Add this to your `.env` / Spaces secrets:
```
CHROMA_PATH=/data/chroma_db
DB_PATH=/data/neumannbot.db
```

HuggingFace `/data/` directory persists between restarts.
Without this, ChromaDB and SQLite reset on every restart.

---

## Plan Limits

| Plan | PDFs | Messages/day |
|---|---|---|
| free | 1 | 50 |
| starter | 3 | 500 |
| growth | 10 | 2000 |
| pro | unlimited | unlimited |

---

## Environment Variables Required

```
GROQ_API_KEY=your_groq_key
CHROMA_PATH=/data/chroma_db       # HuggingFace persistent path
DB_PATH=/data/neumannbot.db       # HuggingFace persistent path
BASE_URL=https://your-deployment-url.com   # For embed code generation
```
