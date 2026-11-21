"""CLI runner for Stage S7: Boiling-frog attack runner and 4-way ablations."""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
backend_path = PROJECT_ROOT / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from ml_engine.evaluation.ablation_runner import BoilingFrogRunner, FourWayAblationRunner

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "ablations"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("=" * 70)
    print("Running Boiling-Frog Poisoning Test Across 3 Configurations...")
    print("=" * 70)
    frog_runner = BoilingFrogRunner()
    seeds = [42, 101, 2024, 777, 999, 123, 456, 789, 2025, 3030]

    boiling_frog_records = []
    for s in seeds:
        batches = frog_runner.generate_slow_poisoning_steps(num_steps=10, step_increment_sigma=0.35, seed=s)
        # Load anchor bundle
        four_way = FourWayAblationRunner()
        anchor_bundle = four_way.anchor_bundle

        res_a = frog_runner.run_configuration("step_only", batches, anchor_bundle)
        res_b = frog_runner.run_configuration("step_plus_budget", batches, anchor_bundle)
        res_c = frog_runner.run_configuration("full_gate", batches, anchor_bundle)

        boiling_frog_records.append({
            "seed": s,
            "step_only": res_a,
            "step_plus_budget": res_b,
            "full_gate": res_c,
        })

    with open(RESULTS_DIR / "boiling_frog_results.json", "w", encoding="utf-8") as f:
        json.dump(boiling_frog_records, f, indent=2)

    print(f"Boiling-frog results saved to {RESULTS_DIR / 'boiling_frog_results.json'}")

    print("\n" + "=" * 70)
    print("Running 4-Way Ablations Across 10 Seeds with Bootstrap CIs...")
    print("=" * 70)
    ablation_runner = FourWayAblationRunner()
    ablation_summary = ablation_runner.run_all(seeds=seeds)

    print("\nAblation Results Summary:")
    for k, v in ablation_summary.items():
        if k.startswith("ablation_"):
            print(f"- {v['name']}:")
            for sub_k, sub_v in v.items():
                if isinstance(sub_v, dict) and "mean" in sub_v:
                    print(f"    {sub_k}: mean={sub_v['mean']}, 95% CI={sub_v['ci_95']}")
            print(f"    Conclusion: {v['conclusion']}")


if __name__ == "__main__":
    main()
