"""Saf Python coğrafi hesaplar (GDAL/PostGIS gerektirmez).

Küçük/orta veri için yeterlidir: önce indeksli bounding box ile SQL'de daraltılır,
ardından kalan birkaç yüz kayıt için haversine mesafesi Python'da hesaplanır.
"""

import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def bounding_box(lat: float, lng: float, radius_km: float) -> tuple[float, float, float, float]:
    """(min_lat, max_lat, min_lng, max_lng) — kutuplara yakın bölgelerde boylam aralığı genişler."""
    lat_delta = math.degrees(radius_km / EARTH_RADIUS_KM)
    cos_lat = max(math.cos(math.radians(lat)), 1e-6)
    lng_delta = math.degrees(radius_km / (EARTH_RADIUS_KM * cos_lat))
    return lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta
