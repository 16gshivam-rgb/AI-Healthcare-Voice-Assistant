import asyncio

import httpx
from app.core.config import settings
from app.services.llm_provider import format_provider_failure_message
from app.services.llm_provider import (
    LLMProviderError,
    OllamaProvider,
    OpenAICompatibleProvider,
    get_llm_provider,
    validate_chat_completion_response,
)
from pydantic import BaseModel, ConfigDict


def test_llm_provider_factory_uses_configured_provider(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    assert isinstance(get_llm_provider(), OllamaProvider)

    monkeypatch.setattr(settings, "llm_provider", "openai_compatible")
    assert isinstance(get_llm_provider(), OpenAICompatibleProvider)

    monkeypatch.setattr(settings, "llm_provider", "custom")
    try:
        get_llm_provider()
        raise AssertionError("Unknown providers must not be silently substituted.")
    except LLMProviderError as error:
        assert "Unsupported configured AI provider" in str(error)


def test_provider_builds_strict_structured_output_payload():
    class Result(BaseModel):
        model_config = ConfigDict(extra="forbid")
        reply: str

    payload = OpenAICompatibleProvider().build_payload(
        [{"role": "user", "content": "test"}],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": Result.__name__, "strict": True, "schema": Result.model_json_schema()},
        },
    )
    assert payload["response_format"]["json_schema"]["strict"] is True
    assert payload["response_format"]["json_schema"]["schema"]["additionalProperties"] is False


def test_gpt6_payload_uses_reasoning_none_and_completion_token_limit(monkeypatch):
    monkeypatch.setattr(settings, "llm_model", "gpt-6-luna")
    monkeypatch.setattr(settings, "llm_max_tokens", 96)
    payload = OpenAICompatibleProvider().build_payload([{"role": "user", "content": "hello"}])
    assert payload["reasoning_effort"] == "none"
    assert payload["max_completion_tokens"] == 96
    assert "temperature" not in payload
    assert "max_tokens" not in payload


def test_provider_retries_only_transient_statuses(monkeypatch):
    monkeypatch.setattr(settings, "llm_max_retries", 1)
    attempts = 0

    def transient_then_success(request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]}, request=request)

    async def run_transient_case():
        async with httpx.AsyncClient(transport=httpx.MockTransport(transient_then_success)) as client:
            return await OpenAICompatibleProvider().complete(client, [{"role": "user", "content": "hello"}])

    result = asyncio.run(run_transient_case())
    assert attempts == 2
    assert validate_chat_completion_response(result) == "ok"

    attempts = 0

    def client_error(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(400, request=request)

    async def run_client_error_case():
        async with httpx.AsyncClient(transport=httpx.MockTransport(client_error)) as client:
            await OpenAICompatibleProvider().complete(client, [{"role": "user", "content": "hello"}])

    try:
        asyncio.run(run_client_error_case())
        raise AssertionError("A 400 response should be surfaced.")
    except httpx.HTTPStatusError:
        assert attempts == 1


def test_provider_rejects_json_that_does_not_match_pydantic_schema():
    class Result(BaseModel):
        model_config = ConfigDict(extra="forbid")
        reply: str

    def malformed_response(request):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{\"reply\":17}"}}]},
            request=request,
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(malformed_response)) as client:
            await OpenAICompatibleProvider().complete_structured(
                client,
                [{"role": "user", "content": "test"}],
                Result,
            )

    try:
        asyncio.run(run())
        raise AssertionError("Invalid structured output must be rejected.")
    except LLMProviderError as error:
        assert "did not match the required response schema" in str(error)


def test_validate_chat_completion_response_requires_non_empty_content():
    valid = {"choices": [{"message": {"content": "General guidance"}}]}
    assert validate_chat_completion_response(valid) == "General guidance"

    try:
        validate_chat_completion_response({"choices": [{"message": {"content": ""}}]})
        raise AssertionError("Expected empty response validation to fail")
    except LLMProviderError:
        pass

    try:
        validate_chat_completion_response({"choices": []})
        raise AssertionError("Expected empty choices validation to fail")
    except LLMProviderError:
        pass


def test_provider_failure_messages_keep_context_and_model_metadata():
    message = format_provider_failure_message(
        provider="ollama",
        model="llama3.2:1b-instruct-q4_K_M",
        status_code=503,
        detail="The provider is temporarily unavailable.",
    )
    assert "ollama" in message
    assert "llama3.2:1b-instruct-q4_K_M" in message
    assert "503" in message
    assert "temporarily unavailable" in message.lower()

    error = LLMProviderError(
        "custom failure",
        provider="ollama",
        model="llama3.2:1b-instruct-q4_K_M",
        status_code=503,
        retryable=True,
    )
    assert error.provider == "ollama"
    assert error.model == "llama3.2:1b-instruct-q4_K_M"
    assert error.status_code == 503
    assert error.retryable is True
