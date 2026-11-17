# 5G-NIDD Dataset Technical Notes & Ingestion Specification

## 1. Dataset Overview & File Inventory

The 5G Network Intrusion Detection Dataset (5G-NIDD) is a comprehensive, flow-level traffic dataset collected from a physical 5G Standalone (SA) testbed by the Canadian Institute for Cybersecurity (CIC) / University of New Brunswick (UNB). Traffic is extracted at the gNodeB and UPF interfaces, with GTP encapsulation removed to expose standard IP flow records processed by Argus.

The dataset directory is located at `data/raw/5g-nidd/`.

| File / Directory | Size | Row Count | Column Count | Description |
| :--- | :--- | :--- | :--- | :--- |
| `BTS1_BTS2_fields_preserved.csv` | 450.6 MB | 1,215,890 flows (+1 header) | 113 | Primary full-fidelity flow log with network headers, IP addresses, ports, and granular timing. |
| `Combined.csv` | 262.5 MB | 1,215,890 flows (+1 header) | 52 | Pre-stripped feature file with IP addresses and granular timestamps removed. |
| `Encoded.csv` | 466.6 MB | 1,215,890 flows (+1 header) | 96 | Machine learning encoded/one-hot feature matrix. |
| `BS1_each_attack_csv/` | ~270 MB | 728,316 flows | 113 | 10 per-attack CSV files for Base Station 1 (`BTS1`). Corresponds exactly to rows 0–728,315 of `BTS1_BTS2_fields_preserved.csv`. |
| `BS2_each_attack_csv/` | ~180 MB | 487,574 flows | 113 | 10 per-attack CSV files for Base Station 2 (`BTS2`). Corresponds exactly to rows 728,316–1,215,889 of `BTS1_BTS2_fields_preserved.csv`. |
| `README.pdf` | ~1.2 MB | N/A | N/A | Upstream documentation detailing the 5G testbed architecture, Open5GS core, Amarisoft/srsRAN gNodeBs, and attack vectors. |

### Label and Attack Distribution

Across all 1,215,890 flow records in `BTS1_BTS2_fields_preserved.csv`:

* **Binary Class (`Label`)**:
  * `Benign`: 477,737 flows (39.29%)
  * `Malicious`: 738,153 flows (60.71%)
* **Multi-Class (`Attack Type`)**:
  * `Benign`: 477,737 flows (39.29%)
  * `UDPFlood`: 457,340 flows (37.61%)
  * `HTTPFlood`: 140,812 flows (11.58%)
  * `SlowrateDoS`: 73,124 flows (6.01%)
  * `TCPConnectScan`: 20,052 flows (1.65%)
  * `SYNScan`: 20,043 flows (1.65%)
  * `UDPScan`: 15,906 flows (1.31%)
  * `SYNFlood`: 9,721 flows (0.80%)
  * `ICMPFlood`: 1,155 flows (0.10%)
* **Attack Tool (`Attack Tool`)**:
  * `Benign`: 477,737 flows
  * `Hping3`: 468,216 flows (UDPFlood, ICMPFlood, SYNFlood)
  * `Goldeneye`: 140,812 flows (HTTPFlood)
  * `Torshammer`: 59,870 flows (SlowrateDoS)
  * `Nmap`: 56,001 flows (TCPConnectScan, SYNScan, UDPScan)
  * `Slowloris`: 13,254 flows (SlowrateDoS)

### Time Representation and Chronology

* **Captures occurred over two distinct days**:
  * **Day 1 (2022-09-13)**: Port scanning and network reconnaissance (`TCPConnectScan`, `SYNScan`, `UDPScan`).
  * **Day 2 (2022-09-15)**: Denial-of-Service and volumetric flooding attacks (`UDPFlood`, `HTTPFlood`, `SlowrateDoS`, `SYNFlood`, `ICMPFlood`).
* **Timestamp Fields**:
  * `IdleTime`: Unix epoch timestamp in integer seconds (e.g. `1663055360` = 2022-09-13 07:49:20 UTC).
  * `StartTime`: Minute and second offset with sub-second resolution (`MM:SS.frac`, e.g. `30:02.6`).
  * Relative offset ordering preserves exact sub-second packet arrivals within each capture session.

---

## 2. Canonical Schema Mapping & Field Availability

Because 5G-NIDD is a flow-level (L3/L4 Argus flow records) dataset extracted after GTP decapsulation, control-plane signalling (NAS registration, authentication, PFCP N4 association, and session management messages) is **not available**. Under CommShield contracts, values must never be fabricated. Missing fields are left `None`/zero-valued with safe division guards, and user-plane proxy metrics are formally designated as **labelled proxies**.

### Mapping Table

| Canonical Field (`CONTRACTS.md`) | Canonical Category | 5G-NIDD Source Column | Status | Description / Proxy Methodology |
| :--- | :--- | :--- | :--- | :--- |
| `active_ue_count` | Raw Counter | `SrcAddr` | **Labelled Proxy** | Count of distinct client IP addresses (`SrcAddr`) observed in window. Flow logs omit SUPI/5G-GUTI. |
| `registration_attempts` | Raw Counter | None | **Not Available** | Control-plane NAS signalling is stripped from flow records. Zero-filled. |
| `registration_failures` | Raw Counter | None | **Not Available** | NAS failure messages not present in user-plane flow logs. Zero-filled. |
| `pdu_sessions_established` | Raw Counter | Flow Count | **Labelled Proxy** | Total distinct concurrent IP connections/flows in window proxy active session multiplexing. |
| `nas_messages_total` | Raw Counter | None | **Not Available** | 5G-AKA/NAS message counts not present in Argus flows. Zero-filled. |
| `nas_failures` | Raw Counter | None | **Not Available** | N1/N2 control failures not present. Zero-filled. |
| `pfcp_association_messages` | Raw Counter | None | **Not Available** | N4 PFCP interface messages not captured in user-plane logs. Zero-filled. |
| `pfcp_failures` | Raw Counter | None | **Not Available** | PFCP session establishment failures not captured. Zero-filled. |
| `total_bytes_uplink` | Raw Counter | `SrcBytes` | **Direct** | Direct sum of source-to-destination payload bytes across flows in window. |
| `total_bytes_downlink` | Raw Counter | `DstBytes` | **Direct** | Direct sum of destination-to-source payload bytes across flows in window. |
| `total_packets` | Raw Counter | `TotPkts` | **Direct** | Direct sum of total packet counts across flows in window. |
| `gtpu_teid_count` | Raw Counter | None | **Not Available** | GTP-U headers were decapsulated prior to Argus flow capture. Zero-filled. |
| `registrations_per_active_ue` | Ratio Feature | Derived | **Not Available** | Defaults to `0.0` due to absence of control-plane registration counters. |
| `nas_failure_ratio` | Ratio Feature | Derived | **Not Available** | Defaults to `0.0`. |
| `pfcp_failure_ratio` | Ratio Feature | Derived | **Not Available** | Defaults to `0.0`. |
| `pdu_session_rate_per_ue` | Ratio Feature | Derived | **Labelled Proxy** | `pdu_sessions_established / max(active_ue_count, 1)`. Measures flow density per client IP. |
| `bytes_per_session` | Ratio Feature | Derived | **Direct** | `(total_bytes_uplink + total_bytes_downlink) / max(pdu_sessions_established, 1)`. |
| `packets_per_session` | Ratio Feature | Derived | **Direct** | `total_packets / max(pdu_sessions_established, 1)`. |
| `gtpu_volume_per_ue` | Ratio Feature | Derived | **Labelled Proxy** | `(total_bytes_uplink + total_bytes_downlink) / max(active_ue_count, 1)`. |
| `ue_hash_entropy` | Ratio Feature | `SrcAddr` | **Labelled Proxy** | Shannon entropy computed across hashed client IP address distribution: $H(X) = -\sum p(x) \log_2 p(x)$. Drops during single-IP floods, elevates during distributed scans. |
| `new_ue_rate` | Ratio Feature | `SrcAddr` | **Labelled Proxy** | Proportion of distinct client IPs in the current window not observed in the preceding window. |
| `registration_ratio` | Composition Vector | None | **Not Available** | Fixed to `0.0`. |
| `session_setup_ratio` | Composition Vector | None | **Not Available** | Fixed to `0.0`. |
| `failure_ratio` | Composition Vector | None | **Not Available** | Fixed to `0.0`. |
| `other_signalling_ratio` | Composition Vector | None | **Direct** | Fixed to `1.0` for canonical schema sum invariant. |
| `protocol_vector` | Composition Vector | `Proto` | **Labelled Proxy** | Detailed user-plane distribution: `tcp_ratio`, `udp_ratio`, `icmp_ratio`, `other_ratio` (sums to 1.0). Captures DoS protocol shifts. |

---

## 3. Network Slice Assignment & Disclosure

The raw 5G-NIDD dataset does **not** contain 3GPP Network Slice identifiers (S-NSSAIs) because flow captures occurred on general base-station and UPF testbed tap points without slice segregation.

To support multi-slice evaluation without fabricating synthetic slice markers:
* **Base Station 1 (`BS1` / `BTS1`)**: Assigned to Slice `sst-1-sd-010203` (Designated: `eMBB` - Assigned Slice).
* **Base Station 2 (`BS2` / `BTS2`)**: Assigned to Slice `sst-2-sd-010203` (Designated: `URLLC` - Assigned Slice).

> **Transparency Disclosure**: Slices for the 5G-NIDD dataset are **assigned by base station, not native 3GPP S-NSSAI tags**. In all UI panels and generated reports, slices derived from 5G-NIDD must display the notice:
> *"Assigned slice based on base station topology (BS1 -> eMBB, BS2 -> URLLC). Not native 3GPP slice tags."*

---

## 4. Ground Truth & Window Label Mapping

Raw records have binary `Label` (`Benign` vs `Malicious`) and multi-class `Attack Type`. When aggregating flows into 10-second and 60-second canonical windows:

1. Let $N_{\text{total}}$ be the total flows in window $W$.
2. Let $N_{\text{malicious}}$ be the count of flows in $W$ where `Label != "Benign"`.
3. Compute the malicious flow ratio:
   $$r_{\text{malicious}} = \frac{N_{\text{malicious}}}{N_{\text{total}}}$$
4. Given configuration threshold $\theta_{\text{attack}}$ (default `0.05` / 5% malicious flows):
   * If $r_{\text{malicious}} \ge \theta_{\text{attack}}$:
     * `ground_truth.is_attack = True`
     * `ground_truth.attack_type = Mode(Attack Type of malicious flows)`
     * `ground_truth.malicious_flow_ratio = round(r_malicious, 4)`
   * If $r_{\text{malicious}} < \theta_{\text{attack}}$:
     * `ground_truth.is_attack = False`
     * `ground_truth.attack_type = None`
     * `ground_truth.malicious_flow_ratio = round(r_malicious, 4)`

---

## 5. Chronological Train / Validation / Test Splitting

To ensure valid evaluation without temporal data leakage:
* **Strict Temporal Ordering**: Records are sorted chronologically by timestamp (`IdleTime` epoch + flow `StartTime`). No random shuffling or cross-window random sampling is permitted.
* **Chronological Partitions**:
  1. **Benign Training Period ($T_{\text{train}}$)**: The initial pure benign capture period (flows with `Label == "Benign"` from the opening segment of Day 1/Day 2). Exclusively used to fit `RobustScaler`, `IsolationForest`, and `Autoencoder` baselines.
  2. **Validation Period ($T_{\text{val}}$)**: Subsequent benign and calibration windows used for threshold calibration ($D_{\text{rms}}$, CUSUM reference limits).
  3. **Test Period ($T_{\text{test}}$)**: Chronologically subsequent window sequence containing the attack campaigns (`UDPFlood`, `TCPConnectScan`, etc.) and mixed legitimate traffic.
* **Non-Overlapping Invariant**:
  $$\max(T_{\text{train}}) < \min(T_{\text{val}}) \le \max(T_{\text{val}}) < \min(T_{\text{test}})$$
  Guarantees zero target leakage into baseline calibration.
