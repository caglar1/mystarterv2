from django.conf import settings


def site(request):
    """Tüm şablonlara site bilgisi ve kurulu modüller (features) geçer."""
    return {
        "site_name": settings.SITE_NAME,
        "site_description": settings.SITE_DESCRIPTION,
        "features": settings.FEATURES,
        "debug": settings.DEBUG,
    }
