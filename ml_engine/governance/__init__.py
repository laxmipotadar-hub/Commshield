"""CommShield Governance Engine Package.

Provides pluggable governance checks, shadow candidate generation,
canary retention evaluation, cumulative drift budgeting, and atomic baseline management.
"""

from .base import (
    GovernanceCheck,
    GovernanceCheckResult,
    GovernanceEvaluationResult,
    GovernancePipeline,
)
from .canary import (
    evaluate_canary_retention,
    load_canary_dataset,
    rescale_canary_window,
)
from .candidate import (
    build_shadow_candidate,
    load_base_training_windows,
)
from .checks import (
    CanaryRetentionTestCheck,
    DriftBudgetCheck,
    NormalHoldoutBacktestCheck,
    ProportionalGrowthCheck,
    build_default_governance_pipeline,
)
from .config import (
    CANARY_RECALL_MARGIN_DELTA,
    CANARY_SCALE_METHOD,
    DRIFT_BUDGET_CANARY_SHIFT_B_CAN,
    DRIFT_BUDGET_CUMULATIVE_B_RMS,
    DRIFT_BUDGET_MAX_FEATURE_B_MAX,
    DRIFT_BUDGET_STEP_LIMIT_B_STEP,
    MAX_HOLDOUT_FPR,
    MAX_JSD_DIVERGENCE,
    MAX_PER_UE_RATE_DEVIATION,
    PERSISTENT_DRIFT_THRESHOLD,
)
from .naive_adapter import naive_retrain_on_drift

__all__ = [
    "GovernanceCheck",
    "GovernanceCheckResult",
    "GovernanceEvaluationResult",
    "GovernancePipeline",
    "NormalHoldoutBacktestCheck",
    "ProportionalGrowthCheck",
    "CanaryRetentionTestCheck",
    "DriftBudgetCheck",
    "build_default_governance_pipeline",
    "build_shadow_candidate",
    "load_base_training_windows",
    "evaluate_canary_retention",
    "load_canary_dataset",
    "rescale_canary_window",
    "naive_retrain_on_drift",
    "MAX_HOLDOUT_FPR",
    "MAX_JSD_DIVERGENCE",
    "MAX_PER_UE_RATE_DEVIATION",
    "CANARY_RECALL_MARGIN_DELTA",
    "DRIFT_BUDGET_STEP_LIMIT_B_STEP",
    "DRIFT_BUDGET_CUMULATIVE_B_RMS",
    "DRIFT_BUDGET_MAX_FEATURE_B_MAX",
    "DRIFT_BUDGET_CANARY_SHIFT_B_CAN",
    "PERSISTENT_DRIFT_THRESHOLD",
]
