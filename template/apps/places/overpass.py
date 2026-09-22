"""Dayanıklı Overpass API istemcisi: birden fazla sunucu, geri çekilmeli tekrar deneme, açık hatalar.

Kullanım kuralları (https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances):
iletişim bilgisi içeren User-Agent gönderin, sorguları seyrek ve dar tutun, sonuçları veritabanında saklayın.
"""

import logging
import time
from collections.abc import Callable

import httpx

logger = logging.getLogger(__name__)

# 400: sorgu hatası -> diğer sunucular da aynı cevabı verir, hemen dur.
FAIL_FAST_STATUS = {400}
HINTS = {
    403: "erişim reddedildi",
    406: "User-Agent reddedildi; OVERPASS_USER_AGENT içinde gerçek bir iletişim adresi olmalı",
    429: "istek limiti aşıldı",
}


class OverpassError(RuntimeError):
    pass


def around_query(lat: float, lng: float, radius_m: int, filters: list[str], timeout_s: int = 60) -> str:
    """`nwr[filter](around:...)` sorgusu; yollar/alanlar için merkez koordinatı döner."""
    parts = "\n".join(f"  nwr[{flt}](around:{radius_m},{lat},{lng});" for flt in filters)
    return f"[out:json][timeout:{timeout_s}];\n(\n{parts}\n);\nout center tags;"


class OverpassClient:
    def __init__(
        self,
        endpoints: list[str],
        user_agent: str,
        *,
        timeout: float = 90.0,
        rounds: int = 2,
        backoff: float = 5.0,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if not endpoints:
            raise OverpassError("En az bir Overpass sunucusu tanımlanmalı (OVERPASS_ENDPOINTS).")
        self.endpoints = endpoints
        self.rounds = rounds
        self.backoff = backoff
        self.sleep = sleep
        self.http = httpx.Client(
            timeout=timeout,
            transport=transport,
            headers={"User-Agent": user_agent, "Accept": "application/json"},
        )

    def query(self, ql: str) -> list[dict]:
        failures: list[str] = []
        for round_index in range(self.rounds):
            if round_index:
                self.sleep(self.backoff * round_index)
            for endpoint in self.endpoints:
                try:
                    response = self.http.post(endpoint, data={"data": ql})
                except httpx.HTTPError as exc:
                    failures.append(f"{endpoint}: {type(exc).__name__}")
                    continue
                if response.status_code == 200:
                    return response.json().get("elements", [])
                hint = HINTS.get(response.status_code)
                failures.append(f"{endpoint}: HTTP {response.status_code}" + (f" ({hint})" if hint else ""))
                if response.status_code in FAIL_FAST_STATUS:
                    raise OverpassError(f"Overpass sorgusu reddedildi: {' | '.join(failures)}")
        raise OverpassError(f"Tüm Overpass sunucuları başarısız: {' | '.join(failures)}")
