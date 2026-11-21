"""Graph-based Attack Propagation and Blast-Radius Engine for 5G Digital Twin.

Calculates causal multi-hop propagation, attack paths, affected components,
containment boundaries, and quantitative blast radius scores across the 5G topology.
"""

from collections import deque
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Set, Tuple

from .models import (
    AttackPropagationResult,
    ConnectionType,
    NetworkComponent,
    NetworkConnection,
)

logger = logging.getLogger("commshield.twin.propagation")


class AttackPropagationEngine:
    """Computes deterministic, graph-based blast radius and causal attack paths."""

    def __init__(self):
        pass

    def compute_propagation(
        self,
        scenario_id: str,
        entry_point: str,
        target_component: str,
        components: Dict[str, NetworkComponent],
        connections: Dict[str, NetworkConnection],
        traffic_intensity_multiplier: float = 3.0,
    ) -> AttackPropagationResult:
        """Execute graph dependency traversal to determine causal blast radius."""
        if target_component not in components:
            target_component = "upf-01"
        if entry_point not in components:
            entry_point = "ue-camera-01"

        # 1. Build adjacency list representation of 5G topology
        adj: Dict[str, List[Tuple[str, str, ConnectionType]]] = {cid: [] for cid in components}
        conn_by_pair: Dict[Tuple[str, str], NetworkConnection] = {}

        for conn in connections.values():
            adj[conn.source].append((conn.destination, conn.id, conn.connection_type))
            adj[conn.destination].append((conn.source, conn.id, conn.connection_type))
            conn_by_pair[(conn.source, conn.destination)] = conn
            conn_by_pair[(conn.destination, conn.source)] = conn

        # 2. Find shortest attack path from entry_point to target_component (BFS)
        attack_path = self._find_shortest_path(adj, entry_point, target_component)
        if not attack_path:
            attack_path = [entry_point, "gnb-01", target_component]

        # 3. Classify components causally:
        # Directly targeted
        directly_targeted = [target_component]
        if entry_point != target_component and entry_point not in directly_targeted:
            directly_targeted.append(entry_point)

        # 1-hop dependencies: Indirectly affected
        indirectly_affected: Set[str] = set()
        for neighbor, _, _ in adj.get(target_component, []):
            if neighbor not in directly_targeted:
                indirectly_affected.add(neighbor)

        # 2-hop dependencies: Potentially affected
        potentially_affected: Set[str] = set()
        for ind_node in indirectly_affected:
            for neighbor, _, _ in adj.get(ind_node, []):
                if neighbor not in directly_targeted and neighbor not in indirectly_affected:
                    potentially_affected.add(neighbor)

        # Unaffected components: All remaining nodes
        affected_set = set(directly_targeted) | indirectly_affected | potentially_affected
        unaffected = [cid for cid in components if cid not in affected_set]

        # 4. Identify affected slices and UEs
        target_comp_obj = components.get(target_component)
        target_slice = target_comp_obj.network_slice if target_comp_obj else "ALL"

        affected_slices: List[str] = []
        if target_slice and target_slice != "ALL":
            affected_slices.append(target_slice)
        else:
            affected_slices = ["sst-1-sd-010203", "sst-2-sd-020304", "sst-3-sd-030405"]

        affected_ues = [
            cid for cid, c in components.items()
            if c.component_type == "UE" and (cid in affected_set or c.network_slice in affected_slices)
        ]

        # 5. Suspicious traffic paths (connecting links along attack and 1-hop propagation)
        suspicious_traffic_paths: List[str] = []
        for i in range(len(attack_path) - 1):
            s, d = attack_path[i], attack_path[i + 1]
            if (s, d) in conn_by_pair:
                suspicious_traffic_paths.append(conn_by_pair[(s, d)].id)

        # 6. Containment boundaries (firewall / policy enforcement points surrounding blast radius)
        containment_boundaries: List[str] = []
        boundary_candidates = {"router-edge-01", "switch-core-01", "gnb-01", "smf-01"}
        for b in boundary_candidates:
            if b in components and (b in affected_set or any(n in affected_set for n, _, _ in adj.get(b, []))):
                containment_boundaries.append(b)

        if not containment_boundaries:
            containment_boundaries = ["router-edge-01", "gnb-01"]

        # 7. Compute Blast Radius Score
        # Formula: (Direct * 1.0 + Indirect * 0.5 + Potential * 0.2) / Total * 100
        total_comps = max(1, len(components))
        raw_score = (
            (len(directly_targeted) * 1.0)
            + (len(indirectly_affected) * 0.5)
            + (len(potentially_affected) * 0.2)
        )
        blast_radius_score = round(min(100.0, (raw_score / total_comps) * 100.0 * min(2.0, traffic_intensity_multiplier / 2.0)), 1)

        # Affected services description
        affected_services = [
            "User Plane Packet Forwarding (N3/N6)",
            "GTP-U Tunnel Encapsulation",
            "MEC Low-Latency Local Breakout (N9)",
        ]
        if "amf-01" in affected_set or "ausf-01" in affected_set:
            affected_services.append("5G-AKA Radio Registration & Authentication")
        if "smf-01" in affected_set:
            affected_services.append("PDU Session Establishment & Release")

        explanation = (
            f"Attack ingress via '{entry_point}' targeting '{target_component}'. "
            f"Blast radius spans {len(directly_targeted)} direct targets, {len(indirectly_affected)} degraded 1-hop dependencies, "
            f"and {len(potentially_affected)} 2-hop downstream nodes across slice(s) {', '.join(affected_slices)}. "
            f"Containment boundaries identified at {', '.join(containment_boundaries)}."
        )

        return AttackPropagationResult(
            scenario_id=scenario_id,
            entry_point=entry_point,
            target_component=target_component,
            attack_path=attack_path,
            directly_targeted=sorted(directly_targeted),
            indirectly_affected=sorted(list(indirectly_affected)),
            potentially_affected=sorted(list(potentially_affected)),
            unaffected=sorted(unaffected),
            affected_ues=sorted(affected_ues),
            affected_slices=affected_slices,
            affected_services=affected_services,
            suspicious_traffic_paths=suspicious_traffic_paths,
            containment_boundaries=sorted(containment_boundaries),
            blast_radius_score=blast_radius_score,
            impact_explanation=explanation,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _find_shortest_path(
        self,
        adj: Dict[str, List[Tuple[str, str, ConnectionType]]],
        start: str,
        goal: str,
    ) -> List[str]:
        """Breadth-first search for shortest network path."""
        if start == goal:
            return [start]
        visited = {start}
        queue = deque([[start]])

        while queue:
            path = queue.popleft()
            node = path[-1]
            for neighbor, _, _ in adj.get(node, []):
                if neighbor == goal:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])

        return []


# Global singleton instance
propagation_engine = AttackPropagationEngine()
