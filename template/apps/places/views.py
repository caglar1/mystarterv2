from django.conf import settings
from django.shortcuts import render
from django.templatetags.static import static
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

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


@require_POST
def nearby_view(request):
    # POST: kullanıcının konumu adres satırına ve erişim loglarına düşmesin (KVKK). Sunucuda da ~11 m'ye
    # yuvarlanır; yakındaki yerleri bulmak için daha hassası gerekmez.
    lat = _coordinate(request.POST.get("lat"), -90, 90)
    lng = _coordinate(request.POST.get("lng"), -180, 180)
    radius = _coordinate(request.POST.get("radius"), 0.1, 50) or 2.0
    context = {"results": None, "radius": radius, "error": None}
    if lat is None or lng is None:
        context["error"] = _("Could not get your location. Make sure your browser allows location access.")
    else:
        context["results"] = nearby(round(lat, 4), round(lng, 4), radius_km=radius)
    template = "places/map.html#nearby" if request.htmx else "places/map.html"
    if not request.htmx:
        context.update(
            places=list(Place.objects.values("id", "name", "category", "lat", "lng")[:MAX_MARKERS]),
            map_config=_map_config(),
            missing_tile_config=_missing_tile_config(),
            place_count=Place.objects.count(),
        )
    return render(request, template, context)
