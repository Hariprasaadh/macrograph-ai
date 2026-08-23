"""Persistent Macroeconomic Knowledge Graph Connector for Neo4j."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
try:
    from neo4j import GraphDatabase, Driver
except ImportError:
    GraphDatabase = None
    Driver = None

from .ontology import ontology, MacroeconomicOntology


class Neo4jKnowledgeGraphStore:
    """Persistent Neo4j Knowledge Graph store with Cypher schema constraints and graph seeding."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ) -> None:
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self._driver: Optional[Driver] = None
        self._is_connected = False
        self._try_connect()

    def _try_connect(self) -> bool:
        if not GraphDatabase:
            return False
        try:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self._driver.verify_connectivity()
            self._is_connected = True
            return True
        except Exception:
            self._is_connected = False
            return False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def close(self) -> None:
        if self._driver:
            self._driver.close()

    def sync_ontology(self, onto: Optional[MacroeconomicOntology] = None) -> bool:
        """Seeds or updates the persistent Neo4j Knowledge Graph from the canonical ontology."""
        if not self._is_connected or not self._driver:
            return False

        target_onto = onto or ontology
        with self._driver.session() as session:
            # 1. Create constraints
            session.run("""
                CREATE CONSTRAINT indicator_id_unique IF NOT EXISTS
                FOR (i:Indicator) REQUIRE i.indicator_id IS UNIQUE
            """)

            # 2. Merge Indicator Nodes
            for ind in target_onto.indicators.values():
                session.run("""
                    MERGE (i:Indicator {indicator_id: $id})
                    SET i.name = $name,
                        i.sector = $sector,
                        i.subsector = $subsector,
                        i.unit = $unit,
                        i.frequency = $freq,
                        i.source_authority = $source
                """, {
                    "id": ind.indicator_id,
                    "name": ind.name,
                    "sector": ind.sector.value if hasattr(ind.sector, "value") else str(ind.sector),
                    "subsector": ind.subsector or "",
                    "unit": ind.unit,
                    "freq": ind.frequency,
                    "source": ind.source_authority
                })

            # 3. Merge Causal Relationships
            for rel in target_onto.relationships:
                session.run("""
                    MATCH (source:Indicator {indicator_id: $src})
                    MATCH (target:Indicator {indicator_id: $tgt})
                    MERGE (source)-[r:TRANSMITS_TO {relation_id: $rel_id}]->(target)
                    SET r.relation_type = $rel_type,
                        r.transmission_lag_months = $lag,
                        r.elasticity_sign = $elasticity,
                        r.confidence_score = $confidence,
                        r.mechanism_description = $mechanism,
                        r.empirical_p_value = $p_value
                """, {
                    "src": rel.source_indicator_id,
                    "tgt": rel.target_indicator_id,
                    "rel_id": rel.relation_id,
                    "rel_type": rel.relation_type.value if hasattr(rel.relation_type, "value") else str(rel.relation_type),
                    "lag": rel.transmission_lag_months,
                    "elasticity": rel.elasticity_sign,
                    "confidence": rel.confidence_score,
                    "mechanism": rel.mechanism_description,
                    "p_value": rel.empirical_p_value or 0.0
                })

        return True

    def query_transmission_path(self, source_id: str, target_id: str) -> List[Dict[str, Any]]:
        """Queries the shortest Cypher transmission path from Neo4j."""
        if not self._is_connected or not self._driver:
            return []

        query = """
            MATCH p = shortestPath((s:Indicator {indicator_id: $src})-[r:TRANSMITS_TO*]->(t:Indicator {indicator_id: $tgt}))
            RETURN [n in nodes(p) | n.indicator_id] as node_ids,
                   [rel in relationships(p) | {
                       type: rel.relation_type,
                       lag_months: rel.transmission_lag_months,
                       elasticity: rel.elasticity_sign,
                       mechanism: rel.mechanism_description,
                       confidence: rel.confidence_score
                   }] as edge_details
        """
        with self._driver.session() as session:
            result = session.run(query, {"src": source_id, "tgt": target_id}).single()
            if result:
                return [{
                    "node_ids": result["node_ids"],
                    "edges": result["edge_details"]
                }]
        return []


# Global store singleton
neo4j_store = Neo4jKnowledgeGraphStore()
