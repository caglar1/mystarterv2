# Değişiklik günlüğü

## 2.1.1 — 2026-09-22

Şablonun baştan sona gözden geçirilmesinden çıkan düzeltmeler.

Hatalar:
- Canlıda yakalanmamış hatalar (500) artık `ADMINS` adreslerine e-postayla gidiyor: özel `LOGGING` ayarı
  Django'nun `mail_admins` handler'ını eziyordu. `ADMINS` de Django 6'nın istediği biçimde (e-posta listesi).
- `robots.txt` artık her dilin hesap adresini engelliyor (i18n'den sonra `/hesap/` yanlış kalmıştı) ve
  yönetim paneli adresini yazmıyor (robots.txt herkese açık, gizli adresi ele veriyordu).
- Teklif formunun onay e-postası ziyaretçinin yazdığı ad ve mesajı artık içermiyor: form, sizin alan
  adınızdan üçüncü kişilere spam göndermek için kullanılabiliyordu.
- "Yakınımdakiler" konumu GET yerine POST ile alıyor ve ~11 m'ye yuvarlıyor; konum artık erişim loglarına düşmüyor.
- Üretilen README'deki modül adresleri projenin diline göre yazılıyor (İngilizce kökte `/harita/` 404 veriyordu).
- Haberlerde çok dillilikten kalan Türkçe varsayılanlar: kaynak dili projenin diline göre,
  arama kök bulma dili `SEARCH_CONFIG` (projenin ilk dilinden; desteklenmeyen dillerde `simple`).
- "İ" ile başlayan proje adları geçerli bir klasör adı üretiyor.
- `scripts/messages.py` ve çeviri testi bölgeli dil kodlarını (`pt-br` -> `pt_BR`) doğru klasöre yazıyor.

Eklenenler:
- Kurulumda `git init` + ilk commit (`copier update` yalnızca git'teki projelerde çalışır). Copier ≥ 9.6.
- `deploy/backup.sh`: veritabanı yedeği (Postgres `pg_dump`, SQLite `sqlite3.backup`), 14 günlük saklama;
  cron örneklerine yedek ve `clearsessions` eklendi, örnekler artık yalnızca kurulu modülleri içeriyor.
- `Permissions-Policy` başlığı (kamera/mikrofon kapalı, konum yalnızca harita modülünde).
- Senkronizasyon kartı, iş 1 dakikadan uzun kuyrukta kalırsa "worker çalışıyor mu?" uyarısı veriyor.
- Şifre sıfırlama e-postası arka plan görevinde gönderiliyor; kayıt formunda e-posta zorunlu.
- Sürümler: `python:3.13-slim-trixie` (Debian 13), CI'da `actions/checkout@v7`, `astral-sh/setup-uv@v10`.
- Kullanılmayan `author_name` sorusu kaldırıldı.

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
- Haber kategori kodları İngilizce oldu (`technology`, `world`...).
- Kanban durumları bağlamlı çeviriyle (`pgettext`).
- `make messages` / `scripts/messages.py`; eksik çeviriyi yakalayan test; matriste dil kombinasyonları ve
  gerçek ayarlarla smoke adımı.
- Talepte `language` alanı. Migration'lar ilk migration'lara katıldı: 2.0.0 ile başlatılmış proje olmadığı için
  2.0.0 → 2.1.0 `copier update` yolu desteklenmiyor.
- Test matrisi son etiketi değil çalışma ağacını test ediyor (`--vcs-ref HEAD`).
- `AGENTS.md`: çeviri kuralları, widget-tweaks/django-honeypot'un neden kullanılmadığı.


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
