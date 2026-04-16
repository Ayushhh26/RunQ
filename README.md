# RunQ

Distributed job processing system with async workers, Redis queueing, and PostgreSQL-backed job state.

## Current Status

Implemented through Step 7:

- Step 0: Dockerized API, worker, Redis, and Postgres
- Step 1: Database schema + service-local DB/config modules
- Step 2: `POST /jobs` and `GET /jobs/{job_id}`
- Step 2.5: Sample document mounting for API/worker
- Step 3: Worker queue consumption with lifecycle updates (`pending -> running -> success/failed`)
- Step 4: Synthetic document generator (`scripts/generate_data.py`) producing 150 docs
- Step 5: **`extract_metadata`** uses spaCy `en_core_web_sm` NER (`worker-service/processors/extract.py`); output keys: `persons`, `organizations`, `dates`, `amounts`, `locations`
- Step 6: **`classify_document`** uses TF-IDF + Linear SVM (`worker-service/processors/classify.py`); train with `scripts/train_classifier.py` → `worker-service/models/classifier.pkl`
- Step 7: **`summarize_document`** uses extractive TF-IDF sentence scoring (`worker-service/processors/summarize.py`); default top 3 segments
- Next (per plan): retries + DLQ (Step 8), graceful shutdown + stale reaper (Step 9), filtered job list + metrics + logging, Makefile, load tests

## Tech Stack

- API: FastAPI
- Queue: Redis list (`runq:queue`)
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