from pydantic import BaseModel
from typing import Optional


class IncidentAction(BaseModel):
    root_cause: str
    severity: str          # "low", "medium", "high", "critical"
    affected_systems: str
    next_steps: str
    estimated_resolution_time: Optional[str] = ""


class IncidentObservation(BaseModel):
    incident_description: str
    task_id: str
    task_difficulty: str   # "easy", "medium", "hard"
    step_number: int
    feedback: Optional[str] = ""


class IncidentReward(BaseModel):
    value: float           # 0.0 to 1.0
    breakdown: dict        # per-field scores
    done: bool
