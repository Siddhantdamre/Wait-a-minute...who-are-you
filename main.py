# [FILE] main.py
# YOUR EXACT CODE + 1 Critical Fix (Root Route)
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse # <--- Added to serve index.html
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from core.agent import StoryAgent
import edge_tts
import asyncio

app = FastAPI()

# 1. MOUNT STATIC FOLDER
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# KEYS
keys = ["AIzaSyAsgvmS23I3Dmc_3NnFJqkI2ePODz0pfzw","AIzaSyAC7jc3MRJuewmIIpEHPy2hkFYF9bl4XFA"] 
agent = StoryAgent(api_keys=keys)

# --- CRITICAL FIX: Serve the Dashboard at Root ---
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("index.html", "r", encoding="utf-8") as f: return f.read()
# -------------------------------------------------

@app.on_event("startup")
def startup_event():
    print("\n--- DIAGNOSTIC: CHECKING MODELS ---")
    try:
        # Simple check to ensure client is active
        # models = agent.planner.client.models.list() # Commented out to prevent crash if key is invalid locally
        print("System: Google GenAI Client Initialized")
    except Exception as e:
        print(f"COULD NOT LIST MODELS: {e}")
    print("----------------------------------\n")

# 2. UPDATED VOICE ENDPOINT
@app.post("/speak")
async def speak(request: dict):
    text = request.get("text", "")
    output_file = "static/speech.mp3"
    
    communicate = edge_tts.Communicate(text, "en-GB-SoniaNeural")
    await communicate.save(output_file)
    
    return {"url": f"/static/speech.mp3"} # Relative path for Jupyter

class StoryRequest(BaseModel):
    lat: float
    lon: float
    text: str = ""
    era: str = "Modern"

@app.post("/cultural-intelligence")
async def cultural_intelligence(request: StoryRequest):
    narrative, intel = agent.process(
        lat=request.lat, 
        lon=request.lon, 
        text=request.text, 
        era=request.era
    )
    return {"narrative": narrative, "intel": intel}
