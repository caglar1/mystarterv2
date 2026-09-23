import re

import pytest
from django.core import mail
from django.urls import reverse


@pytest.mark.django_db
def test_login_page_renders_styled_form(client, settings):
    response = client.get(reverse("accounts:login"))
    assert response.status_code == 200
    body = response.content.decode()
    assert 'class="input w-full' in body
    # Django'nun auth view'ları kendi site_name'ini koyar; başlık yine proje adını göstermeli
    assert f"<title>Log in · {settings.SITE_NAME}</title>" in body


@pytest.mark.django_db
def test_login_and_logout(client, user):
    response = client.post(reverse("accounts:login"), {"username": "ayse", "password": "gizli-Sifre-123"})
    assert response.status_code == 302
    assert client.get(reverse("pages:home")).context["user"].is_authenticated
    response = client.post(reverse("accounts:logout"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_login_is_rate_limited(client, user):
    url = reverse("accounts:login")
    for _ in range(10):
        client.post(url, {"username": "ayse", "password": "yanlis"})
    assert client.post(url, {"username": "ayse", "password": "yanlis"}).status_code == 429


@pytest.mark.django_db
def test_password_reset_sends_email(client, user, settings):
    response = client.post(reverse("accounts:password_reset"), {"email": "ayse@example.com"})
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["ayse@example.com"]
    assert settings.SITE_NAME in mail.outbox[0].subject
    # Worker'da üretilen bağlantı geçerli: şifre belirleme adımına yönlendirir
    link = re.search(r"https?://testserver(/account/password/reset/\S+)", mail.outbox[0].body).group(1)
    assert client.get(link)["Location"].endswith("/set-password/")


@pytest.mark.django_db
def test_password_reset_email_goes_through_a_task_without_the_token(client, user, monkeypatch):
    """İstek SMTP'yi beklemez (yanıt süresi adresin kayıtlı olup olmadığını ele vermez) ve sıfırlama
    bağlantısı görev kuyruğu tablosuna yazılmaz: token worker'da üretilir."""
    from apps.accounts import forms

    calls = []

    class Recorder:
        def enqueue(self, *args):
            calls.append(args)

    monkeypatch.setattr(forms, "send_password_reset_email", Recorder())
    client.post(reverse("accounts:password_reset"), {"email": "ayse@example.com"})
    # Argümanların tamamı bu: bağlantı ya da token yok
    assert calls == [
        (
            user.pk,
            "testserver",
            "testserver",
            "http",
            "en",
            "accounts/password_reset_subject.txt",
            "accounts/password_reset_email.txt",
            None,
        )
    ]


@pytest.mark.django_db
def test_signup_requires_email(client, settings):
    settings.ACCOUNTS_ALLOW_SIGNUP = True
    page = client.get(reverse("accounts:signup"))
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "yeni",
            "password1": "Cok-Guclu-Sifre-42",
            "password2": "Cok-Guclu-Sifre-42",
            "form_ts": page.context["form"]["form_ts"].initial,
        },
    )
    assert response.status_code == 422
    assert "email" in response.context["form"].errors


@pytest.mark.django_db
def test_signup_disabled_by_default(client):
    assert client.get(reverse("accounts:signup")).status_code == 404


@pytest.mark.django_db
def test_signup_when_enabled(client, settings, django_user_model):
    settings.ACCOUNTS_ALLOW_SIGNUP = True
    page = client.get(reverse("accounts:signup"))
    form_ts = page.context["form"]["form_ts"].initial
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "yeni",
            "email": "yeni@example.com",
            "password1": "Cok-Guclu-Sifre-42",
            "password2": "Cok-Guclu-Sifre-42",
            "form_ts": form_ts,
        },
    )
    assert response.status_code == 302
    assert django_user_model.objects.filter(username="yeni").exists()
