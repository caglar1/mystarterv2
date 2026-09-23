"""Sentry kurulumu: DSN yoksa başlatılmaz, varken gizlilik ayarlarıyla başlatılır (ağ yok)."""

import sys
import types

from apps.core.observability import configure_sentry


def fake_sentry(monkeypatch) -> list[dict]:
    calls: list[dict] = []
    module = types.ModuleType("sentry_sdk")
    module.init = lambda **kwargs: calls.append(kwargs)
    monkeypatch.setitem(sys.modules, "sentry_sdk", module)
    return calls


def test_without_dsn_nothing_is_started(monkeypatch):
    calls = fake_sentry(monkeypatch)
    assert configure_sentry("") is False
    assert not calls


def test_with_dsn_starts_without_personal_data(monkeypatch):
    calls = fake_sentry(monkeypatch)
    assert configure_sentry("https://key@sentry.example.com/1", environment="production") is True
    (options,) = calls
    assert options["dsn"] == "https://key@sentry.example.com/1"
    assert options["environment"] == "production"
    # KVKK: kullanıcı bilgisi ve form içerikleri gönderilmez, performans izleme kapalı
    assert options["send_default_pii"] is False
    assert options["max_request_body_size"] == "never"
    assert options["traces_sample_rate"] == 0.0
