from urllib.parse import urlsplit

import httpx

from app.core.config import settings


class SpeechToTextError(RuntimeError):
    def __init__(self, message: str, *, kind: str):
        super().__init__(message)
        self.kind = kind


def configured_speech_provider() -> str:
    return settings.speech_to_text_provider.strip().lower()


def speech_provider_available() -> bool:
    provider = configured_speech_provider()
    if provider == "browser":
        return True
    if provider == "openai_compatible":
        base_url = settings.speech_to_text_base_url or (
            settings.llm_base_url if settings.llm_api_key else ""
        )
        return bool(base_url and (settings.speech_to_text_api_key or settings.llm_api_key or _is_local(base_url)))
    return bool(settings.speech_to_text_base_url)


def _is_local(url: str) -> bool:
    return urlsplit(url).hostname in {"ollama", "localhost", "127.0.0.1", "host.docker.internal"}


async def transcribe_audio(audio: bytes, *, filename: str, content_type: str, language: str) -> str:
    provider = configured_speech_provider()
    if provider == "browser":
        raise SpeechToTextError("Speech recognition is configured in the browser.", kind="configuration")
    if provider not in {"openai_compatible", "indicconformer"}:
        raise SpeechToTextError("The configured speech-to-text provider is unsupported.", kind="configuration")

    if provider == "indicconformer":
        url = settings.speech_to_text_base_url.strip()
        if not url:
            raise SpeechToTextError(
                "Set SPEECH_TO_TEXT_BASE_URL to the IndicConformer inference adapter endpoint.",
                kind="configuration",
            )
    else:
        configured_url = settings.speech_to_text_base_url or (
            settings.llm_base_url if settings.llm_api_key else ""
        )
        if not configured_url:
            raise SpeechToTextError(
                "Set SPEECH_TO_TEXT_BASE_URL and provider credentials to enable hosted speech recognition.",
                kind="configuration",
            )
        base_url = configured_url.rstrip("/")
        url = base_url if base_url.endswith("/audio/transcriptions") else f"{base_url}/audio/transcriptions"

    headers: dict[str, str] = {}
    api_key = settings.speech_to_text_api_key or settings.llm_api_key
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = {"language": language, "response_format": "json"}
    if settings.speech_to_text_model:
        data["model"] = settings.speech_to_text_model
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.speech_to_text_timeout_seconds, connect=5.0)
        ) as client:
            response = await client.post(
                url,
                headers=headers,
                data=data,
                files={"file": (filename, audio, content_type)},
            )
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise SpeechToTextError("Speech recognition timed out. Try again or type the transcript.", kind="timeout") from exc
    except httpx.HTTPStatusError as exc:
        raise SpeechToTextError(
            f"Configured speech-to-text provider returned HTTP {exc.response.status_code}.",
            kind="unavailable",
        ) from exc
    except httpx.RequestError as exc:
        raise SpeechToTextError("Could not reach the configured speech-to-text provider.", kind="unavailable") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise SpeechToTextError("Speech-to-text provider returned malformed output.", kind="malformed") from exc
    transcript = payload.get("text") if isinstance(payload, dict) else None
    if not isinstance(transcript, str) or not transcript.strip() or len(transcript) > 4000:
        raise SpeechToTextError("Speech-to-text provider returned an empty or invalid transcript.", kind="malformed")
    return transcript.strip()
