import json
from pathlib import Path

import httpx
import pytest
from django.urls import reverse

from apps.core.models import SyncRun
from apps.places import services
from apps.places.geo import bounding_box, haversine_km
from apps.places.models import Place
from apps.places.overpass import OverpassClient, OverpassError, around_query
from conftest import HTMX

ELEMENTS = [
    {"type": "node", "id": 1, "lat": 41.0, "lon": 29.0, "tags": {"name": "Eczane A", "amenity": "pharmacy"}},
    {
        "type": "way",
        "id": 2,
        "center": {"lat": 41.01, "lon": 29.01},
        "tags": {"name": "Hastane B", "amenity": "hospital", "phone": "0212 000 00 00"},
    },
    {"type": "node", "id": 3, "lat": 41.02, "lon": 29.02, "tags": {"amenity": "clinic"}},  # adsız -> atlanır
]


def overpass_transport(responses):
    """Sırasıyla verilen yanıtları döndüren sahte HTTP katmanı. Çağrılan URL'ler kaydedilir."""
    calls = []

    def handler(request):
        calls.append(str(request.url))
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        status, payload = item
        return httpx.Response(status, json=payload)

    return httpx.MockTransport(handler), calls


def test_haversine_known_distance():
    # İstanbul (Sultanahmet) - Ankara (Kızılay) ≈ 350 km
    assert 345 < haversine_km(41.0054, 28.9768, 39.9208, 32.8541) < 355
    assert haversine_km(41, 29, 41, 29) == 0


def test_bounding_box_contains_radius():
    min_lat, max_lat, min_lng, max_lng = bounding_box(41.0, 29.0, 1)
    assert haversine_km(41.0, 29.0, max_lat, 29.0) == pytest.approx(1, rel=1e-3)
    assert haversine_km(41.0, 29.0, 41.0, max_lng) == pytest.approx(1, rel=1e-2)
    assert min_lat < 41.0 < max_lat and min_lng < 29.0 < max_lng


def test_around_query():
    ql = around_query(41.0, 29.0, 500, ['amenity="pharmacy"'])
    assert 'nwr[amenity="pharmacy"](around:500,41.0,29.0);' in ql
    assert "out center tags;" in ql


def test_overpass_falls_back_to_second_endpoint():
    transport, calls = overpass_transport([(504, {}), (200, {"elements": ELEMENTS})])
    client = OverpassClient(["https://a.test/api", "https://b.test/api"], "test/1.0", transport=transport)
    assert len(client.query("[out:json];")) == 3
    assert calls == ["https://a.test/api", "https://b.test/api"]


def test_overpass_retries_then_raises_with_all_failures():
    responses = [(429, {}), httpx.ConnectError("yok")] * 2
    transport, calls = overpass_transport(list(responses))
    sleeps = []
    client = OverpassClient(
        ["https://a.test/api", "https://b.test/api"], "test/1.0", transport=transport, sleep=sleeps.append
    )
    with pytest.raises(OverpassError, match=r"HTTP 429.*ConnectError"):
        client.query("[out:json];")
    assert len(calls) == 4
    assert sleeps == [5.0]


def test_overpass_bad_query_fails_fast():
    transport, calls = overpass_transport([(400, {})])
    client = OverpassClient(["https://a.test/api", "https://b.test/api"], "test/1.0", transport=transport)
    with pytest.raises(OverpassError, match="rejected"):
        client.query("bozuk")
    assert len(calls) == 1


@pytest.mark.django_db
def test_upsert_is_idempotent_and_updates():
    assert services.upsert_places(ELEMENTS) == 2
    assert services.upsert_places(ELEMENTS) == 2
    assert Place.objects.count() == 2
    hospital = Place.objects.get(osm_id="way/2")
    assert (hospital.lat, hospital.phone) == (41.01, "0212 000 00 00")

    renamed = [{**ELEMENTS[0], "tags": {"name": "Eczane A (yeni)", "amenity": "pharmacy"}}]
    services.upsert_places(renamed)
    assert Place.objects.get(osm_id="node/1").name == "Eczane A (yeni)"


@pytest.mark.django_db
def test_nearby_sorted_by_distance_and_filtered_by_radius():
    services.upsert_places(ELEMENTS)
    results = services.nearby(41.0, 29.0, radius_km=2)
    assert [p.name for p in results] == ["Eczane A", "Hastane B"]
    assert results[0].distance_km == pytest.approx(0, abs=1e-6)
    assert services.nearby(41.0, 29.0, radius_km=0.5)[0].name == "Eczane A"
    assert len(services.nearby(41.0, 29.0, radius_km=0.5)) == 1


@pytest.mark.django_db
def test_map_page_embeds_places_and_config(client):
    services.upsert_places(ELEMENTS)
    response = client.get(reverse("places:map"))
    assert response.status_code == 200
    body = response.content.decode()
    places = json.loads(body.split('id="places-data" type="application/json">')[1].split("</script>")[0])
    assert {p["name"] for p in places} == {"Eczane A", "Hastane B"}
    assert "leaflet.js" in body
    assert 'x-data="leafletMap"' in body


@pytest.mark.django_db
def test_nearby_partial_via_htmx(client):
    services.upsert_places(ELEMENTS)
    response = client.post(reverse("places:nearby"), {"lat": "41.0", "lng": "29.0", "radius": "5"}, **HTMX)
    body = response.content.decode()
    assert response.status_code == 200
    assert "<html" not in body  # yalnızca partial
    assert "Eczane A" in body and "km" in body


@pytest.mark.django_db
def test_nearby_rejects_invalid_coordinates(client):
    response = client.post(reverse("places:nearby"), {"lat": "abc", "lng": "999"}, **HTMX)
    assert "Could not get your location" in response.content.decode()


def test_nearby_does_not_accept_location_in_url(client):
    # Konum GET parametresi olarak gelirse erişim loglarına düşer (KVKK); yalnızca POST kabul edilir.
    response = client.get(reverse("places:nearby"), {"lat": "41.0", "lng": "29.0"}, **HTMX)
    assert response.status_code == 405


@pytest.mark.django_db
def test_nearby_form_posts_and_rounds_location(client):
    body = client.get(reverse("places:map")).content.decode()
    assert 'hx-post="' + reverse("places:nearby") + '"' in body
    script = (Path(__file__).resolve().parents[1] / "static/places/map.js").read_text()
    assert "toFixed(4)" in script and "toFixed(6)" not in script


@pytest.mark.django_db
def test_sync_job_registered_and_records_run(monkeypatch):
    from apps.core import sync

    monkeypatch.setattr(services, "sync_area", lambda *args, **kwargs: 7)
    run = sync.run_job("places")
    assert run.status == SyncRun.Status.SUCCESS
    assert run.items == 7


def test_overpass_user_agent_rejection_has_hint_and_tries_next():
    transport, calls = overpass_transport([(406, {}), (200, {"elements": []})])
    client = OverpassClient(["https://a.test/api", "https://b.test/api"], "test/1.0", transport=transport)
    assert client.query("[out:json];") == []
    assert len(calls) == 2

    transport, _ = overpass_transport([(406, {}), (406, {})])
    client = OverpassClient(
        ["https://a.test/api"], "test/1.0", transport=transport, rounds=2, sleep=lambda s: None
    )
    with pytest.raises(OverpassError, match="OVERPASS_USER_AGENT"):
        client.query("[out:json];")


@pytest.mark.django_db
def test_missing_tile_config_warns_staff(client, staff_user, settings):
    provider = settings.MAP_TILE_PROVIDERS[settings.MAP_TILES]
    settings.MAP_TILE_PROVIDERS = {
        **settings.MAP_TILE_PROVIDERS,
        settings.MAP_TILES: {**provider, "missing_config": "CARTO_API_KEY"},
    }
    assert "CARTO_API_KEY" not in client.get(reverse("places:map")).content.decode()
    client.force_login(staff_user)
    assert "CARTO_API_KEY" in client.get(reverse("places:map")).content.decode()
