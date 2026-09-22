# Starterpack v2

Django 6.1 + htmx 2 + Alpine.js (CSP build) + Tailwind CSS 4 / DaisyUI 5 ile hafif, güvenli ve yapay zeka
ajanlarıyla çalışmaya hazır iş uygulamaları için **Copier** şablonu. Node.js, Redis ve Celery gerekmez.

```bash
uvx copier copy --trust ~/Desktop/starterpackv2 benim-projem   # repo GitHub'a konunca: gh:<kullanıcı>/starterpackv2
cd benim-projem
make setup   # uv sync, .env (rastgele SECRET_KEY), Tailwind CLI, migrate, demo veri
make dev     # runserver + tailwind --watch + görev worker'ı
```

Tek ön koşul [uv](https://docs.astral.sh/uv/) (`brew install uv`); Python 3.13'ü de uv kurar.

## Sorular

| Soru | Varsayılan | Açıklama |
|---|---|---|
| `project_name` / `project_slug` | Benim Uygulamam | Slug Türkçe karakterlerden arındırılır |
| `author_email` | dev@example.com | Bildirimler ve dış API'lere giden User-Agent. **Gerçek adres verin**: OSM sunucuları `example.com`'u reddeder |
| `domain` | example.com | ALLOWED_HOSTS, Caddyfile |
| `languages` | en,tr | Arayüz dilleri; ilk dil kökte (`/about/`), diğerleri önekli (`/tr/hakkimizda/`). Türkçe çeviri hazır |
| `database` | postgres | `postgres` veya `sqlite` (WAL + IMMEDIATE, tek sunucu için) |
| `use_maps` + `map_tiles` | evet, stadia | Leaflet + Overpass senkronizasyonu + yakınımdakiler |
| `use_llm` + `llm_provider` | evet, anthropic | Saf httpx LLM gateway + SSE streaming demo |
| `use_news` | hayır | RSS → makale → AI özet → Postgres tam metin araması (LLM gerekir) |
| `use_kanban` | evet | SortableJS + htmx, sıralama veritabanına kaydedilir |
| `use_ui_kit` | evet | `/dev/ui-kit/` bileşen vitrini (yalnızca DEBUG) |

Üretilen projeye sonradan gelen şablon düzeltmeleri: `uvx copier update --trust`.

## Neler var

**Her projede:** özel User modeli ve giriş/şifre sıfırlama · KVKK onaylı teklif formu (honeypot + zaman
damgası + rate limit, e-postalar arka plan görevinde) · htmx yanıtlarında otomatik toast · açık/koyu tema ·
PWA manifest ve ikonlar · OG/Twitter meta · sitemap/robots · `/healthz` · sıkı CSP (nonce) · `check --deploy`
uyarısız · Docker (çok aşamalı, root olmayan kullanıcı) + compose (web / worker / db / Caddy) · GitHub Actions CI ·
tek kaynak `AGENTS.md` (+ `CLAUDE.md`).

**Modüller:** her biri gerçek, test edilmiş kod; kapatılınca klasörü, URL'leri, navbar linkleri ve
bağımlılıkları birlikte gider (`settings.FEATURES`).

| Modül | İçerik |
|---|---|
| Harita | Overpass istemcisi (çoklu sunucu, geri çekilmeli tekrar deneme, açıklayıcı hatalar), bulk upsert, saf Python haversine, HTMX "yakınımdakiler", Leaflet'i Alpine ile yöneten bileşen |
| LLM | Anthropic (adaptive thinking + `effort`, refusal, sunucu tarafı fallback, structured output) ve OpenAI uyumlu sağlayıcılar; 429/5xx tekrar deneme; SSE ile akan özet sayfası |
| Haberler | Koşullu feed çekme (ETag), robots.txt'e uyum, newspaper4k ile metin çıkarma, JSON şemalı AI zenginleştirme, Postgres fonksiyonel GIN index + Türkçe kök bulma, HTMX anlık arama |
| Kanban | Kullanıcıya göre izole panolar, transaction içinde sıralama, OOB sayaç güncellemesi |

## Çok dillilik

- **Kaynak dil İngilizce.** Bu Django/gettext standardı: çeviri araçları ve yapay zeka ajanları en iyi bununla
  çalışır. Türkçe çevirinin tamamı hazır geliyor (yaklaşık 340 metin, `.po` + derlenmiş `.mo`).
- **Adresler:** ilk dil kökte, diğerleri önekli; yol parçaları da çevriliyor
  (`/about/` ↔ `/tr/hakkimizda/`, `/quote/send/` ↔ `/tr/teklif/gonder/`). `hreflang` etiketleri ve
  çok dilli sitemap SEO için hazır. Dil seçici Django'nun `set_language` view'ını kullanıyor; geçerli sayfanın
  karşılığına yönlendiriyor.
- **Dilin doğru olması gereken yerler:**
  - Teklif formu hangi dilde doldurulduysa müşteriye e-posta o dilde gidiyor, ekibe ise varsayılan dilde.
  - AI özeti sayfanın dilinde üretiliyor.
  - HTMX uçları önekli olduğu için yanıtlar da sayfanın dilinde dönüyor.
- **Her uygulamanın kendi `locale/` klasörü var.** Bir modül kapatıldığında çevirileri de onunla gidiyor.
- `test_translations_are_complete` eksik ya da "fuzzy" çeviri kaldığında testi kırıyor.
  Yeni metin eklendiğinde `make messages` çalıştırılıyor (GNU gettext gerekir).
- **Yeni dil eklemek:** `LANGUAGES=en,tr,de` ve ardından `uv run python scripts/messages.py de`.
  Sağdan sola yazılan diller için `dir="rtl"` otomatik ekleniyor.

## Ölçümler

Brotli ile sıkıştırılmış CSS + JS (HTML hariç):

| Sayfa | Boyut |
|---|---|
| Ana sayfa | **51 KB** (CSS 15 · htmx 14,6 · Alpine 20,8 · app.js 0,5) |
| Harita | 91 KB (+ Leaflet yalnızca bu sayfada) |
| Kanban | 65 KB (+ Sortable yalnızca bu sayfada) |
| AI özet | 52 KB |

v1'de her sayfa yaklaşık 386 KB (gzip) yüklüyordu: DaisyUI'nin tamamı 198 KB, Lucide 100 KB, Leaflet ve Sortable her sayfada.

Docker imajı: yaklaşık 430 MB (tüm modüller açık; payın çoğu newspaper4k'nın lxml/Pillow bağımlılıkları).

## Doğrulama

- `scripts/test_matrix.py`: 9 seçenek kombinasyonunu üretir; `tr,en` (Türkçe kökte) ve tek dil de bunlara dahil.
  Her birinde vendor sha256, ruff, `makemigrations --check`, pytest ve Tailwind derlemesi çalışır.
  Ardından projenin gerçek ayarlarıyla her dilde sayfa açılır. Postgres kombinasyonları gerçek Postgres 18'e karşı test edilir.
- Tüm modüller açık projede 112 test (Postgres'te; index kullanımı `EXPLAIN` ile doğrulanır).
- `docker compose up` ile doğrulananlar: healthz, migration'lar, worker, brotli + `immutable` önbellekli statik dosyalar.

```bash
docker run -d --name testdb -e POSTGRES_PASSWORD=test -p 5432:5432 postgres:18-alpine
TEST_DATABASE_URL=postgres://postgres:test@localhost:5432/postgres \
  uv run --no-project --with copier python scripts/test_matrix.py --css
```

## v1'deki sorunlar ve v2'deki karşılıkları

| v1 | v2 |
|---|---|
| Django 5.1 (desteği bitti) | Django 6.1 (6.2 LTS çıkınca yükseltme) |
| `STATICFILES_STORAGE` Django 5.1'de kaldırılmış bir ayar, WhiteNoise fiilen kapalı | `STORAGES` + gerçek `collectstatic` testi |
| Dev'de Tailwind v3 Play CDN, prod'da `latest` v4; DaisyUI 4'ün tamamı (2,9 MB) | Her ortamda aynı sabit CLI (sha256), DaisyUI 5 plugin |
| Lucide 424 KB JS | Sunucu tarafı SVG, 0 KB JS |
| Mesajlar HTMX yanıtında çıkmıyor, sonraki sayfaya kayıyordu | OOB toast middleware'i |
| `DEBUG=True`, `ALLOWED_HOSTS=*` | Güvenli varsayılanlar, CSP, HSTS, `check --deploy` testi |
| Senkron worker'da LLM/sync çağrıları | `django.tasks` + db_worker, SSE için gthread |
| Sahte sync / zenginleştirme / kanban kaydı | Gerçek implementasyon + mock'lu testler |
| Seçenek kapatınca sayfalar 500 veriyordu | `FEATURES` + test matrisi |
| Compose Postgres'i açıp SQLite kullanıyordu | Veritabanı seçimi compose/.env/CI'ı belirler; Postgres 18 volume yolu doğru |
| Anthropic: `budget_tokens` + `temperature` (400), `content[0]` | adaptive thinking + effort, text blokları, refusal |
| Üç ayrı ve birbirinden kopmuş AI dokümanı | Tek `AGENTS.md`; kalıplar gerçek dosyalarda (`docs/recipes.md`) |

## Harita katmanları (Eylül 2026 itibarıyla)

- **Stadia:** localhost'ta anahtarsız. Canlıda alan adını panelden yetkilendirin; ticari kullanım ücretli plan ister.
  Sayfanın `Referrer-Policy: same-origin` ayarı yüzünden karo isteklerine yalnızca origin gönderilir.
- **CARTO:** artık **API anahtarı gerekiyor** (ücretsiz, anında: carto.com/basemaps/apikey). Anahtarsız karolar filigranlı gelir.
  Ayda 5M karo, öncelik ticari olmayan kullanım.
- **PMTiles:** tek dosya (ör. Cloudflare R2, çıkış trafiği ücretsiz). Yüksek trafikte en ucuzu; `protomaps-leaflet` ile.

## Şablonu geliştirmek

```
copier.yml                 sorular, koşullu modüller, özel Jinja ayraçları ([[ ]], [% %])
template/                  üretilen proje (yalnızca *.jinja dosyaları işlenir)
scripts/test_matrix.py     kombinasyon testleri
scripts/make_icons.py      PWA ikonlarını yeniden üretir
```

- Vendor sürümü yükseltmek: ilgili `template/apps/*/vendor.json`'da sürümü ve URL'yi değiştirin, sonra
  `cd template && python3 scripts/vendor.py lock`.
- Tailwind yükseltmek: `template/apps/core/tailwind.py` (sürüm + sha256sums.txt değerleri).
- Değişiklikten sonra: `uv run --no-project --with copier python scripts/test_matrix.py`.
