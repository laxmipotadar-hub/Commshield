"""Lightweight, deterministic Isolation Forest for per-device anomaly detection.

Implements Liu, Ting, Zhou (2008) "Isolation Forest" in pure Python with guaranteed
cross-platform determinism, explicit random_state, bounded tree depth, and zero external
dependencies.
"""

import math
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Tuple, Union


def c_factor(n: int) -> float:
    """Average path length of unsuccessful search in a Binary Search Tree (BST)."""
    if n <= 1:
        return 0.0
    if n == 2:
        return 1.0
    euler_mascheroni = 0.5772156649
    return 2.0 * (math.log(n - 1) + euler_mascheroni) - (2.0 * (n - 1) / float(n))


class IsolationTreeNode:
    """Node in an Isolation Tree."""

    def __init__(
        self,
        size: int,
        feature_idx: Optional[int] = None,
        split_value: Optional[float] = None,
        left: Optional["IsolationTreeNode"] = None,
        right: Optional["IsolationTreeNode"] = None,
    ):
        self.size = size
        self.feature_idx = feature_idx
        self.split_value = split_value
        self.left = left
        self.right = right

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


class DeviceIsolationForest:
    """Deterministic Isolation Forest tailored for per-device telemetry features.
    
    Attributes:
        n_estimators: Number of isolation trees (default: 25, bounded).
        max_depth: Maximum tree depth (default: 6, preventing overfitting).
        random_state: Deterministic random seed.
    """

    def __init__(
        self,
        n_estimators: int = 25,
        max_depth: int = 6,
        random_state: int = 42,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        self.trees: List[IsolationTreeNode] = []
        self.n_features: int = 0
        self.n_train_samples: int = 0
        self.c_n: float = 1.0
        self.fitted: bool = False

    def _build_tree(
        self,
        X: List[List[float]],
        current_depth: int,
        rng: random.Random,
    ) -> IsolationTreeNode:
        """Recursively build an isolation tree."""
        n_samples = len(X)
        if current_depth >= self.max_depth or n_samples <= 1:
            return IsolationTreeNode(size=n_samples)

        # Select a random feature dimension that has varying values
        feature_indices = list(range(self.n_features))
        rng.shuffle(feature_indices)

        split_feature: Optional[int] = None
        split_val: Optional[float] = None
        min_v: float = 0.0
        max_v: float = 0.0

        for f_idx in feature_indices:
            vals = [row[f_idx] for row in X]
            f_min = min(vals)
            f_max = max(vals)
            if f_max > f_min:
                split_feature = f_idx
                min_v = f_min
                max_v = f_max
                split_val = rng.uniform(min_v, max_v)
                break

        if split_feature is None or split_val is None:
            # All features are constant in this subset
            return IsolationTreeNode(size=n_samples)

        # Partition samples
        left_X = [row for row in X if row[split_feature] < split_val]
        right_X = [row for row in X if row[split_feature] >= split_val]

        if not left_X or not right_X:
            return IsolationTreeNode(size=n_samples)

        left_node = self._build_tree(left_X, current_depth + 1, rng)
        right_node = self._build_tree(right_X, current_depth + 1, rng)

        return IsolationTreeNode(
            size=n_samples,
            feature_idx=split_feature,
            split_value=split_val,
            left=left_node,
            right=right_node,
        )

    def fit(self, X: List[List[float]]) -> "DeviceIsolationForest":
        """Fit isolation trees on benign training matrix."""
        if not X or not X[0]:
            raise ValueError("Training matrix X cannot be empty.")

        self.n_train_samples = len(X)
        self.n_features = len(X[0])
        self.c_n = c_factor(self.n_train_samples)
        if self.c_n == 0.0:
            self.c_n = 1.0

        rng = random.Random(self.random_state)
        self.trees = []

        for tree_idx in range(self.n_estimators):
            # Subsample up to 128 samples per tree if data is large
            subsample_size = min(len(X), 128)
            indices = list(range(len(X)))
            selected_idx = rng.sample(indices, subsample_size) if subsample_size < len(X) else indices
            subsample = [X[i] for i in selected_idx]

            tree_rng = random.Random(rng.getrandbits(32))
            root = self._build_tree(subsample, current_depth=0, rng=tree_rng)
            self.trees.append(root)

        self.fitted = True
        return self

    def _path_length(self, x: List[float], node: IsolationTreeNode, current_depth: int) -> float:
        """Compute path length h(x) of instance x in a single tree."""
        if node.is_leaf or node.feature_idx is None or node.split_value is None:
            return current_depth + c_factor(node.size)

        f_val = x[node.feature_idx]
        if f_val < node.split_value:
            if node.left is not None:
                return self._path_length(x, node.left, current_depth + 1)
        else:
            if node.right is not None:
                return self._path_length(x, node.right, current_depth + 1)

        return current_depth + c_factor(node.size)

    def score(self, x: List[float]) -> float:
        """Compute nonconformity anomaly score for instance x.
        
        Returns:
            float: Anomaly score in [0.0, 1.0], where higher indicates more anomalous.
        """
        if not self.fitted:
            raise RuntimeError("DeviceIsolationForest must be fitted before scoring.")
        if len(x) != self.n_features:
            raise ValueError(f"Feature length mismatch: expected {self.n_features}, got {len(x)}")

        total_path = sum(self._path_length(x, tree, 0) for tree in self.trees)
        avg_path = total_path / float(len(self.trees))

        # s(x, n) = 2^(- avg_path / c(n))
        anomaly_score = 2.0 ** (- (avg_path / self.c_n))
        return float(max(0.0, min(1.0, anomaly_score)))

    def score_samples(self, X: List[List[float]]) -> List[float]:
        """Compute nonconformity scores for multiple feature vectors."""
        return [self.score(row) for row in X]
# CommShield AI Core
