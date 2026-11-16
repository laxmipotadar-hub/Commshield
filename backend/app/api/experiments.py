"""API endpoints for triggering and retrieving three-arm experiment benchmark results."""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ExperimentResult

router = APIRouter(prefix="/experiments", tags=["Experiments"])
logger = logging.getLogger("commshield.api.experiments")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"

# Global in-memory experiment execution status tracker
_EXPERIMENT_STATUS: Dict[str, Any] = {
    "status": "IDLE",
    "scenarios": [],
    "seeds": [],
    "progress": "No experiment has been run yet.",
    "started_at": None,
    "completed_at": None,
    "error": None,
}


class ExperimentRunRequest(BaseModel):
    scenarios: List[str] = Field(default=["stable_benign", "legitimate_growth", "slow_attack_ramp", "attack_in_growth", "mimicry_attack"])
    seeds: List[int] = Field(default=[42, 101, 2024, 777, 999])
    num_windows: int = Field(default=40, ge=10, le=100)


def _execute_experiment_task(scenarios: List[str], seeds: List[int], num_windows: int) -> None:
    """Background task executing the multi-seed three-arm benchmark."""
    global _EXPERIMENT_STATUS
    _EXPERIMENT_STATUS["status"] = "RUNNING"
    _EXPERIMENT_STATUS["scenarios"] = scenarios
    _EXPERIMENT_STATUS["seeds"] = seeds
    _EXPERIMENT_STATUS["progress"] = f"Replaying {len(scenarios)} scenarios across {len(seeds)} seeds..."
    _EXPERIMENT_STATUS["started_at"] = datetime.now(timezone.utc).isoformat()
    _EXPERIMENT_STATUS["error"] = None

    try:
        from ml_engine.evaluation.experiment import ThreeArmExperimentRunner
        runner = ThreeArmExperimentRunner()
        summary = runner.run_all(
            scenarios=scenarios,
            seeds=seeds,
            num_windows=num_windows,
            write_db=True,
        )
        _EXPERIMENT_STATUS["status"] = "COMPLETED"
        _EXPERIMENT_STATUS["progress"] = "Benchmark completed successfully across all arms."
        _EXPERIMENT_STATUS["completed_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        logger.error("Experiment background task failed: %s", e)
        _EXPERIMENT_STATUS["status"] = "FAILED"
        _EXPERIMENT_STATUS["progress"] = f"Failed with error: {e}"
        _EXPERIMENT_STATUS["error"] = str(e)


@router.post("/run")
def trigger_experiment_run(
    payload: ExperimentRunRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """Trigger the multi-seed three-arm experiment benchmark as an asynchronous background task."""
    global _EXPERIMENT_STATUS
    if _EXPERIMENT_STATUS["status"] == "RUNNING":
        raise HTTPException(
            status_code=409,
            detail="An experiment benchmark is already actively running. Check /api/experiments/status for progress.",
        )

    background_tasks.add_task(
        _execute_experiment_task,
        scenarios=payload.scenarios,
        seeds=payload.seeds,
        num_windows=payload.num_windows,
    )

    return {
        "status": "QUEUED",
        "message": "Three-arm experiment task queued successfully.",
        "scenarios": payload.scenarios,
        "seeds": payload.seeds,
        "num_windows": payload.num_windows,
    }


@router.get("/status")
def get_experiment_status() -> Dict[str, Any]:
    """Retrieve the real-time execution status and progress of the experiment benchmark."""
    return _EXPERIMENT_STATUS


@router.get("/results")
def get_all_experiment_results(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve the aggregated multi-seed experiment benchmark results across all scenarios."""
    summary_file = RESULTS_DIR / "experiment_summary.json"
    if summary_file.is_file():
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Error reading summary file: %s", e)

    # Fallback: Query from experiment_results DB table
    rows = db.query(ExperimentResult).all()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No experiment benchmark results found. Run /api/experiments/run or execute experiments/run_experiments.py.",
        )

    scenarios = list(set(r.scenario for r in rows))
    seeds = list(set(r.seed for r in rows))

    return {
        "source": "database",
        "scenarios": scenarios,
        "seeds": seeds,
        "total_records": len(rows),
        "results": [
            {
                "id": r.id,
                "scenario": r.scenario,
                "seed": r.seed,
                "arm": r.arm,
                "config_version": r.config_version,
                "recall": r.recall,
                "fpr": r.fpr,
                "contamination_final": r.contamination_final,
                "adaptations_count": r.adaptations_count,
                "quarantined_count": r.quarantined_count,
                "recovery_time_windows": r.recovery_time_windows,
                "metrics": r.metrics,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in rows
        ],
    }


@router.get("/results/{scenario}")
def get_scenario_experiment_results(
    scenario: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve multi-seed benchmark results for a designated scenario."""
    # Check summary file first
    summary_file = RESULTS_DIR / "experiment_summary.json"
    if summary_file.is_file():
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                summary_data = json.load(f)
                summaries = summary_data.get("summaries", {})
                if scenario in summaries:
                    return {
                        "scenario": scenario,
                        "config_version": summary_data.get("config_version", "v1.0.0"),
                        "generated_at": summary_data.get("generated_at"),
                        "summary": summaries[scenario],
                    }
        except Exception as e:
            logger.warning("Error reading scenario from summary file: %s", e)

    # Check database
    rows = db.query(ExperimentResult).filter(ExperimentResult.scenario == scenario).all()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment results for scenario '{scenario}' not found.",
        )

    return {
        "scenario": scenario,
        "total_runs": len(rows),
        "records": [
            {
                "id": r.id,
                "seed": r.seed,
                "arm": r.arm,
                "recall": r.recall,
                "fpr": r.fpr,
                "contamination_final": r.contamination_final,
                "adaptations_count": r.adaptations_count,
                "quarantined_count": r.quarantined_count,
                "recovery_time_windows": r.recovery_time_windows,
                "metrics": r.metrics,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in rows
        ],
    }
