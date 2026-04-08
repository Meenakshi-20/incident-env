"""
Baseline inference script for Incident Report Auto-Filler environment.
Uses OpenAI client to run an LLM against the environment.

STDOUT FORMAT (strictly followed):
  [START] task=<task_name> env=<benchmark> model=<model_name>
  [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...>

Usage:
  export API_BASE_URL=https://router.huggingface.co/v1
  export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
  export HF_TOKEN=your_token_here
  export MY_ENV_BASE_URL=http://localhost:7860   # your running environment
  python inference.py
"""

import os
import json
import textwrap
import requests
from typing import List, Optional
from openai import OpenAI

# ── Configuration ──────────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "your-token-here")
ENV_BASE_URL = os.getenv("MY_ENV_BASE_URL", "http://localhost:7860")

TASK_NAMES   = ["easy", "medium", "hard"]
BENCHMARK    = "incident-report-autofiller"
MAX_STEPS    = 3
TEMPERATURE  = 0.2
MAX_TOKENS   = 512
SUCCESS_SCORE_THRESHOLD = 0.5

# ── Logging helpers ────────────────────────────────────────────────────────────
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val  = str(done).lower()
    action_flat = action.replace("\n", " ").replace("\r", " ")[:200]
    print(
        f"[STEP] step={step} action={action_flat} reward={reward:.2f} "
        f"done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ── Environment helpers ────────────────────────────────────────────────────────
def env_reset(task_id: str) -> dict:
    resp = requests.post(f"{ENV_BASE_URL}/reset", json={"task_id": task_id}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def env_step(action: dict) -> dict:
    resp = requests.post(f"{ENV_BASE_URL}/step", json=action, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ── LLM helpers ───────────────────────────────────────────────────────────────
SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert Site Reliability Engineer (SRE) filling incident reports.
    You will receive a raw incident description and must return a JSON object with EXACTLY these fields:
    {
      "root_cause": "<what caused the incident>",
      "severity": "<one of: low, medium, high, critical>",
      "affected_systems": "<comma-separated list of affected systems>",
      "next_steps": "<concrete actions to resolve the incident>",
      "estimated_resolution_time": "<e.g. 30 minutes, 2 hours>"
    }
    Return ONLY the JSON object. No explanation, no markdown, no extra text.
""").strip()


def build_user_prompt(obs: dict, feedback: str, step: int) -> str:
    return textwrap.dedent(f"""
        Step {step} — Fill the incident report.

        INCIDENT DESCRIPTION:
        {obs['incident_description']}

        PREVIOUS FEEDBACK (if any): {feedback or 'None'}

        Return a JSON object with fields: root_cause, severity, affected_systems, next_steps, estimated_resolution_time.
    """).strip()


def get_llm_action(client: OpenAI, obs: dict, feedback: str, step: int) -> dict:
    prompt = build_user_prompt(obs, feedback, step)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        raw = (completion.choices[0].message.content or "{}").strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as exc:
        print(f"[DEBUG] LLM call failed: {exc}", flush=True)
        # Fallback default action
        return {
            "root_cause": "unknown",
            "severity": "medium",
            "affected_systems": "unknown",
            "next_steps": "investigate logs and escalate",
            "estimated_resolution_time": "1 hour",
        }


# ── Main loop ─────────────────────────────────────────────────────────────────
def run_task(client: OpenAI, task_id: str) -> float:
    """Run one full episode for a given task. Returns final score."""
    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    feedback = ""

    try:
        obs = env_reset(task_id)

        for step in range(1, MAX_STEPS + 1):
            action_dict = get_llm_action(client, obs, feedback, step)
            action_str = json.dumps(action_dict)

            error = None
            try:
                result = env_step(action_dict)
                reward  = float(result.get("reward", 0.0))
                done    = bool(result.get("done", False))
                info    = result.get("info", {})
                score   = float(info.get("best_score", 0.0))
                feedback = result.get("observation", {}).get("feedback", "")
                obs     = result.get("observation", obs)
            except Exception as e:
                reward = 0.0
                done   = False
                error  = str(e)

            rewards.append(reward)
            steps_taken = step
            log_step(step=step, action=action_str, reward=reward, done=done, error=error)

            if done:
                break

        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Episode error: {e}", flush=True)
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    all_scores = []
    for task_id in TASK_NAMES:
        score = run_task(client, task_id)
        all_scores.append(score)
    avg = sum(all_scores) / len(all_scores)
    print(f"\n[SUMMARY] avg_score={avg:.3f} scores={','.join(f'{s:.3f}' for s in all_scores)}", flush=True)


if __name__ == "__main__":
    main()
