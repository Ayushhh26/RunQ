from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


def _request_json(method: str, url: str, body: dict | None = None, timeout: float = 10.0) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url=url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = resp.read().decode("utf-8")
        return json.loads(payload)


def build_file_pool(documents_dir: Path, pattern: str) -> list[str]:
    files = sorted(documents_dir.glob(pattern))
    if not files:
        raise RuntimeError(f"No files matched pattern {pattern!r} in {documents_dir}")
    return [f"documents/{path.name}" for path in files]


def submit_jobs(base_url: str, job_type: str, file_pool: list[str], count: int) -> list[str]:
    job_ids = []
    for i in range(count):
        payload = {
            "job_type": job_type,
            "file_path": file_pool[i % len(file_pool)],
        }
        resp = _request_json("POST", f"{base_url}/jobs", payload)
        job_ids.append(resp["job_id"])
    return job_ids


def poll_until_complete(
    base_url: str,
    job_ids: list[str],
    poll_interval: float,
    timeout_seconds: float,
) -> dict:
    remaining = set(job_ids)
    status_counts: dict[str, int] = {}
    processing_samples: list[float] = []

    started = time.time()
    while remaining:
        if time.time() - started > timeout_seconds:
            raise TimeoutError(f"Timed out with {len(remaining)} jobs unfinished")

        finished_this_round = []
        for job_id in list(remaining):
            job = _request_json("GET", f"{base_url}/jobs/{job_id}")
            status = job["status"]
            if status in {"success", "failed", "dead"}:
                finished_this_round.append(job_id)
                status_counts[status] = status_counts.get(status, 0) + 1
                if job.get("processing_ms") is not None:
                    processing_samples.append(float(job["processing_ms"]))

        for jid in finished_this_round:
            remaining.remove(jid)

        if remaining:
            time.sleep(poll_interval)

    elapsed = time.time() - started
    total = len(job_ids)
    completed = sum(status_counts.values())
    avg_processing_ms = sum(processing_samples) / len(processing_samples) if processing_samples else 0.0
    throughput_per_min = (completed / elapsed) * 60.0 if elapsed > 0 else 0.0
    failure_rate = ((status_counts.get("failed", 0) + status_counts.get("dead", 0)) / total) * 100.0

    return {
        "total_jobs": total,
        "completed_jobs": completed,
        "status_counts": status_counts,
        "elapsed_seconds": elapsed,
        "throughput_jobs_per_min": throughput_per_min,
        "avg_processing_time_ms": avg_processing_ms,
        "failure_rate_percent": failure_rate,
    }


def main():
    parser = argparse.ArgumentParser(description="RunQ load test script")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--count", type=int, default=1000, help="Number of jobs to submit")
    parser.add_argument("--job-type", default="classify_document", help="Job type to submit")
    parser.add_argument(
        "--file-pattern",
        default="invoice_*.txt",
        help="Glob pattern under documents/ for file selection",
    )
    parser.add_argument("--poll-interval", type=float, default=0.5, help="Polling interval seconds")
    parser.add_argument("--timeout", type=float, default=900.0, help="Overall timeout seconds")
    parser.add_argument(
        "--label",
        default="",
        help="Optional label (e.g., worker=1) to annotate printed summary",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    file_pool = build_file_pool(repo_root / "documents", args.file_pattern)

    print(f"Submitting {args.count} jobs ({args.job_type}) using {len(file_pool)} source documents...")
    submit_start = time.time()
    job_ids = submit_jobs(args.base_url, args.job_type, file_pool, args.count)
    submit_elapsed = time.time() - submit_start
    print(f"Submitted {len(job_ids)} jobs in {submit_elapsed:.2f}s")

    result = poll_until_complete(
        base_url=args.base_url,
        job_ids=job_ids,
        poll_interval=args.poll_interval,
        timeout_seconds=args.timeout,
    )
    result["submit_seconds"] = submit_elapsed
    if args.label:
        result["label"] = args.label

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
