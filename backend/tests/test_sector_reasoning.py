from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest

from core import sector_reasoning


def test_explicit_indicator_selects_only_matching_service():
    selected = sector_reasoning.select_relevant_services(
        "What unemployment-rate observations are available?",
        {
            "unemployment": ("unemployment", "jobless", "unemployment rate"),
            "lfpr": ("lfpr", "labour force participation"),
            "wpr": ("wpr", "worker population ratio"),
        },
    )

    assert selected == {"unemployment"}


@pytest.mark.asyncio
async def test_llm_service_selection_filters_unknown_service_names(monkeypatch):
    calls = {}

    class FakeGroq:
        def __init__(self, **_kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self.create_completion)
            )

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def create_completion(self, **kwargs):
            calls.update(kwargs)
            message = SimpleNamespace(content='{"services":["lfpr","unknown"]}')
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr(sector_reasoning, "AsyncGroq", FakeGroq)
    selected, error = await sector_reasoning.select_relevant_services_with_llm(
        query="How does women's participation in work compare?",
        service_keywords={
            "unemployment": ("unemployment", "jobless"),
            "lfpr": ("lfpr", "labour force participation", "female participation"),
            "wpr": ("wpr", "worker population ratio"),
        },
        api_key="test-key",
        model="test-model",
    )

    assert selected == {"lfpr"}
    assert error is None
    assert "women's participation" in calls["messages"][1]["content"]


@pytest.mark.asyncio
async def test_reasoning_uses_expanded_explanation_budget(monkeypatch):
    calls = {}

    class FakeGroq:
        def __init__(self, **_kwargs):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self.create_completion)
            )

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def create_completion(self, **kwargs):
            calls.update(kwargs)
            message = SimpleNamespace(content="Direct answer with supported explanation.")
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr(sector_reasoning, "AsyncGroq", FakeGroq)
    response = await sector_reasoning.reason_over_sector_data(
        query="Explain the observation and what it implies.",
        sector_name="Test",
        system_prompt="Stay within scope.",
        data_context={"indicator": {"value": 5, "period": "2026-01"}},
        api_key="test-key",
        model="test-model",
    )

    assert response == "Direct answer with supported explanation."
    assert calls["max_tokens"] == 2200
    system_prompt = calls["messages"][0]["content"]
    assert "2-5 specific key takeaways" in system_prompt
    assert "never make the response tables-only" in system_prompt


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("module_name", "node_name", "data_key", "freshness_key", "service_name"),
    [
        (
            "external_sector.agent",
            "external_agent_node",
            "external_sector_data",
            "external_sector_freshness",
            "exchange_rates",
        ),
        (
            "labour_sector.agent",
            "labour_agent_node",
            "labour_sector_data",
            "labour_sector_freshness",
            "unemployment",
        ),
        (
            "capital_market_sector.agent",
            "capital_agent_node",
            "capital_market_sector_data",
            "capital_market_sector_freshness",
            "nifty_snapshot",
        ),
        (
            "monetary_sector.agent",
            "monetary_agent_node",
            "monetary_sector_data",
            "monetary_sector_freshness",
            "policy_rates",
        ),
    ],
)
async def test_sector_agent_fetches_only_selected_service(
    monkeypatch, module_name, node_name, data_key, freshness_key, service_name
):
    module = importlib.import_module(module_name)
    called: list[str] = []

    async def fetch(service):
        called.append(service)
        return [{"period": "test-period", "value": 1, "citation": {"freshness": "cached"}}]

    for name in module._FETCHERS:
        monkeypatch.setitem(module._FETCHERS, name, lambda name=name: fetch(name))

    async def select_service(**_kwargs):
        return {service_name}, None

    async def reason(**_kwargs):
        return "Evidence-based response."

    monkeypatch.setattr(module, "select_relevant_services_with_llm", select_service)
    monkeypatch.setattr(module, "reason_over_sector_data", reason)
    result = await getattr(module, node_name)({"query": "a specific sector question"})

    assert called == [service_name]
    assert set(result[data_key]) == {service_name}
    assert set(result[freshness_key]) == {service_name}


@pytest.mark.asyncio
async def test_sector_agent_reuses_preselected_services_without_routing_again(monkeypatch):
    module = importlib.import_module("capital_market_sector.agent")
    called: list[str] = []

    async def fail_if_selected_again(**_kwargs):
        pytest.fail("Preselected services should not trigger a second routing call.")

    async def fetch_breadth():
        called.append("market_breadth")
        return [{
            "period": "test-period",
            "value": 1,
            "citation": {"freshness": "cached"},
        }]

    async def reason(**_kwargs):
        return "Evidence-based answer."

    monkeypatch.setattr(module, "select_relevant_services_with_llm", fail_if_selected_again)
    monkeypatch.setitem(module._FETCHERS, "market_breadth", fetch_breadth)
    monkeypatch.setattr(module, "reason_over_sector_data", reason)

    result = await module.capital_agent_node({
        "query": "What is market breadth?",
        "_selected_services": {"market_breadth"},
    })

    assert called == ["market_breadth"]
    assert set(result["capital_market_sector_data"]) == {"market_breadth"}


@pytest.mark.asyncio
async def test_sector_selector_does_not_fetch_everything_without_llm_key(monkeypatch):
    monkeypatch.setattr(sector_reasoning, "_resolve_groq_api_key", lambda _key: None)
    selected, error = await sector_reasoning.select_relevant_services_with_llm(
        query="How are things going?",
        service_keywords={"one": ("indicator one",), "two": ("indicator two",)},
        api_key=None,
        model="test-model",
    )

    assert selected == set()
    assert error == "No Groq API key is configured in sector, platform, or Finance settings."


def test_groq_key_resolution_falls_back_to_existing_finance_key(monkeypatch):
    from core import config
    from finance_sector.config import finance_settings

    monkeypatch.setattr(config.settings, "GROQ_API_KEY", "")
    monkeypatch.setattr(finance_settings, "FIN_FIS_KEY", "configured-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    assert sector_reasoning._resolve_groq_api_key(None) == "configured-key"


def test_specialist_groq_keys_follow_env_sector_groups(monkeypatch):
    from capital_market_sector.config import CapitalMarketSectorSettings
    from external_sector.config import ExternalSectorSettings
    from labour_sector.config import LabourSectorSettings
    from monetary_sector.config import MonetarySectorSettings

    monkeypatch.setenv("SERV_EXT_KEY", "external-key")
    monkeypatch.setenv("PRIC_LAB_KEY", "prices-labour-key")
    monkeypatch.setenv("CAP_MON_KEY", "capital-monetary-key")

    external = ExternalSectorSettings(_env_file=None)
    labour = LabourSectorSettings(_env_file=None)
    capital = CapitalMarketSectorSettings(_env_file=None)
    monetary = MonetarySectorSettings(_env_file=None)

    assert external.SERV_EXT_KEY == "external-key"
    assert labour.LABOUR_LLM_KEY == "prices-labour-key"
    assert capital.CAPITAL_LLM_KEY == monetary.MONETARY_LLM_KEY == "capital-monetary-key"


def test_specialist_sector_models_use_the_verified_groq_model():
    from capital_market_sector.config import CapitalMarketSectorSettings
    from external_sector.config import ExternalSectorSettings
    from labour_sector.config import LabourSectorSettings
    from monetary_sector.config import MonetarySectorSettings

    verified_model = "openai/gpt-oss-120b"
    assert ExternalSectorSettings(_env_file=None).EXTERNAL_LLM_MODEL == verified_model
    assert LabourSectorSettings(_env_file=None).LABOUR_LLM_MODEL == verified_model
    assert CapitalMarketSectorSettings(_env_file=None).CAPITAL_LLM_MODEL == verified_model
    assert MonetarySectorSettings(_env_file=None).MONETARY_LLM_MODEL == verified_model
