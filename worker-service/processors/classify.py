import pickle
from pathlib import Path

import numpy as np

_pipeline = None


def _model_path() -> Path:
    return Path(__file__).resolve().parent.parent / "models" / "classifier.pkl"


def preload_classifier():
    global _pipeline
    if _pipeline is None:
        path = _model_path()
        if not path.is_file():
            raise FileNotFoundError(
                f"Classifier model not found at {path}. Run: python scripts/train_classifier.py"
            )
        with open(path, "rb") as f:
            _pipeline = pickle.load(f)


def _softmax(vec):
    x = np.asarray(vec, dtype=float)
    x = x - np.max(x)
    e = np.exp(x)
    return e / np.sum(e)


def classify_document(text: str) -> dict:
    preload_classifier()
    pipeline = _pipeline
    label = pipeline.predict([text])[0]
    decisions = pipeline.decision_function([text])[0]
    probs = _softmax(decisions)
    classes = pipeline.classes_
    all_scores = {str(classes[i]): float(probs[i]) for i in range(len(classes))}
    confidence = float(np.max(probs))
    return {
        "label": str(label),
        "confidence": confidence,
        "all_scores": all_scores,
    }
