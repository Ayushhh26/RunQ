"""Train TF-IDF + Linear SVM on synthetic documents; save worker classifier pickle."""
from pathlib import Path
import pickle

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

BASE = Path(__file__).resolve().parent.parent
DOCS = BASE / "documents"
MODEL_PATH = BASE / "worker-service" / "models" / "classifier.pkl"

# Labels match filename prefixes from scripts/generate_data.py
LABEL_GLOBS = [
    ("invoice", "invoice_*.txt"),
    ("resume", "resume_*.txt"),
    ("report", "report_*.txt"),
]


def load_corpus():
    texts = []
    labels = []
    for label, pattern in LABEL_GLOBS:
        for path in sorted(DOCS.glob(pattern)):
            texts.append(path.read_text(encoding="utf-8"))
            labels.append(label)
    if not texts:
        raise RuntimeError(f"No training files matched under {DOCS}")
    return texts, labels


def main():
    texts, labels = load_corpus()
    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    max_features=16384,
                    ngram_range=(1, 2),
                    min_df=1,
                    stop_words="english",
                ),
            ),
            (
                "svc",
                LinearSVC(random_state=42, dual=False, max_iter=8000),
            ),
        ]
    )
    pipeline.fit(texts, labels)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(pipeline, f)
    print(f"Wrote {MODEL_PATH} ({len(texts)} samples).")


if __name__ == "__main__":
    main()
