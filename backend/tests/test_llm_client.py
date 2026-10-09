"""Regression: LLM client must fall back to the offline notice when no API key is configured."""
from __future__ import annotations

import asyncio
import importlib

llm_module = importlib.import_module("core.orchestrator.llm_client")

KEY_ENV_VARS = ("GROQ_API_KEY", "ORCH_KEY", "PRIC_LAB_KEY", "FIN_FIS_KEY", "SERV_EXT_KEY", "AGR_REAL_KEY", "CAP_MON_KEY")


def test_complete_returns_unavailable_notice_without_keys(monkeypatch):
    for name in KEY_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(llm_module.settings, "GROQ_API_KEY", "", raising=False)
    client = llm_module.ModelAgnosticLLMClient()
    client.provider = "groq"
    assert asyncio.run(client.complete("hello")) == client._unavailable_notice()
