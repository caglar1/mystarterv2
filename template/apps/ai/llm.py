"""Evrensel LLM gateway — saf httpx, SDK yok.

İki sağlayıcı ailesi desteklenir (LLM_PROVIDER ile açıkça seçilir, URL'den tahmin edilmez):

- "anthropic": https://api.anthropic.com/v1/messages
    * adaptive thinking + `output_config.effort` (güncel Claude modelleri; Haiku hariç)
    * `temperature` / `budget_tokens` GÖNDERİLMEZ (güncel modellerde 400 döner)
    * yanıt metni `type == "text"` bloklarından toplanır (thinking blokları atlanır)
    * `stop_reason == "refusal"` -> LLMRefused; claude-opus-5 için sunucu tarafı fallback açık
    * JSON: structured outputs (`output_config.format`)
- "openai": OpenAI uyumlu /chat/completions (OpenRouter, DeepSeek, Groq, Gemini, Ollama, vLLM...)
    * `reasoning_effort` ve JSON modu yalnızca ayarlarda açıksa gönderilir (her model desteklemez)

Kullanım:
    client = LLMClient()
    client.generate("Merhaba").text
    client.generate_json("...", schema={...})
    for parca in client.stream("..."): ...
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

ANTHROPIC_VERSION = "2023-06-01"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Sunucu tarafı fallback'in belgelendiği modeller (diğerlerine parametre gönderilmez).
FALLBACK_MODEL_PREFIXES = ("claude-opus-5", "claude-fable-5")
RETRY_STATUS = {408, 429, 500, 502, 503, 504, 529}
MAX_RETRY_AFTER = 30.0


class LLMError(Exception):
    """Sağlayıcı hatası (geçersiz istek, kimlik doğrulama, beklenmeyen yanıt...)."""


class LLMConfigError(LLMError):
    pass


class LLMRateLimited(LLMError):
    pass


class LLMRefused(LLMError):
    """Model isteği güvenlik gerekçesiyle reddetti (Anthropic `stop_reason: refusal`)."""


@dataclass
class LLMResponse:
    text: str
    model: str = ""
    stop_reason: str | None = None
    usage: dict = field(default_factory=dict)

    @property
    def truncated(self) -> bool:
        return self.stop_reason in {"max_tokens", "length"}


def parse_json_text(text: str) -> dict:
    """Modelin döndürdüğü metinden JSON nesnesini çıkarır (```json çitlerini de temizler)."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise LLMError("Yanıtta JSON bulunamadı") from None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise LLMError(f"Geçersiz JSON yanıtı: {exc}") from exc


def _iter_sse(lines: Iterator[str]) -> Iterator[tuple[str, str]]:
    """Ham SSE satırlarını (event, data) çiftlerine çevirir."""
    event, data = "message", []
    for line in lines:
        if not line:
            if data:
                yield event, "\n".join(data)
            event, data = "message", []
        elif line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].lstrip())
    if data:
        yield event, "\n".join(data)


class LLMClient:
    def __init__(
        self,
        *,
        provider: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        effort: str | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.provider = provider or settings.LLM_PROVIDER
        self.base_url = base_url or settings.LLM_BASE_URL
        self.api_key = api_key if api_key is not None else settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL
        self.effort = effort or settings.LLM_EFFORT
        self.max_tokens = max_tokens or settings.LLM_MAX_TOKENS
        self.max_retries = settings.LLM_MAX_RETRIES if max_retries is None else max_retries
        self.sleep = sleep
        if self.provider not in {"anthropic", "openai"}:
            raise LLMConfigError(f"Bilinmeyen LLM_PROVIDER: {self.provider!r}")
        self.http = httpx.Client(timeout=timeout or settings.LLM_TIMEOUT, transport=transport)

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model and self.base_url)

    # ------------------------------------------------------------------ public
    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_schema: dict | None = None,
        effort: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        payload, headers = self._build(prompt, system, json_schema, effort, max_tokens, stream=False)
        data = self._post(payload, headers).json()
        return self._parse_anthropic(data) if self.provider == "anthropic" else self._parse_openai(data)

    def generate_json(self, prompt: str, *, schema: dict, system: str | None = None, **kwargs) -> dict:
        response = self.generate(prompt, system=system, json_schema=schema, **kwargs)
        if response.truncated:
            raise LLMError("Yanıt max_tokens sınırında kesildi; JSON eksik olabilir.")
        return parse_json_text(response.text)

    def stream(
        self,
        prompt: str,
        *,
        system: str | None = None,
        effort: str | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        payload, headers = self._build(prompt, system, None, effort, max_tokens, stream=True)
        response = self._open_stream(payload, headers)
        try:
            events = _iter_sse(response.iter_lines())
            if self.provider == "anthropic":
                yield from self._stream_anthropic(events)
            else:
                yield from self._stream_openai(events)
        finally:
            response.close()

    # ----------------------------------------------------------- request build
    def _build(self, prompt, system, json_schema, effort, max_tokens, *, stream):
        if not self.configured:
            raise LLMConfigError("LLM yapılandırılmamış: LLM_API_KEY ve LLM_MODEL gerekli.")
        effort = effort or self.effort
        max_tokens = max_tokens or self.max_tokens
        if self.provider == "anthropic":
            return self._anthropic_payload(prompt, system, json_schema, effort, max_tokens, stream)
        return self._openai_payload(prompt, system, json_schema, effort, max_tokens, stream)

    def _anthropic_payload(self, prompt, system, json_schema, effort, max_tokens, stream):
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        payload: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system
        output_config: dict = {}
        if not self.model.startswith("claude-haiku"):
            # Haiku 4.5 adaptive thinking ve effort desteklemez; diğer güncel modeller destekler.
            payload["thinking"] = {"type": "adaptive"}
            if effort:
                output_config["effort"] = effort
        if json_schema:
            output_config["format"] = {"type": "json_schema", "schema": json_schema}
        if output_config:
            payload["output_config"] = output_config
        if settings.LLM_FALLBACKS == "default" and self.model.startswith(FALLBACK_MODEL_PREFIXES):
            payload["fallbacks"] = "default"
            headers["anthropic-beta"] = FALLBACK_BETA
        if stream:
            payload["stream"] = True
        return payload, headers

    def _openai_payload(self, prompt, system, json_schema, effort, max_tokens, stream):
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        messages = [{"role": "system", "content": system}] if system else []
        messages.append({"role": "user", "content": prompt})
        payload: dict = {"model": self.model, "messages": messages, "max_tokens": max_tokens}
        if settings.LLM_OPENAI_REASONING and effort:
            payload["reasoning_effort"] = effort
        if json_schema:
            mode = settings.LLM_OPENAI_JSON_MODE
            if mode == "schema":
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {"name": "sonuc", "schema": json_schema, "strict": True},
                }
            elif mode == "object":
                payload["response_format"] = {"type": "json_object"}
            # "none": şema, prompt'a eklenen talimatla istenir; yanıt parse_json_text ile ayrıştırılır.
            instruction = "Yalnızca şu JSON şemasına uyan geçerli bir JSON nesnesi döndür:\n" + json.dumps(
                json_schema, ensure_ascii=False
            )
            messages[-1]["content"] = f"{prompt}\n\n{instruction}"
        if stream:
            payload["stream"] = True
        return payload, headers

    # ----------------------------------------------------------- HTTP + retry
    def _retry_delay(self, response: httpx.Response | None, attempt: int) -> float:
        header = response.headers.get("retry-after") if response is not None else None
        try:
            return min(float(header), MAX_RETRY_AFTER) if header else float(2**attempt)
        except ValueError:
            return float(2**attempt)

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return response.text[:300]
        error = body.get("error", body)
        if isinstance(error, dict):
            return str(error.get("message") or error)[:300]
        return str(error)[:300]

    def _raise_for(self, response: httpx.Response) -> None:
        message = f"HTTP {response.status_code}: {self._error_message(response)}"
        if response.status_code == 429:
            raise LLMRateLimited(message)
        raise LLMError(message)

    def _post(self, payload: dict, headers: dict) -> httpx.Response:
        for attempt in range(self.max_retries + 1):
            try:
                response = self.http.post(self.base_url, json=payload, headers=headers)
            except httpx.TransportError as exc:
                if attempt == self.max_retries:
                    raise LLMError(f"Bağlantı hatası: {type(exc).__name__}") from exc
                self.sleep(self._retry_delay(None, attempt))
                continue
            if response.status_code == 200:
                return response
            if response.status_code in RETRY_STATUS and attempt < self.max_retries:
                self.sleep(self._retry_delay(response, attempt))
                continue
            self._raise_for(response)
        raise LLMError("Beklenmeyen durum: yeniden deneme döngüsü sonlandı")  # pragma: no cover

    def _open_stream(self, payload: dict, headers: dict):
        """Akışı açar; yalnızca ilk bayttan önceki hatalarda yeniden dener."""
        for attempt in range(self.max_retries + 1):
            request = self.http.build_request("POST", self.base_url, json=payload, headers=headers)
            try:
                response = self.http.send(request, stream=True)
            except httpx.TransportError as exc:
                if attempt == self.max_retries:
                    raise LLMError(f"Bağlantı hatası: {type(exc).__name__}") from exc
                self.sleep(self._retry_delay(None, attempt))
                continue
            if response.status_code == 200:
                return response
            response.read()
            response.close()
            if response.status_code in RETRY_STATUS and attempt < self.max_retries:
                self.sleep(self._retry_delay(response, attempt))
                continue
            self._raise_for(response)
        raise LLMError("Beklenmeyen durum: yeniden deneme döngüsü sonlandı")  # pragma: no cover

    # ------------------------------------------------------------- parse
    @staticmethod
    def _parse_anthropic(data: dict) -> LLMResponse:
        stop_reason = data.get("stop_reason")
        if stop_reason == "refusal":
            details = data.get("stop_details") or {}
            raise LLMRefused(f"Model isteği reddetti ({details.get('category') or 'kategori yok'})")
        text = "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        )
        return LLMResponse(
            text=text, model=data.get("model", ""), stop_reason=stop_reason, usage=data.get("usage", {})
        )

    @staticmethod
    def _parse_openai(data: dict) -> LLMResponse:
        choices = data.get("choices") or []
        if not choices:
            raise LLMError(f"Beklenmeyen yanıt: {str(data)[:200]}")
        choice = choices[0]
        return LLMResponse(
            text=(choice.get("message") or {}).get("content") or "",
            model=data.get("model", ""),
            stop_reason=choice.get("finish_reason"),
            usage=data.get("usage", {}),
        )

    @staticmethod
    def _stream_anthropic(events: Iterator[tuple[str, str]]) -> Iterator[str]:
        for event, data in events:
            if event == "ping":
                continue
            payload = json.loads(data)
            kind = payload.get("type")
            if kind == "content_block_delta" and payload["delta"].get("type") == "text_delta":
                yield payload["delta"]["text"]
            elif kind == "message_delta" and payload.get("delta", {}).get("stop_reason") == "refusal":
                raise LLMRefused("Model isteği yanıt sırasında reddetti")
            elif kind == "error":
                raise LLMError(payload.get("error", {}).get("message", "Akış hatası"))

    @staticmethod
    def _stream_openai(events: Iterator[tuple[str, str]]) -> Iterator[str]:
        for _event, data in events:
            if data.strip() == "[DONE]":
                return
            payload = json.loads(data)
            if "error" in payload:
                raise LLMError(str(payload["error"])[:300])
            for choice in payload.get("choices", []):
                chunk = (choice.get("delta") or {}).get("content")
                if chunk:
                    yield chunk


def get_client(**kwargs) -> LLMClient:
    """View'lar ve servisler istemciyi buradan alır (testlerde kolayca değiştirilebilir)."""
    return LLMClient(**kwargs)
