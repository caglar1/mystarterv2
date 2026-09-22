"""Haber pipeline'ı: RSS/Atom -> makale metni -> AI zenginleştirme -> veritabanı.

Nazik tarama kuralları:
- Her istekte iletişim bilgisi içeren User-Agent (NEWS_USER_AGENT)
- robots.txt'e uyulur; izin yoksa yalnızca RSS özeti kullanılır
- Feed'ler ETag / Last-Modified ile koşullu çekilir (değişmediyse 304, trafik yok)
- Daha önce kaydedilmiş adresler yeniden işlenmez (LLM ücreti tekrar ödenmez)
- newspaper4k yalnızca bizim indirdiğimiz HTML'i ayrıştırır, kendisi ağa çıkmaz
"""

import calendar
import logging
import warnings
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import feedparser
import httpx
from django.conf import settings
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext as _

with warnings.catch_warnings():
    # newspaper4k, opsiyonel NLP özellikleri için nltk yoksa her import'ta uyarı basar; kullanmıyoruz.
    warnings.filterwarnings("ignore", message="nltk is not installed")
    from newspaper import Article as NewspaperArticle
    from newspaper import ArticleException, Config

from apps.ai import llm
from apps.ai.prompts import language_name

from .models import Article, Category, Feed

logger = logging.getLogger(__name__)

MAX_HTML_BYTES = 3_000_000
ENRICH_INPUT_CHARS = 6000  # maliyet sınırı: modele metnin ilk ~6000 karakteri gönderilir

CATEGORIES = Category.values

ENRICHMENT_SYSTEM = (
    "You are an experienced news editor. Analyze the given article. "
    "Summary points must be short, factual and neutral; do not add information that is not in the article. "
    "Write the summary points and tags in {language}."
)

ENRICHMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "tldr": {
            "type": "array",
            "items": {"type": "string"},
            "description": "At most 3 short summary points",
        },
        "category": {"type": "string", "enum": CATEGORIES},
        "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
        "importance": {"type": "integer", "description": "From 1 (trivial) to 10 (very important)"},
        "tags": {"type": "array", "items": {"type": "string"}, "description": "At most 5 tags"},
    },
    "required": ["tldr", "category", "sentiment", "importance", "tags"],
    "additionalProperties": False,
}


@dataclass
class SyncStats:
    new: int = 0
    skipped: int = 0
    robots_blocked: int = 0
    extract_failed: int = 0
    enriched: int = 0
    enrich_failed: int = 0
    enrich_skipped: bool = False
    feed_errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        # "etiket: sayı" biçimi çoğul eklerine takılmadan her dile çevrilebilir.
        parts = [_("new: %d") % self.new, _("already saved: %d") % self.skipped]
        if self.robots_blocked:
            parts.append(_("RSS excerpt only (robots.txt): %d") % self.robots_blocked)
        if self.extract_failed:
            parts.append(_("text extraction failed: %d") % self.extract_failed)
        if self.enrich_skipped:
            parts.append(_("AI summaries skipped (LLM not configured)"))
        else:
            parts.append(_("AI summaries: %d") % self.enriched)
            if self.enrich_failed:
                parts.append(_("AI errors: %d") % self.enrich_failed)
        if self.feed_errors:
            parts.append(_("feed errors: %s") % "; ".join(self.feed_errors))
        return " · ".join(parts)


class RobotsCache:
    """robots.txt kurallarını alan adı başına bir kez çeker."""

    def __init__(self, http: httpx.Client, user_agent: str):
        self.http = http
        self.user_agent = user_agent
        self.parsers: dict[str, RobotFileParser | None] = {}

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self.parsers:
            self.parsers[origin] = self._load(origin)
        parser = self.parsers[origin]
        # robots.txt okunamadıysa (ağ hatası) temkinli davran: makaleyi çekme.
        return parser.can_fetch(self.user_agent, url) if parser else False

    def _load(self, origin: str) -> RobotFileParser | None:
        parser = RobotFileParser()
        try:
            response = self.http.get(f"{origin}/robots.txt", timeout=10)
        except httpx.HTTPError:
            return None
        if response.status_code in (401, 403):
            parser.disallow_all = True
        elif response.status_code >= 400:
            parser.allow_all = True
        else:
            parser.parse(response.text.splitlines())
        return parser


def http_client(**kwargs) -> httpx.Client:
    return httpx.Client(
        timeout=20,
        follow_redirects=True,
        headers={"User-Agent": settings.NEWS_USER_AGENT},
        **kwargs,
    )


def parse_entries(content: bytes) -> list[dict]:
    parsed = feedparser.parse(content)
    entries = []
    for entry in parsed.entries:
        link = entry.get("link")
        title = strip_tags(entry.get("title") or "").strip()
        if not link or not title:
            continue
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        entries.append(
            {
                "url": link,
                "title": title[:500],
                "summary": strip_tags(entry.get("summary") or "").strip(),
                "published_at": datetime.fromtimestamp(calendar.timegm(published), tz=UTC)
                if published
                else None,
            }
        )
    return entries


def fetch_feed(feed: Feed, http: httpx.Client) -> list[dict] | None:
    """Feed'i koşullu çeker. Değişmediyse (304) None döner."""
    headers = {}
    if feed.etag:
        headers["If-None-Match"] = feed.etag
    if feed.last_modified:
        headers["If-Modified-Since"] = feed.last_modified
    response = http.get(feed.url, headers=headers)
    if response.status_code == 304:
        return None
    response.raise_for_status()
    feed.etag = response.headers.get("etag", "")[:255]
    feed.last_modified = response.headers.get("last-modified", "")[:255]
    return parse_entries(response.content)


def download_html(url: str, http: httpx.Client) -> str | None:
    with http.stream("GET", url) as response:
        if response.status_code != 200 or "html" not in response.headers.get("content-type", ""):
            return None
        chunks, size = [], 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > MAX_HTML_BYTES:
                return None
            chunks.append(chunk)
    return b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")


def extract_article(url: str, html: str, language: str = "tr") -> dict:
    config = Config()
    config.fetch_images = False  # görsel boyutu için ağa çıkmasın
    config.language = language  # dil verilmezse Türkçe metinler boş çıkar (İngilizce stopword'ler)
    article = NewspaperArticle(url, config=config)
    article.download(input_html=html, ignore_read_more=True)
    article.parse()
    return {"content": (article.text or "").strip(), "image_url": (article.top_image or "")[:1000]}


def enrich(title: str, text: str, client: llm.LLMClient) -> dict:
    prompt = f"Title: {title}\n\nArticle:\n{text[:ENRICH_INPUT_CHARS]}"
    system = ENRICHMENT_SYSTEM.format(language=language_name(settings.NEWS_SUMMARY_LANGUAGE))
    data = client.generate_json(prompt, schema=ENRICHMENT_SCHEMA, system=system, effort="low")
    category = data.get("category")
    sentiment = data.get("sentiment")
    try:
        importance = min(max(int(data.get("importance", 5)), 1), 10)
    except (TypeError, ValueError):
        importance = 5
    return {
        "summary": [str(item).strip() for item in data.get("tldr", []) if str(item).strip()][:3],
        "category": category if category in CATEGORIES else Category.OTHER,
        "sentiment": sentiment if sentiment in Article.Sentiment.values else "neutral",
        "importance": importance,
        "tags": [str(tag).strip()[:40] for tag in data.get("tags", []) if str(tag).strip()][:5],
    }


def sync_feed(
    feed: Feed,
    *,
    http: httpx.Client,
    robots: RobotsCache,
    stats: SyncStats,
    llm_client: llm.LLMClient | None,
    limit: int,
) -> None:
    entries = fetch_feed(feed, http)
    feed.last_synced_at = timezone.now()
    feed.save(update_fields=["etag", "last_modified", "last_synced_at"])
    if entries is None:
        return

    entries = entries[:limit]
    existing = set(Article.objects.filter(url__in=[e["url"] for e in entries]).values_list("url", flat=True))
    articles = []
    for entry in entries:
        if entry["url"] in existing:
            stats.skipped += 1
            continue

        content, image_url = entry["summary"], ""
        if robots.allowed(entry["url"]):
            try:
                html = download_html(entry["url"], http)
                if html:
                    extracted = extract_article(entry["url"], html, feed.language)
                    content = extracted["content"] or content
                    image_url = extracted["image_url"]
                else:
                    stats.extract_failed += 1
            except (httpx.HTTPError, ArticleException) as exc:
                logger.info("Makale çıkarılamadı (%s): %s", entry["url"], exc)
                stats.extract_failed += 1
        else:
            stats.robots_blocked += 1

        article = Article(
            feed=feed,
            url=entry["url"],
            title=entry["title"],
            excerpt=entry["summary"][:1000],
            content=content,
            image_url=image_url,
            published_at=entry["published_at"],
            category=feed.category,
        )
        if llm_client and content:
            try:
                for key, value in enrich(entry["title"], content, llm_client).items():
                    setattr(article, key, value)
                article.enriched_at = timezone.now()
                stats.enriched += 1
            except llm.LLMError as exc:
                logger.warning("AI zenginleştirme başarısız (%s): %s", entry["url"], exc)
                stats.enrich_failed += 1
        articles.append(article)

    created = Article.objects.bulk_create(articles, ignore_conflicts=True)
    stats.new += len(created)


def sync_all(*, http: httpx.Client | None = None, llm_client: llm.LLMClient | None = None) -> tuple[int, str]:
    """Senkronizasyon işi (bkz. apps.core.sync): tüm aktif kaynakları işler."""
    stats = SyncStats()
    if llm_client is None and settings.NEWS_ENRICH:
        client = llm.get_client()
        llm_client = client if client.configured else None
    stats.enrich_skipped = llm_client is None

    feeds = list(Feed.objects.filter(is_active=True))
    owns_http = http is None
    http = http or http_client()
    try:
        robots = RobotsCache(http, settings.NEWS_USER_AGENT)
        for feed in feeds:
            try:
                sync_feed(
                    feed,
                    http=http,
                    robots=robots,
                    stats=stats,
                    llm_client=llm_client,
                    limit=settings.NEWS_SYNC_LIMIT,
                )
            except httpx.HTTPError as exc:
                logger.warning("Kaynak çekilemedi (%s): %s", feed.url, exc)
                stats.feed_errors.append(f"{feed.name}: {type(exc).__name__}")
    finally:
        if owns_http:
            http.close()

    if feeds and len(stats.feed_errors) == len(feeds):
        raise RuntimeError(_("None of the feeds could be fetched: %s") % "; ".join(stats.feed_errors))
    return stats.new, stats.summary()
