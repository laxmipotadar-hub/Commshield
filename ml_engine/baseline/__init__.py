"""Baseline management and training for CommShield."""

from .trainer import (
    SLICE_TRAINING_CONFIGS,
    train_all_baselines,
    train_slice_baseline,
)

__all__ = [
    "SLICE_TRAINING_CONFIGS",
    "train_slice_baseline",
    "train_all_baselines",
]
