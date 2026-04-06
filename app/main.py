# app/main.py
import os
import uuid  # <--- NEW IMPORT
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from core.agent import StoryAgent
import edge_tts

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

# REPLACING WITH YOUR ACTUAL KEYS
keys = ["AIzaSyAC7jc3MRJuewmIIpEHPy2hkFYF9bl4XFA"] 
agent = StoryAgent(api_keys=keys)

@app.on_event("startup")
def startup_event():
    print("\n--- DIAGNOSTIC: CHECKING MODELS ---")
    try:
        # Simple check to ensure client is active
        models = agent.planner.client.models.list()
        print("System: Google GenAI Client Connected")
    except Exception as e:
        print(f"COULD NOT LIST MODELS: {e}")
    print("----------------------------------\n")

# 2. FIXED ENDPOINT: Unique Filenames for Audio
@app.post("/speak")
async def speak(request: dict):
    text = request.get("text", "")
    
    # Generate unique filename to prevent browser caching issues
    unique_filename = f"speech_{uuid.uuid4()}.mp3"
    output_file = os.path.join("static", unique_filename)
    
    # Generate Audio
    communicate = edge_tts.Communicate(text, "en-GB-SoniaNeural")
    await communicate.save(output_file)
    
    # Return full URL
    return {"url": f"http://localhost:8000/{output_file}"}

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