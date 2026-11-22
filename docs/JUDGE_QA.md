# CommShield — Hackathon Judge Q&A & Technical Defense

This document provides rigorous, evidence-backed answers to the ten most critical architectural, mathematical, and operational questions regarding the CommShield 5G Zero-Trust Adaptive Governance prototype.

---

### Q1: Why did the earlier prototype dashboard report zero adaptations?
**Answer:**
Zero adaptations in initial tests resulted from two specific root causes:
1. **Exclusively Manual Approval Pipeline**: The original promotion endpoint required an analyst Bearer authorization token on `POST /api/candidates/{id}/approve`. No autonomous promotion logic existed to promote verified models without manual human intervention.
2. **Attribution Buffer Starvation in Experiment Replay**: In the simulation loop, recent telemetry windows were erroneously sliced from an unpopulated historical buffer (`legitimate_growth_pool[-10:]`), causing the attribution engine to perpetually report `uncertain` and never accumulate the 5 consecutive verified windows required to trigger candidate synthesis.

**Resolution**: We implemented the **Three-Tier Graduated Adaptation Engine** (`backend/app/governance.py`). Under Tier 1 (`AUTO_APPROVE`), candidate baselines exhibiting minimal drift ($JSD < 0.020$) and passing all four critical gates are atomically promoted with semver patch increment (`v1.0.0` $\rightarrow$ `v1.0.1`), resolving zero adaptations while strictly maintaining safety invariants.

---

### Q2: What is the mathematical definition and engineering rationale for Jensen-Shannon Divergence (JSD) thresholds?
**Answer:**
Jensen-Shannon Divergence ($JSD$) measures the symmetric statistical distance between the baseline signaling composition distribution $P$ and incoming telemetry distribution $Q$:
$$M = \frac{1}{2}(P + Q)$$
$$JSD(P \parallel Q) = \frac{1}{2} D_{KL}(P \parallel M) + \frac{1}{2} D_{KL}(Q \parallel M)$$
where $D_{KL}(P \parallel M) = \sum_{i} P(i) \ln \frac{P(i)}{M(i)}$ across the four canonical traffic components (TCP session setup, UDP data/registration, ICMP diagnostic, RST/abnormal failures). Because $JSD$ is bounded between $0$ and $\ln(2) \approx 0.693$, its square root is a true metric.

**Thresholds Rationale**:
- **Tier 1 Auto-Approve ($JSD < 0.020$)**: Traffic composition variation is mathematically negligible. The shift represents pure proportional scaling (e.g. organic crowd surge) without protocol skew.
- **Tier 2 Flag for Review ($0.020 \le JSD < 0.035$)**: Measurable composition shift within safe operational bounds. Detector retention is preserved, but operator sign-off is required.
- **Tier 3 Block and Quarantine ($JSD \ge 0.035$)**: Structural protocol distortion indicative of stealth reconnaissance, port scanning, or signaling exhaustion.

---

### Q3: Why does low drift alone never guarantee automatic promotion?
**Answer:**
A low drift score ($JSD < 0.020$) indicates only that protocol proportions match expectations; it **does not** prove the traffic is benign. For example:
- A sophisticated adversary can execute a **mimicry attack**, injecting malicious control-plane packets distributed identically to normal background traffic.
- A model trained on high-volume traffic may suffer **canary forgetting**, losing sensitivity to low-rate historical exploits.

**Safety Invariant**: Low drift is a **necessary but not sufficient** condition. Any single failure in the four mandatory gates (normal holdout FPR $> 5\%$, canary recall degradation $> 5\%$, or drift budget $> 1.5\sigma$) immediately overrides the decision to **Tier 3 (BLOCK & QUARANTINE)**.

---

### Q4: How does the four-gate verification pipeline prevent model degradation?
**Answer:**
Every shadow candidate model must pass four independent gates prior to serving live traffic:
1. **Normal Holdout Backtest**: Evaluates the candidate against a held-out slice of historical clean traffic. If false positive rate inflation exceeds $5\%$, the model is rejected.
2. **Canary Retention Test**: Injects historical synthetic and real attack signatures into the test batch. The candidate must detect $\ge 95\%$ of canary attacks (maximum permitted degradation $\Delta \le 5\%$).
3. **Bounded Drift Budget**: Enforces two statistical constraints on parameter drift:
   - Single-step shift: $D_{rms}(\text{candidate}, \text{active}) \le 1.50\sigma$.
   - Cumulative drift from anchor: $D_{rms}(\text{candidate}, \text{anchor}) \le 2.50\sigma$.
4. **Proportional Growth Test**: Verifies per-UE throughput and session rates remain within nominal bounds.

---

### Q5: How are network slices mapped and isolated?
**Answer:**
CommShield maps traffic into 3GPP S-NSSAI slices:
- **eMBB (`sst-1-sd-010203`)**: High throughput, large byte-per-session ratios, streaming and mobile broadband.
- **URLLC (`sst-2-sd-010203`)**: Ultra-low latency, high packet rates, minimal buffering.
- **mMTC (`sst-3-sd-010203`)**: Massive IoT telemetry, low byte volume, high device count.

In real 5G-NIDD datasets where physical GTP-U encapsulation headers were stripped by Argus, CommShield uses empirical base-station mapping (`BS1` = eMBB, `BS2` = URLLC) with transparent UI labeling (`"slices assigned"`). Baselines, thresholds, and quarantine tables are partitioned strictly per slice ID.

---

### Q6: How does CommShield prevent "boiling frog" poisoning attacks?
**Answer:**
"Boiling frog" poisoning occurs when an adversary gradually ramps attack volume at sub-threshold increments, forcing naive adaptive detectors to accept attack signatures as the new "normal."
CommShield neutralizes this via **Immutable Trusted Anchors**:
- Every slice maintains an immutable **Anchor Baseline** (`v1.0.0-anchor`) calibrated on clean commissioning telemetry.
- While adaptive baselines update incrementally, cumulative drift is **always measured relative to the immutable Anchor**:
  $$D_{rms}(\text{candidate}, \text{anchor}) \le 2.50\sigma$$
- If cumulative shifts exceed $2.50\sigma$, adaptation halts regardless of individual step sizes, and the system can execute an instantaneous **atomic rollback**.

---

### Q7: Why did alert scores previously saturate at 100%, and how was this fixed?
**Answer:**
- **Root Cause**: The Isolation Forest percentile mapping used `searchsorted(train_scores, raw_score) / N * 100`. In a benign calibration set, severe attack anomalies have raw anomaly scores far outside the training distribution tail, mapping every attack window to index $N$ ($100.0\%$). Furthermore, a frontend formatting bug multiplied the percentile by 100 again (`(score * 100).toFixed(1)%`), resulting in `10000.0%`.
- **Resolution**:
  1. Fixed the frontend formatter to detect scale and eliminate double multiplication.
  2. Implemented statistical mid-rank tie-handling:
     $$\text{Percentile} = \frac{\text{count}_{<} + 0.5 \cdot \text{count}_{=}}{N} \times 100$$
  3. Exposed **Raw Negated Anomaly Scores** alongside percentiles in all APIs and UI panels, complemented by an interactive **Score Distribution Histogram** (`GET /api/detection/distribution`).

---

### Q8: What is the difference between the 5G-NIDD dataset and the Digital Twin?
**Answer:**
- **5G-NIDD (Real)**: Real-world 5G testbed dataset (Samarakoon et al. 2022) captured from an operational 5G testbed running Argus flow collectors. Contains 4,351 flow records, 156 60-second telemetry windows, and 8 ground-truth attack classes (UDP Flood, HTTP Flood, SYN Flood, TCP Connect, SYN Scan, Slowloris, Torshammer, Normal).
- **Simulated Digital Twin**: Synthetic telemetry generated via parameterized Poisson-Gaussian traffic generators with exact ground truth, used to stress-test controlled volume scaling and stealth ramp adaptations.
- **Honest UI Labeling**: CommShield explicitly tags all graphs and tables with their precise provenance (`5G-NIDD (Real)` vs `Simulated Twin`).

---

### Q9: How does the cryptographic SHA-256 lineage ledger protect against model tampering?
**Answer:**
Implemented in `backend/app/services/lineage.py`, the **Lineage Provenance Adapter** maintains an append-only hash-chained ledger:
$$\text{Block Hash} = \text{SHA-256}(\text{prev\_hash} \parallel \text{index} \parallel \text{timestamp} \parallel \text{event\_type} \parallel \text{payload})$$
- Every model lifecycle event (candidate synthesis, Tier 1 auto-approval, Tier 2 flagging, Tier 3 quarantine, and atomic rollback) generates an immutable cryptographically chained block.
- Any unauthorized tampering with database records breaks the hash chain, triggering instant alerts via `GET /api/governance/lineage`.

---

### Q10: How will CommShield deploy in production 3GPP 5G Core networks?
**Answer:**
1. **Data Plane**: Ingests telemetry via UPF eBPF flow probes or 3GPP N4 (PFCP) session reporting without touching user payload encryption.
2. **Control Plane / NWDAF**: Exposes standard 3GPP TS 29.520 **NWDAF** services (`Nnwdaf_AnalyticsInfo` and `Nnwdaf_EventsSubscription`) to stream anomaly verdicts directly to the Policy Control Function (PCF) for dynamic QoS modification or slice quarantine.
3. **Audit & Compliance**: Supplies continuous cryptographic proof of model governance for regulatory audit compliance.
<!-- CommShield AI Core -->
