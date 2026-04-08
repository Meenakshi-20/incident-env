"""
Core environment logic.
Implements step(), reset(), state() as required by OpenEnv spec.
Each episode = one task. Agent has up to MAX_STEPS attempts.
Reward improves if the agent refines its answer across steps.
"""

from typing import Dict, Any, Optional
from server.models import IncidentAction, IncidentObservation, IncidentReward
from server.tasks import TASKS, grade

MAX_STEPS = 3  # agent gets up to 3 attempts per task


class IncidentEnv:
    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._task_order = ["easy", "medium", "hard"]
        self._task_index = 0
        self._step_number = 0
        self._done = False
        self._best_score = 0.0
        self._last_feedback = ""

    def reset(self, task_id: Optional[str] = None) -> IncidentObservation:
        """Start a new episode. Returns initial observation."""
        if task_id and task_id in TASKS:
            self._current_task_id = task_id
        else:
            self._current_task_id = self._task_order[
                self._task_index % len(self._task_order)
            ]
            self._task_index += 1

        task = TASKS[self._current_task_id]
        self._step_number = 0
        self._done = False
        self._best_score = 0.0
        self._last_feedback = ""

        self._state = {
            "task_id": self._current_task_id,
            "task_difficulty": task["task_difficulty"],
            "step_number": self._step_number,
            "done": self._done,
            "best_score": self._best_score,
        }

        return IncidentObservation(
            incident_description=task["incident_description"],
            task_id=self._current_task_id,
            task_difficulty=task["task_difficulty"],
            step_number=self._step_number,
            feedback="Read the incident description carefully and fill in all fields.",
        )

    def step(self, action: IncidentAction) -> Dict[str, Any]:
        """
        Process one agent action.
        Returns observation, reward, done, info.
        """
        if self._done:
            return {
                "observation": self._make_obs("Episode already done. Call reset() to start again."),
                "reward": 0.0,
                "done": True,
                "info": {"message": "Episode done"},
            }

        self._step_number += 1

        # Grade the action
        result = grade(
            self._current_task_id,
            action.model_dump()
        )
        score = result["score"]
        breakdown = result["breakdown"]
        feedback = result["feedback"]

        # Reward = improvement over best score so far (encourages refinement)
        reward = max(0.0, score - self._best_score)
        if score > self._best_score:
            self._best_score = score

        # Done if: perfect score OR max steps reached
        self._done = (score >= 1.0) or (self._step_number >= MAX_STEPS)

        self._last_feedback = feedback
        self._state.update({
            "step_number": self._step_number,
            "done": self._done,
            "best_score": self._best_score,
            "last_score": score,
            "last_breakdown": breakdown,
        })

        obs = self._make_obs(feedback)

        return {
            "observation": obs.model_dump(),
            "reward": round(reward, 4),
            "done": self._done,
            "info": {
                "score": score,
                "best_score": self._best_score,
                "breakdown": breakdown,
                "step": self._step_number,
            },
        }

    def state(self) -> Dict[str, Any]:
        """Return current environment state."""
        return dict(self._state)

    def _make_obs(self, feedback: str) -> IncidentObservation:
        task = TASKS[self._current_task_id]
        return IncidentObservation(
            incident_description=task["incident_description"],
            task_id=self._current_task_id,
            task_difficulty=task["task_difficulty"],
            step_number=self._step_number,
            feedback=feedback,
        )
