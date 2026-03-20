# Scaling Strategy

Current architecture handles ~1,000 conversations/minute on a single Celery worker. Here's how it scales.

---

## Current Bottlenecks

| Component | Bottleneck | Current limit |
|-----------|-----------|---------------|
| Celery worker | Single process, sequential evaluators | ~50 evals/min per worker |
| LLM evaluator | Ollama HTTP call, synchronous per turn | ~2–5s per conversation |
| PostgreSQL | Single writer, no read replicas | ~500 writes/s |
| Redis | Single instance, no clustering | ~100k ops/s (not a bottleneck yet) |

---

## 10x Load (~10,000 conversations/minute)

**Add Celery workers horizontally**
```bash
docker-compose scale worker=10
```
No code changes needed. Celery distributes tasks across workers automatically. Each worker runs all four evaluators per task.

**Run evaluators concurrently within a task**
Replace the sequential `for evaluator in self._evaluators` loop with `asyncio.gather`. This cuts per-conversation latency from ~5s to ~1.5s for LLM-heavy workloads.

**PostgreSQL connection pooling**
Increase `pool_size` and `max_overflow` in `create_async_engine`. Add PgBouncer in front of Postgres to multiplex connections from multiple workers.

**Separate queues per evaluator type**
Route LLM-heavy evaluations to dedicated workers, heuristic-only evaluations to lighter workers. Celery already has 3 queues configured (`evaluations`, `self_updater`, `meta_eval`).

---

## 100x Load (~100,000 conversations/minute)

**Replace Redis with Kafka**
Redis Streams work up to ~50k msg/s. Beyond that, Kafka handles millions of messages/minute with consumer groups, replay, and durable partitioned storage. Celery supports Kafka via `kombu`.

**PostgreSQL read replicas**
Evaluation reads (`GET /evaluations/{id}`) hit a read replica. Writes go to primary. Add a replica with `async_engine = create_async_engine(READ_REPLICA_URL)` for query services.

**Batch LLM scoring**
Instead of one Ollama call per conversation, batch 10–20 conversations into a single prompt and parse the array response. Reduces HTTP overhead and model cold-start cost by ~80%.

**Async evaluators with `asyncio.gather`**
```python
results = await asyncio.gather(*[ev.evaluate(conversation) for ev in self._evaluators])
```
Cuts wall-clock time per evaluation by running all four evaluators in parallel.

**Shard PostgreSQL by `agent_version`**
Each agent version writes to its own schema or database. Horizontal partitioning keeps table sizes manageable at scale.

**Cache evaluation results in Redis**
LLM judge results are already cached. Extend caching to heuristic scores — same conversation re-ingested doesn't re-evaluate.

---

## Production Checklist (beyond prototype)

- [ ] Alembic migrations instead of `create_all` — safe schema evolution without downtime
- [ ] Dead-letter queue for failed Celery tasks — failed evaluations don't silently disappear
- [ ] Rate limiting on `POST /conversations` — prevent burst ingestion from overwhelming the queue
- [ ] Structured logging with correlation IDs — trace a conversation through ingestion → evaluation → suggestions
- [ ] Prometheus metrics on evaluator latency, queue depth, failure rates
- [ ] Horizontal pod autoscaling (HPA) on worker CPU — Kubernetes scales workers automatically under load
