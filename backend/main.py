from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from agent import create_support_agent
from sarvam_client import speech_to_text, text_to_speech
from langchain_core.messages import HumanMessage
import base64
import asyncio

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

agent = create_support_agent()
sessions = {}

@app.post("/voice-chat/{session_id}")
async def voice_chat(
    session_id: str,
    audio: UploadFile = File(...)
):
    # Step 1: Voice → Text
    audio_bytes = await audio.read()
    stt_result = await speech_to_text(audio_bytes)
    transcript = stt_result.get("transcript", "")
    detected_language = stt_result.get("language_code", "en-IN")

    print(f"🎙️ Transcript: {transcript}")
    print(f"🌐 Language: {detected_language}")

    # Step 2: Session history
    if session_id not in sessions:
        sessions[session_id] = []
    sessions[session_id].append(HumanMessage(content=transcript))

    # Step 3: Run agent
    result = agent.invoke({"messages": sessions[session_id]})
    agent_reply = result["messages"][-1].content
    sessions[session_id] = result["messages"]

    print(f"🤖 Agent reply: {agent_reply}")

    # Step 4: Convert reply to voice
    audio_response = await text_to_speech(agent_reply, detected_language)

    return JSONResponse({
        "transcript": transcript,
        "agent_response": agent_reply,
        "language": detected_language,
        "audio_base64": base64.b64encode(audio_response).decode("utf-8")
    })

@app.get("/health")
def health():
    return {"status": "running"}
