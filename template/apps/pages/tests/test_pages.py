import pytest
from django.urls import reverse

PUBLIC_PAGES = ["pages:home", "pages:about", "pages:services", "pages:contact", "pages:privacy"]


@pytest.mark.django_db
@pytest.mark.parametrize("name", PUBLIC_PAGES)
def test_public_pages_render(client, name):
    response = client.get(reverse(name))
    assert response.status_code == 200
    body = response.content.decode()
    assert "<main" in body
    assert 'hx-headers=\'{"X-CSRFToken"' in body


@pytest.mark.django_db
def test_home_shows_inquiry_form(client):
    body = client.get(reverse("pages:home")).content.decode()
    assert 'id="inquiry-form"' in body
    assert f'hx-post="{reverse("inquiries:submit")}"' in body


@pytest.mark.django_db
def test_navbar_only_links_installed_modules(client, settings):
    body = client.get(reverse("pages:home")).content.decode()
    for feature, url_prefix in [("maps", "/map/"), ("news", "/news/")]:
        if settings.FEATURES[feature]:
            assert f'href="{url_prefix}"' in body
        else:
            assert f'href="{url_prefix}"' not in body


@pytest.mark.django_db
def test_ui_kit_only_in_debug(client, settings):
    if not settings.FEATURES["ui_kit"]:
        pytest.skip("UI kit bu projede kurulu değil")
    assert client.get("/dev/ui-kit/").status_code == 404
    settings.DEBUG = True
    assert client.get("/dev/ui-kit/").status_code == 200
