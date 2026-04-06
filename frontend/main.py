# [FILE] main.py
import os, uuid
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core.agent import StoryAgent
import edge_tts

app = FastAPI()
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Initialize Agent
agent = StoryAgent(api_keys=["mock_key"])

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("index.html", "r", encoding="utf-8") as f: return f.read()

@app.post("/speak")
async def speak(request: dict):
    text = request.get("text", "")
    filename = f"speech_{uuid.uuid4()}.mp3"
    output_file = os.path.join("static", filename)
    communicate = edge_tts.Communicate(text, "en-GB-SoniaNeural")
    await communicate.save(output_file)
    return {"url": f"/static/{filename}"}

class StoryRequest(BaseModel):
    lat: float
    lon: float
    text: str = ""
    era: str = "Modern"

@app.post("/cultural-intelligence")
async def cultural_intelligence(req: StoryRequest):
    narrative, intel = agent.process(req.lat, req.lon, req.text, req.era)
    return {"narrative": narrative, "intel": intel}
