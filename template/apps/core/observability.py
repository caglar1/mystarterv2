"""Hata izleme (Sentry) kurulumu.

Ayarlardan çağrılır; DSN yoksa hiçbir şey başlatılmaz ve dışarıya veri gitmez.
Varsayılanlar KVKK tarafında temkinlidir: kullanıcı bilgisi ve istek gövdesi gönderilmez.
"""

from __future__ import annotations


def configure_sentry(
    dsn: str,
    *,
    environment: str = "",
    release: str = "",
    traces_sample_rate: float = 0.0,
) -> bool:
    """Sentry'yi başlatır. DSN boşsa ya da paket kurulu değilse sessizce atlar."""
    if not dsn:
        return False
    try:
        import sentry_sdk
    except ImportError:  # pragma: no cover - paket yalnızca use_sentry seçilince kurulur
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=environment or None,
        release=release or None,
        # Kişisel veri gönderme: kullanıcı kimliği/IP ve istek gövdesi (form alanları) hariç tutulur.
        send_default_pii=False,
        max_request_body_size="never",
        # Performans izleme varsayılan kapalı; açmak ücretli kotayı hızla tüketir.
        traces_sample_rate=traces_sample_rate,
    )
    return True
