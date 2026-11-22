"""Configuration thresholds and parameters for CommShield Governance Engine.

All limits, budgets, margins, and thresholds are defined centrally here
with detailed engineering rationale and references to COMMSHIELD_SPEC_v9.md.
No limits should be defined inline in governance checks or services.
"""

# -----------------------------------------------------------------------------
# 1. Normal-Holdout Backtest Limits
# -----------------------------------------------------------------------------
# Maximum permissible false-positive rate on held-out clean normal windows.
# Candidate baseline must not produce an FPR higher than this limit, ensuring
# that adapting to growth has not widened the normal decision boundary excessively.
MAX_HOLDOUT_FPR: float = 0.05

# Maximum allowable margin between candidate FPR and anchor FPR on normal holdout.
MAX_HOLDOUT_FPR_MARGIN: float = 0.02


# -----------------------------------------------------------------------------
# 2. Proportional-Growth Verification Limits
# -----------------------------------------------------------------------------
# Maximum Jensen-Shannon Divergence (JSD) permitted between active baseline composition
# and candidate adaptation window distribution. Consistent with F3 attribution threshold.
MAX_JSD_DIVERGENCE: float = 0.0350

# Maximum allowed deviation in per-UE session rate ratio (|R - 1.0| <= 0.25).
# Ensures traffic expansion is driven by additional devices rather than single-device abuse.
MAX_PER_UE_RATE_DEVIATION: float = 0.25


# -----------------------------------------------------------------------------
# 3. Canary Retention Test Limits
# -----------------------------------------------------------------------------
# Maximum permissible degradation in canary attack detection recall (delta = 5.0%).
# Candidate recall must stay within delta of anchor recall in every canary category.
CANARY_RECALL_MARGIN_DELTA: float = 0.05

# Rescaling mode for canary attacks ('proportional' vs 'fixed' vs 'fat_pipe').
# Proportional rescaling preserves scale-invariant ratio features while scaling raw counts.
# Fat-pipe mode scales volume-per-session features by k.
CANARY_SCALE_METHOD: str = "proportional"


# -----------------------------------------------------------------------------
# 4. Cumulative Drift Budget Limits (Spec Feature 4 Section C)
# -----------------------------------------------------------------------------
# Scale-invariant ratio features evaluated under proportional growth
RATIO_FEATURE_NAMES: list[str] = [
    "registrations_per_active_ue",
    "nas_failure_ratio",
    "pfcp_failure_ratio",
    "pdu_session_rate_per_ue",
    "new_ue_rate",
]
# Per-update step limit: Maximum root-mean-square robust distance between candidate
# and the currently active serving baseline: D_rms(cand, active) <= b_step.
DRIFT_BUDGET_STEP_LIMIT_B_STEP: float = 1.50

# Cumulative drift budget: Maximum root-mean-square distance from the trusted anchor
# baseline: D_rms(cand, anchor) <= B_rms. Prevents boiling-frog parameter drift.
DRIFT_BUDGET_CUMULATIVE_B_RMS: float = 2.50

# Maximum single-feature deviation: D_max(cand, anchor) <= B_max.
# Prevents single-feature shifts from being masked/diluted across multiple features.
DRIFT_BUDGET_MAX_FEATURE_B_MAX: float = 3.00

# Canary score degradation limit: Median difference in score percentiles between anchor
# and candidate on canary attack windows: Delta_can <= B_can percentiles.
DRIFT_BUDGET_CANARY_SHIFT_B_CAN: float = 10.0


# -----------------------------------------------------------------------------
# 5. Candidate Generation & Adaptation Controls
# -----------------------------------------------------------------------------
# Minimum number of consecutive legitimate (likely_benign) windows required
# to establish persistent drift before triggering shadow candidate creation.
PERSISTENT_DRIFT_THRESHOLD: int = 3

# Minimum total adaptation windows required to fit a candidate baseline.
MIN_ADAPTATION_WINDOWS: int = 5

# Dwell time in seconds required between successive baseline promotions
# to allow operational observation.
DWELL_TIME_MIN_SECONDS: int = 300

# Small epsilon added to denominator for robust z-score calculation stability.
EPSILON: float = 1e-6
# CommShield AI Core
