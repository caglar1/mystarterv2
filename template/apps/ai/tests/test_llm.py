import json

import httpx
import pytest

from apps.ai.llm import LLMClient, LLMError, LLMRateLimited, LLMRefused, parse_json_text

SCHEMA = {
    "type": "object",
    "properties": {"ozet": {"type": "string"}},
    "required": ["ozet"],
    "additionalProperties": False,
}


def make_client(responses, *, provider="anthropic", model="claude-opus-5", **kwargs):
    """Sırayla yanıt veren sahte HTTP katmanı; gönderilen istekler `client.requests` içinde."""
    requests = []

    def handler(request):
        requests.append(request)
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    sleeps = []
    client = LLMClient(
        provider=provider,
        base_url="https://llm.test/v1",
        api_key="k",
        model=model,
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
        **kwargs,
    )
    client.requests, client.sleeps = requests, sleeps
    return client


def anthropic_message(text="Merhaba", stop_reason="end_turn", thinking=True):
    content = [{"type": "thinking", "thinking": "", "signature": "x"}] if thinking else []
    content.append({"type": "text", "text": text})
    return httpx.Response(
        200, json={"model": "claude-opus-5", "content": content, "stop_reason": stop_reason}
    )


def sse_body(events):
    return "".join(f"event: {name}\ndata: {json.dumps(data)}\n\n" for name, data in events).encode()


def body_of(request):
    return json.loads(request.content)


# ---------------------------------------------------------------- Anthropic
def test_anthropic_payload_uses_current_api_shape():
    client = make_client([anthropic_message()], effort="low")
    response = client.generate("Selam", system="Kısa yaz")
    assert response.text == "Merhaba"  # thinking bloğu atlandı

    request = client.requests[0]
    body = body_of(request)
    assert request.headers["x-api-key"] == "k"
    assert request.headers["anthropic-version"] == "2023-06-01"
    assert body["thinking"] == {"type": "adaptive"}
    assert body["output_config"] == {"effort": "low"}
    assert body["system"] == "Kısa yaz"
    # Güncel modellerde 400 döndüren eski parametreler gönderilmez
    assert "temperature" not in body
    assert "budget_tokens" not in json.dumps(body)
    # claude-opus-5: sunucu tarafı fallback varsayılan olarak açık
    assert body["fallbacks"] == "default"
    assert request.headers["anthropic-beta"] == "server-side-fallback-2026-07-01"


def test_anthropic_fallbacks_only_for_supported_models(settings):
    client = make_client([anthropic_message()], model="claude-sonnet-5")
    client.generate("x")
    body = body_of(client.requests[0])
    assert "fallbacks" not in body
    assert "anthropic-beta" not in client.requests[0].headers

    settings.LLM_FALLBACKS = "off"
    client = make_client([anthropic_message()])
    client.generate("x")
    assert "fallbacks" not in body_of(client.requests[0])


def test_anthropic_haiku_has_no_thinking_or_effort():
    client = make_client([anthropic_message(thinking=False)], model="claude-haiku-4-5")
    client.generate("x")
    body = body_of(client.requests[0])
    assert "thinking" not in body
    assert "output_config" not in body


def test_anthropic_structured_output_merged_with_effort():
    client = make_client([anthropic_message(text='{"ozet": "kısa"}')], effort="medium")
    assert client.generate_json("x", schema=SCHEMA) == {"ozet": "kısa"}
    body = body_of(client.requests[0])
    assert body["output_config"] == {"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}}


def test_anthropic_refusal_raises():
    client = make_client(
        [
            httpx.Response(
                200, json={"content": [], "stop_reason": "refusal", "stop_details": {"category": "cyber"}}
            )
        ]
    )
    with pytest.raises(LLMRefused, match="cyber"):
        client.generate("x")


def test_truncated_json_is_an_error():
    client = make_client([anthropic_message(text='{"ozet": "yar', stop_reason="max_tokens")])
    with pytest.raises(LLMError, match="max_tokens"):
        client.generate_json("x", schema=SCHEMA)


def test_anthropic_stream_yields_only_text_deltas():
    events = [
        ("message_start", {"type": "message_start", "message": {}}),
        (
            "content_block_start",
            {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking"}},
        ),
        (
            "content_block_delta",
            {"type": "content_block_delta", "delta": {"type": "thinking_delta", "thinking": ""}},
        ),
        ("ping", {"type": "ping"}),
        (
            "content_block_delta",
            {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Mer"}},
        ),
        (
            "content_block_delta",
            {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "haba"}},
        ),
        ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn"}}),
        ("message_stop", {"type": "message_stop"}),
    ]
    client = make_client([httpx.Response(200, content=sse_body(events))])
    assert "".join(client.stream("x")) == "Merhaba"
    assert body_of(client.requests[0])["stream"] is True


def test_anthropic_stream_refusal_raises():
    events = [("message_delta", {"type": "message_delta", "delta": {"stop_reason": "refusal"}})]
    client = make_client([httpx.Response(200, content=sse_body(events))])
    with pytest.raises(LLMRefused):
        list(client.stream("x"))


# ---------------------------------------------------------------- OpenAI uyumlu
def openai_message(text="Merhaba", finish_reason="stop"):
    return httpx.Response(
        200, json={"model": "m", "choices": [{"message": {"content": text}, "finish_reason": finish_reason}]}
    )


def test_openai_payload_is_conservative_by_default():
    client = make_client([openai_message()], provider="openai", model="deepseek-chat")
    assert client.generate("Selam", system="Kısa yaz").text == "Merhaba"
    request = client.requests[0]
    body = body_of(request)
    assert request.headers["authorization"] == "Bearer k"
    assert body["messages"][0] == {"role": "system", "content": "Kısa yaz"}
    assert "reasoning_effort" not in body  # her model desteklemez
    assert "response_format" not in body


def test_openai_reasoning_and_json_schema_when_enabled(settings):
    settings.LLM_OPENAI_REASONING = True
    settings.LLM_OPENAI_JSON_MODE = "schema"
    client = make_client([openai_message(text='```json\n{"ozet": "a"}\n```')], provider="openai", model="o")
    assert client.generate_json("x", schema=SCHEMA, effort="high") == {"ozet": "a"}
    body = body_of(client.requests[0])
    assert body["reasoning_effort"] == "high"
    assert body["response_format"]["type"] == "json_schema"


def test_openai_stream():
    raw = (
        b'data: {"choices":[{"delta":{"content":"Mer"}}]}\n\n'
        b'data: {"choices":[{"delta":{"content":"haba"}}]}\n\n'
        b"data: [DONE]\n\n"
    )
    client = make_client([httpx.Response(200, content=raw)], provider="openai", model="m")
    assert "".join(client.stream("x")) == "Merhaba"


# ---------------------------------------------------------------- Hata ve tekrar deneme
def test_retries_on_429_with_retry_after_then_succeeds():
    client = make_client([httpx.Response(429, headers={"retry-after": "3"}, json={}), anthropic_message()])
    assert client.generate("x").text == "Merhaba"
    assert client.sleeps == [3.0]


def test_rate_limit_exhausted_raises():
    client = make_client([httpx.Response(429, json={"error": {"message": "yavaş"}})] * 3, max_retries=2)
    with pytest.raises(LLMRateLimited, match="yavaş"):
        client.generate("x")
    assert len(client.requests) == 3


def test_client_errors_are_not_retried():
    client = make_client([httpx.Response(400, json={"error": {"message": "geçersiz model"}})])
    with pytest.raises(LLMError, match="geçersiz model"):
        client.generate("x")
    assert len(client.requests) == 1


def test_connection_error_retried():
    client = make_client([httpx.ConnectError("yok"), anthropic_message()])
    assert client.generate("x").text == "Merhaba"


def test_unconfigured_client_raises():
    client = LLMClient(provider="anthropic", api_key="", model="claude-opus-5", base_url="https://x.test")
    assert not client.configured
    with pytest.raises(LLMError, match="LLM_API_KEY"):
        client.generate("x")


def test_parse_json_text_handles_fences_and_noise():
    assert parse_json_text('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_text('Elbette! {"a": 2} umarım işe yarar') == {"a": 2}
    with pytest.raises(LLMError):
        parse_json_text("json yok")
