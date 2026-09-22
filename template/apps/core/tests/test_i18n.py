"""Çok dillilik: öneksiz kaynak dil, önekli diğer diller, çevrilmiş URL'ler, hreflang, e-posta dili."""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.core import mail, signing
from django.urls import reverse
from django.utils import translation
from django.utils.translation import to_locale

from conftest import HTMX

BASE_DIR = Path(__file__).resolve().parents[3]
OTHER_LANGUAGES = [code for code, _name in settings.LANGUAGES if code != settings.LANGUAGE_CODE]
needs_turkish = pytest.mark.skipif("tr" not in dict(settings.LANGUAGES), reason="Türkçe etkin değil")


def url_in(language: str, name: str, *args) -> str:
    with translation.override(language):
        return reverse(name, args=args)


@pytest.mark.django_db
def test_default_language_is_unprefixed(client):
    body = client.get("/").content.decode()
    assert f'<html lang="{settings.LANGUAGE_CODE}"' in body
    assert reverse("pages:about") == "/about/"


@needs_turkish
@pytest.mark.django_db
def test_turkish_pages_are_prefixed_and_translated(client):
    about = url_in("tr", "pages:about")
    assert about == "/tr/hakkimizda/"
    body = client.get(about).content.decode()
    assert '<html lang="tr"' in body
    assert "Hakkımızda" in body
    assert "Tüm hakları saklıdır" in body  # footer (blocktranslate)
    # Aynı sayfa İngilizce'de de açılır
    assert "About us" in client.get("/about/").content.decode()


@needs_turkish
@pytest.mark.django_db
def test_hreflang_alternates(client):
    body = client.get("/about/").content.decode()
    assert '<link rel="alternate" hreflang="en" href="http://testserver/about/">' in body
    assert '<link rel="alternate" hreflang="tr" href="http://testserver/tr/hakkimizda/">' in body
    assert '<link rel="alternate" hreflang="x-default" href="http://testserver/about/">' in body


@needs_turkish
@pytest.mark.django_db
def test_language_switcher_translates_the_current_url(client):
    response = client.post(reverse("set_language"), {"language": "tr", "next": "/about/"})
    assert response.status_code == 302
    assert response["Location"] == "/tr/hakkimizda/"


@needs_turkish
@pytest.mark.django_db
def test_sitemap_lists_every_language(client):
    body = client.get("/sitemap.xml").content.decode()
    assert "http://testserver/about/" in body
    assert "http://testserver/tr/hakkimizda/" in body
    assert 'hreflang="x-default"' in body


@needs_turkish
@pytest.mark.django_db
def test_htmx_endpoints_answer_in_page_language(client):
    """Önekli sayfadaki form, önekli uca gider; hata mesajları o dilde döner."""
    submit = url_in("tr", "inquiries:submit")
    assert submit == "/tr/teklif/gonder/"
    body = client.post(submit, {"full_name": ""}, **HTMX).content.decode()
    assert "Bu alan zorunludur" in body  # Django'nun kendi Türkçe çevirisi
    assert "onay vermeniz gerekiyor" in body  # bizim çevirimiz


@needs_turkish
@pytest.mark.django_db
def test_inquiry_emails_use_the_form_language(client, settings):
    settings.NOTIFICATION_EMAILS = ["ekip@example.com"]
    data = {
        "full_name": "Ayşe Yılmaz",
        "email": "ayse@example.com",
        "message": "Web sitemizi yenilemek istiyoruz.",
        "consent": "on",
        "form_ts": signing.dumps(0.0, salt="form-ts"),
    }
    client.post(url_in("tr", "inquiries:submit"), data, **HTMX)
    by_recipient = {message.to[0]: message for message in mail.outbox}
    assert "talebinizi aldık" in by_recipient["ayse@example.com"].subject  # müşteri: formun dili
    assert by_recipient["ekip@example.com"].subject.startswith("New quote request")  # ekip: varsayılan dil


def _po_entries(path: Path):
    """Basit .po ayrıştırıcı: (msgid, [msgstr...], fuzzy) üretir (polib bağımlılığı olmadan)."""
    for block in path.read_text().split("\n\n"):
        lines = [line for line in block.splitlines() if line and not line.startswith("#~")]
        fuzzy = any(line.startswith("#,") and "fuzzy" in line for line in lines)
        fields: dict[str, list[str]] = {}
        current = None
        for line in lines:
            if line.startswith("#"):
                continue
            match = re.match(r'^(msgid|msgid_plural|msgstr(?:\[\d+\])?|msgctxt) "(.*)"$', line)
            if match:
                current = match.group(1)
                fields[current] = [match.group(2)]
            elif line.startswith('"') and current:
                fields[current].append(line[1:-1])
        if "msgid" not in fields:
            continue
        msgid = "".join(fields["msgid"])
        if not msgid:
            continue  # başlık
        strs = ["".join(v) for k, v in fields.items() if k.startswith("msgstr")]
        yield msgid, strs, fuzzy


def test_translations_are_complete():
    """Kaynak dil dışındaki her dil için boş ya da 'fuzzy' çeviri kalmamalı (`make messages`)."""
    problems = []
    for code in OTHER_LANGUAGES + (["tr"] if "tr" not in OTHER_LANGUAGES else []):
        locale = to_locale(code)  # pt-br -> pt_BR
        for po in [
            *BASE_DIR.glob(f"apps/*/locale/{locale}/LC_MESSAGES/django.po"),
            *BASE_DIR.glob(f"locale/{locale}/LC_MESSAGES/django.po"),
        ]:
            for msgid, strs, fuzzy in _po_entries(po):
                if fuzzy or not all(strs):
                    problems.append(f"{po.relative_to(BASE_DIR)}: {msgid!r}")
    assert not problems, "Eksik çeviriler:\n" + "\n".join(problems)
    for po in BASE_DIR.glob("apps/*/locale/*/LC_MESSAGES/django.po"):
        assert po.with_suffix(".mo").exists(), f"Derlenmemiş: {po} (make messages)"
