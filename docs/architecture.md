# Architecture — AI Agent Evaluation Pipeline

## System Overview

An async evaluation pipeline that ingests multi-turn AI agent conversations, scores them across four dimensions, collects human annotations, detects recurring failure patterns, and calibrates its own evaluators against human labels.

---

## Architecture Diagram

```
                    ┌──────────────────────┐
                    │    FastAPI Gateway    │  ← Swagger UI (/docs)
                    └──────────┬───────────┘
                               │
          ┌──────────┬─────────┼──────────┬──────────────┐
          │          │         │          │              │
   ┌──────▼───┐ ┌────▼────┐ ┌──▼──────┐ ┌▼───────────┐ ┌▼──────────┐
   │Ingest API│ │Eval API │ │Feedback │ │Suggestions │ │Meta-Eval  │
   │          │ │         │ │   API   │ │    API     │ │    API    │
   └──────┬───┘ └────┬────┘ └──┬──────┘ └┬───────────┘ └┬──────────┘
          │          │         │          │              │
          └────┬─────┘         └────┬─────┴──────────────┘
               │                   │
        ┌──────▼──────┐     ┌──────▼──────────────────────────┐
        │ Redis Queue │     │           PostgreSQL              │
        │  + Cache    │     │  conversations | evaluations      │
        └──────┬──────┘     │  annotations  | agreement_records│
               │            │  suggestions  | meta_eval_reports │
        ┌──────▼──────┐     └──────────────────────────────────┘
        │   Celery    │              ▲
        │   Worker    │              │ write results
        └──────┬──────┘              │
               │                    │
     ┌─────────┼──────────┐         │
     │         │          │         │
┌────▼───┐ ┌───▼────┐ ┌───▼──────┐  │
│  LLM   │ │  Tool  │ │Heuristic │──┘
│ Judge  │ │  Call  │ │+MultiTurn│
│(Ollama)│ │        │ │          │
└────────┘ └────────┘ └──────────┘

POST /suggestions/trigger ──► Pattern Detector ──► Ollama ──► suggestions table
POST /meta-eval/run       ──► Calibrator ──► meta_eval_reports table
```

---

## Layer Responsibilities

### API Layer (`app/api/routes/`)
Thin controllers only — request validation via Pydantic, delegates immediately to the service layer. No business logic.

### Service Layer (`app/services/`)
Orchestrates domain logic and handles transactions. Publishes tasks to the Redis queue (or runs evaluation inline when `SYNC_EVAL=true`).

### Domain Layer (`app/domain/`)
Core business logic — evaluators, Cohen's Kappa, pattern detection, suggestion generation, calibration. Zero dependencies on FastAPI or SQLAlchemy. Fully unit testable in isolation.

### Repository Layer (`app/db/repositories/`)
All DB access behind repository classes. Services never touch SQLAlchemy directly. Swapping the database doesn't touch service or domain code.

### Worker Layer (`app/worker/`)
Celery tasks for async evaluation processing. Retries only transient exceptions (`OperationalError`, `ConnectionError`, `TimeoutError`) with exponential backoff. Non-retryable errors fail fast.

---

## Data Flow

### Async path (local with Celery)
```
POST /conversations
  → validate schema (Pydantic)
  → persist conversation (status: PENDING)
  → push task to Redis queue
  → return 201 + conversation_id

Celery worker picks up task:
  → run HeuristicEvaluator
  → run LLMJudgeEvaluator    (Ollama, Redis-cached)
  → run ToolCallEvaluator
  → run MultiTurnEvaluator   (Ollama)
  → aggregate scores
  → persist evaluation result
  → update status: COMPLETED
```

### Sync path (Render — no Celery)
```
POST /conversations (SYNC_EVAL=true)
  → validate schema
  → persist conversation
  → run all evaluators inline (same request)
  → persist evaluation result
  → return 201
```

### Batch path
```
POST /conversations/batch
  → validate all items
  → ingest each conversation sequentially
  → return 201 + list of conversation_ids
```

---

## Evaluation Pipeline

```
EvaluationService.run()
    │
    ├── HeuristicEvaluator    — latency, empty responses, tool failures, mission completion
    ├── LLMJudgeEvaluator     — quality, helpfulness, factuality (Ollama / llama3.2, Redis-cached)
    ├── ToolCallEvaluator     — parameter hallucination, selection accuracy, schema adherence
    └── MultiTurnEvaluator    — coherence, consistency, context retention (Ollama / llama3.2)
```

Evaluators run sequentially. LLM responses are cached in Redis by `conversation_id` to avoid redundant Ollama calls. Each evaluator returns a score (0.0–1.0) and a list of detected issues; the orchestrator aggregates them into `overall_score`.

---

## Self-Updating Engine

Triggered on-demand via `POST /suggestions/trigger`.

```
SelfUpdaterService.run(agent_version)
  → fetch all evaluations for agent_version that have detected issues
  → PatternDetector groups issues by type, filters by min_occurrences (default: 3)
  → generate_suggestions() sends patterns to Ollama for actionable fixes
  → falls back to rule-based suggestions if Ollama unavailable
  → persist to improvement_suggestions table
```

Suggestions are categorised as `prompt` (fix system prompt/few-shot examples), `tool` (fix tool schemas/selection logic), or `training` (flag for fine-tuning/RLHF).

---

## Meta-Evaluation

Triggered on-demand via `POST /meta-eval/run`.

```
MetaEvalService.run()
  → fetch conversations that have both an Evaluation and an AgreementRecord
  → for each: compare evaluator verdict (score >= 0.7) vs human routing_decision
  → compute per-evaluator: agreement_rate, false_positive_rate, false_negative_rate
  → detect blind spots: annotation types humans flagged that evaluators missed
  → persist to meta_eval_reports table
```

---

## API Versioning

Routes are unversioned (`/conversations`, `/evaluations`, etc.) per OpenAPI spec — `info.version` tracks the document version, not the URL. URL versioning is introduced only when breaking changes require multiple versions to coexist simultaneously.
