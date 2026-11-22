# CommShield Privacy by Design Specification

## 1. Executive Summary

CommShield is engineered under strict **Privacy by Design** principles (GDPR Article 25, 3GPP TS 33.501 zero-trust guidelines). The detection and governance pipeline operates exclusively on aggregate behavioral and ratio statistics, ensuring that no personally identifiable information (PII), permanent subscriber identifiers (SUPI/IMSI), temporary identifiers (GUTI/TMSI), or raw IP network addresses ever reach downstream anomaly detectors, machine learning models, persistent databases, API responses, snapshot artifacts, or frontend dashboards.

---

## 2. Ingestion Scope & Data Sources

CommShield processes two data sources:
1. **Public 5G-NIDD Testbed Captures**: Benchmark flow records from the University of New Brunswick (UNB) / Canadian Institute for Cybersecurity (CIC) 5G testbed, captured on realistic 5G core network interfaces (gNB, UPF, AMF).
2. **Parametric Synthetic Streams**: Pure mathematical generation of statistical flow and session counts (Poisson arrival rates, Pareto-distributed packet sizes, Dirichlet-multinomial slice compositions). No individual packet payloads or user identifiers are generated.

**Zero Raw Data Ingress**: Raw packet captures (PCAP) and full payload captures are never ingested into the CommShield runtime. All data passes through specialized preprocessing adapters before entering the system.

---

## 3. Cryptographic Pseudonymisation

Where raw flow records contain network identifiers (`SrcAddr`, `DstAddr`, or simulated UE IP addresses), they are transformed at parse time within `ml_engine/preprocessing/adapters/` using keyed cryptographic pseudonymisation:

- **Algorithm**: `HMAC-SHA256` keyed by an operational secret (`COMMSHIELD_HMAC_KEY`).
- **Configuration**: Injected securely via environment variables (never committed to version control, never written to log files, documented in `.env.example`).
- **One-Way Mapping**: Raw IP addresses and subscriber tokens cannot be inverted or rainbow-table attacked without access to the secret HMAC key.
- **Shannon Entropy Invariance**: For any statistical window $W$, the Shannon entropy of identifiers $H(X) = -\sum p(x) \log_2 p(x)$ is mathematically invariant under deterministic injective pseudonymisation. The behavioral entropy signal `ue_hash_entropy` remains identically informative for detecting distributed flood attacks or botnet scanning without preserving the underlying subscriber identity.

---

## 4. Strict Aggregate-Only Boundary

To prevent accidental data leakage or field expansion, CommShield enforces a strict allowlist schema at the adapter boundary via `enforce_aggregate_boundary()`:

1. **Canonical Window Allowlist**:
   - Metadata: `window_id`, `slice_id`, `timestamp`, `window_duration_sec`, `data_source`, `label`, `attack_type`.
   - Aggregate Counters: `packet_count`, `byte_count`, `flow_count`, `active_ue_count`, `nas_requests`, `nas_failures`, `pdu_sessions_requested`, `pdu_sessions_established`.
   - Ratio Features (9D Model Input): `byte_rate`, `packet_rate`, `bytes_per_flow`, `flows_per_ue`, `nas_failure_ratio`, `pdu_setup_success_ratio`, `ue_hash_entropy`, `pdu_session_rate_per_ue`, `bytes_per_session`.
   - Composition Vectors: Layer 4 protocol distribution (`TCP`, `UDP`, `ICMP`, `SCTP`, `OTHER`), service type distribution (`EMBB`, `URLLC`, `MMTC`).
2. **Strict Drop Policy**:
   - Any flow-level identifier, IP address, MAC address, port number, IMSI, SUPI, or GUTI present in raw adapter memory is explicitly dropped.
   - Any unapproved key outside the canonical allowlist raises an error or is stripped prior to object creation.

---

## 5. Small-Group Suppression ($K$-Anonymity)

In mobile network slices, low user counts create re-identification risk through traffic volume side-channels. CommShield enforces small-group suppression:

- **Threshold ($K$)**: Configured via `COMMSHIELD_SUPPRESSION_K` (default: $K = 5$).
- **Mechanism**:
  - When a time window contains fewer than $K$ distinct active UEs (`active_ue_count < K`), granular entropy metrics (`ue_hash_entropy`) are redacted and replaced with a documented sentinel value:
    $$\text{ue\_hash\_entropy} = -1.0$$
- **Attribution & Detection Handling**:
  - The Attribution Engine (`backend/app/services/attribution.py`) explicitly detects `ue_hash_entropy < 0`.
  - Suppressed entropy is treated as **missing evidence**: the delta is forced to zero ($\Delta = 0$), preventing false attack alarms or indicator conflicts.
  - The decision trace annotates the result with `entropy_suppressed: true` and `entropy_drop_triggered: false`.
  - Existing governance gate thresholds and model pipelines remain robust without metric skew.

---

## 6. Access Control & Role-Based Authorization

Mutating operations in the governance pipeline can alter active baseline parameters and network admission criteria. CommShield enforces role-based access control:

- **Analyst Token**: Defined by `COMMSHIELD_ANALYST_TOKEN` from the runtime environment.
- **Protected Endpoints**:
  - `POST /api/v1/candidates/{id}/approve` (or `/api/governance/candidates/{id}/approve`)
  - `POST /api/v1/candidates/{id}/reject` (or `/api/governance/candidates/{id}/reject`)
  - `POST /api/v1/baselines/rollback`
- **Validation**: Requests must provide `Authorization: Bearer <token>`. Unauthorized requests receive `401 Unauthorized`.
- **Demo Mode Isolation**: When `DEMO_MODE=true`, inspection and telemetry replay endpoints remain open for observation, while state-mutating administrative actions still require the analyst token. The frontend dashboard includes a secure token configuration panel in Settings.

---

## 7. Storage Architecture & Retention Policy

### Storage Isolation
CommShield stores **only aggregate window statistics and governance decision records**. The relational database schema consists strictly of:
- `canonical_windows`: Aggregate 60-second window feature vectors and ratios.
- `baselines`: Quantile profiles ($Q_{0.05}, Q_{0.50}, Q_{0.95}$) and covariance matrices.
- `candidate_baselines`: Proposed adaptation baselines and sandbox evaluation metrics.
- `detection_results`: Anomaly scores, percentile rankings, and ensemble agreement states.
- `attribution_results`: Root-cause verdicts, abstention reasons, and proportional growth tests.
- `quarantine_windows`: Pointers to flagged anomalous windows held for evaluation.
- `audit_events`: Tamper-evident governance decisions and operator approvals.
- `experiment_results`: Multi-seed benchmark metrics.

**Zero Raw Flow Storage**: Under no circumstances does CommShield persist per-packet or per-flow records, IP addresses, port numbers, or subscriber traces.

### Retention Rules
1. **Canonical Windows & Detections**: 30-day sliding retention window. Daily automated partition purging drops expired window telemetry.
2. **Quarantine Records**: 14-day retention. Quarantined windows older than 14 days without active candidate association are purged.
3. **Audit Trails & Anchor Baselines**: Retained indefinitely (append-only) for regulatory compliance and zero-trust provenance.

---

## 8. Threat Model & Adversary Capabilities

### Threat Model Definition
We analyze an adversary with **full passive read access** to the relational database (`commshield.db`) or the canonical telemetry stream (`data/lab/windows.jsonl` or API responses). The adversary is assumed to possess knowledge of public IP address ranges, cellular prefix allocations, and standard 5G Core protocol specifications.

### Summary of Privacy Controls
| Mechanism | Target Telemetry | Implementation | Cryptographic / Mathematical Guarantee |
| :--- | :--- | :--- | :--- |
| **HMAC-SHA256 Pseudonymisation** | Client IP addresses, SIM IDs, IMSIs | `ml_engine/preprocessing/adapters/base.py` | Keyed one-way hashing with `COMMSHIELD_HMAC_KEY`. Immune to rainbow table preimage attacks without key. |
| **Aggregate-Only Boundary** | Telemetry window ingress | `enforce_aggregate_boundary()` allowlist | Individual flow/packet records dropped in adapter memory; only 60s aggregates exported. |
| **Small-Group Suppression** | Active UE count $< K$ ($K=5$) | `SUPPRESSED_ENTROPY_VALUE = -1.0` | Prevents volume/entropy fingerprinting of individual devices in sparse slices. |
| **Analyst Bearer Token** | State mutations (`approve`, `reject`, `rollback`) | `require_analyst_token` | HTTP 401 unauthorized block without `COMMSHIELD_ANALYST_TOKEN`. |

### What an Attacker with Read Access COULD Learn
1. **Network-Wide Macro-Traffic Volumetrics**: The attacker can observe total uplink/downlink bytes, total packets, and session establishment rates aggregated over 60-second epochs.
2. **Slice-Level Operational Health**: The attacker can observe aggregate control-plane failure ratios (`nas_failure_ratio`, `pfcp_failure_ratio`) and protocol compositions.
3. **Anomaly Verdicts**: The attacker can observe whether CommShield flagged a given 60-second window as anomalous, quarantined, or undergoing legitimate growth.

### What an Attacker CANNOT Learn
1. **Subscriber Identity**: No permanent (IMSI/SUPI) or temporary (GUTI) identifier exists anywhere in the database or stream. All IDs are HMAC-SHA256 hashed at parse time.
2. **Subscriber IP Addresses**: Raw IP addresses are dropped immediately at the adapter boundary and never persisted.
3. **Communication Contents & Destinations**: No packet payloads, URLs, destination domain names, or application-layer data are ingested or stored.
4. **Individual Device Trajectories**: Because windows represent 60-second slice-level sums, an attacker cannot track the movement, browsing, or activity of any specific device.
5. **Sparse Group Signatures**: When fewer than 5 UEs are active in a window, entropy is suppressed to prevent side-channel fingerprinting.

---

## 9. Requirements for Production Carrier Deployment

While CommShield is verified privacy-compliant on public benchmark datasets (5G-NIDD), deployment in a live commercial telecommunications or private 5G network requires the following additional controls:

1. **Carrier Legal & Regulatory Review**:
   - Formal Data Protection Impact Assessment (DPIA) under GDPR Article 35 / ePrivacy Directive.
   - Carrier-specific telecommunications secrecy compliance (e.g., lawful interception separation).
2. **Hardware Security Module (HSM) / KMS Key Management**:
   - Integration with cloud KMS (e.g., GCP Cloud KMS, AWS KMS, or on-prem PKCS#11 HSM) for `COMMSHIELD_HMAC_KEY` storage and automated 90-day key rotation.
   - Enforce cryptographic salt salting per slice or per diurnal epoch to prevent linkability across rolling baselines.
3. **Automated Time-To-Live (TTL) Purge Pipelines**:
   - Scheduled database partition dropping (e.g., PostgreSQL `pg_partman` or ClickHouse TTL expressions) enforcing strict 30-day data lifecycle.
4. **Enterprise Identity Federation (OIDC / mTLS)**:
   - Upgrade static analyst bearer tokens to OpenID Connect (OIDC) / OAuth 2.0 with mutual TLS (mTLS), integrating with telecom SOC identity providers (Active Directory, Okta, Keycloak) with hardware MFA.
<!-- CommShield AI Core -->
