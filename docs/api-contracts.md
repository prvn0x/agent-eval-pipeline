# API Contracts

Base URL: `/`

> No URL versioning on first release — per OpenAPI spec, `info.version` tracks the document
> version. URL versioning is introduced only when breaking changes require multiple versions
> to coexist simultaneously.

---

## Ingestion

### POST /conversations
Ingest a single conversation for evaluation.

**Request:**
```json
{
  "conversation_id": "conv_abc123",
  "agent_version": "v1.0",
  "turns": [
    {
      "turn_id": 1,
      "role": "user",
      "content": "Book me a flight to Mumbai",
      "timestamp": "2025-01-15T10:00:00Z"
    },
    {
      "turn_id": 2,
      "role": "assistant",
      "content": "Found 3 flights.",
      "timestamp": "2025-01-15T10:00:02Z",
      "tool_calls": [
        { "tool_name": "search_flights", "parameters": { "destination": "Mumbai" } }
      ]
    }
  ],
  "metadata": { "mission_completed": true, "total_latency_ms": 1200 }
}
```

**Response:** `201 Created`
```json
{
  "conversation_id": "conv_abc123",
  "status": "PENDING",
  "message": "Queued for evaluation"
}
```

### POST /conversations/batch
Bulk ingest conversations.

**Request:** `{ "conversations": [...] }`

**Response:** `201 Created`
```json
{
  "accepted": 3,
  "conversation_ids": ["conv_1", "conv_2", "conv_3"]
}
```

---

## Evaluation

### GET /evaluations/{conversation_id}
Fetch evaluation report for a conversation.

**Response:** `200 OK`
```json
{
  "evaluation_id": "eval_abc12345",
  "conversation_id": "conv_abc123",
  "overall_score": 0.87,
  "response_quality": 0.90,
  "tool_accuracy": 0.95,
  "coherence": 0.85,
  "tool_evaluation": {
    "execution_success": true,
    "total_tools": 1,
    "tool_failures": 0,
    "selection_accuracy": 1.0,
    "parameter_accuracy": 0.95
  },
  "issues_detected": [
    {
      "type": "parameter_hallucination",
      "severity": "warning",
      "description": "Tool 'search_flights' has parameters not grounded in conversation: date"
    }
  ],
  "improvement_suggestions": [],
  "evaluator_scores": {
    "heuristic": 0.75,
    "llm_judge": 0.90,
    "tool_call": 0.95,
    "multi_turn": 0.88
  },
  "created_at": "2025-01-15T10:00:05Z"
}
```

---

## Feedback

### POST /feedback/{conversation_id}
Submit human annotations for a conversation.

**Request:**
```json
{
  "annotator_id": "reviewer_1",
  "annotations": [
    { "type": "tool_accuracy", "label": "incorrect", "confidence": 0.95 }
  ]
}
```

**Response:** `201 Created`
```json
{
  "conversation_id": "conv_abc123",
  "annotator_id": "reviewer_1",
  "accepted": 1,
  "message": "Annotations saved"
}
```

### GET /feedback/agreement/{conversation_id}
Inter-annotator agreement stats. Requires at least 2 annotators.

**Response:** `200 OK`
```json
{
  "conversation_id": "conv_abc123",
  "cohen_kappa": 0.82,
  "agreement_level": "strong",
  "routing_decision": "auto_label",
  "annotator_count": 2,
  "label_distribution": { "incorrect": 2 }
}
```

`agreement_level`: `poor` | `fair` | `moderate` | `strong` | `perfect`

`routing_decision`: `auto_label` | `human_review`

---

## Suggestions

### POST /suggestions/trigger
Run the self-updater for an agent version. Detects recurring failure patterns across evaluations and generates improvement suggestions.

**Request:**
```json
{ "agent_version": "v1.0" }
```

**Response:** `200 OK`
```json
{
  "agent_version": "v1.0",
  "suggestions_saved": 3
}
```

### GET /suggestions?agent_version=v1.0
List improvement suggestions. `agent_version` is optional.

**Response:** `200 OK`
```json
{
  "agent_version": "v1.0",
  "total": 1,
  "suggestions": [
    {
      "id": "sug_abc12345",
      "agent_version": "v1.0",
      "pattern_type": "parameter_hallucination",
      "pattern_summary": "Tool 'search_flights' has parameters not grounded in conversation: date",
      "suggestion_text": "Tighten parameter schemas; reject calls with undeclared keys.",
      "category": "tool",
      "occurrence_count": 5,
      "created_at": "2025-01-15T10:00:00Z"
    }
  ]
}
```

`category`: `prompt` | `tool` | `training`

---

## Meta-Evaluation

### POST /meta-eval/run
Run evaluator calibration against human annotations. Persists the report and returns it.

**Response:** `201 Created`
```json
{
  "conversations_analyzed": 10,
  "overall_agreement": 0.85,
  "evaluator_calibration": [
    {
      "evaluator": "llm_judge",
      "sample_count": 10,
      "agreement_rate": 0.90,
      "false_positive_rate": 0.05,
      "false_negative_rate": 0.10
    }
  ],
  "blind_spots": [
    {
      "issue_type": "tool_accuracy",
      "human_flagged_count": 4,
      "evaluator_missed_count": 4
    }
  ],
  "run_at": "2025-01-15T10:00:00Z"
}
```

### GET /meta-eval/latest
Fetch the most recent calibration report.

**Response:** `200 OK` — same schema as above. `404` if no report exists yet.

---

## Health

### GET /health

**Response:** `200 OK`
```json
{
  "status": "ok",
  "version": "1.0.0",
  "llm_enabled": true
}
```
