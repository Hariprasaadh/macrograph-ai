"""Neo4j mirror: optional, lazy, and written only through sync_ontology."""
from __future__ import annotations

import importlib

neo4j_module = importlib.import_module("core.knowledge_graph.neo4j_store")
from core.knowledge_graph.neo4j_store import Neo4jKnowledgeGraphStore
from core.knowledge_graph.ontology import ontology


class FakeSession:
    def __init__(self, log):
        self.log = log

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def run(self, query, **params):
        self.log.append((query, params))


class FakeDriver:
    def __init__(self):
        self.log = []

    def session(self):
        return FakeSession(self.log)

    def close(self):
        pass


def test_disabled_without_uri_returns_safe_values():
    store = Neo4jKnowledgeGraphStore(uri="")
    assert store.enabled is False
    assert store.sync_ontology() is False
    assert store.query_transmission_path("a", "b") == []
    assert store.get_causal_neighborhood("a") == {"indicator_id": "a", "upstream": [], "downstream": []}
    store.close()


def test_no_connection_on_construction(monkeypatch):
    calls = []
    monkeypatch.setattr(neo4j_module, "GraphDatabase", type("G", (), {"driver": staticmethod(lambda *a, **k: calls.append(a))}))
    Neo4jKnowledgeGraphStore(uri="bolt://example:7687")
    assert calls == []


def test_sync_is_the_write_path(monkeypatch):
    driver = FakeDriver()
    monkeypatch.setattr(neo4j_module, "GraphDatabase", type("G", (), {"driver": staticmethod(lambda *a, **k: driver)}))
    store = Neo4jKnowledgeGraphStore(uri="bolt://example:7687")
    assert store.sync_ontology() is True
    merges_nodes = [p for q, p in driver.log if "MERGE (i:Indicator" in q]
    merges_edges = [p for q, p in driver.log if "AFFECTS" in q]
    assert len(merges_nodes) == len(ontology.indicators)
    assert len(merges_edges) == len(ontology.relationships)
    assert {p["rel_id"] for p in merges_edges} == {r.relation_id for r in ontology.relationships}


def test_sync_failure_is_non_fatal(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(neo4j_module, "GraphDatabase", type("G", (), {"driver": staticmethod(boom)}))
    store = Neo4jKnowledgeGraphStore(uri="bolt://example:7687")
    monkeypatch.setattr(Neo4jKnowledgeGraphStore, "_sync", lambda self, onto: boom())
    assert store.sync_ontology() is False
