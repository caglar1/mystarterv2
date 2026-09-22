from django import template
from django.conf import settings
from django.urls import translate_url

register = template.Library()


@register.simple_tag(takes_context=True)
def language_alternates(context) -> list[tuple[str, str]]:
    """Geçerli sayfanın her dildeki mutlak adresi: [(dil, url), ...] (hreflang için)."""
    request = context.get("request")
    if request is None or len(settings.LANGUAGES) < 2:
        return []
    url = request.build_absolute_uri(request.path)
    return [(code, translate_url(url, code)) for code, _name in settings.LANGUAGES]


@register.simple_tag(takes_context=True)
def nav_active(context, *url_names: str) -> str:
    """Geçerli sayfa verilen URL adlarından biriyse 'menu-active' döner (navbar vurgusu)."""
    match = getattr(context.get("request"), "resolver_match", None)
    if match and match.view_name in url_names:
        return "menu-active"
    return ""


@register.inclusion_tag("core/components/sync_card.html", takes_context=True)
def sync_card(context, job: str):
    """Yöneticiler için "Şimdi senkronize et" kartı + son çalışmanın durumu."""
    from apps.core.models import SyncRun
    from apps.core.sync import JOBS

    user = context.get("user")
    last_run = SyncRun.objects.filter(job=job).first() if user and user.is_staff else None
    return {
        "user": user,
        "job": job,
        "label": JOBS[job].label if job in JOBS else job,
        "last_run": last_run,
    }
