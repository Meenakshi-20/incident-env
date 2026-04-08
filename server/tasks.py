"""
3 incident tasks with deterministic graders.
Each grader returns a score between 0.0 and 1.0.
Fields checked: root_cause, severity, affected_systems, next_steps
Each field = 0.2 points. estimated_resolution_time = 0.2 bonus points.
Total = 1.0
"""

from typing import Dict, Any

TASKS = {
    "easy": {
        "task_id": "easy",
        "task_difficulty": "easy",
        "incident_description": (
            "INCIDENT REPORT - 2024-03-15 03:42 UTC\n"
            "Alert: Web server (prod-web-01) is returning HTTP 500 errors.\n"
            "Logs show: 'FATAL: database connection refused at 03:41 UTC'\n"
            "Database server (prod-db-01) is not responding to pings.\n"
            "Disk usage on prod-db-01 was at 99.8% as of last monitoring check (03:30 UTC).\n"
            "Affected users: ~2,400 active sessions dropped.\n"
            "On-call engineer has been paged."
        ),
        "gold": {
            "root_cause": ["disk full", "disk space", "storage full", "99", "database disk", "out of disk"],
            "severity": ["high", "critical"],
            "affected_systems": ["web", "database", "db", "prod-web", "prod-db"],
            "next_steps": ["free disk", "clear disk", "delete", "increase disk", "storage", "restart database", "expand"],
            "estimated_resolution_time": ["30", "1 hour", "2 hour", "15 min", "45 min", "hour"],
        },
    },
    "medium": {
        "task_id": "medium",
        "task_difficulty": "medium",
        "incident_description": (
            "INCIDENT REPORT - 2024-03-20 14:15 UTC\n"
            "Multiple alerts firing simultaneously:\n"
            "- Payment service: timeout errors spiking (latency >30s)\n"
            "- Order service: 'upstream payment service unavailable'\n"
            "- User dashboard: orders stuck in 'processing' state\n"
            "- Redis cache cluster: memory usage at 97%, eviction rate high\n"
            "Timeline:\n"
            "  14:00 UTC - Marketing sent bulk promotional email to 500k users\n"
            "  14:08 UTC - Traffic spike 8x normal load\n"
            "  14:10 UTC - Redis memory alarm triggered\n"
            "  14:12 UTC - Payment service latency alarm triggered\n"
            "  14:15 UTC - Order service alarm triggered\n"
            "No recent deployments. All services on same version as yesterday."
        ),
        "gold": {
            "root_cause": ["redis", "cache", "memory", "traffic spike", "email campaign", "bulk email", "promotional", "overload"],
            "severity": ["high", "critical"],
            "affected_systems": ["payment", "order", "redis", "cache", "dashboard", "user"],
            "next_steps": ["scale redis", "increase redis memory", "flush cache", "throttle", "rate limit", "scale", "restart redis", "add capacity"],
            "estimated_resolution_time": ["1 hour", "2 hour", "30 min", "45 min", "3 hour"],
        },
    },
    "hard": {
        "task_id": "hard",
        "task_difficulty": "hard",
        "incident_description": (
            "INCIDENT REPORT - 2024-03-25 09:05 UTC\n"
            "Customer support receiving complaints about intermittent login failures.\n"
            "Error rate: ~12% of login attempts failing (not all users affected).\n"
            "Logs show mixed signals:\n"
            "  - Auth service: occasional 'token validation failed'\n"
            "  - Some requests succeed, some fail with same credentials\n"
            "  - No obvious pattern in which users are affected\n"
            "  - Load balancer distributing to 3 auth service instances (auth-1, auth-2, auth-3)\n"
            "Recent changes:\n"
            "  - JWT secret key was rotated 2 days ago as part of routine security policy\n"
            "  - Deployment rolled out to auth-1 and auth-2 but deployment logs for auth-3 are missing\n"
            "  - auth-3 was restarted manually by an engineer last week for 'memory issues'\n"
            "No monitoring alert was triggered (error rate below 15% threshold)."
        ),
        "gold": {
            "root_cause": ["jwt", "secret", "key rotation", "auth-3", "old secret", "stale secret", "partial deployment", "inconsistent", "token"],
            "severity": ["high", "medium"],
            "affected_systems": ["auth", "login", "authentication", "load balancer", "auth-3"],
            "next_steps": ["redeploy auth-3", "update auth-3", "rotate secret", "restart auth-3", "verify deployment", "check auth-3", "update secret"],
            "estimated_resolution_time": ["30 min", "1 hour", "15 min", "45 min", "2 hour"],
        },
    },
}


def grade(task_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Grade the action against the gold standard.
    Returns score (0.0-1.0) and per-field breakdown.
    """
    task = TASKS.get(task_id)
    if not task:
        return {"score": 0.0, "breakdown": {}, "feedback": "Unknown task"}

    gold = task["gold"]
    breakdown = {}
    total = 0.0

    # Root cause: 0.25 points
    rc = action.get("root_cause", "").lower()
    rc_hit = any(kw in rc for kw in gold["root_cause"])
    breakdown["root_cause"] = 0.25 if rc_hit else 0.0
    total += breakdown["root_cause"]

    # Severity: 0.25 points
    sev = action.get("severity", "").lower()
    sev_hit = any(kw in sev for kw in gold["severity"])
    breakdown["severity"] = 0.25 if sev_hit else 0.0
    total += breakdown["severity"]

    # Affected systems: 0.25 points (partial credit)
    sys_text = action.get("affected_systems", "").lower()
    sys_hits = sum(1 for kw in gold["affected_systems"] if kw in sys_text)
    sys_score = min(sys_hits / max(len(gold["affected_systems"]), 1), 1.0) * 0.25
    breakdown["affected_systems"] = round(sys_score, 3)
    total += breakdown["affected_systems"]

    # Next steps: 0.15 points
    ns = action.get("next_steps", "").lower()
    ns_hit = any(kw in ns for kw in gold["next_steps"])
    breakdown["next_steps"] = 0.15 if ns_hit else 0.0
    total += breakdown["next_steps"]

    # Estimated resolution time: 0.10 bonus
    ert = action.get("estimated_resolution_time", "").lower()
    ert_hit = any(kw in ert for kw in gold["estimated_resolution_time"])
    breakdown["estimated_resolution_time"] = 0.10 if ert_hit else 0.0
    total += breakdown["estimated_resolution_time"]

    total = round(min(total, 1.0), 3)

    # Build feedback string
    misses = [f for f, v in breakdown.items() if v == 0.0]
    feedback = f"Score: {total}. "
    if misses:
        feedback += f"Improve: {', '.join(misses)}."
    else:
        feedback += "All fields correct!"

    return {"score": total, "breakdown": breakdown, "feedback": feedback}
