# CommShield: Final 5-Feature Specification (v9)

This is v8 with the fixes from the review built in, and it keeps the v7/v8 table format. Literature claims are mostly abstract-level until the full-text reads are done. “Not found” in a search means unverified, not absent. Items from my own background knowledge are marked (verify). Numbers like thresholds and budgets are placeholders to be set on tuning streams, and I haven’t given any as established values.

## Positioning and novelty

**Positioning:** CommShield is a telecom-native anomaly detection layer for the 5G core. It tests whether a traffic shift is explainable as proportional growth, abstains when evidence is thin, and lets a baseline change only through a canary-checked, budget-limited, approved, reversible update.

**Core question:** “Is it safe to learn from this change?”

**Novelty statement:**
We evaluate whether a 5G-core anomaly detector can avoid learning from attacks hidden in legitimate growth. It tests whether a shift is explainable as proportional scaling, uses cross-slice comparison as supporting evidence, abstains when unsure, and promotes a candidate baseline only if it keeps detecting canary attacks and stays within a distance budget of a trusted anchor. We report where it fails.

**Not novel (say so yourself):** Isolation Forest, autoencoders, SHAP, ADWIN, CUSUM, score fusion, ratio features, divergence-based composition tests, canary and regression testing, abstention, quarantine, shadow and rollback practice, explanation-based drift (E2D2), per-feature drift diagnosis (Pacheco & Pedroso). The contribution is applying them together to attack-during-growth in 5G-core data, measured honestly.

## Changes from v8

| Change | Reason |
| :--- | :--- |
| Canary retention test with rescaled canaries and a separate canary set | Replaying old attacks at old volume punishes legitimate adaptation, and reusing test attacks inflates results |
| Drift budget uses ratio features, a per-feature cap and a canary-score measure, with re-anchoring | An RMS over medians dilutes single-feature shifts, ignores shape, and legitimate growth eventually exhausts it |
| Proportional-growth test with a benign-vs-benign null threshold and small-count smoothing | A bare divergence threshold is arbitrary |
| Control slice demoted to supporting evidence, reported separately for lab and simulated slices | Circular if slice 2 is built to be stable |
| Fusion rule fixed a priori, both variants reported | Benign data can’t measure recall, delay or evasion |
| Context baselines limited to hour and day, off by default | UE-count buckets can be inflated by an attacker and absorb the growth signal |
| One drift detector (ADWIN) plus CUSUM for score accumulation | Removes the duplicate detector |
| “Four streams plus one stress test” | The mimicry case is a stress test, not a core scenario |
| Separate tuning and test streams | Budgets and thresholds must not be tuned on the test data |

## Architecture

```
5. Operator layer:   replay dashboard, decision traces, approvals
4. Governance layer: attribution, quarantine, shadow candidate, canary test,
                     budgets, approval, versioning, atomic rollback
3. Detection engine: IF + autoencoder, percentile scoring, CUSUM,
                     ADWIN, explainers
2. Canonical model:  windows keyed by (slice, NF, time),
                     ratio features, change-event log
1. Telemetry adapters (only network-specific part):
                     5G-NIDD flows | Open5GS logs/PCAP | real-growth trace | [private 5G] | [6G]
```

Layers 3 to 5 see only the canonical schema.
UE identifiers are hashed in the adapter. Detectors never see them, and only aggregate statistics (entropy, new-UE rate) reach later layers.

---

## Feature 1: Per-Slice Baseline Learning

| Field | Description |
| :--- | :--- |
| **What it does** | Learns normal behaviour per slice and NF, and stores it as a versioned, atomic baseline package |
| **How** | Aggregate flows and testbed telemetry into windows (10s and 60s, plus a 5-minute scale for CUSUM). Key by (slice, NF). Train on benign data only with a chronological split. Log-transform and robust-scale. Set thresholds on benign validation data. Package model, scaler, schema, thresholds and training window together, so rollback restores all of them |
| **What’s in it [Must]** | Ratio and rate features (registrations per active UE, NAS and PFCP failure ratios, PDU-session rate per UE, bytes and packets per session, GTP-U volume per UE, flow length and inter-arrival stats). Immutable trusted anchor. Global fallback for slices with little data. Baseline registry. Change-event log |
| **What’s in it [Should]** | Time-of-day context: separate expected levels for hour-of-day and day-of-week buckets, which an attacker can’t influence. Real lab slices in Open5GS + UERANSIM with different UE groups (S-NSSAI configuration is supported by both (verify in their docs)) |
| **Context caveat** | UE-count or traffic-quantile buckets are off by default. An attacker who inflates UE counts also inflates the expected value, and conditioning on volume absorbs the growth signal that F3 uses. Enable only as a tested option, and only if the data has those fields and enough windows per bucket |
| **Algorithms** | Robust scaling (median/IQR), log transform |
| **Data** | 5G-NIDD benign (about 477,737 of 1,215,890 flows per papers using it, to be verified), own testbed runs, synthetic slices as fallback |
| **Novelty** | Low. Ratio and context-aware preprocessing exist. New part: telecom keying plus atomic, anchored baselines that F4 governs |
| **Gap filled** | Generic tools aren’t slice-, NF- or version-aware, and raw-count baselines misfire under growth |
| **Limitations** | Slice labels in 5G-NIDD are unconfirmed, so slices may be simulated. Lab slices are not operator slices. Less data per slice weakens baselines. Benign time-continuity and capture duration are unverified. 5G-NIDD is flow data, so signalling-level features exist only in the testbed. If the testbed isn’t producing usable logs by day 7, fall back to synthetic slices and say so |
| **Evaluation** | Raw vs ratio features under growth. Global vs per-slice baselines. Hour-bucket context on vs off. Contamination tolerance curve (add 0, 1, 5, 10, 20% attack windows to training and measure the change) |

---

## Feature 2: Multi-Model Unseen-Attack Detection

| Field | Description |
| :--- | :--- |
| **What it does** | Scores each window for deviation from its baseline without labelled attacks, including slow ramps |
| **How [Must]** | Run Isolation Forest (score negated so higher means more anomalous) and a dense autoencoder (reconstruction error) per (slice, NF). Convert both to benign-reference percentiles. Output each detector’s percentile, a fused score and an agreement state. Apply CUSUM to the fused percentile stream. Evaluate with leave-one-attack-category-out |
| **Fusion rule** | Fix the primary rule before running (for example max of percentiles, since either detector may catch an attack) and report the mean variant as secondary. Benign validation data can’t measure recall, delay or evasion, so don’t “select” fusion on it. If you want data-driven selection, reserve some attack categories as a selection set and keep the rest as the test set |
| **Disagreement states** | Both fire (stronger evidence). Only Isolation Forest fires (hypothesis: unusual magnitude along single features). Only the autoencoder fires (hypothesis: unusual feature relationships). Neither fires. Disagreement is not evidence of benign behaviour. Test the hypotheses with the complementarity table (which detector catches which attack), and drop any that don’t hold |
| **Robustness [Must]** | One evasion test following the SAGE-5GC approach: an attacker who sees scores and the threshold ramps just below it. Vary ramp speed |
| **Robustness [Should]** | Random evasion, feature-subset disagreement, extra timescales |
| **Attack coverage** | 5G-NIDD families (floods, PFCP, IP spoofing, as reported by papers using it; verify against the files). [Should] Lab attacks in an isolated lab only: registration flood (many UERANSIM UEs), PFCP flood (Open5GS issue #3497 recipe), slow ramp. Vary intensity, duration and spread as separate conditions and call them variants, not new families |
| **Algorithms** | Isolation Forest, dense autoencoder, percentile fusion, CUSUM, plus per-feature z-score and static-threshold baselines |
| **Metrics** | Per-category recall with bootstrap confidence intervals, FPR, ROC-AUC, PR-AUC, false positives per million benign windows, mean time to detect, CUSUM detection delay vs false-alarm rate |
| **Novelty** | Low. Fusion and CUSUM are standard, and no exact match was found for CUSUM on unsupervised 5G-core score streams. The value is the honest per-category evaluation and the tested complementarity of the detectors |
| **Gap filled** | Most 5G XAI papers reviewed classify known attacks with supervised models. This one is benign-only and tested on held-out categories |
| **Limitations** | Few real attack families, so wide intervals. Perfect mimicry that follows protocol and ramps under the budget will pass. Both detectors may fail on the same attacks. Signalling coverage beyond PFCP is unconfirmed. Wording: “detects previously unseen attack behaviour”, never “zero-day” |
| **Pass check** | Both detectors must beat the z-score baseline, or fix the features first |

---

## Feature 3: Drift Attribution with Abstention (core contribution)

**What it does:** Detects shifts in normal behaviour and attributes the cause as likely benign, likely attack, or uncertain, with named evidence.

### A. Scenario streams

| Element | Detail |
| :--- | :--- |
| **Real growth backbone** | A public trace with natural daily and weekly variation, such as MAWI (verify it is public, its licence and format, and note it is not 5G). Inject attacks into it, so the growth is real and only the attack is constructed |
| **Generator families** | (1) Parametric scaling, (2) block-bootstrap of real benign segments, (3) seasonal growth model. Randomise parameters |
| **Held-out generators** | Hold out whole generator families when testing the attributor |
| **Tuning vs test streams** | Generate separate tuning streams for thresholds and budgets, freeze them, then evaluate on test streams |
| **Slices** | Two, with the event in slice 1. If slices are simulated, give them independent noise plus a shared diurnal component, so slice 2 isn’t trivially stable |
| **Open release** | Publish the generator so others can challenge it |

| Stream | Correct outcome |
| :--- | :--- |
| **Stable benign** | No drift, no update |
| **Authorised benign growth (2 to 4×, new UEs)** | Adapt after approval |
| **Slow attack ramp** | Quarantine, no learning |
| **Attack during growth** | Adapt to growth, quarantine the attack part |
| **Stress test: mimicry (attack imitating organic structure)** | Report the failure rate honestly |

### B. Attributor

| Component | Detail |
| :--- | :--- |
| **Drift detection** | ADWIN on the fused percentile stream and key rates (pre-register ADWIN as the single drift detector) |
| **Complementary signals** | Volume and normalised composition. They may be statistically related, so call them complementary, not independent |
| **Proportional-growth test [Must]** | Ask whether current traffic is explainable as a scaled copy of the baseline. Estimate the volume factor k (context-matched by hour). Compare the current composition vector with the baseline using Jensen-Shannon divergence with pseudo-count smoothing and a minimum-count rule, since divergence is biased upward on small counts. Also compare per-UE rate distributions and failure ratios. Set the threshold from a null distribution of benign-vs-benign comparisons (same-period windows plus benign growth episodes from the tuning streams, for example the 99th percentile), not by hand |
| **What “composition” means** | In the testbed: procedure and session-type mix (registration, session setup, other). In 5G-NIDD flow data: protocol mix and flow-size bins. State which one each result uses |
| **Supporting signals** | Entropy of hashed UE identifiers per slice, new-UE rate, NAS and PFCP failure ratios (your inference, not a standard feature), breadth across NFs, change-log match, detector agreement state |
| **Control-slice evidence [Should]** | Compare slice 1 against slice 2. Both change together suggests a network-wide change. Only slice 1 changes in composition is a localised change. Treat it as one supporting signal, not a verdict: slices share infrastructure and genuine growth can be slice-specific (a new enterprise customer on one slice). Report results separately for real lab slices and simulated slices |
| **Model [Must]** | Hand-written rules |
| **Model [Should]** | Small classifier on the same signals, sequential decisions (accumulate evidence over a few windows), explanation-drift signal (E2D2-inspired) |
| **Abstention (central principle)** | Three evidence outcomes: strong growth evidence and no independent threat indicators (likely benign), strong malicious indicators (likely attack), conflicting or insufficient evidence (uncertain). Every uncertain output carries a named reason: insufficient baseline history, volume and composition disagree, detectors disagree, inconclusive growth pattern, cannot separate attack from growth. Report an accuracy-vs-coverage curve |
| **Confidence wording** | The rules attributor outputs evidence categories, never probabilities. Only calibrate if you add a probabilistic classifier |
| **Comparison baselines** | Gera & Battula entropy rule (a real, citable baseline from web DDoS and NS-2 simulation), drift detection with no attribution, the attributor without governance |

### Policy table

| Observed | Action |
| :--- | :--- |
| **Volume up, composition consistent with scaling** | Possible proportional growth, check change log and context |
| **Composition changed, no independent threat evidence** | Abstain, quarantine, collect more evidence |
| **Composition changed plus malicious indicators** | Alert |
| **Verified labels or approval available** | Consider a controlled update |
| **Update degrades performance** | Roll back |

### Validating attribution

| Check | Detail |
| :--- | :--- |
| **Lab ground truth** | In the testbed you cause growth and attack yourself, so measure attribution precision and recall against the true cause |
| **Calibration** | Only if a probabilistic classifier exists: reliability diagram |
| **Informal analyst check** | 3 to 5 people see an alert with evidence. Report how many agree |
| **Wording** | “Evidence-ranked hypothesis”, never “root cause” |

| Metadata | Details |
| :--- | :--- |
| **Novelty** | The integrated attribution, abstention and governance design, evaluated on attack-during-growth. In the abstracts reviewed, none tested that case, and the flash-crowd literature found no peer-reviewed evaluation of a slow attack injected into measured organic growth (unverified beyond abstracts) |
| **Gap filled** | Drift detectors say traffic changed but not whether it is safe to learn from it |
| **Limitations** | Identifiability: a proportional-growth test is exactly what a mimicking attacker defeats, and if telemetry lacks the information to separate the two, no method can. Signals are evidence, not proof. Injected attacks are constructed. Entropy rules are reported to fail under mimicry. If any variant uses attack prototypes, it uses attack knowledge, so state the split |

---

## Feature 4: Approval-Gated Adaptation

**What it does:** Lets a baseline change only through a controlled, canary-checked, budget-limited, reversible process.

### A. Controls

| Control | Detail | Tier |
| :--- | :--- | :--- |
| **Quarantine** | Suspicious or uncertain windows excluded from retraining | Must |
| **Shadow candidate** | Train a candidate per slice, so one slice’s update can’t affect another | Must |
| **Normal-holdout backtest** | Candidate FPR on a known-normal holdout must stay within a margin of the anchor’s | Must |
| **Canary retention test** | See B below | Must |
| **Per-update step limit** | Candidate vs currently active baseline | Must |
| **Cumulative drift budget** | Candidate vs the trusted anchor, see C below | Must |
| **Approval** | Analyst approval before promotion | Must |
| **Atomic rollback** | Restores model, scaler, schema and thresholds together, with the change log recording it | Must |
| **Dwell time** | Minimum interval between promotions | Should |
| **Registry security** | Signed and hashed artifacts, audit log | Should |
| **Re-anchoring** | See C below | Should |
| **Cohort quarantine** | Quarantine newly appearing UEs with provisional learning, then promote or reject | Roadmap |

### B. Canary retention test

* **Purpose:** check that adapting to growth hasn’t made the detector blind to attacks.
* **Canary set:** a held-out set of attack windows, kept separate from the attacks you evaluate on, and rotated between runs. Include several attack categories.
* **Rescaling:** Rescale to the current traffic level. An old attack replayed at its old volume would be less anomalous after legitimate growth, and would wrongly penalise good adaptation. Express each canary’s effect relative to a matched benign reference (a ratio in log space for count-like features, a difference for bounded ratios), and apply that effect to current benign windows. Report a second variant with fixed absolute attack volume, since proportional scaling is an approximation of how a real attack behaves at larger scale.
* **Metric:** Measure canary recall at the active threshold for both the anchor and the candidate, per category, not only on average.
* **Pass rule (pre-registered):** candidate recall must stay within a pre-registered margin $\delta$ of the anchor’s, in every canary category, and normal-holdout FPR must stay within its margin.
* **Constraint:** Do not reward a lower FPR that comes with lost recall. Both conditions must pass.
* **Limits:** The governance layer now uses labelled attack data (detection itself stays unsupervised, so disclose it). An attacker could preserve recall on the canaries while weakening detection of other attacks. Canary and regression testing is standard ML practice, so present it as an application, not a novelty claim.

### C. Cumulative drift budget (explicit definition)

Computed on the ratio features the detector uses, so legitimate proportional growth doesn’t consume the budget.

For feature $i$, with anchor median $\text{med}_{i,0}$ and anchor robust scale $s_{i,0}$ ($1.4826 \times \text{MAD}$, floored at a small constant):

$$z_i = \frac{\text{med}_{i,\text{cand}} - \text{med}_{i,0}}{s_{i,0} + \varepsilon}$$

$$D_{\text{rms}} = \sqrt{\frac{1}{n} \sum z_i^2} \quad \text{(distance from the anchor)}$$

$$D_{\text{max}} = \max_i |z_i| \quad \text{(largest single-feature shift)}$$

$$\Delta_{\text{can}} = \text{median over canaries of } (\text{anchor percentile} - \text{candidate percentile}) \quad \text{(decision-relevant shift in detection strength)}$$

Promotion requires all of:

| Condition | Meaning |
| :--- | :--- |
| $D_{\text{rms}}(\text{cand}, \text{active}) \le b_{\text{step}}$ | Per-update step limit |
| $D_{\text{rms}}(\text{cand}, \text{anchor}) \le B_{\text{rms}}$ | Cumulative budget |
| $D_{\text{max}}(\text{cand}, \text{anchor}) \le B_{\text{max}}$ | No single feature may carry the shift (RMS alone dilutes it across many features) |
| $\Delta_{\text{can}} \le B_{\text{can}}$ | Detection strength on canaries hasn’t dropped too far |
| **Canary retention test passed** | Section B |
| **Dwell time elapsed, analyst approval** | Governance |

Set $b_{\text{step}}$, $B_{\text{rms}}$, $B_{\text{max}}$, $B_{\text{can}}$ and $\delta$ on the tuning streams, then freeze them before running on test streams. This is one possible engineering definition, not an established safe-update criterion, so validate it with the poisoning experiments. No universal safe value exists.

* **Why three measures:** medians capture location only and RMS dilutes single-feature shifts, so $D_{\text{max}}$ and the canary measure cover shape and decision-relevant changes that the medians miss.
* **Re-anchoring (Should):** legitimate long-term structural change will eventually exhaust any fixed budget. Provide an explicit re-anchoring procedure: offline review, a fresh anchor from verified-normal data, optionally two approvers, and a budget reset. Test how often it is needed, and report it as a cost of the design.
* **Algorithms:** Retraining of the F2 models on filtered windows, the distance measures above.
* **Data:** Same streams as F3, plus the canary set.
* **Novelty:** Low per control (quarantine, shadow, canary, rollback are standard practice). The new part is combining them with the attribution verdict and testing against a ramp attacker.
* **Gap filled:** Boiling-frog poisoning of periodically retrained detectors is documented generally, but nothing found quantifies it for 5G or tests a gated defence.
* **Limitations:** The benefit is a hypothesis your experiment measures. Approval depends on a human who can be wrong or slow. A perfect mimic within the budget can still move the baseline. Re-anchoring is a human step that can itself be abused.

---

## Feature 5: Investigation Dashboard

| Field | Description |
| :--- | :--- |
| **What it does** | Makes every model decision traceable and shows the experiment’s central result |
| **How** | Replay saved traffic through the pipeline (FastAPI plus a single-page front end such as React or Streamlit, SQLite or files for storage). Label it “replay mode”. Keep a pre-recorded fallback. Build against mock JSON first |
| **[Must] panels** | Three-arm replay: the same stream under no adaptation, naive adaptation and CommShield, showing baseline contamination building in one and prevented in another. Alert detail: expected vs observed values, SHAP for Isolation Forest (flagged windows only), a 5G-style hypothesis (not a root cause), the abstain reason. Model-health card: baseline version, drift state, attribution verdict, budget used ($D_{\text{rms}}$, $D_{\text{max}}$), quarantine size, abstention rate, pending candidate, Approve and Rollback buttons. Decision trace for every candidate (below) |
| **Decision trace example** | Normal holdout: passed. Canary retention: failed (category X recall below the anchor’s by more than $\delta$). Step limit: passed. Cumulative budget: passed. Analyst approval: pending. Final decision: REJECTED, attack detection degraded (illustrative wording, not results) |
| **[Should] panels** | Update preview like a code diff, change-log strip, scale benchmark curve (windows scored per second at 1×, 10× and 100× synthetic load) |
| **Roadmap** | Incident grouping, analyst-burden panel, NF panels, risk-score sensitivity bands, grouped SHAP, case notes, PCAP link |
| **Risk labels** | If shown, use a simple documented formula (score percentile, persistence, breadth), and display percentiles, never “95% attack probability” |
| **Novelty** | Low. Showing pending updates, budgets, abstentions and decision traces beside alerts is a design proposal from your research, not an established practice |
| **Gap filled** | Opaque model behaviour, and a way for judges to see the decision process |
| **Limitations** | Replay, not live. Laptop-scale evidence only. Attribution is not causation, and SHAP can be unstable under correlated features (your own tests are the evidence). Explanations should reach authenticated analysts only, since exposed logic can aid evasion (Pacheco & Pedroso). Usability evidence is an informal small check at best |

---

## Centrepiece experiment (pre-registered)

| Arm | Description |
| :--- | :--- |
| **A** | No adaptation |
| **B** | Naive auto-retrain on drift alarms (Gupta-style continuous training) |
| **C** | CommShield (gated adaptation) |

Run on legitimate growth, a slow attack ramp and an attack hidden inside growth, plus the mimicry stress test, with several seeds and bootstrap confidence intervals. Report real-backbone and constructed-data results separately.

| Measure | A | B | C |
| :--- | :--- | :--- | :--- |
| Legitimate growth handling | | | |
| Attack detection | | | |
| Baseline contamination (attack share of retraining data) | | | |
| False-positive rate | | | |
| Recovery after attack, including rollback time | | | |

### Ablations (each isolates one mechanism)

| Ablation | Question |
| :--- | :--- |
| **Per-update step limit alone vs step limit plus cumulative budget** | Does the budget stop a ramp attacker who stays under every step? Plot baseline movement from the anchor over time |
| **With vs without canary retention test** | Does it block candidates that lost attack recall? |
| **With vs without abstention** | What does abstention buy, and at what coverage? |
| **With vs without proportional-growth test** | Does it improve growth-vs-attack separation? |
| **With vs without control-slice evidence** | Lab slices vs simulated slices, reported separately |
| **Real backbone vs synthetic-only growth** | How much does realism change the result? |
| **Global vs per-slice baselines** | Does per-slice containment help? |

Also plot an evasion boundary map (attacker ramp speed and spread against detection, attribution and abstention outcomes). Fill the tables only with numbers you produce.

### Fallback story

| If this happens | Then say |
| :--- | :--- |
| **Gated beats naive on contamination** | Headline result, with the cost to legitimate adaptation shown |
| **Gated matches naive** | Report it, and focus on abstention and the evasion boundary |
| **Abstention rate is too high** | Present the coverage-accuracy trade-off and the share needing an analyst |
| **Budget is exhausted by legitimate growth** | Report re-anchoring frequency as the cost |
| **Testbed fails** | Synthetic slices, disclosed |

---

## Data and validation levels

| Level | Source | Claim you can make |
| :--- | :--- | :--- |
| **Real public capture** | 5G-NIDD (testbed traffic, reported CC BY 4.0, verify access) | “Tested on real captured 5G testbed traffic” |
| **Real growth backbone** | Public trace with natural variation (not 5G) | “Growth pattern is real, attacks are injected” |
| **Own lab** | Open5GS + UERANSIM in an isolated VM | “Lab testbed data we generated, with known ground truth” |
| **Semi-synthetic** | Real flows scaled, mixed, ramped | “Constructed drift scenarios from real flows” |
| **Operator data** | None | “Not yet validated” |

---

## Cross-cutting protocol

1. **Full-text reads first:** Gupta et al., Pacheco & Pedroso, Murugesan, DyNA-IDS, E2D2, ExpIDS, SAGE-5GC (Table 4 and dataset access), Gera & Battula, and the poisoning papers. Keep an evidence table with a “full text read: yes/no” column and cite only rows marked yes.
2. **Pre-register:** splits, thresholds, the primary fusion rule, the single drift detector, budget parameters (to be set on tuning streams), metrics, seeds and pass criteria before running.
3. **Early separability test:** by day 14, with success criteria set beforehand (beats a majority-class rule, abstention stays under a set rate).
4. **Inspect 5G-NIDD yourself:** attack labels, timestamps, benign continuity, duplicates, slice fields, window counts. Confirm Open5GS log fields.
5. **Threats-to-validity slide:** internal (leakage, tuning), external (generalisation), construct (do the metrics measure what you claim).
6. **Public repository:** with the data card, generators and exact commands.

---

## Effort tiers (honest)

| Effort | Items |
| :--- | :--- |
| **Small** | Decision trace, atomic rollback, abstain reasons, proportional-growth test, time-of-day context |
| **Moderate** | Canary set and rescaling, drift budget with tuning streams, ablations |
| **Depends on the lab** | Real lab slices, control-slice evidence, lab attacks |

Every extra mechanism adds an ablation to run and explain, and scope was already your weakest area, so build in this order: proportional-growth test, canary retention with rescaling, the budget metric, decision trace. Add the rest only if time allows.

---

## Cut line

| Tier | Contents |
| :--- | :--- |
| **Must** | Ratio-feature per-slice baselines with anchor, fallback and atomic packaging, IF + AE with per-category evaluation, one evasion test and a pre-registered fusion rule, CUSUM, four streams plus the mimicry stress test with a real backbone and held-out generator families, rules attributor with proportional-growth test and named abstention reasons, quarantine, shadow candidate, step limit, cumulative budget with canary retention, approval and atomic rollback, three-arm experiment with ablations, replay dashboard with three-arm view and decision traces |
| **Should** | Real lab slices, lab attacks, control-slice evidence, time-of-day context, classifier attributor, sequential decisions, dwell time, re-anchoring, scale curve, informal analyst check |
| **Roadmap only** | Cohort quarantine, partial pooling, UE-count context, grouped SHAP, incident grouping, burden panel, second dataset, federated learning, GNN, LSTM, conformal calibration under drift, case management, auto-response, real private-5G and 6G validation |

---

## What to claim and not claim

| Claim | Don’t claim |
| :--- | :--- |
| Measured evaluation of attack-during-growth with benign/attack/uncertain attribution, canary-checked and budget-limited gated updates, and an evasion boundary | First-ever CUSUM, conformal, poisoning-resistant or context-aware detection, or novelty of SHAP, ADWIN, divergence tests, canary testing |
| Per-slice baselines contain effects to the affected slice (lab or simulated, stated which) | Real-slice or operator validation |
| Detects previously unseen attack behaviour with per-category results | Zero-day detection |
| Architecture extends to private 5G and 6G through adapters | 6G capability, operator-scale validity, proven root cause, NWDAF compliance (“NWDAF-style” only) |

### Limitations to state openly
Synthetic or constructed drift scenarios, abstract-level literature check until the full-text reads are done, simulated slices if the lab fails, perfect-mimicry evasion (an identifiability limit, not only an engineering one), few attack families, canary data bringing attack knowledge into governance, budgets tuned by you, re-anchoring as a human step, no operator-scale or real-network validation, and attribution that is hypothesis, not proof.
