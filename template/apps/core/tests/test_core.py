import os
import subprocess
import sys
from pathlib import Path

import pytest
from django import forms
from django.contrib import messages
from django.core import signing
from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from django.urls import reverse

from apps.core import sync
from apps.core.forms import SpamProtectedFormMixin, StyledFormMixin
from apps.core.models import SyncRun
from apps.core.ratelimit import is_limited, parse_rate
from conftest import HTMX

BASE_DIR = Path(__file__).resolve().parents[3]


@pytest.mark.django_db
def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_robots_txt_points_to_sitemap(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert "Sitemap: http://testserver/sitemap.xml" in response.content.decode()


@pytest.mark.django_db
def test_sitemap_lists_pages(client):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert "/iletisim/" in response.content.decode()


def test_favicon_redirects_to_svg(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 301
    assert response["Location"].endswith("favicon.svg")


def test_web_manifest(client):
    response = client.get("/manifest.webmanifest")
    assert response["Content-Type"] == "application/manifest+json"
    assert response.json()["icons"][0]["src"].startswith("/static/core/icons/")


@pytest.mark.django_db
def test_security_headers_and_csp_nonce(client):
    response = client.get("/")
    csp = response["Content-Security-Policy"]
    assert "script-src 'self' 'nonce-" in csp
    assert "unsafe-eval" not in csp
    assert response["X-Frame-Options"] == "DENY"
    # Inline tema betiği nonce taşımalı
    assert 'nonce="' in response.content.decode()


def test_parse_rate():
    assert parse_rate("5/m") == (5, 60)
    assert parse_rate("5/10m") == (5, 600)
    assert parse_rate("100/d") == (100, 86400)
    with pytest.raises(ValueError):
        parse_rate("5 per minute")


def test_is_limited_counts_per_identity():
    assert not any(is_limited("t", "1.1.1.1", "3/m") for _ in range(3))
    assert is_limited("t", "1.1.1.1", "3/m")
    assert not is_limited("t", "2.2.2.2", "3/m")


class DemoForm(SpamProtectedFormMixin, StyledFormMixin, forms.Form):
    name = forms.CharField()
    agree = forms.BooleanField()
    note = forms.CharField(widget=forms.Textarea, required=False)


def _valid_data(**extra):
    data = {"name": "Ayşe", "agree": "on", "form_ts": signing.dumps(0.0, salt="form-ts")}
    data.update(extra)
    return data


def test_styled_form_classes():
    form = DemoForm()
    assert "input" in form.fields["name"].widget.attrs["class"]
    assert "checkbox" in form.fields["agree"].widget.attrs["class"]
    assert "textarea" in form.fields["note"].widget.attrs["class"]


def test_styled_form_marks_errors():
    form = DemoForm(data=_valid_data(name=""))
    assert not form.is_valid()
    assert "input-error" in form.fields["name"].widget.attrs["class"]
    assert form.fields["name"].widget.attrs["aria-invalid"] == "true"


def test_spam_protection_honeypot_and_timestamp(settings):
    assert DemoForm(data=_valid_data()).is_valid()
    assert not DemoForm(data=_valid_data(website="http://spam.example")).is_valid()
    assert not DemoForm(data=_valid_data(form_ts="bozuk")).is_valid()
    settings.FORM_MIN_SUBMIT_SECONDS = 10**12  # "çok hızlı" gönderim
    assert not DemoForm(data=_valid_data()).is_valid()


def test_honeypot_rendered_hidden():
    html = str(DemoForm())
    assert 'class="hidden" aria-hidden="true"' in html
    assert 'name="website"' in html


@pytest.mark.django_db
def test_htmx_messages_middleware_appends_oob_toast(rf):
    from django.contrib.messages.storage.fallback import FallbackStorage
    from django.contrib.sessions.middleware import SessionMiddleware
    from django_htmx.middleware import HtmxMiddleware

    from apps.core.middleware import HtmxMessagesMiddleware

    def view(request):
        messages.success(request, "Kaydedildi")
        return HttpResponse("<p>içerik</p>")

    request = RequestFactory().get("/", headers={"HX-Request": "true"})
    SessionMiddleware(lambda r: None).process_request(request)
    request._messages = FallbackStorage(request)
    response = HtmxMiddleware(HtmxMessagesMiddleware(view))(request)
    body = response.content.decode()
    assert body.startswith("<p>içerik</p>")
    assert 'hx-swap-oob="beforeend"' in body
    assert "Kaydedildi" in body


def _register_demo_job(result=(3, "tamam"), error=None):
    def handler():
        if error:
            raise error
        return result

    sync.register_job("demo", "Demo işi", handler)


@pytest.mark.django_db
def test_run_job_success_and_failure():
    _register_demo_job()
    run = sync.run_job("demo")
    assert run.status == SyncRun.Status.SUCCESS
    assert run.items == 3
    assert run.duration_seconds is not None

    _register_demo_job(error=RuntimeError("bağlantı yok"))
    run = sync.run_job("demo")
    assert run.status == SyncRun.Status.FAILED
    assert "bağlantı yok" in run.message


@pytest.mark.django_db
def test_sync_trigger_requires_staff(user_client):
    _register_demo_job()
    response = user_client.post(reverse("core:sync_trigger", args=["demo"]), **HTMX)
    assert response.status_code == 302  # yönetici girişine yönlendirilir
    assert not SyncRun.objects.exists()


@pytest.mark.django_db
def test_sync_trigger_and_status(staff_client):
    _register_demo_job()
    response = staff_client.post(reverse("core:sync_trigger", args=["demo"]), **HTMX)
    assert response.status_code == 200
    run = SyncRun.objects.get()
    # ImmediateBackend: görev hemen çalıştı
    assert run.status == SyncRun.Status.SUCCESS
    status = staff_client.get(reverse("core:sync_status", args=[run.pk]), **HTMX)
    assert status.status_code == 286  # htmx sorgulamayı durdurur
    assert staff_client.post(reverse("core:sync_trigger", args=["yok"]), **HTMX).status_code == 404


@pytest.mark.django_db
def test_sync_command(capsys):
    from django.core.management import call_command

    _register_demo_job()
    call_command("sync", "demo")
    assert "demo: 3 öge" in capsys.readouterr().out


def _deploy_check(**overrides):
    # test_settings os.environ'u değiştirdiği için temiz bir ortamla başla (.env de okunmasın)
    env = {key: os.environ[key] for key in ("PATH", "HOME", "VIRTUAL_ENV") if key in os.environ}
    env.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "DEBUG": "False",
            "SECRET_KEY": "prod-" + "k" * 60,
            "ALLOWED_HOSTS": "example.com",
            "CSRF_TRUSTED_ORIGINS": "https://example.com",
            "EMAIL_PROVIDER": "smtp",
            "SECURE_HSTS_PRELOAD": "True",
            "DOTENV_PATH": "/dev/null",
        }
    )
    env.update(overrides)
    return subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_deploy_check_passes_with_production_env():
    """`check --deploy` prod ortam değişkenleriyle hiç uyarı vermemeli."""
    result = _deploy_check()
    assert result.returncode == 0, result.stdout + result.stderr


def test_deploy_check_catches_console_email_in_production():
    result = _deploy_check(EMAIL_PROVIDER="console")
    assert result.returncode != 0
    assert "mail.E001" in result.stdout + result.stderr


def test_production_uses_hashed_compressed_static_storage():
    from django.conf import settings as django_settings

    # test_settings sade depolama kullanır; asıl ayarı kaynak koddan doğrula
    source = (BASE_DIR / "config" / "settings.py").read_text()
    assert "whitenoise.storage.CompressedManifestStaticFilesStorage" in source
    assert "STATICFILES_STORAGE" not in source  # Django 5.1'de kaldırıldı
    assert django_settings.STORAGES["staticfiles"]


@override_settings(DEBUG=False)
def test_404_page(client):
    response = client.get("/boyle-bir-sayfa-yok/")
    assert response.status_code == 404
    assert "bulunamadı" in response.content.decode()
