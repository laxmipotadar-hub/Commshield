#!/usr/bin/env python3
"""Run Comparative Attribution Evaluation: Rules vs Learned Attributor.

Saves structured JSON results to experiments/results/attribution/learned_vs_rules_summary.json
and prints formatted comparative performance tables with bootstrap confidence intervals.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml_engine.evaluation.attribution_evaluator import run_comparative_attribution_evaluation


def main():
    print("=" * 80)
    print("      COMM-SHIELD DRIFT ATTRIBUTION EVALUATION: RULES VS LEARNED")
    print("=" * 80)

    summary = run_comparative_attribution_evaluation()

    print("\n1. SYNTHETIC SCENARIOS (Multi-Seed Average)")
    print("-" * 80)
    print(f"{'Scenario':<20} | {'Model':<8} | {'Atk Rec':<10} | {'Atk Prec':<10} | {'Ben Rec':<10} | {'Abstain':<8}")
    print("-" * 80)

    for sc_name, sc_data in summary["synthetic_scenarios"].items():
        r = sc_data["rules"]
        l = sc_data["learned"]
        print(f"{sc_name:<20} | Rules    | {r['attack_recall_mean']:<10.1%} | {r['attack_precision_mean']:<10.1%} | {r['benign_recall_mean']:<10.1%} | {r['abstain_rate_mean']:<8.1%}")
        print(f"{'':<20} | Learned  | {l['attack_recall_mean']:<10.1%} | {l['attack_precision_mean']:<10.1%} | {l['benign_recall_mean']:<10.1%} | {l['abstain_rate_mean']:<8.1%}")
        print("-" * 80)

    print("\n2. HELD-OUT REAL 5G-NIDD FAMILY")
    print("-" * 80)
    print(f"{'Scenario':<24} | {'Model':<8} | {'Atk Rec':<10} | {'Atk Prec':<10} | {'Ben Rec':<10} | {'Abstain':<8}")
    print("-" * 80)
    for sc_name, sc_data in summary["held_out_real_family"].items():
        r_atk = sc_data["rules"]["attack_class"]["recall"]["point_estimate"]
        r_pre = sc_data["rules"]["attack_class"]["precision"]["point_estimate"]
        r_ben = sc_data["rules"]["benign_class"]["recall"]["point_estimate"]
        r_abs = sc_data["rules"]["abstain_rate"]

        l_atk = sc_data["learned"]["attack_class"]["recall"]["point_estimate"]
        l_pre = sc_data["learned"]["attack_class"]["precision"]["point_estimate"]
        l_ben = sc_data["learned"]["benign_class"]["recall"]["point_estimate"]
        l_abs = sc_data["learned"]["abstain_rate"]

        print(f"{sc_name:<24} | Rules    | {r_atk:<10.1%} | {r_pre:<10.1%} | {r_ben:<10.1%} | {r_abs:<8.1%}")
        print(f"{'':<24} | Learned  | {l_atk:<10.1%} | {l_pre:<10.1%} | {l_ben:<10.1%} | {l_abs:<8.1%}")
        print("-" * 80)

    print("\n3. WHERE THE LEARNED MODEL IS WORSE THAN RULES")
    print("-" * 80)
    for item in summary["where_learned_is_worse"]:
        print(f"- [{item['domain'].upper()}] {item['scenario']}: {item['metric']} dropped by {item['delta']:.1%} (Rules: {item['rules']:.1%}, Learned: {item['learned']:.1%})")
        print(f"  Reason: {item['reason']}")

    print("=" * 80)
    print(f"Results saved to: experiments/results/attribution/learned_vs_rules_summary.json\n")


if __name__ == "__main__":
    main()

# CommShield AI Core
