import re

import pytest
from django.urls import reverse

from apps.ai import llm, views
from conftest import HTMX

TEXT = "Django, hızlı geliştirme ve temiz tasarımı teşvik eden üst düzey bir Python web çatısıdır. " * 2


class FakeClient:
    configured = True

    def __init__(self, chunks=None, error=None):
        self.chunks, self.error, self.calls = chunks or [], error, []

    def stream(self, prompt, system=None, **kwargs):
        self.calls.append(prompt)
        self.systems = [*getattr(self, "systems", []), system]
        if self.error:
            raise self.error
        yield from self.chunks


@pytest.fixture
def fake_client(monkeypatch):
    fake = FakeClient(chunks=["Kısa ", "özet <b>"])
    monkeypatch.setattr(llm, "get_client", lambda **kwargs: fake)
    return fake


def start(client, text=TEXT, url=None):
    return client.post(url or reverse("ai:summarize_start"), {"text": text, "length": "short"}, **HTMX)


def stream_url(response) -> str:
    return re.search(r'sse-connect="([^"]+)"', response.content.decode()).group(1)


def stream_body(client, response):
    url = stream_url(response)
    streamed = client.get(url)
    assert streamed["Content-Type"] == "text/event-stream"
    return b"".join(streamed.streaming_content).decode(), url


@pytest.mark.django_db
def test_requires_login(client):
    response = client.get(reverse("ai:summarize"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]


@pytest.mark.django_db
def test_page_warns_when_unconfigured(user_client, settings):
    settings.LLM_API_KEY = ""
    body = user_client.get(reverse("ai:summarize")).content.decode()
    assert "The LLM is not configured" in body
    assert "inert" in body


@pytest.mark.django_db
def test_invalid_form_returns_422(user_client, fake_client):
    response = start(user_client, text="kısa")
    assert response.status_code == 422
    assert "input-error" in response.content.decode() or "textarea-error" in response.content.decode()


@pytest.mark.django_db
def test_stream_escapes_html_and_finishes(user_client, fake_client):
    response = start(user_client)
    assert stream_url(response).startswith("/ai/summary/stream/")
    body, url = stream_body(user_client, response)
    assert "event: delta\ndata: Kısa \n\n" in body
    assert "özet &lt;b&gt;" in body  # model çıktısı HTML olarak yorumlanmaz
    assert body.rstrip().endswith('data: <span class="text-success">Done</span>')
    assert "Django" in fake_client.calls[0]
    # Tek kullanımlık anahtar
    assert user_client.get(url).status_code == 404


@pytest.mark.django_db
def test_stream_reports_refusal(user_client, monkeypatch):
    fake = FakeClient(error=llm.LLMRefused("hayır"))
    monkeypatch.setattr(llm, "get_client", lambda **kwargs: fake)
    body, _ = stream_body(user_client, start(user_client))
    assert "event: failure" in body and "declined" in body


@pytest.mark.django_db
def test_stream_key_is_bound_to_user(user_client, fake_client, django_user_model, client):
    url = stream_url(start(user_client))
    other = django_user_model.objects.create_user("baska", password="x")
    client.force_login(other)
    assert client.get(url).status_code == 404


@pytest.mark.django_db
def test_busy_server_rejects_extra_streams(user_client, fake_client, monkeypatch):
    import threading

    monkeypatch.setattr(views, "_STREAM_SLOTS", threading.BoundedSemaphore(1))
    views._STREAM_SLOTS.acquire()
    try:
        body, _ = stream_body(user_client, start(user_client))
    finally:
        views._STREAM_SLOTS.release()
    assert "busy" in body


@pytest.mark.django_db
def test_summary_is_written_in_the_page_language(user_client, fake_client, settings):
    if "tr" not in dict(settings.LANGUAGES):
        pytest.skip("Türkçe etkin değil")
    from django.utils import translation

    with translation.override("tr"):
        url = reverse("ai:summarize_start")
    assert url == "/tr/ai/ozet/baslat/"
    body, _ = stream_body(user_client, start(user_client, url=url))
    assert "Tamamlandı" in body
    assert "Write in Turkish." in fake_client.systems[-1]
