import httpx
import pytest
from django.db import connection
from django.urls import reverse

from apps.ai import llm
from apps.core import sync
from apps.core.models import SyncRun
from apps.news import pipeline
from apps.news.models import Article, Feed
from conftest import HTMX

FEED_URL = "https://haber.test/rss.xml"

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
<item><title>Birinci &lt;b&gt;haber&lt;/b&gt;</title><link>https://haber.test/1</link>
  <description>&lt;p&gt;RSS \xc3\xb6zeti bir&lt;/p&gt;</description>
  <pubDate>Mon, 21 Sep 2026 10:00:00 +0300</pubDate></item>
<item><title>Engelli haber</title><link>https://haber.test/gizli/2</link>
  <description>RSS \xc3\xb6zeti iki</description></item>
<item><title></title><link>https://haber.test/3</link></item>
</channel></rss>"""

PARAGRAPH = (
    "Belediye bu hafta şehir merkezinde yeni bir bisiklet yolu ağını hizmete açtı "
    "ve vatandaşlar ilgi gösterdi. "
)
ARTICLE_HTML = (
    "<html><head><title>Birinci haber</title></head><body><article><h1>Birinci haber</h1>"
    + "".join(f"<p>{PARAGRAPH * 3}</p>" for _ in range(5))
    + "</article></body></html>"
)
ROBOTS = "User-agent: *\nDisallow: /gizli/\n"


def transport(overrides=None, calls=None):
    routes = {
        FEED_URL: (200, RSS, "application/rss+xml", {"etag": '"v1"'}),
        "https://haber.test/robots.txt": (200, ROBOTS.encode(), "text/plain", {}),
        "https://haber.test/1": (200, ARTICLE_HTML.encode(), "text/html; charset=utf-8", {}),
    }
    routes.update(overrides or {})

    def handler(request):
        if calls is not None:
            calls.append(str(request.url))
        if str(request.url) == FEED_URL and request.headers.get("if-none-match") == '"v1"':
            return httpx.Response(304)
        status, body, content_type, headers = routes.get(str(request.url), (404, b"", "text/plain", {}))
        if isinstance(status, Exception):
            raise status
        return httpx.Response(status, content=body, headers={"content-type": content_type, **headers})

    return httpx.MockTransport(handler)


class FakeLLM:
    configured = True

    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, 0

    def generate_json(self, prompt, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result or {
            "tldr": ["Yeni bisiklet yolu açıldı", "Vatandaşlar ilgi gösterdi"],
            "category": "world",
            "sentiment": "positive",
            "importance": 7,
            "tags": ["ulaşım", "belediye"],
        }


def run_sync(fake_llm=None, overrides=None, calls=None):
    http = pipeline.http_client(transport=transport(overrides, calls))
    return pipeline.sync_all(http=http, llm_client=fake_llm)


@pytest.fixture
def feed(db):
    # Örnek HTML Türkçe: metin çıkarma dile göre yapılır (varsayılan dil projeye göre değişir).
    return Feed.objects.create(name="Test Haber", url=FEED_URL, category="other", language="tr")


@pytest.mark.django_db
def test_feed_language_defaults_to_project_language(settings):
    assert Feed(name="x", url="https://x.test/rss").language == settings.LANGUAGE_CODE.split("-")[0]


def test_parse_entries_strips_html_and_parses_dates():
    entries = pipeline.parse_entries(RSS)
    assert [e["url"] for e in entries] == ["https://haber.test/1", "https://haber.test/gizli/2"]
    first = entries[0]
    assert first["title"] == "Birinci haber"
    assert first["summary"] == "RSS özeti bir"
    assert first["published_at"].isoformat() == "2026-09-21T07:00:00+00:00"


def test_full_pipeline_extracts_enriches_and_respects_robots(feed):
    fake = FakeLLM()
    count, message = run_sync(fake)
    assert count == 2
    first = Article.objects.get(url="https://haber.test/1")
    assert "bisiklet yolu" in first.content  # newspaper4k ile çıkarıldı
    assert first.summary == ["Yeni bisiklet yolu açıldı", "Vatandaşlar ilgi gösterdi"]
    assert (first.category, first.sentiment, first.importance) == ("world", "positive", 7)
    assert first.enriched_at is not None
    assert first.excerpt == "RSS özeti bir"
    blocked = Article.objects.get(url="https://haber.test/gizli/2")
    assert blocked.content == "RSS özeti iki"  # robots.txt: makale sayfası çekilmedi
    assert "robots.txt" in message
    feed.refresh_from_db()
    assert feed.etag == '"v1"' and feed.last_synced_at


def test_second_run_is_conditional_and_skips_llm(feed):
    run_sync(FakeLLM())
    fake = FakeLLM()
    calls = []
    count, _ = run_sync(fake, calls=calls)
    assert count == 0
    assert fake.calls == 0  # tekrar ücret ödenmez
    assert calls == [FEED_URL]  # 304: yalnızca feed kontrol edildi


def test_existing_articles_are_not_reprocessed(feed):
    run_sync(FakeLLM())
    Feed.objects.filter(pk=feed.pk).update(etag="")  # feed değişmiş gibi davran
    fake = FakeLLM()
    count, message = run_sync(fake)
    assert count == 0 and fake.calls == 0
    assert "already saved: 2" in message


def test_enrichment_failure_still_saves_article(feed):
    count, message = run_sync(FakeLLM(error=llm.LLMError("kota")))
    assert count == 2
    assert Article.objects.filter(enriched_at__isnull=True).count() == 2
    assert "AI errors: 2" in message


def test_enrichment_output_is_normalized(feed):
    weird = {
        "tldr": ["a", " ", "b", "c", "d"],
        "category": "uzay",
        "sentiment": "?",
        "importance": 42,
        "tags": [],
    }
    run_sync(FakeLLM(result=weird))
    article = Article.objects.get(url="https://haber.test/1")
    assert article.summary == ["a", "b", "c"]
    assert (article.category, article.sentiment, article.importance) == ("other", "neutral", 10)


def test_without_llm_enrichment_is_skipped(feed, settings):
    settings.LLM_API_KEY = ""
    count, message = run_sync(None)
    assert count == 2
    assert "AI summaries skipped" in message


def test_robots_rules():
    http = pipeline.http_client(
        transport=httpx.MockTransport(
            lambda r: (
                {
                    "https://a.test/robots.txt": httpx.Response(403),
                    "https://b.test/robots.txt": httpx.Response(404),
                }.get(str(r.url))
                or (_ for _ in ()).throw(httpx.ConnectError("yok"))
            )
        )
    )
    robots = pipeline.RobotsCache(http, "test")
    assert not robots.allowed("https://a.test/x")  # 403 -> hepsi yasak
    assert robots.allowed("https://b.test/x")  # robots.txt yok -> serbest
    assert not robots.allowed("https://c.test/x")  # okunamadı -> temkinli


def test_all_feeds_failing_marks_run_failed(feed, monkeypatch):
    failing = transport({FEED_URL: (httpx.ConnectError("yok"), b"", "", {})})

    def broken():
        return pipeline.sync_all(http=pipeline.http_client(transport=failing), llm_client=None)

    monkeypatch.setitem(sync.JOBS, "news", sync.SyncJob("news", "Haberler", broken))
    run = sync.run_job("news")
    assert run.status == SyncRun.Status.FAILED
    assert "None of the feeds could be fetched" in run.message


@pytest.mark.django_db
def test_list_page_and_htmx_search(client, feed):
    Article.objects.create(
        feed=feed, url="https://haber.test/a", title="Bisiklet yolu açıldı", content="şehir"
    )
    Article.objects.create(
        feed=feed, url="https://haber.test/b", title="Borsa güne yükselişle başladı", content=""
    )
    page = client.get(reverse("news:list"))
    assert page.status_code == 200
    assert "Read at source" in page.content.decode()

    results = client.get(reverse("news:list"), {"q": "bisiklet"}, **HTMX).content.decode()
    assert "<html" not in results
    assert "Bisiklet yolu açıldı" in results and "Borsa" not in results


@pytest.mark.django_db
def test_load_more_returns_only_items(client, feed):
    for i in range(15):
        Article.objects.create(feed=feed, url=f"https://haber.test/{i}", title=f"Haber {i}")
    first = client.get(reverse("news:list")).content.decode()
    assert 'id="load-more"' in first
    more = client.get(reverse("news:list"), {"page": 2}, **HTMX).content.decode()
    assert more.count("<article") == 3
    assert 'id="results"' not in more and 'id="load-more"' not in more


@pytest.mark.django_db
def test_remote_images_hidden_by_default(client, feed):
    Article.objects.create(
        feed=feed, url="https://haber.test/i", title="Görselli", image_url="https://cdn.test/a.jpg"
    )
    assert "cdn.test" not in client.get(reverse("news:list")).content.decode()


# Kök bulma dili projeye göre değişir (settings.SEARCH_CONFIG): (başlık, aranan kelime)
SEARCH_SAMPLES = {
    "turkish": ("Kitaplar ve kütüphaneler", "kitap"),
    "english": ("Books and libraries", "book"),
}


@pytest.mark.django_db
@pytest.mark.skipif(connection.vendor != "postgresql", reason="Yalnızca PostgreSQL")
def test_postgres_search_uses_gin_index(feed, settings):
    from apps.core.search import hybrid_search

    # Bilinmeyen dillerde 'simple' kullanılır: kök bulma yok, kelimenin tamamı aranır.
    title, term = SEARCH_SAMPLES.get(settings.SEARCH_CONFIG, ("Kitaplar ve kütüphaneler", "kitaplar"))
    Article.objects.create(feed=feed, url="https://haber.test/p1", title=title, content="")
    Article.objects.create(feed=feed, url="https://haber.test/p2", title="Futbol", content="maç sonucu")
    results = hybrid_search(Article.objects.all(), term, fields=["title", "content"])
    assert [a.title for a in results] == [title]  # kök bulma çalışıyor
    with connection.cursor() as cursor:
        cursor.execute("SET enable_seqscan = off")
        plan = results.explain()
        cursor.execute("SET enable_seqscan = on")
    assert "news_article_fts_idx" in plan
