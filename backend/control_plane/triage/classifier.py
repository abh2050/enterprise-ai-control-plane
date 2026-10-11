"""classifier_v1: TF-IDF plus logistic regression, calibrated on the development set.

Training uses the classifier training split only. Probability calibration (sigmoid, one
vs rest) is fit on the development split with the trained model frozen.
"""

from __future__ import annotations

import hashlib
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from control_plane.triage.dataset import REPO_ROOT, Case

MODEL_DIR = REPO_ROOT / "artifacts" / "models"
HYPERPARAMS = {
    "word_ngrams": (1, 2),
    "char_ngrams": (2, 5),
    "C": 10.0,
    "max_iter": 3000,
    "calibration": "sigmoid",
}


@dataclass(frozen=True)
class Prediction:
    label: str
    prob: float


class Classifier:
    def __init__(self, model: CalibratedClassifierCV) -> None:
        self._model = model
        self.labels: list[str] = [str(c) for c in model.classes_]

    def predict(self, texts: list[str]) -> list[Prediction]:
        probs = self._model.predict_proba(texts)
        idx = np.argmax(probs, axis=1)
        return [Prediction(self.labels[i], float(probs[row, i])) for row, i in enumerate(idx)]


def train(train_cases: list[Case], dev_cases: list[Case]) -> Classifier:
    features = FeatureUnion(
        [
            ("word", TfidfVectorizer(ngram_range=HYPERPARAMS["word_ngrams"], sublinear_tf=True)),
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb", ngram_range=HYPERPARAMS["char_ngrams"], sublinear_tf=True
                ),
            ),
        ]
    )
    base = Pipeline(
        [
            ("features", features),
            ("lr", LogisticRegression(C=HYPERPARAMS["C"], max_iter=HYPERPARAMS["max_iter"])),
        ]
    )
    base.fit([c.text for c in train_cases], [c.label for c in train_cases])
    calibrated = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid")
    calibrated.fit([c.text for c in dev_cases], [c.label for c in dev_cases])
    return Classifier(calibrated)


def save(clf: Classifier, name: str) -> tuple[Path, str]:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    path = MODEL_DIR / f"{name}.pkl"
    data = pickle.dumps(clf._model)
    path.write_bytes(data)
    return path, hashlib.sha256(data).hexdigest()


def load(name: str, expected_sha256: str) -> Classifier:
    """Load only a model this repository trained, verified by its recorded hash."""
    data = (MODEL_DIR / f"{name}.pkl").read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha256:
        raise ValueError(f"model {name} hash {digest} does not match {expected_sha256}")
    return Classifier(pickle.loads(data))  # noqa: S301 (hash-verified local artifact)
