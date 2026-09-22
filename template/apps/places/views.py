from django.conf import settings
from django.shortcuts import render
from django.templatetags.static import static
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from .models import Place
from .services import nearby

MAX_MARKERS = 1000


def _missing_tile_config() -> str:
    return settings.MAP_TILE_PROVIDERS[settings.MAP_TILES]["missing_config"]


def _map_config() -> dict:
    provider = settings.MAP_TILE_PROVIDERS[settings.MAP_TILES]
    icons = "places/vendor/leaflet/images/"
    return {
        "tiles": settings.MAP_TILES,
        "url": provider["url"],
        "attribution": provider["attribution"],
        "maxZoom": provider["max_zoom"],
        "center": list(settings.MAP_DEFAULT_CENTER),
        "zoom": settings.MAP_DEFAULT_ZOOM,
        # Hash'li statik dosya adları için ikon yolları açıkça verilir.
        "icon": {
            "iconUrl": static(icons + "marker-icon.png"),
            "iconRetinaUrl": static(icons + "marker-icon-2x.png"),
            "shadowUrl": static(icons + "marker-shadow.png"),
        },
    }


@require_GET
def map_view(request):
    places = list(Place.objects.values("id", "name", "category", "lat", "lng")[:MAX_MARKERS])
    return render(
        request,
        "places/map.html",
        {
            "places": places,
            "map_config": _map_config(),
            "missing_tile_config": _missing_tile_config(),
            "place_count": Place.objects.count(),
        },
    )


def _coordinate(value: str | None, low: float, high: float) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if low <= number <= high else None


@require_GET
def nearby_view(request):
    lat = _coordinate(request.GET.get("lat"), -90, 90)
    lng = _coordinate(request.GET.get("lng"), -180, 180)
    radius = _coordinate(request.GET.get("radius"), 0.1, 50) or 2.0
    context = {"results": None, "radius": radius, "error": None}
    if lat is None or lng is None:
        context["error"] = _("Could not get your location. Make sure your browser allows location access.")
    else:
        context["results"] = nearby(lat, lng, radius_km=radius)
    template = "places/map.html#nearby" if request.htmx else "places/map.html"
    if not request.htmx:
        context.update(
            places=list(Place.objects.values("id", "name", "category", "lat", "lng")[:MAX_MARKERS]),
            map_config=_map_config(),
            missing_tile_config=_missing_tile_config(),
            place_count=Place.objects.count(),
        )
    return render(request, template, context)
