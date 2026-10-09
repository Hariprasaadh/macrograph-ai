"""Model-Agnostic LLM Client with rate limit backoff, model fallback, and offline modes."""
from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
import logging
import os
from typing import Any, Optional

from ..config import settings

logger = logging.getLogger(__name__)

_SYNC_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2)


class _GroqWrapper:
    """Thin synchronous wrapper around the raw Groq SDK when langchain_groq is absent."""

    def __init__(self, api_key: str, model: str, temperature: float, timeout: int) -> None:
        from groq import Groq
        self._client = Groq(api_key=api_key, timeout=timeout, max_retries=1)
        self._model = model
        self._temperature = temperature

    def invoke(self, messages: list) -> Any:
        formatted = [
            {"role": "user" if r == "human" else r, "content": c}
            for r, c in messages
        ]
        result = self._client.chat.completions.create(
            model=self._model, messages=formatted, temperature=self._temperature
        )

        class _Resp:
            content = result.choices[0].message.content or ""

        return _Resp()


class ModelAgnosticLLMClient:
    """Resilient model-agnostic LLM completions across Groq, OpenAI, or a deterministic fallback."""

    def __init__(self) -> None:
        self.provider = settings.MODEL_PROVIDER.lower()
        self.fast_model = settings.FAST_MODEL
        self.reasoning_model = settings.REASONING_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_retries = settings.LLM_MAX_RETRIES

    def _get_api_key(self) -> str:
        if self.provider == "groq":
            return (
                settings.GROQ_API_KEY
                or os.getenv("GROQ_API_KEY", "")
                or os.getenv("ORCH_KEY", "")
                or os.getenv("PRIC_LAB_KEY", "")
                or os.getenv("FIN_FIS_KEY", "")
                or os.getenv("SERV_EXT_KEY", "")
                or os.getenv("AGR_REAL_KEY", "")
                or os.getenv("CAP_MON_KEY", "")
            )
        elif self.provider == "openai":
            return settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
        return ""

    def _get_chat_model(self, model_name: str) -> Optional[Any]:
        """Initialize LangChain chat model wrapper based on provider."""
        api_key = self._get_api_key()
        if self.provider == "groq" and api_key:
            try:
                from langchain_groq import ChatGroq
                return ChatGroq(
                    groq_api_key=api_key,
                    model_name=model_name,
                    temperature=self.temperature,
                    timeout=settings.LLM_TIMEOUT,
                    max_retries=1,
                )
            except Exception:
                try:
                    return _GroqWrapper(
                        api_key=api_key,
                        model=model_name,
                        temperature=self.temperature,
                        timeout=settings.LLM_TIMEOUT,
                    )
                except Exception as exc:
                    logger.warning("Could not initialize Groq wrapper: %s", exc)
                    return None
        elif self.provider == "openai" and api_key:
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    openai_api_key=api_key,
                    model_name=model_name,
                    temperature=self.temperature,
                    timeout=settings.LLM_TIMEOUT,
                )
            except Exception as exc:
                logger.warning("Could not initialize ChatOpenAI: %s", exc)
                return None
        return None

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        use_reasoning_model: bool = False,
    ) -> str:
        """Execute LLM completion with exponential async retry and fallback from reasoning to fast model."""
        target_model = self.reasoning_model if use_reasoning_model else self.fast_model
        chat_llm = self._get_chat_model(target_model)

        if chat_llm:
            messages = []
            if system_prompt:
                messages.append(("system", system_prompt))
            messages.append(("human", prompt))

            for attempt in range(self.max_retries):
                try:
                    response = await asyncio.to_thread(chat_llm.invoke, messages)
                    return str(response.content)
                except Exception as err:
                    err_str = str(err)
                    logger.warning("LLM attempt %d failed: %s", attempt + 1, err_str)
                    if "429" in err_str and use_reasoning_model and attempt == 0:
                        fallback_llm = self._get_chat_model(self.fast_model)
                        if fallback_llm:
                            try:
                                resp = await asyncio.to_thread(fallback_llm.invoke, messages)
                                return str(resp.content)
                            except Exception as fallback_err:
                                logger.warning("Fast-model fallback failed: %s", fallback_err)
                    await asyncio.sleep(1.5 * (attempt + 1))

        return self._unavailable_notice()

    def complete_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        use_reasoning_model: bool = False,
    ) -> str:
        """Synchronous wrapper used by LangGraph sync nodes via run_sync()."""
        res = self.complete(prompt, system_prompt, use_reasoning_model)
        if inspect.isawaitable(res):
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return asyncio.run(res)
            return _SYNC_POOL.submit(asyncio.run, res).result()
        return str(res)

    @staticmethod
    def _unavailable_notice() -> str:
        """Returned when no LLM endpoint is reachable — never fabricates analysis."""
        return (
            "**LLM Synthesis Unavailable**: No API key is configured or the LLM "
            "endpoint is unreachable. Raw indicator data from sector agents is "
            "included in the sections below; narrative synthesis could not be generated."
        )


llm_client = ModelAgnosticLLMClient()
