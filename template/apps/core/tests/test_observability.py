"""Sentry kurulumu: DSN yoksa başlatılmaz, varken gizlilik ayarlarıyla başlatılır (ağ yok)."""

import os
import subprocess
import sys
import types
from pathlib import Path

from apps.core.observability import configure_sentry

BASE_DIR = Path(__file__).resolve().parents[3]


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


def request_logger_handlers(sentry_dsn: str) -> list[str]:
    """Ayarları ayrı bir süreçte yükleyip `django.request` handler'larını okur."""
    code = (
        "import logging, django; django.setup(); "
        "print([type(h).__name__ for h in logging.getLogger('django.request').handlers])"
    )
    environment = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.test_settings",
        "SENTRY_DSN": sentry_dsn,
    }
    result = subprocess.run(  # noqa: S603
        [sys.executable, "manage.py", "shell", "-c", code],
        cwd=BASE_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip().splitlines()[-1]


def test_error_emails_stop_when_sentry_is_running():
    """Sentry açıkken aynı hata iki kanaldan bildirilmesin; DSN yoksa e-posta devrede kalsın."""
    assert "AdminEmailHandler" in request_logger_handlers("")
    assert "AdminEmailHandler" not in request_logger_handlers("https://key@sentry.invalid/1")
