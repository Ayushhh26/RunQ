# RunQ

RunQ is a distributed backend that accepts document-processing jobs through an API, processes them asynchronously with Redis-backed workers, stores lifecycle/results in PostgreSQL, and exposes health, metrics, retries, and dead-letter recovery for reliability.

## Architecture

```text
Client
  └─> FastAPI (api-service)
       ├─ POST /jobs
       ├─ GET /jobs/{id}
       ├─ GET /jobs?status=&job_type=&page=&per_page=
       ├─ GET /health
       └─ GET /metrics
             │
             ├─ PostgreSQL (jobs table: lifecycle + results + retry_count)
             └─ Redis
                ├─ runq:queue (main FIFO queue)
                └─ runq:dlq (dead-letter queue)

Redis runq:queue
  └─> Worker(s) (worker-service)
       ├─ extract_metadata (spaCy NER)
       ├─ classify_document (TF-IDF + Linear SVM)
       └─ summarize_document (extractive TF-IDF sentence scoring)
```

## Tech Stack

| Layer | Technology |
| --- | --- |
| API | FastAPI |
| Queue | Redis lists (`runq:queue`, `runq:dlq`) |
| Database | PostgreSQL |
| NLP extract | spaCy `en_core_web_sm` |
| Classification | scikit-learn (`TfidfVectorizer` + `LinearSVC`) |
| Summarization | TF-IDF sentence scoring |
| Tooling | Docker Compose, Makefile |

## Current Status

Implemented through **Step 15** (MVP complete):

- Async pipeline + job lifecycle (`pending -> running -> success/failed/dead`)
- 3 job types working end-to-end
- Retries with backoff and DLQ
- Graceful shutdown + stale running-job reaper
- Job query with filters + pagination
- Health and metrics endpoints
- Structured JSON logs in API + worker
- Makefile workflow and load-testing script
- Scaling benchmark (1 vs 2 vs 4 workers)

## Quick Start

From repo root:

```bash
make generate-data
make train
make start
make test
```

Health checks:

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

Stop:

```bash
make stop
```

## Makefile Commands

- `make start` - build and start stack
- `make stop` - stop stack
- `make test` - basic API checks
- `make generate-data` - generate synthetic documents
- `make train` - train classifier and write `worker-service/models/classifier.pkl`
- `make load-test` - run load test script
- `make logs` - stream compose logs
- `make scale` - scale workers to 4

## API Reference

### Submit job

`POST /jobs`

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_type":"extract_metadata","file_path":"documents/sample_invoice.txt"}'
```

Response:

```json
{
  "job_id": "a1b2c3d4-....",
  "status": "pending"
}
```

### Get job by ID

`GET /jobs/{job_id}`

```bash
curl http://localhost:8000/jobs/<job_id>
```

### List jobs (filters + pagination)

`GET /jobs?status=&job_type=&page=&per_page=`

```bash
curl "http://localhost:8000/jobs?status=dead&page=1&per_page=20"
curl "http://localhost:8000/jobs?job_type=classify_document&page=1&per_page=10"
```

### Health

`GET /health`

Example:

```json
{
  "status": "healthy",
  "postgres": "connected",
  "redis": "connected",
  "active_workers": 1,
  "queue_depth": 0
}
```

### Metrics

`GET /metrics`

Example:

```json
{
  "total_jobs": 3023,
  "success": 3017,
  "failed": 0,
  "dead": 1,
  "success_rate": "99.8%",
  "avg_processing_time_ms": 9.02,
  "queue_depth": 0,
  "jobs_per_minute": 2000.0
}
```

## Sample Processor Outputs

`extract_metadata` (shape; entities vary by text):

```json
{
  "persons": ["..."],
  "organizations": ["..."],
  "dates": ["..."],
  "amounts": ["..."],
  "locations": ["..."]
}
```

`classify_document`:

```json
{
  "label": "invoice",
  "confidence": 0.77,
  "all_scores": {
    "invoice": 0.77,
    "resume": 0.12,
    "report": 0.11
  }
}
```

`summarize_document` (`SUMMARY_TOP_N` default `3`):

```json
{
  "summary": ["...", "...", "..."],
  "original_sentence_count": 13,
  "compression_ratio": 0.2308
}
```

## Reliability Features

- **Retries + backoff**: `1s`, `2s`, `4s` (`MAX_JOB_RETRY_ATTEMPTS=3`)
- **DLQ**: job goes to `runq:dlq` and status becomes `dead` after retry limit
- **Graceful shutdown**: worker handles `SIGTERM`/`SIGINT`, finishes current job before exit
- **Stale reaper**: startup recovery for `running` jobs older than `STALE_JOB_THRESHOLD_SECONDS`
- **Optional failure injection for testing**: `RUNQ_FORCE_FAIL_PATH`

DLQ size check:

```bash
docker compose exec redis redis-cli LLEN runq:dlq
```

## Structured Logging

API and worker emit JSON log events.

Typical fields:

- `timestamp`
- `service`
- `event`
- `job_id` (when relevant)
- `status`
- `processing_ms`
- `error`

Common events:

- API: `job_submitted`, `job_get`, `jobs_list`, validation rejections
- Worker: `job_started`, `job_success`, `job_failure`, `job_retry_scheduled`, `job_moved_to_dlq`, reaper events

## Load Test Results

Benchmark setup:

- Script: `scripts/load_test.py`
- Jobs per run: `1000`
- Job type: `classify_document`
- Inputs: `documents/invoice_*.txt`

Observed results:

- **worker=1**: elapsed `7.39s`, throughput `8123.84 jobs/min`, avg processing `7.40ms`, failure rate `0.0%`
- **worker=2**: elapsed `6.13s`, throughput `9787.46 jobs/min`, avg processing `10.46ms`, failure rate `0.0%`
- **worker=4**: elapsed `4.62s`, throughput `12987.54 jobs/min`, avg processing `9.09ms`, failure rate `0.0%`

Cross-check:

- `/metrics`: `total_jobs=3023`, `success=3017`, `dead=1`, `queue_depth=0`
- DB grouped counts matched status totals

## Design Decisions and Tradeoffs

- **Redis list queue vs RabbitMQ/Kafka**
  - Chosen: Redis list for simplicity and speed in a single-node dev setup.
  - Tradeoff: fewer advanced durability/routing features than dedicated brokers.
- **PostgreSQL as source of truth for job state**
  - Chosen for queryability, durability, and auditability.
  - Tradeoff: more DB writes than a Redis-only approach.
- **spaCy small model (`en_core_web_sm`)**
  - Chosen for CPU-friendly local execution.
  - Tradeoff: lower NER accuracy vs larger models.
- **TF-IDF + Linear SVM for classification**
  - Chosen for fast, deterministic CPU inference and simple retraining.
  - Tradeoff: less semantic power than transformer-based models.
- **Extractive TF-IDF summarization**
  - Chosen for deterministic behavior and no external dependency.
  - Tradeoff: no abstractive rewriting.
- **Backoff retries + DLQ**
  - Chosen to avoid silent loss and make failures observable.
  - Tradeoff: more state transitions and ops logic.

## What I’d Add Next

- Full automated test suite (`pytest`) for API, worker, and failure paths
- Real-time dashboards and alerting (Prometheus/Grafana)
- Persistent benchmark result artifacts + trend tracking
- Auth/rate-limits and multi-tenant queue isolation
- Optional broker abstraction (Redis/RabbitMQ)

## Notes

- `documents/` is mounted into API and worker at `/app/documents`.
- `RUNQ_FORCE_FAIL_PATH` is for local failure-path validation and should remain unset in normal runs.