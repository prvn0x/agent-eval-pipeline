# Agent Eval Pipeline

An evaluation system for AI agents. It ingests multi-turn conversation logs, scores them across four dimensions, collects human annotations, detects recurring failure patterns, and calibrates its own evaluators against human labels.

Live API: **https://agent-eval-pipeline.onrender.com/docs**

---

## What it does

Most agent teams eyeball conversation logs or run ad-hoc spot checks. This pipeline makes evaluation systematic:

1. **Ingest** — POST a conversation log (turns, tool calls, metadata)
2. **Evaluate** — four evaluators run in parallel and produce a scored report
3. **Annotate** — human reviewers label turns; Cohen's Kappa measures inter-annotator agreement and routes conversations to auto-label or human review
4. **Self-update** — the system scans evaluations for recurring failure patterns and generates concrete improvement suggestions (prompt fixes, tool schema changes, training flags)
5. **Meta-evaluate** — calibrates each evaluator against human labels to surface blind spots and drift

---

## Evaluation dimensions

| Evaluator | What it checks |
|-----------|---------------|
| Heuristic | Empty responses, latency thresholds, tool execution failures, mission completion |
| LLM-as-Judge | Response quality, helpfulness, factuality (via Ollama / llama3.2) |
| Tool Call | Parameter hallucination, selection accuracy, schema adherence |
| Multi-turn | Coherence across turns, context retention, self-contradiction |

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/conversations` | Ingest a single conversation |
| POST | `/conversations/batch` | Ingest multiple conversations |
| GET | `/evaluations/{id}` | Fetch evaluation report |
| POST | `/feedback/{id}` | Submit human annotations |
| GET | `/feedback/agreement/{id}` | Inter-annotator agreement (Cohen's Kappa) |
| POST | `/suggestions/trigger` | Run self-updater for an agent version |
| GET | `/suggestions` | List improvement suggestions |
| POST | `/meta-eval/run` | Run evaluator calibration |
| GET | `/meta-eval/latest` | Latest calibration report |
| GET | `/health` | Health check |

Full schema at `/docs` (Swagger) or `/redoc`.

---

## Architecture

```
POST /conversations
      │
      ▼
ConversationService ──► Celery task (async) ──► EvaluationService
                                                      │
                              ┌───────────────────────┼───────────────────────┐
                              ▼                       ▼                       ▼
                     HeuristicEvaluator      LLMJudgeEvaluator        ToolCallEvaluator
                                                 (Ollama)
                              └───────────────────────┼───────────────────────┘
                                                      ▼
                                               MultiTurnEvaluator
                                                 (Ollama)
                                                      │
                                                      ▼
                                              Evaluation saved to DB

POST /feedback/{id} ──► FeedbackService ──► Cohen's Kappa ──► routing decision
POST /suggestions/trigger ──► pattern detection ──► Ollama suggestions
POST /meta-eval/run ──► calibrate evaluators vs human annotations
```

**Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Redis, Celery, Ollama (llama3.2), Docker

---

## Local setup

**Prerequisites:** Docker, Ollama with `llama3.2` pulled

```bash
git clone git@github.com:prvn0x/agent-eval-pipeline.git
cd agent-eval-pipeline

cp .env.example .env
# edit .env if needed — defaults work out of the box

docker-compose up --build
```

API runs at `http://localhost:8000`. Swagger at `http://localhost:8000/docs`.

Pull the model if you haven't:

```bash
ollama pull llama3.2
```

**Dashboard (optional):**

```bash
pip install -r requirements-dashboard.txt
streamlit run dashboard.py
```

Opens at `http://localhost:8501`.

---

## Example request

```bash
curl -X POST http://localhost:8000/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv_001",
    "agent_version": "v1.0",
    "turns": [
      {"turn_id": 1, "role": "user", "content": "Book me a flight to Mumbai", "timestamp": "2025-01-15T10:00:00Z"},
      {"turn_id": 2, "role": "assistant", "content": "Found 3 flights.", "timestamp": "2025-01-15T10:00:02Z",
       "tool_calls": [{"tool_name": "search_flights", "parameters": {"destination": "Mumbai"}}]}
    ],
    "metadata": {"mission_completed": true}
  }'
```

```bash
# fetch the evaluation
curl http://localhost:8000/evaluations/conv_001
```

---

## Design decisions

- **Repository pattern** — services never touch SQLAlchemy directly. All DB access goes through a repository class, keeping business logic clean and testable.
- **Open/Closed Principle** — adding a new evaluator means creating one new file. The orchestrator (`EvaluationService`) never changes.
- **Strategy pattern** — each evaluator implements `BaseEvaluator` and is fully swappable. The orchestrator only knows about the interface, not the implementation.
- **Domain layer isolation** — evaluators are pure Python with zero FastAPI or SQLAlchemy imports. The web framework and database are irrelevant to scoring logic.
- **Graceful degradation** — LLM evaluators return `null` scores when Ollama or Redis is unavailable. Heuristic and tool evaluators always run regardless.
- **No URL versioning on first release** — per OpenAPI spec, `info.version` is the document version, not a URL prefix. Routes will be versioned when a breaking v2 exists.
- **Celery retries only transient exceptions** — `OperationalError`, `ConnectionError`, `TimeoutError`. Non-retryable errors fail fast and log instead of retrying indefinitely.
