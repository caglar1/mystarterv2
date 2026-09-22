# Değişiklik günlüğü

## 2.0.0 — 2026-09-22

v1'in (`starterpack`, cookiecutter) yerine sıfırdan yazıldı.

- Copier şablonu. Özel Jinja ayraçları sayesinde Django şablonlarında `{% raw %}` gerekmiyor. Modüller
  `_exclude` ile koşullu, `copier update` destekleniyor.
- Django 6.1, Python 3.13, uv.
- Tailwind CSS 4.3.3 standalone CLI (sha256 doğrulamalı) ve DaisyUI 5.7 plugin. İkonlar sunucu tarafı Lucide ile.
- htmx 2.0.10 ve Alpine 3.17 CSP build. Vendor dosyalarının sürümü ve sha256'sı `vendor.json` içinde kilitli.
- Güvenlik: güvenli varsayılanlar, nonce'lu CSP, rate limit, spam korumalı formlar, `check --deploy` testi.
- Arka plan görevleri için `django.tasks` + `django-tasks-db`, e-posta için Django 6.1 `MAILERS`.
- Modüller: harita (Overpass), LLM gateway (saf httpx), haberler (RSS + AI + Postgres FTS), kanban.
- Docker: çok aşamalı imaj, compose (web/worker/Postgres 18/Caddy), cron örnekleri.
- CI: üretilen proje için GitHub Actions ve şablon için kombinasyon matrisi.
- `AGENTS.md` tek kaynak olarak eklendi (`CLAUDE.md` onu içe aktarır).

Bilinen kısıtlar:
- Arayüz metinleri Türkçe; i18n (çoklu dil) altyapısı yok.
- `SECURE_HSTS_PRELOAD` varsayılanı `False`; bu yüzden `check --deploy` yalnızca `security.W021` uyarısını verir.
  Preload bilinçli olarak açılmalı.
