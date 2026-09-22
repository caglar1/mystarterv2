import pytest
from django.core.cache import cache

HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture(autouse=True)
def _clear_cache():
    """Rate limit sayaçları testler arasında sızmasın."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user("ayse", "ayse@example.com", "gizli-Sifre-123")


@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user(
        "yonetici", "yonetici@example.com", "gizli-Sifre-123", is_staff=True
    )


@pytest.fixture
def user_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def staff_client(client, staff_user):
    client.force_login(staff_user)
    return client
