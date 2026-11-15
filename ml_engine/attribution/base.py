"""Abstract Attributor interface and extensible AttributionEngine for CommShield."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseAttributor(ABC):
    """Abstract base interface for drift attribution models.
    
    Permits plugging in rule-based attributor, sequential evidence accumulator,
    or probabilistic classifiers without changing callers or API contracts.
    """

    @abstractmethod
    def attribute(
        self,
        window: Dict[str, Any],
        baseline_bundle: Dict[str, Any],
        recent_windows: Optional[List[Dict[str, Any]]] = None,
        drift_detected: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Perform drift attribution on the current telemetry window.
        
        Args:
            window: Canonical traffic window dictionary.
            baseline_bundle: Active baseline artifact dictionary (scaler, training stats, schema).
            recent_windows: Sequence of recently evaluated windows for trend analysis.
            drift_detected: Boolean indicator from ADWIN drift tracker.
            **kwargs: Additional contextual signals (e.g. control slice telemetry, change logs).
            
        Returns:
            Dictionary matching the AttributionOutput contract.
        """
        pass


class AttributionEngine:
    """Orchestrates registered attributors, allowing runtime model selection and extensibility."""

    def __init__(self, default_attributor: Optional[BaseAttributor] = None):
        self.attributors: Dict[str, BaseAttributor] = {}
        if default_attributor is not None:
            self.register_attributor("default", default_attributor)

    def register_attributor(self, name: str, attributor: BaseAttributor) -> None:
        """Register an attributor under a designated identifier."""
        self.attributors[name] = attributor

    def get_attributor(self, name: str = "default") -> Optional[BaseAttributor]:
        """Retrieve an attributor by name."""
        return self.attributors.get(name)

    def attribute(
        self,
        window: Dict[str, Any],
        baseline_bundle: Dict[str, Any],
        recent_windows: Optional[List[Dict[str, Any]]] = None,
        drift_detected: bool = False,
        attributor_name: str = "default",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute attribution using the designated registered attributor."""
        attributor = self.get_attributor(attributor_name)
        if attributor is None:
            if not self.attributors:
                raise RuntimeError("No attributors registered in AttributionEngine.")
            # Fall back to first registered attributor
            attributor = next(iter(self.attributors.values()))

        return attributor.attribute(
            window=window,
            baseline_bundle=baseline_bundle,
            recent_windows=recent_windows,
            drift_detected=drift_detected,
            **kwargs,
        )
