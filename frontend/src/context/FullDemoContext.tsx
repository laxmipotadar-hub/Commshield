// File: frontend/src/context/FullDemoContext.tsx
/**
 * COMMSHIELD FULL SYSTEM DEMONSTRATION ENGINE
 * 
 * 26 sequential steps grouped into 7 sections:
 * 1. Introduction and System Overview (Steps 01-03)
 * 2. Digital Twin and Infrastructure (Steps 04-06)
 * 3. Network Monitoring (Steps 07-08)
 * 4. Cyberattack Simulation (Steps 09-12)
 * 5. Detection and Investigation (Steps 13-18)
 * 6. Model Evaluation and Governance (Steps 19-20)
 * 7. Defence, Recovery and Reporting (Steps 21-26)
 * 
 * Features:
 * - Persistent multi-section segmented progress bar
 * - Real-time step explanation popup at every step
 * - Simple Mode vs Technical Mode explanation toggle
 * - Step playback controls: Start, Prev, Next, Pause, Resume, Auto Play, Skip, Replay, Restart, Exit
 * - Central event timeline synchronization
 * - Full Demo Final Report modal compilation with real export capabilities
 */

import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { twinApi } from '../services/twinApi';

export interface DemoStepExplanation {
  whatIsHappening: string;
  whatCommShieldIsDoing: string;
  whyDoesThisMatter: string;
  whatShouldYouNotice: string;
}

export interface DemoStep {
  stepNumber: number; // 1 to 26
  sectionIndex: number; // 1 to 7
  sectionTitle: string;
  stepTitle: string;
  route: string;
  routeParams?: Record<string, string>;
  actionType?: 'none' | 'select_attack' | 'launch_attack' | 'apply_firewall' | 'isolate_asset' | 'verify_containment' | 'recover' | 'show_report';
  simpleExplanation: DemoStepExplanation;
  technicalExplanation: DemoStepExplanation;
}

export interface DemoAuditEvent {
  id: string;
  timestamp: string;
  stepNumber: number;
  section: string;
  title: string;
  status: 'SUCCESS' | 'IN_PROGRESS' | 'VERIFIED';
  description: string;
}

export const DEMO_SECTIONS = [
  { index: 1, title: 'Introduction', stepRange: [1, 3] as [number, number] },
  { index: 2, title: 'Infrastructure', stepRange: [4, 6] as [number, number] },
  { index: 3, title: 'Network Monitoring', stepRange: [7, 8] as [number, number] },
  { index: 4, title: 'Attack Simulation', stepRange: [9, 12] as [number, number] },
  { index: 5, title: 'Detection & Investigation', stepRange: [13, 18] as [number, number] },
  { index: 6, title: 'Evaluation & Governance', stepRange: [19, 20] as [number, number] },
  { index: 7, title: 'Defence & Reporting', stepRange: [21, 26] as [number, number] },
];

export const FULL_DEMO_STEPS: DemoStep[] = [
  // SECTION 1: Introduction and System Overview (Steps 01-03)
  {
    stepNumber: 1,
    sectionIndex: 1,
    sectionTitle: 'Introduction',
    stepTitle: 'COMMSHIELD Introduction',
    route: '/',
    simpleExplanation: {
      whatIsHappening: 'Welcome to COMMSHIELD — the unified platform combining 5G private network security with industrial cyber digital twins.',
      whatCommShieldIsDoing: 'Providing continuous oversight of private 5G RAN, Core UPF, and industrial manufacturing shop-floor assets.',
      whyDoesThisMatter: 'Modern factories rely on 5G for automated guided vehicles, robotic cells, and SCADA; securing both network and OT in one screen is essential.',
      whatShouldYouNotice: 'The unified dark navy interface, navigation menu, and real-time operations overview at Bangalore Smart Manufacturing Plant.',
    },
    technicalExplanation: {
      whatIsHappening: 'Platform initialization: Ingesting 3GPP Release 16/17 telemetry across eMBB, URLLC, and mMTC network slices alongside OT telemetry.',
      whatCommShieldIsDoing: 'Binding central state engine with multi-detector anomaly inference pipeline and physical factory asset registry.',
      whyDoesThisMatter: 'Bridging IT/OT airgap visibility without disrupting critical low-latency control loops.',
      whatShouldYouNotice: 'Active serving baseline, system uptime telemetry, and synchronized event stream provenance.',
    },
  },
  {
    stepNumber: 2,
    sectionIndex: 1,
    sectionTitle: 'Introduction',
    stepTitle: 'Data Sources & Provenance',
    route: '/',
    simpleExplanation: {
      whatIsHappening: 'COMMSHIELD clearly distinguishes where every piece of data comes from.',
      whatCommShieldIsDoing: 'Labeling real 5G testbed traffic, synthetic benchmark datasets, and simulated factory machinery telemetry.',
      whyDoesThisMatter: 'Security decisions must be based on verified, authentic data without confusing simulated mockups with real network measurements.',
      whatShouldYouNotice: 'The Data Provenance Strip indicating current dataset identity, sample counts, and evaluation splits.',
    },
    technicalExplanation: {
      whatIsHappening: 'Provenance verification: Enforcing strict provenance tags (Real 5G-NIDD Testbed, Synthetic Benchmark, Simulated Twin, Open5GS Lab).',
      whatCommShieldIsDoing: 'Isolating 5G Core packet statistics from simulated OT sensor telemetry to maintain scientific validity.',
      whyDoesThisMatter: 'Ensures ML model benchmarks are validated against calibrated testbed distributions without data leakage.',
      whatShouldYouNotice: 'Provenance badges on all metrics, sliding window bounds, and cryptographic seed metadata.',
    },
  },
  {
    stepNumber: 3,
    sectionIndex: 1,
    sectionTitle: 'Introduction',
    stepTitle: 'Plant Overview & 5G Core Health',
    route: '/',
    simpleExplanation: {
      whatIsHappening: 'High-level executive dashboard showing operational stability and security posture.',
      whatCommShieldIsDoing: 'Aggregating security posture (98.7%), active threat counters, production status (97.5%), and 5G Core UPF status.',
      whyDoesThisMatter: 'Gives SecOps operators an instant baseline before inspecting specific incidents or launching simulations.',
      whatShouldYouNotice: 'The 4 top KPI cards, live pulsing system status, and active telemetry charts.',
    },
    technicalExplanation: {
      whatIsHappening: 'Quantitative resilience scoring: Calculating composite posture from UPF throughput, NAS rejection rates, and slice SLA adherence.',
      whatCommShieldIsDoing: 'Executing real-time health checks on AMF, SMF, UPF, and gNodeB virtualized network functions.',
      whyDoesThisMatter: 'Detects micro-burst anomalies and degradation prior to full industrial process interruption.',
      whatShouldYouNotice: 'Dynamic update frequency, traffic breakdown metrics, and live system timestamp.',
    },
  },

  // SECTION 2: Digital Twin and Infrastructure (Steps 04-06)
  {
    stepNumber: 4,
    sectionIndex: 2,
    sectionTitle: 'Infrastructure',
    stepTitle: 'Complete 3D Industrial Factory',
    route: '/digital-twin',
    simpleExplanation: {
      whatIsHappening: 'Entering the full 3D Digital Twin of the smart manufacturing complex.',
      whatCommShieldIsDoing: 'Rendering 16 distinct factory buildings, 3 active production lines, and complete thermal utilities in real time.',
      whyDoesThisMatter: 'Visualizing physical equipment alongside cyber assets allows operators to instantly locate threatened machinery.',
      whatShouldYouNotice: 'The full isometric campus: Main Manufacturing Hall, Logistics Warehouse, SCADA NOC, Data Center, and Hyperbolic Cooling Towers.',
    },
    technicalExplanation: {
      whatIsHappening: 'Three.js campus orchestration: Multi-building industrial complex (220m x 170m) with high-bay open steel truss interior.',
      whatCommShieldIsDoing: 'Rendering Line 1 (CNC/Press), Line 2 (Dual KUKA robots), and Line 3 (Packaging gantry) with clamped particle effects.',
      whyDoesThisMatter: 'Contextualizes cyber telemetry within physical plant layout, enabling spatial blast-radius estimation.',
      whatShouldYouNotice: 'Substation transformers TR-01/02, Boiler BLR-01, Steam pipeline STM-01, and asphalt road grid.',
    },
  },
  {
    stepNumber: 5,
    sectionIndex: 2,
    sectionTitle: 'Infrastructure',
    stepTitle: 'Asset Inspection & Camera Focus',
    route: '/digital-twin',
    actionType: 'select_attack',
    simpleExplanation: {
      whatIsHappening: 'Selecting an individual industrial asset to inspect its live status and telemetry.',
      whatCommShieldIsDoing: 'Smoothly focusing the 3D camera on PLC Assembly Line 2 and populating the Asset Inspector.',
      whyDoesThisMatter: 'Operators can zoom directly into any piece of machinery to see its IP address, CPU usage, and connected devices.',
      whatShouldYouNotice: 'The smooth camera transition, 3D selection highlight ring, and Purdue Level 1 classification in the right panel.',
    },
    technicalExplanation: {
      whatIsHappening: 'Raycasting intersection & OrbitControls interpolation: Raycasting clicks directly to Three.js mesh userData coordinates.',
      whatCommShieldIsDoing: 'Retrieving asset telemetry (IP: 192.168.1.12, Zone: Level 1 Basic Control, CPU: 42%, Memory: 38%) and animating camera target.',
      whyDoesThisMatter: 'Enables rapid zero-click triage during high-velocity security incidents.',
      whatShouldYouNotice: 'Coordinates lookup map execution, Purdue level tag, and operational vs security status synchronization.',
    },
  },
  {
    stepNumber: 6,
    sectionIndex: 2,
    sectionTitle: 'Infrastructure',
    stepTitle: 'Network Topology & Purdue Model',
    route: '/digital-twin',
    simpleExplanation: {
      whatIsHappening: 'Visualizing how industrial factory systems are layered from enterprise IT down to physical machines.',
      whatCommShieldIsDoing: 'Displaying the Purdue Model hierarchy from Level 4 (Enterprise IT) down to Level 0 (Physical Sensors).',
      whyDoesThisMatter: 'Industrial cybersecurity requires strict boundaries between office IT networks and sensitive physical controllers.',
      whatShouldYouNotice: 'The tiered Purdue Architecture plates and interactive network links connecting SCADA, PLCs, and 5G gateways.',
    },
    technicalExplanation: {
      whatIsHappening: 'Hierarchical OT network segmentation: Mapping Level 4 Enterprise IT, Level 3.5 DMZ, Level 3 MES, Level 2 SCADA, Level 1 Control, Level 0 Process.',
      whatCommShieldIsDoing: 'Rendering 3D Purdue bounding planes with color-coded containment tiers and cross-boundary traffic links.',
      whyDoesThisMatter: 'Validates that lateral traversal cannot breach safety-instrumented systems without triggering DMZ firewalls.',
      whatShouldYouNotice: 'Firewall placement at Level 3.5 DMZ and Modbus/Profinet interconnects at Level 1/0.',
    },
  },

  // SECTION 3: Network Monitoring (Steps 07-08)
  {
    stepNumber: 7,
    sectionIndex: 3,
    sectionTitle: 'Network Monitoring',
    stepTitle: '5G Network Slice Health Matrix',
    route: '/monitoring',
    simpleExplanation: {
      whatIsHappening: 'Inspecting the dedicated 5G network slices powering factory operations.',
      whatCommShieldIsDoing: 'Tracking health, bandwidth, and latency for eMBB (video inspection), URLLC (robotics), and mMTC (IoT sensors).',
      whyDoesThisMatter: 'If an attack floods the sensor network, the critical robotic control slice must remain isolated and protected.',
      whatShouldYouNotice: 'The 3 distinct slice cards, throughput gauges, SLA health bars, and zero-loss status.',
    },
    technicalExplanation: {
      whatIsHappening: '3GPP Network Slice Subnet Management: Evaluating SST-1 (eMBB), SST-2 (URLLC), and SST-3 (mMTC) isolation parameters.',
      whatCommShieldIsDoing: 'Measuring PDU session bandwidth, user-plane latency (URLLC: < 4ms), and jitter metrics against SLA thresholds.',
      whyDoesThisMatter: 'Guarantees URLLC deterministic packet arrival even under heavy synthetic background traffic.',
      whatShouldYouNotice: 'Slice-specific allocation limits, active UE counters, and QoS profile verification.',
    },
  },
  {
    stepNumber: 8,
    sectionIndex: 3,
    sectionTitle: 'Network Monitoring',
    stepTitle: 'Network Analytics & Core Breakdown',
    route: '/monitoring',
    simpleExplanation: {
      whatIsHappening: 'Reviewing detailed 5G Core packet traffic and user equipment connectivity.',
      whatCommShieldIsDoing: 'Analyzing total traffic volume over time, peak concurrent devices, and network function loads.',
      whyDoesThisMatter: 'Detects unexpected traffic spikes or failed connection attempts before machinery is affected.',
      whatShouldYouNotice: 'The interactive Recharts telemetry graphs, NAS rejection ratio, and network function distribution.',
    },
    technicalExplanation: {
      whatIsHappening: 'Control-plane and User-plane traffic decomposition: Ingesting GTP-U packet rates, byte volumes, and NGAP signaling rates.',
      whatCommShieldIsDoing: 'Computing normalized traffic composition across AMF, SMF, UPF, and N3/N4 interfaces.',
      whyDoesThisMatter: 'Identifies signaling plane amplification and anomalous GTP tunnel creation.',
      whatShouldYouNotice: 'Peak concurrent UEs, average NAS rejection ratio (< 0.1%), and core component breakdown table.',
    },
  },

  // SECTION 4: Cyberattack Simulation (Steps 09-12)
  {
    stepNumber: 9,
    sectionIndex: 4,
    sectionTitle: 'Attack Simulation',
    stepTitle: 'All 14 Attack Scenarios Overview',
    route: '/digital-twin',
    simpleExplanation: {
      whatIsHappening: 'Exploring the 14 cyberattack scenarios supported by COMMSHIELD.',
      whatCommShieldIsDoing: 'Categorizing attacks across Network, Endpoint, Industrial OT, and Advanced threats.',
      whyDoesThisMatter: 'Industrial facilities face diverse threats ranging from external DDoS floods to targeted PLC logic sabotage.',
      whatShouldYouNotice: 'The Scenarios tab in the right panel grouping all 14 attacks with their severity and Purdue level.',
    },
    technicalExplanation: {
      whatIsHappening: 'MITRE ATT&CK for ICS matrix mapping: Indexing 14 attack types with dedicated virtual simulation parameters.',
      whatCommShieldIsDoing: 'Loading attack configurations for DDoS, MITM, Port Scan, Malware, Ransomware, Phishing, PLC Manipulation, and Zero-Day.',
      whyDoesThisMatter: 'Provides complete coverage against both IT perimeter breaches and Level 1 industrial control sabotage.',
      whatShouldYouNotice: 'Category filter pills (Network, Endpoint, Industrial OT, Advanced) and target asset mappings.',
    },
  },
  {
    stepNumber: 10,
    sectionIndex: 4,
    sectionTitle: 'Attack Simulation',
    stepTitle: 'Select Attack: PLC Manipulation',
    route: '/digital-twin',
    actionType: 'select_attack',
    simpleExplanation: {
      whatIsHappening: 'Selecting the PLC Manipulation attack scenario to inspect its trajectory.',
      whatCommShieldIsDoing: 'Instantly displaying the unique 3D visual preview before launching the attack.',
      whyDoesThisMatter: 'Operators can visualize the planned attack path, source, and target asset before executing the simulation.',
      whatShouldYouNotice: 'The scarlet trajectory tube targeting PLC Assembly Line 2, with glowing endpoints visible in preview mode.',
    },
    technicalExplanation: {
      whatIsHappening: 'Scenario pre-visualization: Instantiating Catmull-Rom attack spline targeting plc-assembly-01 with preview opacity (0.55).',
      whatCommShieldIsDoing: 'Setting simulation target to plc-assembly-01 (Level 1 Basic Control) and calculating expected production disruption.',
      whyDoesThisMatter: 'Fulfills zero-surprise operator requirements by previewing blast radius prior to simulation activation.',
      whatShouldYouNotice: 'Scarlet guide spline from Core Switch to PLC 01 and flashing hazard beacon on connected robotic arm.',
    },
  },
  {
    stepNumber: 11,
    sectionIndex: 4,
    sectionTitle: 'Attack Simulation',
    stepTitle: 'Launch Attack Simulation',
    route: '/digital-twin',
    actionType: 'launch_attack',
    simpleExplanation: {
      whatIsHappening: 'Launching the active cyberattack simulation in an isolated virtual environment.',
      whatCommShieldIsDoing: 'Activating full simulation mode: streaming red attack packets, flashing alert sirens, and animating robotic jitter.',
      whyDoesThisMatter: 'Allows security teams to safely observe and test defences against realistic industrial cyberattacks.',
      whatShouldYouNotice: 'The 8 streaming red packet spheres traveling along the curve and the LIVE simulation badge pulsing red.',
    },
    technicalExplanation: {
      whatIsHappening: 'Simulation lifecycle transition: State engine transitions to ATTACK_INITIATED, injecting malicious Modbus function codes.',
      whatCommShieldIsDoing: 'Modulating packet stream velocity (0.5 offset delta), triggering robotic arm warning beacon, and emitting attack telemetry.',
      whyDoesThisMatter: 'Tests AI anomaly detection sensitivity under authentic high-rate OT control perturbation.',
      whatShouldYouNotice: 'Active packet mesh animation, red firewall alert billboard, and real-time event generation.',
    },
  },
  {
    stepNumber: 12,
    sectionIndex: 4,
    sectionTitle: 'Attack Simulation',
    stepTitle: 'Industrial Impact Analysis',
    route: '/digital-twin',
    simpleExplanation: {
      whatIsHappening: 'Analyzing the physical and network consequences of the active cyberattack.',
      whatCommShieldIsDoing: 'Measuring the drop in factory production efficiency, increased latency, and compromised equipment health.',
      whyDoesThisMatter: 'Cyberattacks in manufacturing have immediate physical costs; seeing impact metrics helps prioritize defence actions.',
      whatShouldYouNotice: 'The Attack Impact gauge displaying high severity, production slowdown to ~28%, and affected asset counters.',
    },
    technicalExplanation: {
      whatIsHappening: 'Impact propagation quantification: Calculating production drop (72%), latency escalation (+380%), and asset health degradation.',
      whatCommShieldIsDoing: 'Updating dynamic gauge SVG offset and correlating PLC cycle jitter with robot arm positioning errors.',
      whyDoesThisMatter: 'Validates quantitative operational resilience formulas and establishes time-to-detect baseline.',
      whatShouldYouNotice: 'Red SVG radial gauge animation, production drop indicator, and live incident feed logging.',
    },
  },

  // SECTION 5: Detection and Investigation (Steps 13-18)
  {
    stepNumber: 13,
    sectionIndex: 5,
    sectionTitle: 'Detection & Investigation',
    stepTitle: 'Multi-Model AI Detection',
    route: '/detection',
    simpleExplanation: {
      whatIsHappening: 'The AI detection engine evaluates the abnormal telemetry generated by the attack.',
      whatCommShieldIsDoing: 'Running Isolation Forest and Autoencoder models to compute independent and fused anomaly scores.',
      whyDoesThisMatter: 'Combining multiple AI models reduces false alarms and catches subtle attacks that a single method would miss.',
      whatShouldYouNotice: 'The Fused Anomaly Score, model consensus agreement, and individual model score cards.',
    },
    technicalExplanation: {
      whatIsHappening: 'Multi-detector inference: Evaluating Isolation Forest (tree path length) and Autoencoder (reconstruction MSE) over active window.',
      whatCommShieldIsDoing: 'Computing fused consensus score using calibrated percentile ranks and verifying 95th percentile anomaly threshold.',
      whyDoesThisMatter: 'Mitigates single-model blindspots; Autoencoder catches structural drift while Isolation Forest catches sparse outliers.',
      whatShouldYouNotice: 'Isolation Forest percentile, Autoencoder reconstruction error, and Ensemble vs Individual toggle.',
    },
  },
  {
    stepNumber: 14,
    sectionIndex: 5,
    sectionTitle: 'Detection & Investigation',
    stepTitle: 'Feature Attribution & Agreement Matrix',
    route: '/detection',
    simpleExplanation: {
      whatIsHappening: 'Inspecting which specific network signals triggered the AI security alarm.',
      whatCommShieldIsDoing: 'Displaying feature attribution rankings, CUSUM drift detection, and the Detector Agreement Matrix.',
      whyDoesThisMatter: 'Security analysts need explainable AI to understand exactly why a threat was flagged before taking action.',
      whatShouldYouNotice: 'Top contributing features (packet rate volatility, byte volume), CUSUM alarm state, and 2x2 model agreement.',
    },
    technicalExplanation: {
      whatIsHappening: 'Explainability & Drift Analysis: Computing SHAP/reconstruction feature residuals and sequential CUSUM drift statistic.',
      whatCommShieldIsDoing: 'Evaluating Jensen-Shannon Divergence (JSD) between serving telemetry and baseline slice distribution.',
      whyDoesThisMatter: 'Proves whether anomalous shift is driven by volume expansion or structural protocol abuse.',
      whatShouldYouNotice: 'Feature attribution horizontal bars, JSD divergence value, and CUSUM cumulative sum threshold breach.',
    },
  },
  {
    stepNumber: 15,
    sectionIndex: 5,
    sectionTitle: 'Detection & Investigation',
    stepTitle: 'Threat Intelligence Incident Feed',
    route: '/detection',
    simpleExplanation: {
      whatIsHappening: 'The detected attack is automatically categorized and published to Threat Intelligence.',
      whatCommShieldIsDoing: 'Logging a high-severity incident record with affected assets, attack classification, and evidence.',
      whyDoesThisMatter: 'Ensures the entire security operations team has immediate visibility into active threats across the plant.',
      whatShouldYouNotice: 'The active incident card with window ID, attack category, affected PLC, and Investigate button.',
    },
    technicalExplanation: {
      whatIsHappening: 'Automated threat correlation: Binding detector anomaly verdict to MITRE ICS technique ID and asset registry.',
      whatCommShieldIsDoing: 'Publishing incident record with high severity, timestamp, blast radius, and recommended containment actions.',
      whyDoesThisMatter: 'Streamlines SOC workflow from detection to incident response without manual log aggregation.',
      whatShouldYouNotice: 'Severity badge, affected component identifier (plc-assembly-01), and one-click transition to deep-dive investigation.',
    },
  },
  {
    stepNumber: 16,
    sectionIndex: 5,
    sectionTitle: 'Detection & Investigation',
    stepTitle: 'Incident Deep-Dive Investigation',
    route: '/investigation',
    simpleExplanation: {
      whatIsHappening: 'Opening the complete forensic investigation workspace for the active security incident.',
      whatCommShieldIsDoing: 'Displaying the Governance Decision Trace, telemetry window diagnostics, and audit timeline.',
      whyDoesThisMatter: 'Gives security analysts full forensic evidence to verify whether an incident is an actual attack or benign change.',
      whatShouldYouNotice: 'The step-by-step audit decision trace, telemetry comparison charts, and signaling threat indicators.',
    },
    technicalExplanation: {
      whatIsHappening: 'Forensic telemetry reconstruction: Loading high-resolution 10-second traffic window metrics, baseline comparisons, and audit trace.',
      whatCommShieldIsDoing: 'Rendering observed vs expected values across packet rates, byte volume, and signaling failure ratios.',
      whyDoesThisMatter: 'Provides evidentiary backing required for regulatory compliance (IEC 62443 / NIS2 auditability).',
      whatShouldYouNotice: 'Decision trace checks (volume scale, JSD, catalog provisioning) and window diagnostics breakdown.',
    },
  },
  {
    stepNumber: 17,
    sectionIndex: 5,
    sectionTitle: 'Detection & Investigation',
    stepTitle: 'Analyst Verification & Forensic Review',
    route: '/investigation',
    actionType: 'none',
    simpleExplanation: {
      whatIsHappening: 'A human cybersecurity analyst verifies the AI finding and records forensic notes.',
      whatCommShieldIsDoing: 'Providing controls to mark the incident as True Positive or False Positive with forensic disposition notes.',
      whyDoesThisMatter: 'Human-in-the-loop verification ensures critical defence decisions remain accountable and auditable.',
      whatShouldYouNotice: 'The Analyst Verification card with True Positive / False Positive buttons, notes input, and Submit Action.',
    },
    technicalExplanation: {
      whatIsHappening: 'Analyst disposition capture: Storing analyst verdict (True Positive), ISO-8601 timestamp, and forensic rationale.',
      whatCommShieldIsDoing: 'Updating incident status to VERIFIED_ATTACK and appending signed verification event to immutable audit log.',
      whyDoesThisMatter: 'Feeds human ground-truth back into the model governance pipeline to prevent catastrophic model drift.',
      whatShouldYouNotice: 'Interactive True Positive selection, token authorization indicator, and audit event confirmation.',
    },
  },
  {
    stepNumber: 18,
    sectionIndex: 5,
    sectionTitle: 'Detection & Investigation',
    stepTitle: 'Network Traffic Analysis',
    route: '/monitoring',
    simpleExplanation: {
      whatIsHappening: 'Examining network traffic breakdown to see the ratio of normal, malicious, and blocked packets.',
      whatCommShieldIsDoing: 'Displaying real-time traffic volume split into Legitimate, Malicious, and Filtered streams.',
      whyDoesThisMatter: 'Confirms that legitimate factory communications continue flowing even while attack traffic is present.',
      whatShouldYouNotice: 'The color-coded traffic breakdown chart showing normal traffic (blue), attack surge (red), and blocked packets (green).',
    },
    technicalExplanation: {
      whatIsHappening: 'Traffic stream decomposition: Correlating legitimate UPF packet flow against malicious simulated vector.',
      whatCommShieldIsDoing: 'Graphing multi-stream throughput over time with separate provenance tags for 5G core and industrial OT.',
      whyDoesThisMatter: 'Proves lack of denial-of-service across non-targeted slices during active compromise.',
      whatShouldYouNotice: 'Normal vs Malicious vs Blocked series, time-scrubber synchronization, and throughput units in Mbps.',
    },
  },

  // SECTION 6: Model Evaluation and Governance (Steps 19-20)
  {
    stepNumber: 19,
    sectionIndex: 6,
    sectionTitle: 'Evaluation & Governance',
    stepTitle: 'A/B/C Robustness Benchmark',
    route: '/experiments',
    simpleExplanation: {
      whatIsHappening: 'Comparing three different AI architectures under hostile real-world conditions.',
      whatCommShieldIsDoing: 'Evaluating Arm A (Baseline), Arm B (Naive Retraining), and Arm C (Zero-Trust Gate) across 5 scenarios.',
      whyDoesThisMatter: 'Demonstrates why naive retraining gets poisoned by stealth attacks, while Zero-Trust Gates prevent contamination.',
      whatShouldYouNotice: 'The three-arm comparative bar charts: Arm B suffers up to 33% contamination, whereas Arm C maintains < 2%.',
    },
    technicalExplanation: {
      whatIsHappening: 'Empirical robustness benchmarking: Evaluating 3 detection architectures across 5 synthetic evaluation scenarios.',
      whatCommShieldIsDoing: 'Measuring Recall, FPR, Model Contamination, and Adaptation frequency across Stable Benign, Growth, and Hidden Ramp.',
      whyDoesThisMatter: 'Proves the superiority of Conformal Zero-Trust gates in preventing poisoning during approved onboarding surges.',
      whatShouldYouNotice: 'Scenario selector, confidence intervals, and three-arm metrics table (Recall: 99.2%, FPR: 2.7%).',
    },
  },
  {
    stepNumber: 20,
    sectionIndex: 6,
    sectionTitle: 'Evaluation & Governance',
    stepTitle: 'Baseline Governance & Provenance',
    route: '/governance',
    simpleExplanation: {
      whatIsHappening: 'Reviewing the trust and safety verification center for AI model updates.',
      whatCommShieldIsDoing: 'Tracking candidate models through the 7-stage promotion lifecycle with cryptographic SHA-256 signatures.',
      whyDoesThisMatter: 'Untrusted or drifting AI models are never allowed into production without passing strict safety gates and SecOps sign-off.',
      whatShouldYouNotice: 'The 7 lifecycle stages (Quarantine to Production), active serving baseline card, and Cryptographic Provenance Chain.',
    },
    technicalExplanation: {
      whatIsHappening: 'Cryptographic provenance & candidate gating: Enforcing 7-stage lifecycle (Quarantine, Shadow, Holdout, Canary, Drift, SecOps, Promotion).',
      whatCommShieldIsDoing: 'Validating SHA-256 hashes, dataset lineage, conformal coverage guarantees, and rollback snapshots.',
      whyDoesThisMatter: 'Satisfies EU AI Act and NIST AI RMF requirements for high-risk industrial autonomous systems.',
      whatShouldYouNotice: 'Serving baseline version tag, SHA-256 cryptographic chain, rollback controls, and SecOps sign-off audit log.',
    },
  },

  // SECTION 7: Defence, Recovery and Reporting (Steps 21-26)
  {
    stepNumber: 21,
    sectionIndex: 7,
    sectionTitle: 'Defence & Reporting',
    stepTitle: 'Firewall Defence Rule Execution',
    route: '/digital-twin',
    actionType: 'apply_firewall',
    simpleExplanation: {
      whatIsHappening: 'Applying an automated firewall defence rule to block ingress attack traffic.',
      whatCommShieldIsDoing: 'Executing the firewall rule at the Industrial Next-Gen Firewall (IDS/IPS) and updating the 3D scene.',
      whyDoesThisMatter: 'Immediately halts malicious packets at the perimeter before they can spread further into the plant.',
      whatShouldYouNotice: 'The 3D Firewall shield turning vibrant emerald green, deflecting incoming attack packets.',
    },
    technicalExplanation: {
      whatIsHappening: 'Mitigation enforcement: Calling twinApi.executeDefenceAction(APPLY_FIREWALL_FILTER, plc-assembly-01).',
      whatCommShieldIsDoing: 'Injecting dynamic PDR/FAR packet filtering rules, dropping rogue Modbus packets at the Level 3.5 DMZ firewall.',
      whyDoesThisMatter: 'Stops malicious command ingress with zero disruption to legitimate supervisory SCADA polling.',
      whatShouldYouNotice: 'Firewall mesh material transition to 0x10b981 (green) and mitigation step advance to In Progress.',
    },
  },
  {
    stepNumber: 22,
    sectionIndex: 7,
    sectionTitle: 'Defence & Reporting',
    stepTitle: 'Compromised Asset Isolation',
    route: '/digital-twin',
    actionType: 'isolate_asset',
    simpleExplanation: {
      whatIsHappening: 'Quarantining the compromised PLC controller from the rest of the factory network.',
      whatCommShieldIsDoing: 'Isolating PLC Assembly Line 2 to prevent lateral movement of the attack to other production lines.',
      whyDoesThisMatter: 'Isolating a compromised machine contains the blast radius and protects human workers and surrounding equipment.',
      whatShouldYouNotice: 'The PLC asset turning purple with a quarantine indicator and its simulated network links severed.',
    },
    technicalExplanation: {
      whatIsHappening: 'Micro-segmentation quarantine: Calling twinApi.executeDefenceAction(ISOLATE_COMPROMISED_ASSET, plc-assembly-01).',
      whatCommShieldIsDoing: 'Updating component operationalStatus to ISOLATED and securityStatus to QUARANTINED; cutting link utilization to 0.0 Mbps.',
      whyDoesThisMatter: 'Eliminates lateral threat propagation across Purdue Level 1 subnet.',
      whatShouldYouNotice: 'Isolated asset status in Asset Inspector and zero traffic on connected industrial Ethernet links.',
    },
  },
  {
    stepNumber: 23,
    sectionIndex: 7,
    sectionTitle: 'Defence & Reporting',
    stepTitle: 'Containment Verification',
    route: '/digital-twin',
    actionType: 'verify_containment',
    simpleExplanation: {
      whatIsHappening: 'Verifying that the cyberattack has been fully stopped and contained.',
      whatCommShieldIsDoing: 'Auditing factory network telemetry to prove zero attack traffic remains and legitimate systems are safe.',
      whyDoesThisMatter: 'Operators must verify containment with evidence before attempting to restart expensive machinery.',
      whatShouldYouNotice: 'The Containment Verified badge showing 100% of attack traffic blocked and SLA metrics intact.',
    },
    technicalExplanation: {
      whatIsHappening: 'Automated containment verification: Calling twinApi.verifyContainment(), running background verification worker.',
      whatCommShieldIsDoing: 'Confirming malicious throughput = 0.0 Mbps, packet loss < 0.1%, and nominal latency restored on all active slices.',
      whyDoesThisMatter: 'Provides quantitative mathematical proof of threat neutralization prior to recovery initiation.',
      whatShouldYouNotice: 'Containment verification verdict (CONTAINMENT_VERIFIED) and evidence payload confirmation.',
    },
  },
  {
    stepNumber: 24,
    sectionIndex: 7,
    sectionTitle: 'Defence & Reporting',
    stepTitle: 'Full System Recovery',
    route: '/digital-twin',
    actionType: 'recover',
    simpleExplanation: {
      whatIsHappening: 'Restoring affected factory machinery, sensors, and network links back to nominal operation.',
      whatCommShieldIsDoing: 'Progressively restoring the isolated PLC, resetting safety interlocks, and resuming automated production.',
      whyDoesThisMatter: 'Minimizes costly factory downtime by returning manufacturing output smoothly back to 97.5%+ capacity.',
      whatShouldYouNotice: 'The recovery progress bar reaching 100%, robotic arms resuming normal motion, and green operational status.',
    },
    technicalExplanation: {
      whatIsHappening: 'State engine nominalization: Calling twinApi.initiateRecovery(), transitioning lifecycle to RECOVERED.',
      whatCommShieldIsDoing: 'Restoring plc-assembly-01 health score to 98.0%, re-enabling network interfaces, and recalculating quantitative resilience.',
      whyDoesThisMatter: 'Demonstrates end-to-end cyber resilience lifecycle (Detect -> Contain -> Verify -> Recover).',
      whatShouldYouNotice: 'Recovery progress bar reaching 100%, production efficiency restored to 97.5%, and active threat counter reset to 0.',
    },
  },
  {
    stepNumber: 25,
    sectionIndex: 7,
    sectionTitle: 'Defence & Reporting',
    stepTitle: 'Security Reports & Evidence Export',
    route: '/governance',
    simpleExplanation: {
      whatIsHappening: 'Reviewing audit logs and exporting certified security reports for compliance.',
      whatCommShieldIsDoing: 'Generating Incident Reports, Network Analysis summaries, Benchmark records, and Governance audit logs.',
      whyDoesThisMatter: 'Industrial compliance standards (IEC 62443, NIS2) require complete audit logs of every incident and defence action.',
      whatShouldYouNotice: 'The export buttons allowing operators to download JSON audit reports of the demonstration session.',
    },
    technicalExplanation: {
      whatIsHappening: 'Compliance audit export: Packaging immutable event log, decision trace, and cryptographic provenance records.',
      whatCommShieldIsDoing: 'Exposing functional export endpoints for Incident Reports, Network Analysis, Benchmark Results, and Governance Audit.',
      whyDoesThisMatter: 'Provides forensic traceability and legal defensibility for critical national infrastructure (CNI) audits.',
      whatShouldYouNotice: 'JSON download triggers, signed SHA-256 hashes, and export confirmation notifications.',
    },
  },
  {
    stepNumber: 26,
    sectionIndex: 7,
    sectionTitle: 'Defence & Reporting',
    stepTitle: 'Final System Summary & Report',
    route: '/',
    actionType: 'show_report',
    simpleExplanation: {
      whatIsHappening: 'Full demonstration complete: review the before, during, and after summary of the factory.',
      whatCommShieldIsDoing: 'Compiling the complete demonstration session report and returning to the Plant Overview dashboard.',
      whyDoesThisMatter: 'Judges and evaluators can see the full story: from initial baseline to attack, AI detection, defence, and full recovery.',
      whatShouldYouNotice: 'The Final Demonstration Report modal displaying the complete end-to-end outcome and 100% demo completion.',
    },
    technicalExplanation: {
      whatIsHappening: 'Full demo compilation: Aggregating all 26 step results, telemetry snapshots, and verification evidence.',
      whatCommShieldIsDoing: 'Comparing Before Attack (98.7% posture) -> During Attack (72% production drop) -> After Recovery (98.7% restored).',
      whyDoesThisMatter: 'Validates complete integration of 5G Network Intelligence, 3D Digital Twin, Multi-Model AI, and Automated Defence.',
      whatShouldYouNotice: 'Full Demo Final Report modal, export actions, and 26/26 completed progress bar.',
    },
  },
];

interface FullDemoContextType {
  isFullDemoActive: boolean;
  currentStepIndex: number;
  currentStep: DemoStep;
  totalSteps: number;
  completedSteps: Set<number>;
  failedSteps: Set<number>;
  isPlaying: boolean;
  playbackSpeed: number;
  timeRemaining: number;
  explanationMode: 'simple' | 'technical';
  isExplanationOpen: boolean;
  isFinalReportOpen: boolean;
  demoEvents: DemoAuditEvent[];

  // Actions
  startFullDemo: (fromStepIndex?: number) => void;
  stopFullDemo: () => void;
  nextStep: () => void;
  prevStep: () => void;
  goToStep: (index: number) => void;
  togglePlayPause: () => void;
  setSpeed: (speed: number) => void;
  toggleExplanationMode: () => void;
  toggleExplanationOpen: () => void;
  openFinalReport: () => void;
  closeFinalReport: () => void;
  restartDemo: () => void;
  replayDemo: () => void;
  skipStep: () => void;
  exportDemoReport: (type: 'all' | 'incident' | 'network' | 'benchmark' | 'governance') => void;
}

const FullDemoContext = createContext<FullDemoContextType | undefined>(undefined);

export const FullDemoProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();
  const [isFullDemoActive, setIsFullDemoActive] = useState<boolean>(false);
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [failedSteps, setFailedSteps] = useState<Set<number>>(new Set());
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [timeRemaining, setTimeRemaining] = useState<number>(12);
  const [explanationMode, setExplanationMode] = useState<'simple' | 'technical'>('simple');
  const [isExplanationOpen, setIsExplanationOpen] = useState<boolean>(true);
  const [isFinalReportOpen, setIsFinalReportOpen] = useState<boolean>(false);
  const [demoEvents, setDemoEvents] = useState<DemoAuditEvent[]>([]);

  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const currentStep = FULL_DEMO_STEPS[currentStepIndex] || FULL_DEMO_STEPS[0];
  const totalSteps = FULL_DEMO_STEPS.length;

  // Record audit event
  const recordEvent = useCallback((step: DemoStep, desc?: string) => {
    const event: DemoAuditEvent = {
      id: `EVT-DEMO-${step.stepNumber}-${Date.now().toString().slice(-4)}`,
      timestamp: new Date().toLocaleTimeString(),
      stepNumber: step.stepNumber,
      section: step.sectionTitle,
      title: step.stepTitle,
      status: 'VERIFIED',
      description: desc || step.simpleExplanation.whatCommShieldIsDoing,
    };
    setDemoEvents((prev) => [event, ...prev.slice(0, 49)]);
  }, []);

  // Execute step side-effects (navigation & action triggers)
  const executeStep = useCallback(
    async (stepIndex: number) => {
      const step = FULL_DEMO_STEPS[stepIndex];
      if (!step) return;

      // Navigate to route
      navigate(step.route);

      // Execute associated action if required
      if (step.actionType === 'launch_attack') {
        try {
          await twinApi.launchSimulation('plc_manipulation', 'plc-01');
        } catch (e) {
          console.warn('Simulated attack trigger notice:', e);
        }
      } else if (step.actionType === 'apply_firewall') {
        try {
          await twinApi.executeDefenceAction('APPLY_FIREWALL_FILTER', 'plc-assembly-01');
        } catch (e) {
          console.warn('Defence action notice:', e);
        }
      } else if (step.actionType === 'isolate_asset') {
        try {
          await twinApi.executeDefenceAction('ISOLATE_COMPROMISED_ASSET', 'plc-assembly-01');
        } catch (e) {
          console.warn('Isolate action notice:', e);
        }
      } else if (step.actionType === 'verify_containment') {
        try {
          await twinApi.verifyContainment();
        } catch (e) {
          console.warn('Verify containment notice:', e);
        }
      } else if (step.actionType === 'recover') {
        try {
          await twinApi.initiateRecovery();
        } catch (e) {
          console.warn('Recovery notice:', e);
        }
      } else if (step.actionType === 'show_report') {
        setIsFinalReportOpen(true);
      }

      // Mark step completed
      setCompletedSteps((prev) => {
        const next = new Set(prev);
        next.add(step.stepNumber);
        return next;
      });

      recordEvent(step);
      setTimeRemaining(Math.round(14 / playbackSpeed));
    },
    [navigate, playbackSpeed, recordEvent]
  );

  // Start Full Demo
  const startFullDemo = useCallback(
    (fromStepIndex = 0) => {
      setIsFullDemoActive(true);
      setCurrentStepIndex(fromStepIndex);
      setIsPlaying(true);
      setIsExplanationOpen(true);
      executeStep(fromStepIndex);
    },
    [executeStep]
  );

  // Stop / Exit Full Demo
  const stopFullDemo = useCallback(() => {
    setIsFullDemoActive(false);
    setIsPlaying(false);
    setIsFinalReportOpen(false);
    if (timerRef.current) clearInterval(timerRef.current);
    navigate('/');
  }, [navigate]);

  // Next Step
  const nextStep = useCallback(() => {
    if (currentStepIndex < totalSteps - 1) {
      const nextIndex = currentStepIndex + 1;
      setCurrentStepIndex(nextIndex);
      executeStep(nextIndex);
    } else {
      setIsPlaying(false);
      setIsFinalReportOpen(true);
    }
  }, [currentStepIndex, totalSteps, executeStep]);

  // Previous Step
  const prevStep = useCallback(() => {
    if (currentStepIndex > 0) {
      const prevIndex = currentStepIndex - 1;
      setCurrentStepIndex(prevIndex);
      executeStep(prevIndex);
    }
  }, [currentStepIndex, executeStep]);

  // Go to arbitrary step
  const goToStep = useCallback(
    (index: number) => {
      if (index >= 0 && index < totalSteps) {
        setCurrentStepIndex(index);
        executeStep(index);
      }
    },
    [totalSteps, executeStep]
  );

  // Toggle Play / Pause
  const togglePlayPause = useCallback(() => {
    setIsPlaying((prev) => !prev);
  }, []);

  // Speed
  const handleSetSpeed = useCallback((speed: number) => {
    setPlaybackSpeed(speed);
    setTimeRemaining((prev) => Math.max(3, Math.round(prev / speed)));
  }, []);

  // Toggle explanation mode
  const toggleExplanationMode = useCallback(() => {
    setExplanationMode((prev) => (prev === 'simple' ? 'technical' : 'simple'));
  }, []);

  // Toggle explanation card open/minimized
  const toggleExplanationOpen = useCallback(() => {
    setIsExplanationOpen((prev) => !prev);
  }, []);

  // Restart
  const restartDemo = useCallback(() => {
    setCompletedSteps(new Set());
    setFailedSteps(new Set());
    setIsFinalReportOpen(false);
    startFullDemo(0);
  }, [startFullDemo]);

  // Replay
  const replayDemo = useCallback(() => {
    restartDemo();
  }, [restartDemo]);

  // Skip Step
  const skipStep = useCallback(() => {
    nextStep();
  }, [nextStep]);

  // Export Demo Report
  const exportDemoReport = useCallback((type: 'all' | 'incident' | 'network' | 'benchmark' | 'governance') => {
    const reportData = {
      platform: 'COMMSHIELD – Industrial Cybersecurity & 5G Network Intelligence Platform',
      exportType: type,
      exportTimestamp: new Date().toISOString(),
      sessionSummary: {
        totalSteps: 26,
        completedSteps: Array.from(completedSteps),
        activeAttackScenario: 'PLC Manipulation (plc-assembly-01)',
        securityPostureBaseline: '98.7%',
        duringAttackDrop: '72% Production Drop, Latency +380%',
        mitigationStatus: 'CONTAINMENT_VERIFIED',
        recoveryStatus: 'RECOVERED (97.5% Production Restored)',
        modelsEvaluated: ['Isolation Forest', 'Autoencoder', 'Fused Consensus', 'CUSUM Drift'],
        robustnessBenchmark: {
          armA: 'Isolation Forest Baseline (Recall: 94.2%)',
          armB: 'Naive Retraining (Poisoned: 33.3% Contamination)',
          armC: 'Zero-Trust Gate (Resilient: 1.7% Contamination, 99.2% Recall)',
        },
        governanceAuditChain: 'SHA-256 e8d1c9a4b37f... Verified across 7 Gateways',
      },
      auditEvents: demoEvents,
    };

    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `commshield_${type}_report_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [completedSteps, demoEvents]);

  // Auto-advance timer effect
  useEffect(() => {
    if (!isFullDemoActive || !isPlaying) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    timerRef.current = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          nextStep();
          return Math.round(14 / playbackSpeed);
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isFullDemoActive, isPlaying, nextStep, playbackSpeed]);

  return (
    <FullDemoContext.Provider
      value={{
        isFullDemoActive,
        currentStepIndex,
        currentStep,
        totalSteps,
        completedSteps,
        failedSteps,
        isPlaying,
        playbackSpeed,
        timeRemaining,
        explanationMode,
        isExplanationOpen,
        isFinalReportOpen,
        demoEvents,
        startFullDemo,
        stopFullDemo,
        nextStep,
        prevStep,
        goToStep,
        togglePlayPause,
        setSpeed: handleSetSpeed,
        toggleExplanationMode,
        toggleExplanationOpen,
        openFinalReport: () => setIsFinalReportOpen(true),
        closeFinalReport: () => setIsFinalReportOpen(false),
        restartDemo,
        replayDemo,
        skipStep,
        exportDemoReport,
      }}
    >
      {children}
    </FullDemoContext.Provider>
  );
};

export const useFullDemo = (): FullDemoContextType => {
  const context = useContext(FullDemoContext);
  if (!context) {
    throw new Error('useFullDemo must be used within a FullDemoProvider');
  }
  return context;
};
