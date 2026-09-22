from django.db import models
from django.utils.translation import gettext_lazy as _


class Category(models.TextChoices):
    TECHNOLOGY = "technology", _("Technology")
    BUSINESS = "business", _("Business")
    WORLD = "world", _("World")
    SCIENCE = "science", _("Science")
    HEALTH = "health", _("Health")
    SPORTS = "sports", _("Sports")
    CULTURE = "culture", _("Culture")
    OTHER = "other", _("Other")


class Feed(models.Model):
    name = models.CharField(_("name"), max_length=120)
    url = models.URLField(_("RSS/Atom URL"), max_length=500, unique=True)
    category = models.CharField(
        _("default category"), max_length=40, choices=Category.choices, default=Category.OTHER
    )
    # Metin çıkarma dile göre yapılır (stopword'ler); yanlış dil = boş metin.
    language = models.CharField(
        _("language"), max_length=5, default="tr", help_text=_("ISO code: tr, en, de...")
    )
    is_active = models.BooleanField(_("active"), default=True)
    etag = models.CharField(max_length=255, blank=True, editable=False)
    last_modified = models.CharField(max_length=255, blank=True, editable=False)
    last_synced_at = models.DateTimeField(_("last synced at"), null=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("feed")
        verbose_name_plural = _("feeds")

    def __str__(self):
        return self.name


class Article(models.Model):
    class Sentiment(models.TextChoices):
        POSITIVE = "positive", _("Positive")
        NEUTRAL = "neutral", _("Neutral")
        NEGATIVE = "negative", _("Negative")

    feed = models.ForeignKey(Feed, verbose_name=_("feed"), on_delete=models.CASCADE, related_name="articles")
    url = models.URLField(_("URL"), max_length=1000, unique=True)
    title = models.CharField(_("title"), max_length=500)
    excerpt = models.TextField(_("RSS excerpt"), blank=True)  # kartlarda gösterilir (temiz, kısa)
    content = models.TextField(_("content"), blank=True)  # tam metin: arama ve AI zenginleştirme için
    image_url = models.URLField(_("image"), max_length=1000, blank=True)
    published_at = models.DateTimeField(_("published at"), null=True, blank=True, db_index=True)
    # AI zenginleştirme
    summary = models.JSONField(_("summary points"), default=list, blank=True)
    category = models.CharField(
        _("category"), max_length=40, choices=Category.choices, blank=True, db_index=True
    )
    sentiment = models.CharField(_("sentiment"), max_length=10, choices=Sentiment.choices, blank=True)
    importance = models.PositiveSmallIntegerField(_("importance (1-10)"), null=True, blank=True)
    tags = models.JSONField(_("tags"), default=list, blank=True)
    enriched_at = models.DateTimeField(_("enriched at"), null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = _("article")
        verbose_name_plural = _("articles")

    def __str__(self):
        return self.title
