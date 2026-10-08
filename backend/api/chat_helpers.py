"""Response shaping and progress events for direct sector chat."""
from __future__ import annotations

import logging
import math
from typing import Any

from api.chat_config import _DIRECT_SECTOR_CHAT


def _has_sector_value(value: Any) -> bool:
    if isinstance(value, (int, float)) and not math.isfinite(value):
        return False
    return value is not None and not (
        isinstance(value, str) and value.strip().lower() in {"", "unknown", "unavailable"}
    )


def _format_sector_report(
    config: dict[str, Any],
    data_context: dict[str, Any],
    freshness: dict[str, Any] | None = None,
    citations: list[dict[str, Any]] | None = None,
) -> str:
    freshness = freshness or {}
    citations = citations or []
    lines = [
        "### Latest observations",
        "",
        "| Indicator | Observation | Period | Freshness | Source |",
        "|---|---:|---|---|---|",
    ]
    takeaway_rows: list[tuple[str, str]] = []
    for section_key, section_title, fields in config["sections"]:
        if section_key not in data_context:
            continue
        section = data_context.get(section_key)
        if isinstance(section, dict):
            period = section.get("period")
            period_label = str(period) if _has_sector_value(period) else "Unavailable"
            citation = next(
                (item for item in citations if item.get("dataset") == section_key),
                {},
            )
            source = citation.get("source_authority") or "Unavailable"
            freshness_label = str(freshness.get(section_key, citation.get("freshness", "unavailable")))
            for label, field_key, unit in fields:
                value = section.get(field_key)
                rendered_value = f"{value}{unit}" if _has_sector_value(value) else "Unavailable"
                lines.append(
                    f"| {label} | {rendered_value} | {period_label} | "
                    f"{freshness_label} | {source} |"
                )
            has_section_observation = any(
                _has_sector_value(section.get(field_key))
                for _, field_key, _ in fields
            )
            if not has_section_observation:
                continue
            if section_key == "trade_balance":
                trade_balance = section.get("trade_balance_usd_bn")
                if isinstance(trade_balance, (int, float)) and trade_balance < 0:
                    takeaway_rows.append((
                        "Merchandise trade balance is negative",
                        "Imports exceeded exports in the reported period; this describes goods trade, not the full current account.",
                    ))
                elif isinstance(trade_balance, (int, float)) and trade_balance > 0:
                    takeaway_rows.append((
                        "Merchandise trade balance is positive",
                        "Exports exceeded imports in the reported period; this describes goods trade, not the full current account.",
                    ))
            elif section_key == "exchange_rates" and _has_sector_value(section.get("usd_inr_rate")):
                takeaway_rows.append((
                    "USD/INR is quoted as rupees per U.S. dollar",
                    "A single observation establishes the reference level for that date; compare other dates from the same series to assess movement.",
                ))
            else:
                takeaway_rows.append((
                    f"{section_title} is reported for {period_label}",
                    "The observation describes that period; by itself it does not establish a longer-term trend or its cause.",
                ))

    if not lines or len(lines) == 4:
        lines.extend(["", "| Observation | Detail |", "|---|---|", "| Data availability | No usable observations were returned for the selected datasets. |"])
    lines.extend([
        "",
        "### Take-aways",
        "",
        "| Insight | Implication |",
        "|---|---|",
    ])
    if takeaway_rows:
        lines.extend(f"| {insight} | {implication} |" for insight, implication in takeaway_rows)
    else:
        lines.append("| Data unavailable | There are no observations to interpret. |")
    lines.extend([
        "",
        "Model-generated analysis was unavailable; take-aways are limited to direct interpretation of the returned observations.",
    ])
    return "\n".join(lines)


def _sector_chat_response(target: str, node_result: dict[str, Any]) -> dict[str, Any]:
    config = _DIRECT_SECTOR_CHAT[target]
    data_context = node_result.get(config["data_key"]) or {}
    if not isinstance(data_context, dict):
        data_context = {}
    freshness = node_result.get(config["freshness_key"]) or {}
    raw_errors = node_result.get(config["errors_key"]) or []
    errors = raw_errors if isinstance(raw_errors, list) else [str(raw_errors)]
    raw_citations = node_result.get(config["citations_key"]) or []
    citations = [
        {
            **(citation if target == "agriculture_sector" else {}),
            "source_agent": citation["source_agent"],
            "authority": citation.get("source_authority"),
            "source_authority": citation.get("source_authority"),
            "document_title": citation.get("document_title"),
            "table": citation.get("table_reference"),
            "table_reference": citation.get("table_reference"),
            "retrieval_url": citation.get("retrieval_url"),
            "source_base_url": citation.get("source_base_url"),
            "source_note": citation.get("source_note"),
            "as_of": citation.get("as_of"),
            "fetched_at": citation.get("fetched_at"),
            "frequency": citation.get("frequency"),
            "unit": citation.get("unit"),
            "period": citation.get("observation_period"),
            "observation_period": citation.get("observation_period"),
            "freshness": citation.get("freshness"),
            "dataset": citation.get("dataset"),
        }
        for citation in raw_citations
        if isinstance(citation, dict) and citation.get("source_agent")
    ]
    report = node_result.get(config["analysis_key"])
    if not isinstance(report, str) or not report.strip():
        report = _format_sector_report(config, data_context, freshness, citations)
    else:
        report = report.strip()

    reasoning_errors = [
        error for error in errors
        if isinstance(error, str) and error.startswith("LLM reasoning unavailable:")
    ]
    retrieval_errors = [error for error in errors if error not in reasoning_errors]
    if reasoning_errors:
        report += "\n\nAnalysis note: The configured LLM could not provide a narrative interpretation."
    if retrieval_errors and target != "agriculture_sector":
        report += "\n\n### Data retrieval issues\n\n" + "\n".join(f"- {error}" for error in retrieval_errors)

    available_values = []
    for section_key, _, fields in config["sections"]:
        if section_key not in data_context:
            continue
        section = data_context.get(section_key)
        available_values.extend(
            _has_sector_value(section.get(field_key)) if isinstance(section, dict) else False
            for _, field_key, _ in fields
        )
    has_values = any(available_values)
    status = (
        "unavailable"
        if not has_values
        else "partial"
        if errors or not all(available_values)
        else "completed"
    )

    if target == "agriculture_sector":
        status = node_result.get("agriculture_sector_status", "unavailable")
    if target == "prices_sector":
        status = node_result.get("prices_sector_status", "unavailable")

    return {
        "status": status,
        "agent_routed": f"{config['name']} Specialist",
        "full_report": report,
        "data_context": data_context,
        "freshness": freshness,
        "errors": errors,
        "citations": citations,
    }


async def _run_direct_sector_chat(
    target: str,
    message: str,
    *,
    selected_services: set[str] | None = None,
    selection_error: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = _DIRECT_SECTOR_CHAT[target]
    try:
        state: dict[str, Any] = {"query": message}
        if target == "agriculture_sector":
            state["parameters"] = parameters or {}
        if selected_services is not None:
            state["_selected_services"] = selected_services
            state["_selection_error"] = selection_error
        node_result = await config["node"](state)
    except Exception as exc:
        logging.getLogger(__name__).exception("Direct %s chat agent failed", target)
        return {
            "status": "failed",
            "agent_routed": f"{config['name']} Specialist",
            "full_report": (
                f"### {config['name']} Request Failed\n\n"
                f"The sector agent could not complete this request: {exc}. "
                "No observations are available."
            ),
            "data_context": {},
            "freshness": {},
            "errors": [str(exc)],
            "citations": [],
        }
    return _sector_chat_response(target, node_result)


def _sector_progress_events(
    target: str,
    selected_services: set[str],
    selection_error: str | None,
) -> list[dict[str, Any]]:
    config = _DIRECT_SECTOR_CHAT[target]
    events = [{
        "type": "step",
        "step": 1,
        "agent": target,
        "title": f"Targeting {config['name']} Specialist",
        "detail": "Invoking the selected sector agent directly, without Orchestrator routing.",
    }]
    if selection_error:
        events.append({
            "type": "step",
            "step": 2,
            "agent": target,
            "title": "Resolving query-relevant data",
            "detail": f"Service selection reported an issue: {selection_error}",
        })
    elif selected_services:
        events.append({
            "type": "step",
            "step": 2,
            "agent": target,
            "title": "Matched query-relevant data",
            "detail": "Selected: " + ", ".join(
                service.replace("_", " ") for service in config["service_keywords"]
                if service in selected_services
            ),
        })
    else:
        events.append({
            "type": "step",
            "step": 2,
            "agent": target,
            "title": "No matching sector dataset",
            "detail": "The available sector indicators do not explicitly match this query.",
        })

    step = len(events) + 1
    for service in config["service_keywords"]:
        if service not in selected_services:
            continue
        events.append({
            "type": "step",
            "step": step,
            "agent": target,
            "tool": service,
            "title": f"Retrieving {service.replace('_', ' ')}",
            "detail": (
                "Fetching only this query-selected dataset through the sector client; "
                "availability, source freshness, and cache fallback will be reported."
            ),
        })
        step += 1

    events.append({
        "type": "step",
        "step": step,
        "agent": target,
        "title": "Preparing evidence-based explanation",
        "detail": (
            "After retrieval, the specialist will explain the result, key takeaways, "
            "source periods, and any limitations."
        ),
    })
    return events


def _build_finance_citations(ctx: dict, fresh: dict) -> list[dict]:
    cits = []
    credit_info = ctx.get("credit_growth", {})
    if credit_info.get("status") != "unavailable" and credit_info.get("period"):
        cits.append({
            "source_agent": "finance_sector",
            "authority": "Reserve Bank of India (RBI)",
            "table": credit_info.get("source", "financial_sector.r539_deployment_of_bank_credit_by_major_sectors"),
            "period": credit_info.get("period"),
            "freshness": credit_info.get("freshness", fresh.get("credit", "cached")),
        })
    quality_info = ctx.get("asset_quality", {})
    if quality_info.get("status") != "unavailable" and quality_info.get("period"):
        cits.append({
            "source_agent": "finance_sector",
            "authority": "Reserve Bank of India (RBI)",
            "table": quality_info.get("source", "financial_sector.r330_gross_and_net_npas_of_scheduled_commercial_banks"),
            "period": quality_info.get("period"),
            "freshness": quality_info.get("freshness", fresh.get("quality", "cached")),
        })
    rates_info = ctx.get("lending_rates", {})
    if rates_info.get("status") != "unavailable" and rates_info.get("period"):
        cits.append({
            "source_agent": "finance_sector",
            "authority": "Reserve Bank of India (RBI)",
            "table": rates_info.get("source", "financial_sector.r531_key_rates"),
            "period": rates_info.get("period"),
            "freshness": rates_info.get("freshness", fresh.get("rates", "cached")),
        })
    deposits_info = ctx.get("deposits", {})
    if deposits_info.get("status") != "unavailable" and deposits_info.get("period"):
        cits.append({
            "source_agent": "finance_sector",
            "authority": "Reserve Bank of India (RBI)",
            "table": deposits_info.get("source", "financial_sector.r689_business_of_scheduled_banks"),
            "period": deposits_info.get("period"),
            "freshness": deposits_info.get("freshness", fresh.get("deposits", "cached")),
        })
    return cits
