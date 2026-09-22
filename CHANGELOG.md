# Değişiklik günlüğü

## 2.1.0 — 2026-09-22

Çok dillilik.

- Yeni Copier sorusu `languages` (varsayılan `en,tr`). İlk dil kökte, diğerleri `/<dil>/` önekli (`i18n_patterns`).
  URL yolları da çevriliyor.
- Kaynak metinler İngilizce (gettext standardı). Türkçe çevirinin tamamı hazır (`apps/*/locale`, `locale/`),
  derlenmiş `.mo` dosyaları repoda.
- Dil seçici, `hreflang` + `x-default`, çok dilli sitemap, RTL desteği (`dir`).
- E-postalar formun dilinde (`Inquiry.language`); AI özetleri sayfanın dilinde, haber özetleri
  `NEWS_SUMMARY_LANGUAGE` ile belirlenen dilde.
- Senkronizasyon uçları ayrı `sync` namespace'ine taşındı (i18n_patterns içinde, yanıtlar sayfanın dilinde).
- Haber kategori kodları İngilizce oldu (`technology`, `world`...); eski Türkçe kodlar migration ile dönüştürülüyor.
- Kanban durumları bağlamlı çeviriyle (`pgettext`).
- `make messages` / `scripts/messages.py`; eksik çeviriyi yakalayan test; matriste dil kombinasyonları ve
  gerçek ayarlarla smoke adımı.
- Her uygulamada `0002_i18n` migration'ı var: alan etiketleri çevrilebilir oldu, talepte `language` alanı eklendi.
- Test matrisi son etiketi değil çalışma ağacını test ediyor (`--vcs-ref HEAD`).
- `AGENTS.md`: çeviri kuralları, widget-tweaks/django-honeypot'un neden kullanılmadığı.

2.0.0'dan yükseltme (`uvx copier update --trust`):
- Yeni `languages` sorusuna **`tr,en`** cevabını verin. Varsayılan `en,tr` kökü İngilizce yapar; Türkçe sayfalar
  `/tr/` altına taşınır ve mevcut adresler değişir.
- Ardından `uv sync` ve `manage.py migrate` çalıştırın. Haber kategorileri migration ile dönüştürülür,
  veri kaybı olmaz.
- 2.0.0'daki `project_description` Türkçe olduğu için İngilizce sayfalarda da Türkçe görünür. İsterseniz
  `.env`'e `SITE_DESCRIPTION` olarak İngilizce bir metin yazın ve Türkçesini `locale/tr/LC_MESSAGES/django.po`'ya ekleyin.

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
- Arayüz metinleri yalnızca Türkçe (2.1.0'da giderildi).
- `SECURE_HSTS_PRELOAD` varsayılanı `False`; bu yüzden `check --deploy` yalnızca `security.W021` uyarısını verir.
  Preload bilinçli olarak açılmalı.
