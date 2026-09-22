from django.conf import settings
from django.utils.translation import gettext, gettext_noop

# Varsayılan proje açıklaması makemessages tarafından bulunsun diye burada işaretlenir
# (asıl değer settings.SITE_DESCRIPTION'dan gelir; farklıysa ve çevirisi yoksa olduğu gibi gösterilir).
gettext_noop("A fast, lightweight business app built with Django, htmx and Alpine.js.")


def site(request):
    # `project` adı bilinçli: Django'nun auth view'ları context'e kendi `site` ve `site_name`
    # değişkenlerini (alan adı) koyar ve bunlar context processor'ları ezer.
    return {
        "project": {"name": settings.SITE_NAME, "description": gettext(settings.SITE_DESCRIPTION)},
        "features": settings.FEATURES,
        "debug": settings.DEBUG,
    }
