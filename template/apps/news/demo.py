from django.utils import timezone

from .models import Article, Feed

FEEDS = [
    ("Django Weblog", "https://www.djangoproject.com/rss/weblog/", "teknoloji", "en"),
    ("BBC Türkçe", "https://feeds.bbci.co.uk/turkce/rss.xml", "dunya", "tr"),
]

ARTICLES = [
    (
        "Örnek: Yeni sürüm yayınlandı",
        "Bu bir örnek haberdir. Gerçek haberler için yönetici olarak 'Şimdi senkronize et' "
        "butonunu kullanın.",
        ["Örnek içerik gösterimi", "Senkronizasyon ile gerçek haberler gelir"],
    ),
    (
        "Örnek: Haftanın öne çıkan gelişmeleri",
        "Kaynaklar yönetim panelinden eklenir; her senkronizasyonda yalnızca yeni haberler işlenir.",
        ["Kaynaklar admin panelinden yönetilir"],
    ),
]


def seed() -> str:
    feeds = []
    for name, url, category, language in FEEDS:
        defaults = {"name": name, "category": category, "language": language}
        feeds.append(Feed.objects.get_or_create(url=url, defaults=defaults)[0])
    created = 0
    for index, (title, content, summary) in enumerate(ARTICLES, start=1):
        _, was_created = Article.objects.get_or_create(
            url=f"https://example.com/ornek-haber-{index}",
            defaults={
                "feed": feeds[0],
                "title": title,
                "content": content,
                "summary": summary,
                "category": "teknoloji",
                "published_at": timezone.now(),
            },
        )
        created += was_created
    return f"{len(feeds)} kaynak, {created} örnek haber"
