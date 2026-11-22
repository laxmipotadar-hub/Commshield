"""Abstract Detector interface for CommShield anomaly detection engine."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import numpy as np


class BaseDetector(ABC):
    """Abstract base detector interface.
    
    Permits plugging in Isolation Forest, Autoencoder, CUSUM, or other detectors
    without altering detection engine callers or API contracts.
    """

    @abstractmethod
    def fit(self, X: np.ndarray, **kwargs: Any) -> "BaseDetector":
        """Fit detector on benign reference feature matrix.
        
        Args:
            X: 2D numpy array of shape (n_samples, n_features).
            **kwargs: Additional detector-specific hyperparameters.
        """
        pass

    @abstractmethod
    def score(self, X: np.ndarray) -> np.ndarray:
        """Compute raw anomaly score(s) for feature vectors.
        
        Args:
            X: 2D numpy array of shape (n_samples, n_features).
            
        Returns:
            1D numpy array of raw scores (higher indicates more anomalous).
        """
        pass

    @abstractmethod
    def score_percentile(self, raw_score: float) -> float:
        """Map raw score to a 0-100 percentile score against the benign reference distribution.
        
        Args:
            raw_score: Raw detector anomaly score.
            
        Returns:
            Percentile score in the closed interval [0.0, 100.0].
        """
        pass
# CommShield AI Core
