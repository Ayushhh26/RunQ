import os
import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

DEFAULT_TOP_N = 3


def _top_n():
    return max(1, int(os.getenv("SUMMARY_TOP_N", str(DEFAULT_TOP_N))))


def split_sentences(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def summarize_document(text: str, top_n: int | None = None) -> dict:
    if top_n is None:
        top_n = _top_n()
    sentences = split_sentences(text)
    original_sentence_count = len(sentences)

    if original_sentence_count == 0:
        return {
            "summary": [],
            "original_sentence_count": 0,
            "compression_ratio": 0.0,
        }

    take = min(top_n, original_sentence_count)

    if original_sentence_count == 1:
        return {
            "summary": sentences[:1],
            "original_sentence_count": 1,
            "compression_ratio": 1.0,
        }

    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform(sentences)
    scores = np.asarray(matrix.sum(axis=1)).ravel()
    top_indices = np.argsort(scores)[::-1][:take]
    top_indices_sorted = sorted(top_indices.tolist())
    summary = [sentences[i] for i in top_indices_sorted]

    compression_ratio = take / original_sentence_count

    return {
        "summary": summary,
        "original_sentence_count": original_sentence_count,
        "compression_ratio": round(float(compression_ratio), 4),
    }
