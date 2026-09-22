from django.conf import settings
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from .models import Article, Category, Feed

FEEDS = [
    ("Django Weblog", "https://www.djangoproject.com/rss/weblog/", Category.TECHNOLOGY, "en"),
    ("BBC Türkçe", "https://feeds.bbci.co.uk/turkce/rss.xml", Category.WORLD, "tr"),
]


def seed() -> str:
    feeds = []
    for name, url, category, language in FEEDS:
        defaults = {"name": name, "category": category, "language": language}
        feeds.append(Feed.objects.get_or_create(url=url, defaults=defaults)[0])

    # Örnek haberler sitenin varsayılan dilinde oluşturulur.
    with translation.override(settings.LANGUAGE_CODE):
        samples = [
            (
                _("Sample: a new release is out"),
                _("This is a sample article. Use the 'Sync now' button as an admin to fetch real news."),
                [_("Sample content"), _("Syncing brings in real articles")],
            ),
            (
                _("Sample: highlights of the week"),
                _("Feeds are managed in the admin; each sync only processes new articles."),
                [_("Feeds are managed in the admin")],
            ),
        ]
    created = 0
    for index, (title, content, summary) in enumerate(samples, start=1):
        _article, was_created = Article.objects.get_or_create(
            url=f"https://example.com/sample-article-{index}",
            defaults={
                "feed": feeds[0],
                "title": title,
                "content": content,
                "summary": summary,
                "category": Category.TECHNOLOGY,
                "published_at": timezone.now(),
            },
        )
        created += was_created
    return f"{len(feeds)} kaynak, {created} örnek haber"
