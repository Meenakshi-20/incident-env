"""
FastAPI server — OpenEnv spec compliant.
Endpoints: POST /reset, POST /step, GET /state
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from server.env import IncidentEnv
from server.models import IncidentAction

app = FastAPI(
    title="Incident Report Auto-Filler Environment",
    description=(
        "An OpenEnv environment where AI agents practice filling "
        "structured incident reports from raw incident descriptions."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# One global env instance (stateful per session)
env = IncidentEnv()


class ResetRequest(BaseModel):
    task_id: Optional[str] = None  # "easy", "medium", "hard" or None for auto


@app.get("/")
def root():
    return {
        "name": "Incident Report Auto-Filler",
        "version": "1.0.0",
        "tasks": ["easy", "medium", "hard"],
        "endpoints": ["/reset", "/step", "/state"],
    }


@app.post("/reset")
def reset(request: ResetRequest = ResetRequest()):
    """Reset the environment and return the first observation."""
    obs = env.reset(task_id=request.task_id)
    return obs.model_dump()


@app.post("/step")
def step(action: IncidentAction):
    """
    Submit a filled incident report.
    Returns observation, reward (0.0-1.0), done, info.
    """
    try:
        result = env.step(action)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state")
def state():
    """Return current environment state."""
    return env.state()


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("server.main:app", host="0.0.0.0", port=7860, reload=False)
