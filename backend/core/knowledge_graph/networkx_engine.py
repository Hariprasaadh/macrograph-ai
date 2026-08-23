"""High-Performance In-Memory Macroeconomic Graph Engine using NetworkX."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import networkx as nx

from ..data.schema import CanonicalIndicator, CausalRelationship
from .ontology import ontology, MacroeconomicOntology


class NetworkXGraphEngine:
    """Provides high-speed graph traversal, shortest transmission paths, and causal neighborhood algorithms."""

    def __init__(self, onto: Optional[MacroeconomicOntology] = None) -> None:
        self.ontology = onto or ontology
        self.graph = nx.MultiDiGraph()
        self._build_graph()

    def _build_graph(self) -> None:
        """Initializes the NetworkX graph from canonical ontology entities and edges."""
        self.graph.clear()

        # Add Nodes
        for ind_id, ind in self.ontology.indicators.items():
            self.graph.add_node(
                ind_id,
                name=ind.name,
                sector=ind.sector.value if hasattr(ind.sector, "value") else str(ind.sector),
                subsector=ind.subsector or "",
                unit=ind.unit,
                frequency=ind.frequency,
                source_authority=ind.source_authority
            )

        # Add Edges
        for rel in self.ontology.relationships:
            self.graph.add_edge(
                rel.source_indicator_id,
                rel.target_indicator_id,
                key=rel.relation_id,
                relation=rel,
                relation_type=rel.relation_type.value if hasattr(rel.relation_type, "value") else str(rel.relation_type),
                lag_months=rel.transmission_lag_months,
                elasticity=rel.elasticity_sign,
                confidence=rel.confidence_score,
                mechanism=rel.mechanism_description
            )

    def get_shortest_transmission_path(self, source_id: str, target_id: str) -> List[CausalRelationship]:
        """Finds the most direct transmission chain between two macroeconomic indicators."""
        if not self.graph.has_node(source_id) or not self.graph.has_node(target_id):
            return []

        try:
            path_nodes = nx.shortest_path(self.graph, source=source_id, target=target_id)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

        relationships: List[CausalRelationship] = []
        for u, v in zip(path_nodes[:-1], path_nodes[1:]):
            edge_data = self.graph.get_edge_data(u, v)
            if edge_data:
                # Take the highest confidence edge if multiple exist
                best_rel = max(edge_data.values(), key=lambda d: d.get("confidence", 0.0))["relation"]
                relationships.append(best_rel)

        return relationships

    def get_causal_neighborhood(self, indicator_id: str, depth: int = 2) -> Dict[str, Any]:
        """Extracts upstream drivers and downstream recipients within a given hop distance."""
        if not self.graph.has_node(indicator_id):
            return {"indicator_id": indicator_id, "upstream": [], "downstream": []}

        # Upstream predecessors (causes)
        predecessors = list(self.graph.predecessors(indicator_id))
        upstream_rels = []
        for pred in predecessors:
            edges = self.graph.get_edge_data(pred, indicator_id)
            for e in edges.values():
                upstream_rels.append(e["relation"].model_dump())

        # Downstream successors (effects)
        successors = list(self.graph.successors(indicator_id))
        downstream_rels = []
        for succ in successors:
            edges = self.graph.get_edge_data(indicator_id, succ)
            for e in edges.values():
                downstream_rels.append(e["relation"].model_dump())

        return {
            "indicator_id": indicator_id,
            "upstream_drivers": upstream_rels,
            "downstream_impacts": downstream_rels
        }

    def get_downstream_impacts(self, shock_indicator_id: str) -> List[Dict[str, Any]]:
        """Traverses all reachable downstream indicators affected by a shock to the source indicator."""
        if not self.graph.has_node(shock_indicator_id):
            return []

        reachable = nx.descendants(self.graph, shock_indicator_id)
        impacts: List[Dict[str, Any]] = []

        for target in reachable:
            path = self.get_shortest_transmission_path(shock_indicator_id, target)
            if path:
                total_lag = sum(r.transmission_lag_months for r in path)
                cumulative_conf = 1.0
                for r in path:
                    cumulative_conf *= r.confidence_score

                target_node = self.graph.nodes[target]
                impacts.append({
                    "target_indicator_id": target,
                    "target_name": target_node.get("name", target),
                    "sector": target_node.get("sector", ""),
                    "path_length_hops": len(path),
                    "total_lag_months": total_lag,
                    "cumulative_confidence": round(cumulative_conf, 2),
                    "transmission_chain": [r.mechanism_description for r in path]
                })

        return sorted(impacts, key=lambda x: (x["path_length_hops"], -x["cumulative_confidence"]))

    def generate_mermaid_diagram(self, focus_indicator_ids: Optional[List[str]] = None) -> str:
        """Generates dynamic Mermaid diagram syntax representing transmission graph paths."""
        lines = ["graph LR"]
        edges_to_render = []

        if focus_indicator_ids:
            nodes_set = set(focus_indicator_ids)
            for nid in focus_indicator_ids:
                if self.graph.has_node(nid):
                    nodes_set.update(self.graph.predecessors(nid))
                    nodes_set.update(self.graph.successors(nid))
            for u, v, k, data in self.graph.edges(keys=True, data=True):
                if u in nodes_set and v in nodes_set:
                    edges_to_render.append((u, v, data))
        else:
            for u, v, k, data in self.graph.edges(keys=True, data=True):
                edges_to_render.append((u, v, data))

        rendered_nodes = set()
        for u, v, data in edges_to_render:
            u_label = self.graph.nodes[u].get("name", u).replace('"', "'")
            v_label = self.graph.nodes[v].get("name", v).replace('"', "'")
            u_clean = u.replace(".", "_").replace("-", "_")
            v_clean = v.replace(".", "_").replace("-", "_")

            if u_clean not in rendered_nodes:
                lines.append(f'    {u_clean}["{u_label}"]')
                rendered_nodes.add(u_clean)
            if v_clean not in rendered_nodes:
                lines.append(f'    {v_clean}["{v_label}"]')
                rendered_nodes.add(v_clean)

            lag = f"{data.get('lag_months', 0)}M"
            el = data.get("elasticity", "+")
            rel_type = data.get("relation_type", "THEORY")
            lines.append(f'    {u_clean} -->|"{el} ({lag}) [{rel_type}]"| {v_clean}')

        return "\n".join(lines)


# Global engine singleton
graph_engine = NetworkXGraphEngine()
