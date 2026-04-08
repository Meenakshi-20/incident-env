@"
---
title: Incident Env
emoji: 🚨
colorFrom: red
colorTo: orange
sdk: docker
pinned: false
---
"@ + (Get-Content README.md -Raw) | Set-Content README.md

# Incident Report Auto-Filler — OpenEnv Environment

An OpenEnv environment where AI agents practice filling structured incident
reports from raw incident descriptions. Simulates real Site Reliability
Engineering (SRE) workflows used at companies like Google, Meta, and Amazon.

## Motivation

Every production incident requires a structured post-mortem report. Writing
these reports manually is time-consuming and error-prone under pressure.
This environment trains agents to automatically extract: root cause, severity,
affected systems, next steps, and estimated resolution time from raw log dumps
and alert descriptions.

## Tasks

| Task | Difficulty | Description |
|------|-----------|-------------|
| easy | Easy | Server crash with clear disk-full logs |
| medium | Medium | Multi-system outage from Redis cache overload triggered by email campaign |
| hard | Hard | Intermittent login failures from partial JWT secret key rotation |

## Action Space

```json
{
  "root_cause": "string — what caused the incident",
  "severity": "low | medium | high | critical",
  "affected_systems": "comma-separated list",
  "next_steps": "concrete resolution actions",
  "estimated_resolution_time": "e.g. 30 minutes, 2 hours"
}
```

## Observation Space

```json
{
  "incident_description": "raw incident log or alert text",
  "task_id": "easy | medium | hard",
  "task_difficulty": "easy | medium | hard",
  "step_number": 0,
  "feedback": "per-field grading feedback from previous step"
}
```

## Reward Function

Partial credit scoring per field (deterministic, reproducible):
- `root_cause` — 0.25 points
- `severity` — 0.25 points
- `affected_systems` — 0.25 points (proportional to fields matched)
- `next_steps` — 0.15 points
- `estimated_resolution_time` — 0.10 points

Reward per step = improvement over best score so far (encourages refinement).

## Baseline Scores

| Task | Model | Score |
|------|-------|-------|
| easy | Qwen2.5-72B | ~0.85 |
| medium | Qwen2.5-72B | ~0.75 |
| hard | Qwen2.5-72B | ~0.50 |

## Setup & Usage

### Run locally with Docker

```bash
docker build -t incident-env .
docker run -p 7860:7860 incident-env
```

### Test endpoints

```bash
# Reset (start easy task)
curl -X POST http://localhost:7860/reset -H "Content-Type: application/json" -d '{"task_id": "easy"}'

# Step (submit a report)
curl -X POST http://localhost:7860/step -H "Content-Type: application/json" -d '{
  "root_cause": "disk full on database server",
  "severity": "critical",
  "affected_systems": "prod-db-01, prod-web-01",
  "next_steps": "free disk space, restart database",
  "estimated_resolution_time": "30 minutes"
}'

# State
curl http://localhost:7860/state
```

### Run baseline inference script

```bash
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export HF_TOKEN=your_token_here
export MY_ENV_BASE_URL=http://localhost:7860

python inference.py
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `API_BASE_URL` | LLM API endpoint |
| `MODEL_NAME` | Model identifier |
| `HF_TOKEN` | Hugging Face / API key |
| `MY_ENV_BASE_URL` | Your running environment URL |
