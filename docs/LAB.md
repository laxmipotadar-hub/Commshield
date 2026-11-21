# CommShield 5G Lab Testbed Specification & Offline Telemetry Adapter

## 1. Overview and Lab Architecture

The CommShield Lab environment bridges live 3GPP Release 16 5G Standalone (SA) core network operations with automated telemetry evaluation. Telemetry is collected from an Open5GS core network and UERANSIM radio/UE emulation platform, processed by the cross-platform Lab Adapter (`lab/adapter.py`), and formatted into canonical windows saved to `data/lab/windows.jsonl`.

```
+-----------------------------------------------------------------------------------+
|                              5G Lab Testbed Architecture                          |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [ UERANSIM Emulator ]                     [ Open5GS 5G Core ]                    |
|  +--------------------+                    +------------------------------------+ |
|  | Multi-UE Emulators |  Radio / N1 / N2   | AMF  (Access & Mobility Mgmt)      | |
|  | - Sensors (sst-3)  | =================> | SMF  (Session Management Function) | |
|  | - Cameras (sst-1)  |      SCTP/NGAP     | UPF  (User Plane Function / TUN)   | |
|  | - AGVs    (sst-2)  |                    | AUSF / UDM / NRF / PCF / NSSF      | |
|  +--------------------+                    +------------------------------------+ |
|                                                              |                    |
|                                         Log & Metric Output  |                    |
|                                         - open5gs_amf.log    |                    |
|                                         - open5gs_upf.log    |                    |
|                                         - amf_metrics.json   v                    |
|                                            +------------------------------------+ |
|                                            | lab/sample_logs/ (Offline Capture) | |
|                                            +------------------------------------+ |
|                                                              |                    |
|                                            Offline Replay    v                    |
|                                            +------------------------------------+ |
|                                            | CommShield Lab Adapter             | |
|                                            | - HMAC-SHA256 Pseudonymisation     | |
|                                            | - Canonical Window Aggregation     | |
|                                            | - Schema Validator Enforcement     | |
|                                            +------------------------------------+ |
|                                                              |                    |
|                                            Validated Output  v                    |
|                                            +------------------------------------+ |
|                                            | data/lab/windows.jsonl             | |
|                                            +------------------------------------+ |
+-----------------------------------------------------------------------------------+
```

---

## 2. What the Lab Runs

The live lab testbed runs an end-to-end 5G Standalone network stack:

1. **Open5GS Core Network Functions**:
   * **AMF (`open5gs-amfd`)**: Handles UE registration, 5G-AKA authentication vectors, security mode control (NEA2 ciphering, NIA2 integrity), and NAS connection state management.
   * **SMF (`open5gs-smfd`)**: Manages PDU session contexts, IP address allocation, QoS flow profiles, and N4 session establishment via PFCP.
   * **UPF (`open5gs-upfd`)**: Encapsulates/decapsulates user-plane traffic over GTP-U tunnels anchored at the `ogstun` kernel network interface.
   * **NRF, AUSF, UDM, PCF, NSSF, BSF**: Supporting 5G service-based architecture (SBA) microservices coordinating discovery, credential storage, and slice selection policies.

2. **UERANSIM Radio Access Network & UE Emulation**:
   * **`nr-gnb`**: Emulates a 5G gNodeB base station, establishing SCTP associations over the N2 reference point to the AMF and user-plane GTP-U over N3 to the UPF.
   * **`nr-ue`**: Emulates software radio UEs with virtual USIM credentials, initiating 5G registration and establishing PDU sessions across target network slices.

---

## 3. Live vs Simulated Components

| Component | Status | Implementation Details |
| :--- | :--- | :--- |
| **5G Core Control Plane** | **Live** | Native Open5GS C daemons implementing 3GPP Release 16 specifications (AMF, SMF, NRF, AUSF, UDM). Real SCTP sockets, ASN.1 NGAP serialization, and NAS security procedures. |
| **User Plane Datapath** | **Live** | Linux kernel GTP-U tunnel (`ogstun`) processing real IP packets, encapsulation headers, and TEID assignments. |
| **N4 PFCP Signalling** | **Live** | Real UDP-based PFCP association between SMF and UPF (port 8805). |
| **Radio Channel (RF)** | **Simulated** | UERANSIM simulates the 5G NR physical and MAC layers over UDP socket loopback, removing the need for SDR hardware (USRP/BladeRF). |
| **UE Traffic Generators** | **Simulated** | Simulated hardware profiles inject representative sensor telemetry, camera video frames, and AGV teleoperation commands. |
| **Offline Telemetry** | **Offline Replay** | In development and test environments, captured Open5GS logs and metrics in `lab/sample_logs/` replay the exact telemetry offline. |

---

## 4. The Offline Fallback Architecture

To guarantee strict cross-platform compatibility across Windows 10/11 and Linux CI runners without requiring root privileges, kernel modules, or running daemons:

1. **Zero-Daemon Offline Execution**:
   * The adapter reads saved logs from `lab/sample_logs/` (`open5gs_amf.log`, `open5gs_upf.log`, and `amf_metrics.json`).
   * No active Open5GS core, SCTP network stack, or live lab access is required to generate or test canonical windows.

2. **HMAC-SHA256 Pseudonymisation**:
   * Raw subscriber identifiers (`imsi-9997...`) parsed from logs are hashed using HMAC-SHA256 with `COMMSHIELD_TWIN_HMAC_KEY`:
     $$\text{device\_id\_hash} = \text{HMAC-SHA256}(\text{key}, \text{raw\_imsi})$$
   * No raw IMSIs or SIM IDs ever escape into `data/lab/windows.jsonl`.

3. **Single Output Artifact**:
   * The adapter's sole persistent output is `data/lab/windows.jsonl`.
   * Each record is validated against `ml_engine/provisioning/schema.py` before serialization with `source="lab"`.

---

## 5. Verification Commands

### Windows (PowerShell)

```powershell
# 1. Run the lab adapter offline on sample logs:
python -m lab.adapter

# 2. Validate the generated canonical windows:
python -m lab.validate data\lab\windows.jsonl

# 3. Execute the lab adapter unit test suite (sample logs only, never a running core):
python -m unittest lab\test_adapter.py -v
```

### Ubuntu / Linux (Bash)

```bash
# 1. Run the lab adapter offline on sample logs:
python3 -m lab.adapter

# 2. Validate the generated canonical windows:
python3 -m lab.validate data/lab/windows.jsonl

# 3. Execute the lab adapter unit test suite (sample logs only, never a running core):
python3 -m unittest lab/test_adapter.py -v
```
