# RunQ

Distributed job processing system with async workers, Redis queueing, and PostgreSQL-backed job state.

## Current Status

Implemented through Step 9:

- Step 0: Dockerized API, worker, Redis, and Postgres
- Step 1: Database schema + service-local DB/config modules
- Step 2: `POST /jobs` and `GET /jobs/{job_id}`
- Step 2.5: Sample document mounting for API/worker
- Step 3: Worker queue consumption with lifecycle updates (`pending -> running -> success/failed`)
- Step 4: Synthetic document generator (`scripts/generate_data.py`) producing 150 docs
- Step 5: **`extract_metadata`** uses spaCy `en_core_web_sm` NER (`worker-service/processors/extract.py`); output keys: `persons`, `organizations`, `dates`, `amounts`, `locations`
- Step 6: **`classify_document`** uses TF-IDF + Linear SVM (`worker-service/processors/classify.py`); train with `scripts/train_classifier.py` → `worker-service/models/classifier.pkl`
- Step 7: **`summarize_document`** uses extractive TF-IDF sentence scoring (`worker-service/processors/summarize.py`); default top 3 segments
- Step 8: **Retries + DLQ** — worker backs off **1s / 2s / 4s** between attempts, re-enqueues after up to **3** consecutive failures; a **4th** failure sets status **`dead`** and pushes the job id to Redis **`runq:dlq`**
- Step 9: **Graceful shutdown + stale reaper** — worker handles `SIGTERM`/`SIGINT` by finishing current job before exit; startup reaper re-queues `running` jobs older than `STALE_JOB_THRESHOLD_SECONDS`
- Next (per plan): filtered job list + metrics + structured logging, Makefile, load tests

## Tech Stack

- API: FastAPI
- Queue: Redis list (`runq:queue`), dead-letter list (`runq:dlq`)
- Database: PostgreSQL
- Containers: Docker Compose
- Data generation: Faker + Python scripts
- NLP (extract): spaCy `en_core_web_sm` (installed in worker image)
- ML (classify): scikit-learn TF-IDF + `LinearSVC` (model file loaded at worker startup)
- Summarization: scikit-learn TF-IDF over sentence segments (extractive)

## Quick Start

From repo root:

```bash
docker compose up --build -d
docker compose ps
```

Health checks:

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
```

## Job API (Current)

Create a job:

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_type":"extract_metadata","file_path":"documents/sample_invoice.txt"}'
```

Classify a document:

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_type":"classify_document","file_path":"documents/invoice_001.txt"}'
```

Summarize a document:

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"job_type":"summarize_document","file_path":"documents/report_001.txt"}'
```

Fetch by ID:

```bash
curl http://localhost:8000/jobs/<job_id>
```

Supported `job_type` values:

- `extract_metadata`
- `classify_document`
- `summarize_document`

### Example successful responses

**`extract_metadata`** (shape; entities vary by text):

```json
{
  "persons": ["..."],
  "organizations": ["..."],
  "dates": ["..."],
  "amounts": ["..."],
  "locations": ["..."]
}
```

**`classify_document`**:

```json
{
  "label": "invoice",
  "confidence": 0.77,
  "all_scores": { "invoice": 0.77, "resume": 0.12, "report": 0.11 }
}
```

**`summarize_document`** (default 3 sentences; override with env `SUMMARY_TOP_N` on the worker):

```json
{
  "summary": ["...", "...", "..."],
  "original_sentence_count": 13,
  "compression_ratio": 0.2308
}
```

`compression_ratio` is `len(summary) / original_sentence_count` after splitting (see Notes).

### Retries and dead-letter queue (Step 8)

- On processing failure, the worker increments **`retry_count`**, sleeps **1s → 2s → 4s** (per attempt), sets status back to **`pending`**, and **re-enqueues** the job id — up to **3** retries after failures (**4** processing tries total before the DLQ).
- After the **4th** failure, status becomes **`dead`**, the last error is stored, and the job id is pushed to **`runq:dlq`**.
- Tune worker constants in `worker-service/config.py`: **`MAX_JOB_RETRY_ATTEMPTS`**, **`RETRY_BACKOFF_SECONDS`**.
- Inspect DLQ length: `docker compose exec redis redis-cli LLEN runq:dlq`

#### Testing retries + DLQ (optional, env-gated)

1. Set **`RUNQ_FORCE_FAIL_PATH`** on the worker to a path that exists and matches what you submit (e.g. `documents/report_001.txt`). Example:

   ```bash
   export RUNQ_FORCE_FAIL_PATH=documents/report_001.txt
   docker compose up -d --build worker
   ```

2. Submit any job type for that file (e.g. `summarize_document` or `classify_document`).

3. Poll **`GET /jobs/{id}`**: expect **`retry_count`** `1 → 2 → 3` with **`pending`** between attempts, then **`dead`** after the fourth failure.

4. Confirm DLQ grows: `docker compose exec redis redis-cli LLEN runq:dlq`

5. **Unset** the variable and restart the worker when done:

   ```bash
   unset RUNQ_FORCE_FAIL_PATH
   docker compose up -d --build worker
   ```

### Graceful shutdown and stale-job recovery (Step 9)

- Worker traps `SIGTERM` / `SIGINT` and exits loop only after current in-flight job finishes.
- On startup, reaper checks for `running` jobs older than `STALE_JOB_THRESHOLD_SECONDS` (default `300`) and re-queues them.
- Reaper marks recovered jobs back to `pending` with an explanatory `error_message`, then pushes job ids back to `runq:queue`.

## Synthetic Data

Generate or regenerate corpus:

```bash
python3 scripts/generate_data.py
```

Output in `documents/`:

- `invoice_001.txt` ... `invoice_050.txt`
- `resume_001.txt` ... `resume_050.txt`
- `report_001.txt` ... `report_050.txt`

Train the classifier (after generating or updating documents):

```bash
pip install -r scripts/requirements.txt
python scripts/train_classifier.py
```

This writes `worker-service/models/classifier.pkl`. Rebuild the worker image (or restart) after retraining.

## Notes

- `documents/` is mounted into both API and worker containers at `/app/documents`.
- **`extract_metadata`** is real NER output; labels are approximate (small models can mis-tag text). **`classify_document`** uses the trained TF-IDF + SVM model. **`summarize_document`** scores per-segment TF-IDF sums where segments come from splitting on line breaks and sentence-ending punctuation—bullet lines may count as separate segments.
- Worker env **`SUMMARY_TOP_N`** (default `3`) controls how many top-scoring segments are returned for `summarize_document`.