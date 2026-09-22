from django.conf import settings


def site(request):
    """Tüm şablonlara site bilgisi ve kurulu modüller (features) geçer."""
    # `project` adı bilinçli: Django'nun auth view'ları context'e kendi `site` ve `site_name`
    # değişkenlerini (alan adı) koyar ve bunlar context processor'ları ezer.
    return {
        "project": {"name": settings.SITE_NAME, "description": settings.SITE_DESCRIPTION},
        "features": settings.FEATURES,
        "debug": settings.DEBUG,
    }
