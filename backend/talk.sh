#!/bin/bash

# Record voice
python3 - << 'PYEOF'
import sounddevice as sd
import wave, time
from datetime import datetime

DURATION = 8
SAMPLE_RATE = 16000
filename = f"test_audio_{datetime.now().strftime('%H%M%S')}.wav"

print(f"Saving as: {filename}")
time.sleep(1); print("3...")
time.sleep(1); print("2...")
time.sleep(1); print("1... SPEAK NOW!")

audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
sd.wait()

with wave.open(filename, 'wb') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(audio.tobytes())

with open(".last_recording", "w") as f:
    f.write(filename)
print(f"✅ Saved {filename}")
PYEOF

# Get filename
FILENAME=$(cat .last_recording)

# Send to agent
curl -s -X POST "http://localhost:8000/voice-chat/session_001" \
  -F "audio=@$FILENAME" \
  -o response.json

# Parse and play
python3 - << 'PYEOF'
import json, base64

with open("response.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("\n🎙️  You said:", data["transcript"])
print("🤖 Agent:", data["agent_response"])
print("🌐 Language:", data["language"])

with open("response.wav", "wb") as f:
    f.write(base64.b64decode(data["audio_base64"]))
PYEOF

afplay response.wav

#main yah ordar vaapas karana chaahata hoon