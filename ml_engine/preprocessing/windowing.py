"""Windowing, ratio-based feature extraction, and robust scaling for 5G Core telemetry."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import statistics
from typing import Any, Dict, List, Optional, Tuple

FEATURE_NAMES = [
    "registrations_per_active_ue",
    "nas_failure_ratio",
    "pfcp_failure_ratio",
    "pdu_session_rate_per_ue",
    "bytes_per_session",
    "packets_per_session",
    "gtpu_volume_per_ue",
    "ue_hash_entropy",
    "new_ue_rate",
]


class RobustScaler:
    """Robust feature scaler based on medians and interquartile ranges (IQR).
    
    Adheres strictly to CONTRACTS.md baseline scaler_params schema.
    Fit strictly on benign training periods with zero test leakage.
    """

    def __init__(self, feature_names: Optional[List[str]] = None):
        self.feature_names = feature_names or FEATURE_NAMES
        self.medians: Dict[str, float] = {}
        self.iqrs: Dict[str, float] = {}
        self.fitted: bool = False

    def fit(self, windows: List[Dict[str, Any]]) -> "RobustScaler":
        """Compute medians and IQRs exclusively on training windows."""
        if not windows:
            raise ValueError("Cannot fit RobustScaler on empty window list.")

        feature_values: Dict[str, List[float]] = {f: [] for f in self.feature_names}

        for w in windows:
            ratios = w.get("ratio_features", {})
            for f in self.feature_names:
                val = float(ratios.get(f, 0.0))
                feature_values[f].append(val)

        for f in self.feature_names:
            vals = sorted(feature_values[f])
            n = len(vals)
            med = statistics.median(vals)
            # Compute Q25 and Q75
            if n >= 4:
                quants = statistics.quantiles(vals, n=4)
                q25, q75 = quants[0], quants[2]
            else:
                q25 = vals[0]
                q75 = vals[-1]

            iqr = q75 - q25
            if iqr <= 1e-7:
                # If IQR is zero, fallback to std or unit scale to prevent div-by-zero
                iqr = 1.0

            self.medians[f] = round(med, 6)
            self.iqrs[f] = round(iqr, 6)

        self.fitted = True
        return self

    def transform_vector(self, ratios: Dict[str, Any]) -> Dict[str, float]:
        """Transform a single ratio_features dictionary into robust-scaled values."""
        if not self.fitted:
            raise RuntimeError("RobustScaler must be fit on training data before transform.")

        scaled: Dict[str, float] = {}
        for f in self.feature_names:
            raw_val = float(ratios.get(f, 0.0))
            med = self.medians.get(f, 0.0)
            iqr = self.iqrs.get(f, 1.0)
            scaled[f] = round((raw_val - med) / iqr, 6)
        return scaled

    def transform(self, windows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform ratio_features across windows without modifying the underlying scaler parameters."""
        if not self.fitted:
            raise RuntimeError("RobustScaler must be fit on training data before transform.")

        transformed_windows: List[Dict[str, Any]] = []
        for w in windows:
            w_copy = json.loads(json.dumps(w))
            ratios = w_copy.get("ratio_features", {})
            w_copy["scaled_features"] = self.transform_vector(ratios)
            transformed_windows.append(w_copy)

        return transformed_windows

    def to_dict(self) -> Dict[str, Any]:
        """Export parameters matching CONTRACTS.md scaler_params schema."""
        return {
            "features": self.feature_names,
            "medians": self.medians,
            "iqrs": self.iqrs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RobustScaler":
        """Reconstruct scaler from dictionary."""
        scaler = cls(feature_names=data.get("features", FEATURE_NAMES))
        scaler.medians = data.get("medians", {})
        scaler.iqrs = data.get("iqrs", {})
        scaler.fitted = bool(scaler.medians and scaler.iqrs)
        return scaler

    def save(self, file_path: str | Path) -> None:
        """Serialize scaler parameters to JSON."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, file_path: str | Path) -> "RobustScaler":
        """Load serialized scaler parameters."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


def slice_into_windows(
    per_second_events: List[Dict[str, Any]],
    window_duration_sec: int = 60,
    slice_id: str = "sst-1-sd-010203",
    nf_id: str = "UPF-01",
) -> List[Dict[str, Any]]:
    """Helper to partition raw seconds into 10s or 60s canonical windows."""
    from .adapters.synthetic import SyntheticAdapter

    if not per_second_events:
        return []

    adapter = SyntheticAdapter()
    return adapter.adapt(
        records=per_second_events,
        slice_id=slice_id,
        nf_id=nf_id,
        window_duration_sec=window_duration_sec,
    )
