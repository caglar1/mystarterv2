"""Basit, bağımlılıksız rate limit dekoratörü (Django cache üzerinde sabit pencere).

Settings'teki DatabaseCache sayesinde sayaçlar tüm gunicorn worker'ları arasında paylaşılır.

    @ratelimit("teklif", rate="5/10m")
    def submit(request): ...
"""

import functools
import re
import time

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render

_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_RATE_RE = re.compile(r"^(\d+)/(\d*)([smhd])$")


def parse_rate(rate: str) -> tuple[int, int]:
    """'5/10m' -> (5, 600)."""
    match = _RATE_RE.match(rate)
    if not match:
        raise ValueError(f"Geçersiz rate: {rate!r} (ör. '5/m', '20/h', '5/10m')")
    count, multiplier, unit = match.groups()
    return int(count), int(multiplier or 1) * _UNITS[unit]


def client_ip(request) -> str:
    if settings.TRUST_X_FORWARDED_FOR:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def is_limited(scope: str, ident: str, rate: str) -> bool:
    """Bu istek limiti aşıyor mu? Her çağrı sayacı bir artırır."""
    limit, period = parse_rate(rate)
    window = int(time.time() // period)
    key = f"rl:{scope}:{ident}:{window}"
    cache.add(key, 0, timeout=period)
    try:
        count = cache.incr(key)
    except ValueError:  # anahtar tam o anda süresi dolup silindiyse
        cache.set(key, 1, timeout=period)
        count = 1
    return count > limit


def ratelimit(scope: str, rate: str, methods: tuple[str, ...] = ("POST",), per_user: bool = False):
    """Limit aşılırsa 429 döner. HTMX isteklerinde yanıt toast alanına yönlendirilir."""

    def decorator(view):
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method in methods:
                if per_user and request.user.is_authenticated:
                    ident = f"u{request.user.pk}"
                else:
                    ident = client_ip(request)
                if is_limited(scope, ident, rate):
                    return ratelimited_response(request)
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def ratelimited_response(request):
    if getattr(request, "htmx", False):
        response = render(request, "core/partials/ratelimited_toast.html", status=429)
        response["HX-Retarget"] = "#toasts"
        response["HX-Reswap"] = "beforeend"
        return response
    return render(request, "429.html", status=429)
