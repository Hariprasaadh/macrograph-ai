"""Shared query selection and evidence-grounded reasoning for direct sector agents."""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from groq import AsyncGroq


def _resolve_groq_api_key(preferred_key: str | None) -> str | None:
    if preferred_key:
        return preferred_key
    for key_name in (
        "GROQ_API_KEY",
        "AGR_REAL_KEY",
        "ORCH_KEY",
        "FIN_FIS_KEY",
        "CAP_MON_KEY",
        "PRIC_LAB_KEY",
        "SERV_EXT_KEY",
    ):
        val = os.getenv(key_name)
        if val and val.strip():
            return val.strip()

    from core.config import settings
    if settings.GROQ_API_KEY:
        return settings.GROQ_API_KEY

    from finance_sector.config import finance_settings
    return finance_settings.FIN_FIS_KEY


def select_relevant_services(
    query: str,
    service_keywords: dict[str, tuple[str, ...]],
) -> set[str]:
    """Select services whose explicit indicator terms occur in the query."""
    normalized_query = " ".join(query.casefold().split())
    return {
        service
        for service, keywords in service_keywords.items()
        if any(
            re.search(rf"\b{re.escape(keyword.casefold())}\b", normalized_query)
            for keyword in keywords
        )
    }


async def select_relevant_services_with_llm(
    *,
    query: str,
    service_keywords: dict[str, tuple[str, ...]],
    api_key: str | None,
    model: str,
) -> tuple[set[str], str | None]:
    """Use the model to route unmatched queries to allowlisted sector services."""
    direct_matches = select_relevant_services(query, service_keywords)
    if direct_matches:
        return direct_matches, None

    key = _resolve_groq_api_key(api_key)
    if not key:
        return set(), "No Groq API key is configured in sector, platform, or Finance settings."

    services = {
        name: ", ".join(keywords)
        for name, keywords in service_keywords.items()
    }
    try:
        async with AsyncGroq(api_key=key, timeout=30.0, max_retries=2) as client:
            response = await client.chat.completions.create(
                model=model,
                temperature=0,
                max_tokens=200,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Choose only the existing data services relevant to the user's "
                            "question. Available service names and their coverage are provided "
                            "in the user message. Return a JSON object with one property, "
                            '"services", containing an array of exact service names. Choose '
                            "multiple services only when the question needs them. For a broad "
                            "sector overview choose all relevant services. If none apply, return "
                            '{"services": []}. Never return any other text.'
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Question: {query[:500]}\n"
                            f"Available services: {json.dumps(services, ensure_ascii=True)}"
                        ),
                    },
                ],
            )
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ValueError("The service-selection model returned an empty response.")
        payload = json.loads(content)
        selected = payload.get("services")
        if not isinstance(selected, list) or not all(
            isinstance(name, str) for name in selected
        ):
            raise ValueError("The service-selection response has an invalid services list.")
        allowlisted = set(service_keywords)
        return {name for name in selected if name in allowlisted}, None
    except Exception as exc:
        logging.getLogger(__name__).exception("Sector service selection failed")
        return set(), f"Relevant data services could not be selected: {exc}"


def record_to_dict(record: Any) -> dict[str, Any]:
    if isinstance(record, dict):
        return record
    dump = getattr(record, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    raise TypeError(f"Sector data record has unsupported type: {type(record).__name__}")


async def reason_over_sector_data(
    *,
    query: str,
    sector_name: str,
    system_prompt: str,
    data_context: dict[str, Any],
    api_key: str | None,
    model: str,
    temperature: float = 0.1,
    max_tokens: int = 2200,
) -> str:
    key = _resolve_groq_api_key(api_key)
    if not key:
        raise RuntimeError(
            "No Groq API key is configured in sector, platform, or Finance settings."
        )

    async with AsyncGroq(api_key=key, timeout=45.0, max_retries=2) as client:
        response = await client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"{system_prompt}\n\n"
                        "Reason only from the supplied retrieved records. Never fill missing values "
                        "or infer facts that the records do not support. Answer the user's particular "
                        "question, not a generic sector overview. Start with a direct answer and explain "
                        "the relevant evidence in clear, concise prose so a non-specialist can understand "
                        "what changed and why it matters. Where supported, distinguish observed facts "
                        "from interpretation and explain the mechanism connecting them; do not imply "
                        "causation that the evidence cannot establish. Identify the observation period "
                        "and source/freshness for each material claim. Distinguish cached data and provider "
                        "snapshots from real-time data. If the selected records do not answer the query, "
                        "say so and state what is missing. Use a compact Markdown observations table when "
                        "it makes comparisons clearer, followed by 2-5 specific key takeaways with "
                        "short explanations/implications. Tables are optional when prose is clearer; "
                        "never make the response tables-only or repeat the same full explanation in a "
                        "table. In any observations table, NEVER use 'Same as above', 'ditto', or similar "
                        "abbreviations; state the explicit source and freshness in every row. "
                        "Add a brief limitations note when needed. Keep the answer focused, but "
                        "provide enough detail to explain the result. Do not include raw JSON, code "
                        "fences, invented citations, or unrelated sector context."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Sector: {sector_name}\n"
                        f"Question: {query[:500]}\n"
                        "Selected retrieved evidence (records include provenance):\n"
                        f"{json.dumps(data_context, ensure_ascii=True, default=str)}"
                    ),
                },
            ],
        )
    text = response.choices[0].message.content
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError(f"The reasoning model returned an empty {sector_name} analysis.")
    return text.strip()
