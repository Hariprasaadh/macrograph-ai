"""Optional persistent Neo4j mirror of the canonical ontology.

NetworkX stays the runtime query engine. This store is written only through
sync_ontology() (ontology -> Neo4j) and never connects until first use.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from .ontology import MacroeconomicOntology, ontology

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None

logger = logging.getLogger(__name__)

_CONSTRAINT_CYPHER = (
    "CREATE CONSTRAINT indicator_id_unique IF NOT EXISTS FOR (i:Indicator) REQUIRE i.id IS UNIQUE"
)
_NODE_CYPHER = (
    "MERGE (i:Indicator {id: $id}) SET i.name = $name, i.sector = $sector, i.unit = $unit"
)
_EDGE_CYPHER = (
    "MATCH (s:Indicator {id: $src}) MATCH (t:Indicator {id: $tgt}) "
    "MERGE (s)-[r:AFFECTS {relation_id: $rel_id}]->(t) "
    "SET r.type = $type, r.lag = $lag, r.sign = $sign, r.confidence = $confidence"
)
_PATH_CYPHER = (
    "MATCH p = shortestPath((s:Indicator {id: $src})-[:AFFECTS*]->(t:Indicator {id: $tgt})) "
    "RETURN [n IN nodes(p) | n.id] AS node_ids, "
    "[r IN relationships(p) | {relation_id: r.relation_id, type: r.type, lag: r.lag, "
    "sign: r.sign, confidence: r.confidence}] AS edges"
)
_NEIGHBORHOOD_CYPHER = (
    "MATCH (n:Indicator {id: $id}) "
    "OPTIONAL MATCH (u:Indicator)-[ur:AFFECTS]->(n) "
    "OPTIONAL MATCH (n)-[dr:AFFECTS]->(d:Indicator) "
    "RETURN collect(DISTINCT {id: u.id, relation_id: ur.relation_id}) AS upstream, "
    "collect(DISTINCT {id: d.id, relation_id: dr.relation_id}) AS downstream"
)


class Neo4jKnowledgeGraphStore:
    """Lazy, optional Neo4j mirror. Every method is a safe no-op when NEO4J_URI is unset."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.uri = settings.NEO4J_URI if uri is None else uri
        self.user = user or settings.NEO4J_USER
        self.password = password if password is not None else settings.NEO4J_PASSWORD.get_secret_value()
        self._driver: Any = None

    @property
    def enabled(self) -> bool:
        return bool(self.uri) and GraphDatabase is not None

    def _get_driver(self) -> Any:
        if not self.enabled:
            return None
        if self._driver is None:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self._driver

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=4), reraise=True)
    def _sync(self, onto: MacroeconomicOntology) -> None:
        driver = self._get_driver()
        with driver.session() as session:
            session.run(_CONSTRAINT_CYPHER)
            for ind in onto.indicators.values():
                session.run(_NODE_CYPHER, id=ind.indicator_id, name=ind.name, sector=ind.sector.value, unit=ind.unit)
            for rel in onto.relationships:
                session.run(
                    _EDGE_CYPHER,
                    src=rel.source_indicator_id,
                    tgt=rel.target_indicator_id,
                    rel_id=rel.relation_id,
                    type=rel.relation_type.value,
                    lag=rel.transmission_lag_months,
                    sign=rel.elasticity_sign,
                    confidence=rel.confidence_score,
                )

    def sync_ontology(self, onto: Optional[MacroeconomicOntology] = None) -> bool:
        """The only Neo4j write path: upserts the ontology. Returns True on success."""
        if not self.enabled:
            return False
        try:
            self._sync(onto or ontology)
            return True
        except Exception:
            logger.exception("Neo4j ontology sync failed")
            return False

    def query_transmission_path(self, source_id: str, target_id: str) -> List[Dict[str, Any]]:
        """Persistence-side shortest path; not used by the orchestrator hot path."""
        if not self.enabled:
            return []
        try:
            with self._get_driver().session() as session:
                record = session.run(_PATH_CYPHER, src=source_id, tgt=target_id).single()
                return [{"node_ids": record["node_ids"], "edges": record["edges"]}] if record else []
        except Exception:
            logger.exception("Neo4j path query failed")
            return []

    def get_causal_neighborhood(self, indicator_id: str) -> Dict[str, Any]:
        """Persistence-side one-hop neighborhood; not used by the orchestrator hot path."""
        empty: Dict[str, Any] = {"indicator_id": indicator_id, "upstream": [], "downstream": []}
        if not self.enabled:
            return empty
        try:
            with self._get_driver().session() as session:
                record = session.run(_NEIGHBORHOOD_CYPHER, id=indicator_id).single()
                if not record:
                    return empty
                return {
                    "indicator_id": indicator_id,
                    "upstream": [u for u in record["upstream"] if u.get("id")],
                    "downstream": [d for d in record["downstream"] if d.get("id")],
                }
        except Exception:
            logger.exception("Neo4j neighborhood query failed")
            return empty


# Global store singleton; construction performs no I/O.
neo4j_store = Neo4jKnowledgeGraphStore()
