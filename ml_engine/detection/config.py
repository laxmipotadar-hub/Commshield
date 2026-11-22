"""Detection engine configuration for CommShield.

Contains rules, thresholds, reference levels, and CUSUM parameters.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class DetectionConfig:
    """Detection engine threshold and fusion hyperparameters."""

    # Primary percentile decision threshold
    threshold_percentile: float = 95.0

    # Fusion rule: 'MAX_PERCENTILE' or 'MEAN'
    primary_fusion_rule: str = "MAX_PERCENTILE"

    # Autoencoder architecture
    ae_hidden_dim: int = 6
    ae_latent_dim: int = 3
    ae_learning_rate: float = 0.01
    ae_max_epochs: int = 100
    ae_patience: int = 10
    ae_val_split: float = 0.2

    # CUSUM hyperparameters
    cusum_reference_value: float = 75.0
    cusum_scale: float = 10.0
    cusum_alarm_threshold: float = 4.5
    cusum_reset_on_trigger: bool = True


DEFAULT_DETECTION_CONFIG = DetectionConfig()
# CommShield AI Core
