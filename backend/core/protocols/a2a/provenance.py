"""Maps sector-native citation records onto SourceProvenance without inventing fields."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional

from pydantic import BaseModel

from .messages import SourceProvenance

_MAX_SOURCES = 50

_NAME_KEYS = ("source_authority", "authority", "source_name", "source")
_URL_KEYS = ("source_url", "retrieval_url", "url")
_DATASET_KEYS = ("dataset", "dataset_reference", "document_title")
_TABLE_KEYS = ("table", "table_reference", "series_code")
_PERIOD_KEYS = ("observation_period", "period", "reporting_period")
_TIME_KEYS = ("retrieved_at", "fetched_at")
_SECTION_KEYS = ("page_or_section", "section")
_RECORD_KEYS = ("record_reference", "indicator_id", "indicator", "mcp_tool")


def _first(data: Mapping[str, Any], keys: tuple[str, ...]) -> Optional[str]:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _parse_time(data: Mapping[str, Any]) -> Optional[datetime]:
    for key in _TIME_KEYS:
        value = data.get(key)
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                continue
    return None


def provenance_from_citation(
    citation: Mapping[str, Any] | BaseModel, default_source: str
) -> SourceProvenance:
    """Convert one citation record; absent fields stay None."""
    data: Mapping[str, Any] = citation.model_dump() if isinstance(citation, BaseModel) else citation
    kwargs: dict[str, Any] = {}
    retrieved = _parse_time(data)
    if retrieved is not None:
        kwargs["retrieved_at"] = retrieved
    return SourceProvenance(
        source_name=_first(data, _NAME_KEYS) or default_source,
        source_url=_first(data, _URL_KEYS),
        dataset=_first(data, _DATASET_KEYS),
        table=_first(data, _TABLE_KEYS),
        reporting_period=_first(data, _PERIOD_KEYS),
        page_or_section=_first(data, _SECTION_KEYS),
        record_reference=_first(data, _RECORD_KEYS),
        **kwargs,
    )


def _citation_records(content: Any) -> list[Mapping[str, Any]]:
    if not isinstance(content, dict):
        return []
    records: list[Mapping[str, Any]] = []
    for key in ("citations", "observations"):
        value = content.get(key)
        if isinstance(value, list):
            records.extend(v for v in value if isinstance(v, dict))
    nested = content.get("citation")
    if isinstance(nested, dict):
        inner = nested.get("observations")
        if isinstance(inner, list):
            records.extend(v for v in inner if isinstance(v, dict))
        else:
            records.append(nested)
    return records


def provenance_from_artifact(
    content: Any, default_source: str, artifact_name: str, artifact_hash: Optional[str]
) -> list[SourceProvenance]:
    """Structured citations when the artifact has them, else one artifact-level reference."""
    sources: list[SourceProvenance] = []
    seen: set[tuple[Optional[str], ...]] = set()
    for record in _citation_records(content)[:_MAX_SOURCES]:
        src = provenance_from_citation(record, default_source)
        key = (src.source_name, src.dataset, src.table, src.reporting_period, src.record_reference)
        if key not in seen:
            seen.add(key)
            sources.append(src)
    if not sources:
        sources.append(SourceProvenance(
            source_name=default_source, dataset=artifact_name, record_reference=artifact_hash,
        ))
    return sources
