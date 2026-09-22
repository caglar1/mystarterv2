from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection
from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET, require_POST

from . import sync
from .models import SyncRun
from .ratelimit import ratelimit


@require_GET
def healthz(request):
    """Docker/yük dengeleyici sağlık kontrolü: veritabanına erişilebiliyor mu?"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "error", "database": False}, status=503)
    return JsonResponse({"status": "ok"})


@require_GET
@cache_control(max_age=86400, public=True)
def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse("core:sitemap"))
    lines = ["User-agent: *", f"Disallow: /{settings.ADMIN_URL}", "Disallow: /hesap/", ""]
    lines.append(f"Sitemap: {sitemap_url}")
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")


@require_GET
def favicon(request):
    """Tarayıcıların kendiliğinden istediği /favicon.ico -> SVG ikon (404 gürültüsünü önler)."""
    return HttpResponsePermanentRedirect(static("core/icons/favicon.svg"))


@require_GET
@cache_control(max_age=86400, public=True)
def web_manifest(request):
    """PWA manifest'i (ikon yolları hash'li statik dosyalara işaret etsin diye view olarak üretilir)."""
    manifest = {
        "name": settings.SITE_NAME,
        "short_name": settings.SITE_NAME[:12],
        "description": settings.SITE_DESCRIPTION,
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#1e40af",
        "lang": settings.LANGUAGE_CODE,
        "icons": [
            {"src": static("core/icons/icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static("core/icons/icon-512.png"), "sizes": "512x512", "type": "image/png"},
            {
                "src": static("core/icons/icon-maskable-512.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
    }
    response = JsonResponse(manifest, json_dumps_params={"ensure_ascii": False})
    response["Content-Type"] = "application/manifest+json"
    return response


@staff_member_required
@require_POST
@ratelimit("sync", rate="6/m", per_user=True)
def sync_trigger(request, job: str):
    if job not in sync.JOBS:
        raise Http404
    run = sync.enqueue_job(job, request.user)
    return render(request, "core/components/sync_badge.html", {"run": run})


@staff_member_required
@require_GET
def sync_status(request, pk: int):
    run = get_object_or_404(SyncRun, pk=pk)
    response = render(request, "core/components/sync_badge.html", {"run": run})
    if run.is_finished:
        # 286: htmx'e periyodik sorgulamayı durdurmasını söyler.
        response.status_code = 286
    return response
