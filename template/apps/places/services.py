from django.conf import settings

from .geo import bounding_box, haversine_km
from .models import Place
from .overpass import OverpassClient, around_query

UPDATE_FIELDS = ["name", "category", "lat", "lng", "address", "phone", "website", "opening_hours", "tags"]


def element_to_place(element: dict) -> Place | None:
    tags = element.get("tags", {})
    name = tags.get("name")
    lat = element.get("lat", element.get("center", {}).get("lat"))
    lng = element.get("lon", element.get("center", {}).get("lon"))
    if not name or lat is None or lng is None:
        return None
    address = " ".join(
        part
        for part in (tags.get("addr:street"), tags.get("addr:housenumber"), tags.get("addr:city"))
        if part
    )
    return Place(
        osm_id=f"{element['type']}/{element['id']}",
        name=name[:255],
        category=(tags.get("amenity") or tags.get("healthcare") or tags.get("shop") or "diğer")[:60],
        lat=float(lat),
        lng=float(lng),
        address=address[:255],
        phone=(tags.get("phone") or tags.get("contact:phone") or "")[:60],
        website=(tags.get("website") or tags.get("contact:website") or "")[:500],
        opening_hours=tags.get("opening_hours", "")[:255],
        tags=tags,
    )


def upsert_places(elements: list[dict]) -> int:
    places = {place.osm_id: place for e in elements if (place := element_to_place(e))}
    if not places:
        return 0
    Place.objects.bulk_create(
        places.values(), update_conflicts=True, unique_fields=["osm_id"], update_fields=UPDATE_FIELDS
    )
    return len(places)


def sync_area(lat: float, lng: float, radius_km: float, filters: list[str], client=None) -> int:
    client = client or OverpassClient(settings.OVERPASS_ENDPOINTS, settings.OVERPASS_USER_AGENT)
    elements = client.query(around_query(lat, lng, int(radius_km * 1000), filters))
    return upsert_places(elements)


def sync_default_area() -> tuple[int, str]:
    """Senkronizasyon işi (bkz. apps.core.sync): settings'teki merkez ve filtrelerle çalışır."""
    lat, lng = settings.MAP_DEFAULT_CENTER
    count = sync_area(lat, lng, settings.PLACES_SYNC_RADIUS_KM, settings.PLACES_SYNC_FILTERS)
    return count, f"{lat:.4f},{lng:.4f} çevresinde {settings.PLACES_SYNC_RADIUS_KM:g} km"


def nearby(lat: float, lng: float, radius_km: float = 5, limit: int = 20) -> list[Place]:
    """Yakındaki yerler, mesafeye göre sıralı. Her kayda `distance_km` eklenir."""
    min_lat, max_lat, min_lng, max_lng = bounding_box(lat, lng, radius_km)
    candidates = Place.objects.filter(lat__range=(min_lat, max_lat), lng__range=(min_lng, max_lng))
    results = []
    for place in candidates:
        place.distance_km = haversine_km(lat, lng, place.lat, place.lng)
        if place.distance_km <= radius_km:
            results.append(place)
    results.sort(key=lambda p: p.distance_km)
    return results[:limit]
