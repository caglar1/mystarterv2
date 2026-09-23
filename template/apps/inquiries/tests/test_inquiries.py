import pytest
from django.core import mail, signing
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
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


PDF = b"%PDF-1.7\n" + b"0" * 200


def pdf_upload(name: str = "teklif.pdf", content: bytes = PDF) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type="application/pdf")


@pytest.mark.django_db
def test_submit_with_attachment(client):
    response = client.post(URL, payload(attachment=pdf_upload()), **HTMX)
    assert response.status_code == 200
    inquiry = Inquiry.objects.get()
    # Dosya adı kullanıcıdan gelmez ve herkese açık olmayan klasöre yazılır
    assert inquiry.attachment.name.startswith("private/inquiries/")
    assert "teklif" not in inquiry.attachment.name
    assert inquiry.attachment.read() == PDF


@pytest.mark.django_db
def test_submit_rejects_disguised_attachment(client):
    response = client.post(URL, payload(attachment=pdf_upload(content=b"#!/bin/sh")), **HTMX)
    assert response.status_code == 422
    assert not Inquiry.objects.exists()


@pytest.mark.django_db
def test_attachment_download_is_staff_only(client, django_user_model):
    client.post(URL, payload(attachment=pdf_upload()), **HTMX)
    inquiry = Inquiry.objects.get()
    url = reverse("inquiries:attachment", args=[inquiry.pk])

    assert client.get(url).status_code == 302  # anonim: yönetim girişine

    user = django_user_model.objects.create_user("uye", password="x" * 12)
    client.force_login(user)
    assert client.get(url).status_code == 302  # giriş yapmış ama yetkisiz

    staff = django_user_model.objects.create_user("yonetici", password="x" * 12, is_staff=True)
    client.force_login(staff)
    response = client.get(url)
    assert response.status_code == 200
    assert "attachment;" in response["Content-Disposition"]
    assert b"".join(response.streaming_content) == PDF


@pytest.mark.django_db
def test_attachment_is_deleted_with_the_inquiry(client):
    client.post(URL, payload(attachment=pdf_upload()), **HTMX)
    inquiry = Inquiry.objects.get()
    name = inquiry.attachment.name
    assert default_storage.exists(name)
    inquiry.delete()
    assert not default_storage.exists(name)  # KVKK: kayıt silinince dosya da gider


@pytest.mark.django_db
def test_customer_email_never_echoes_user_input(client, settings):
    """Onay e-postası formdaki metni içermemeli: aksi halde form, spam göndermek için kullanılabilir."""
    settings.NOTIFICATION_EMAILS = ["ekip@example.com"]
    client.post(URL, payload(message="Ucuz kredi: spam.example.com"), **HTMX)
    by_recipient = {message.to[0]: message for message in mail.outbox}
    customer = by_recipient["ayse@example.com"]
    assert "spam.example.com" not in customer.body
    assert "Ayşe Yılmaz" not in customer.body
    # Ekibe giden bildirimde mesaj elbette var
    assert "spam.example.com" in by_recipient["ekip@example.com"].body


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
