"""Pluggable governance interfaces and execution pipeline for CommShield.

Defines the abstract GovernanceCheck interface and GovernancePipeline orchestrator,
ensuring additional policy constraints, audit rules, or automated checks can be registered
modularly without modifying upstream or downstream callers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class GovernanceCheckResult:
    """Standardized output of an individual governance evaluation check."""
    name: str
    passed: bool
    mandatory: bool
    metrics: Dict[str, Any]
    explanation: str


@dataclass
class GovernanceEvaluationResult:
    """Comprehensive evaluation outcome from running a GovernancePipeline."""
    candidate_id: str
    slice_id: str
    overall_passed: bool
    all_mandatory_passed: bool
    check_results: List[GovernanceCheckResult]
    decision_trace_steps: List[Dict[str, Any]]
    gate_metrics: Dict[str, Any]


class GovernanceCheck(ABC):
    """Abstract base class for all pluggable CommShield governance checks."""

    name: str = "base_check"
    mandatory: bool = True

    @abstractmethod
    def evaluate(
        self,
        candidate_bundle: Dict[str, Any],
        active_bundle: Dict[str, Any],
        anchor_bundle: Dict[str, Any],
        context: Dict[str, Any],
    ) -> GovernanceCheckResult:
        """Evaluate a shadow candidate against active and anchor baselines.

        Args:
            candidate_bundle: Artifact bundle and parameters of shadow candidate.
            active_bundle: Currently active serving baseline bundle.
            anchor_bundle: Immutable trusted anchor baseline bundle.
            context: Supplemental context containing holdout windows, canaries,
                     and adaptation window histories.

        Returns:
            GovernanceCheckResult with status, metrics, and plain-language explanation.
        """
        pass


class GovernancePipeline:
    """Executes registered governance checks in sequential order."""

    def __init__(self, checks: Optional[List[GovernanceCheck]] = None):
        self.checks: List[GovernanceCheck] = list(checks) if checks else []

    def register(self, check: GovernanceCheck) -> None:
        """Register a new check at the end of the pipeline."""
        self.checks.append(check)

    def evaluate(
        self,
        candidate_bundle: Dict[str, Any],
        active_bundle: Dict[str, Any],
        anchor_bundle: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> GovernanceEvaluationResult:
        """Execute all registered checks sequentially and aggregate outcomes."""
        ctx = context or {}
        candidate_id = str(candidate_bundle.get("candidate_id", "candidate"))
        slice_id = str(candidate_bundle.get("slice_id", active_bundle.get("slice_id", "unknown")))

        check_results: List[GovernanceCheckResult] = []
        decision_steps: List[Dict[str, Any]] = []
        gate_metrics: Dict[str, Any] = {}
        all_mandatory_passed = True
        overall_passed = True

        for check in self.checks:
            try:
                res = check.evaluate(
                    candidate_bundle=candidate_bundle,
                    active_bundle=active_bundle,
                    anchor_bundle=anchor_bundle,
                    context=ctx,
                )
            except Exception as e:
                res = GovernanceCheckResult(
                    name=check.name,
                    passed=False,
                    mandatory=check.mandatory,
                    metrics={"error": str(e)},
                    explanation=f"Check {check.name} encountered an unexpected execution error: {e}",
                )

            check_results.append(res)
            gate_metrics[res.name] = {
                "passed": res.passed,
                "mandatory": res.mandatory,
                "metrics": res.metrics,
                "explanation": res.explanation,
            }

            decision_steps.append({
                "step_name": f"check_{res.name}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "PASSED" if res.passed else "FAILED",
                "mandatory": res.mandatory,
                "details": {
                    "metrics": res.metrics,
                    "explanation": res.explanation,
                },
            })

            if res.mandatory and not res.passed:
                all_mandatory_passed = False
            if not res.passed:
                overall_passed = False

        gate_metrics["all_mandatory_passed"] = all_mandatory_passed
        gate_metrics["overall_passed"] = overall_passed

        return GovernanceEvaluationResult(
            candidate_id=candidate_id,
            slice_id=slice_id,
            overall_passed=overall_passed,
            all_mandatory_passed=all_mandatory_passed,
            check_results=check_results,
            decision_trace_steps=decision_steps,
            gate_metrics=gate_metrics,
        )
# CommShield AI Core
