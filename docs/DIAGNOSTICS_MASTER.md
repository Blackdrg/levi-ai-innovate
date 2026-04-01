# 🩺 The Master Diagnostics Guide (`/admin/orchestrator/stats`)

How to read the internal telemetry array that the Sovereign OS broadcasts at `http://api.../admin/orchestrator/stats` (Authentication required `is_admin=True`).

## Understanding the Payload

### 1. Route Validation
```json
"orchestration": {
  "routes": {
    "cache": 1420,
    "local": 0,
    "tool": 34,
    "api": 620
  }
}
```
If `cache` is extremely low compared to `api`, your Vector matching threshold (default `0.92`) is likely too restrictive, forcing LEVI to spend computational cycles asking LLMs to re-answer standard identical prompts.

### 2. Agent Health Tracking
```json
"agents": {
  "research_agent": {
      "status": "degraded",
      "failures_7d": 24
  }
}
```
The MetaPlanner monitors the exact instances sub-tasks stall (e.g. Tavily search timeouts). If failures cross 20, LEVI actively routes traffic away from that agent.

### 3. Evolutionary Thresholds
```json
"evolution": {
    "interaction_surplus": 30,
    "threshold": 25
}
```
This is the Critic-Driven Mutation ticker. Once `interaction_surplus` > `threshold`, the overnight Celery task (`learning_tasks.py`) forces an execution sequence crossing Groq and Together AI to evaluate failure points and rewrite LEVI's internal code of conduct/system prompt.
