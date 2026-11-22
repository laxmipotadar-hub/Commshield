"""CLI entrypoint for running the Conformal Calibration and Principled Abstention evaluation."""

import logging
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml_engine.evaluation.conformal_evaluator import ConformalAttributionBenchmark

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def main():
    benchmark = ConformalAttributionBenchmark()
    summary = benchmark.run_full_evaluation()

    print("=" * 80)
    print("CONFORMAL CALIBRATION & PRINCIPLED ABSTENTION EVALUATION COMPLETE")
    print("=" * 80)
    cov = summary["coverage_and_exchangeability"]
    print(f"Stable 1x Traffic Coverage: {cov['stable_traffic_1x']['empirical_coverage'] * 100:.1f}% (Target: {cov['stable_traffic_1x']['target_coverage'] * 100:.1f}%) - Status: {cov['stable_traffic_1x']['exchangeability_status']}")
    print(f"Scaled 2x Traffic Coverage: {cov['scaled_growth_2x']['empirical_coverage'] * 100:.1f}% (Target: {cov['scaled_growth_2x']['target_coverage'] * 100:.1f}%) - Status: {cov['scaled_growth_2x']['exchangeability_status']}")
    print(f"Scaled 3x Traffic Coverage: {cov['scaled_growth_3x']['empirical_coverage'] * 100:.1f}% (Target: {cov['scaled_growth_3x']['target_coverage'] * 100:.1f}%) - Status: {cov['scaled_growth_3x']['exchangeability_status']}")
    print("-" * 80)
    abl = summary["ablation_study"]
    print("Attack-in-Growth Ablation (Attack Recall / Abstention Rate):")
    print(f"  Rules without Conformal:   Recall = {abl['rules_without_conformal']['attack_in_growth']['attack_recall_mean']*100:.1f}%, Abstain = {abl['rules_without_conformal']['attack_in_growth']['abstention_rate_mean']*100:.1f}%")
    print(f"  Rules with Conformal:      Recall = {abl['rules_with_conformal']['attack_in_growth']['attack_recall_mean']*100:.1f}%, Abstain = {abl['rules_with_conformal']['attack_in_growth']['abstention_rate_mean']*100:.1f}%")
    print(f"  Learned without Conformal: Recall = {abl['learned_without_conformal']['attack_in_growth']['attack_recall_mean']*100:.1f}%, Abstain = {abl['learned_without_conformal']['attack_in_growth']['abstention_rate_mean']*100:.1f}%")
    print(f"  Learned with Conformal:    Recall = {abl['learned_with_conformal']['attack_in_growth']['attack_recall_mean']*100:.1f}%, Abstain = {abl['learned_with_conformal']['attack_in_growth']['abstention_rate_mean']*100:.1f}%")
    print("=" * 80)
    print("Weaknesses and Findings:")
    for w in summary["findings_and_weaknesses"]:
        print(f"- {w['issue']}: {w.get('root_cause') or w.get('limitation')}")
    print("=" * 80)


if __name__ == "__main__":
    main()

# CommShield AI Core
