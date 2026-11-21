"""Isolation Forest anomaly detector with benign percentile calibration."""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from sklearn.ensemble import IsolationForest

from .base import BaseDetector


class IsolationForestDetector(BaseDetector):
    """Isolation Forest anomaly detector implementing the BaseDetector interface.
    
    Computes negated score_samples (higher = more anomalous) and converts raw scores
    to a 0-100 percentile score calibrated against benign training windows.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        contamination: float = 0.05,
        random_state: int = 42,
        threshold_percentile: float = 95.0,
        **kwargs: Any,
    ):
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state
        self.threshold_percentile = threshold_percentile
        self.kwargs = kwargs

        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            **self.kwargs,
        )
        self.train_scores_: Optional[np.ndarray] = None
        self.n_train_samples_: int = 0
        self.fitted: bool = False

    def fit(self, X: np.ndarray, **kwargs: Any) -> "IsolationForestDetector":
        """Fit Isolation Forest on scaled benign feature matrix and compute calibration scores."""
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if len(X) == 0:
            raise ValueError("Cannot fit IsolationForestDetector on empty data matrix.")

        self.model.fit(X)
        # Compute raw negated scores: higher is more anomalous
        raw_scores = -self.model.score_samples(X)
        self.train_scores_ = np.sort(raw_scores)
        self.n_train_samples_ = len(self.train_scores_)
        self.fitted = True
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        """Compute raw negated anomaly score(s) for input features."""
        if not self.fitted:
            raise RuntimeError("IsolationForestDetector must be fit before calling score.")
        if X.ndim == 1:
            X = X.reshape(1, -1)

        raw_scores = -self.model.score_samples(X)
        return raw_scores

    def score_percentile(self, raw_score: float) -> float:
        """Map raw score to a 0-100 percentile score against benign training distribution with tie-handling."""
        if not self.fitted or self.train_scores_ is None or self.n_train_samples_ == 0:
            raise RuntimeError("IsolationForestDetector must be fit before computing percentile.")

        count_less = int(np.searchsorted(self.train_scores_, raw_score, side="left"))
        count_equal = int(np.searchsorted(self.train_scores_, raw_score, side="right")) - count_less
        percentile = ((float(count_less) + 0.5 * float(count_equal)) / float(self.n_train_samples_)) * 100.0
        return float(np.clip(round(percentile, 4), 0.0, 100.0))

    def evaluate_sample(self, x: np.ndarray) -> Tuple[float, float, bool]:
        """Evaluate a single feature sample.
        
        Returns:
            Tuple of (raw_score_negated, benign_percentile, is_flagged)
        """
        raw_score = float(self.score(x)[0])
        percentile = self.score_percentile(raw_score)
        is_flagged = bool(percentile >= self.threshold_percentile)
        return raw_score, percentile, is_flagged
