import os
import asyncio
import base64
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from agent import create_support_agent
from sarvam_client import speech_to_text, text_to_speech
from hubspot_client import log_support_session
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Sarvam Customer Support Agent")

# Allow both localhost (dev) and the live Shopify storefront
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://www.kviyengars.com",
    "https://kviyengars.com",
    "https://kviyengars.myshopify.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

agent = create_support_agent()

# session_id → list of LangChain messages
sessions: dict = {}
# session_id → detected customer name (extracted lazily from conversation)
session_customer: dict = {}


@app.post("/voice-chat/{session_id}")
async def voice_chat(
    session_id: str,
    audio: UploadFile = File(...),
):
    # 1. Voice → Text
    audio_bytes = await audio.read()
    stt_result = await speech_to_text(audio_bytes)
    transcript = stt_result.get("transcript", "")
    detected_language = stt_result.get("language_code", "en-IN")

    print(f"🎙️  [{session_id}] Transcript ({detected_language}): {transcript}")

    # 2. Maintain session history
    if session_id not in sessions:
        sessions[session_id] = []
    sessions[session_id].append(HumanMessage(content=transcript))

    # 3. Run agent
    result = agent.invoke({"messages": sessions[session_id]})
    agent_reply = result["messages"][-1].content
    sessions[session_id] = result["messages"]

    print(f"🤖  [{session_id}] Agent: {agent_reply}")

    # 4. Text → Voice
    audio_response = await text_to_speech(agent_reply, detected_language)

    # 5. Best-effort HubSpot logging (fire-and-forget, never blocks the response)
    customer_name = session_customer.get(session_id, "Customer")
    asyncio.create_task(
        log_support_session(
            session_id=session_id,
            customer_name=customer_name,
            language=detected_language,
            messages=sessions[session_id],
        )
    )

    return JSONResponse({
        "transcript": transcript,
        "agent_response": agent_reply,
        "language": detected_language,
        "audio_base64": base64.b64encode(audio_response).decode("utf-8"),
    })


@app.post("/session/{session_id}/set-customer")
async def set_customer(session_id: str, request: Request):
    """
    Optional: let the frontend tell the backend who the customer is
    (e.g. if the Shopify store passes the logged-in customer's name).
    Body: { "name": "Vasupradha" }
    """
    body = await request.json()
    session_customer[session_id] = body.get("name", "Customer")
    return {"ok": True}


@app.delete("/session/{session_id}")
async def end_session(session_id: str):
    """Clear session data (call when the widget is closed)."""
    sessions.pop(session_id, None)
    session_customer.pop(session_id, None)
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "running", "shopify": os.getenv("USE_SHOPIFY", "false")}


# ---------------------------------------------------------------------------
# Serve the compiled React frontend as static files
# The build output (npm run build) goes to frontend/dist/
# ---------------------------------------------------------------------------
_frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/app", StaticFiles(directory=_frontend_dist, html=True), name="frontend")

    @app.get("/")
    def serve_root():
        return FileResponse(os.path.join(_frontend_dist, "index.html"))
