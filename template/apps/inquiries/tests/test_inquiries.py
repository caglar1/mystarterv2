import pytest
from django.core import mail, signing
from django.urls import reverse

from apps.inquiries.models import Inquiry
from conftest import HTMX

URL = "/quote/send/"  # reverse("inquiries:submit"); varsayılan dil önek almaz


def payload(**extra):
    data = {
        "full_name": "Ayşe Yılmaz",
        "email": "ayse@example.com",
        "phone": "05551112233",
        "message": "Web sitemizi yenilemek istiyoruz.",
        "consent": "on",
        "form_ts": signing.dumps(0.0, salt="form-ts"),
    }
    data.update(extra)
    return data


@pytest.mark.django_db
def test_htmx_submit_saves_and_sends_emails(client, settings):
    settings.NOTIFICATION_EMAILS = ["ekip@example.com"]
    response = client.post(URL, payload(), **HTMX)
    assert response.status_code == 200
    body = response.content.decode()
    assert "Thank you, Ayşe Yılmaz" in body
    # Mesaj aynı yanıtta toast olarak gelir (bir sonraki sayfaya kaymaz)
    assert 'hx-swap-oob="beforeend"' in body
    inquiry = Inquiry.objects.get()
    assert inquiry.consent_at is not None
    recipients = sorted(address for message in mail.outbox for address in message.to)
    assert recipients == ["ayse@example.com", "ekip@example.com"]


@pytest.mark.django_db
def test_non_htmx_submit_redirects(client):
    response = client.post(URL, payload())
    assert response.status_code == 302
    assert response["Location"] == reverse("pages:contact")


@pytest.mark.django_db
def test_invalid_submit_returns_422_with_errors(client):
    response = client.post(URL, payload(email="gecersiz", consent=""), **HTMX)
    assert response.status_code == 422
    body = response.content.decode()
    assert "input-error" in body
    assert "give your consent" in body
    assert not Inquiry.objects.exists()


@pytest.mark.django_db
def test_honeypot_blocks_bots(client):
    response = client.post(URL, payload(website="spam"), **HTMX)
    assert response.status_code == 422
    assert not Inquiry.objects.exists()
    assert not mail.outbox


@pytest.mark.django_db
def test_rate_limit_returns_toast(client):
    for _ in range(5):
        client.post(URL, payload(), **HTMX)
    response = client.post(URL, payload(), **HTMX)
    assert response.status_code == 429
    assert response["HX-Retarget"] == "#toasts"
    assert Inquiry.objects.count() == 5


def test_get_not_allowed(client):
    assert client.get(URL).status_code == 405
