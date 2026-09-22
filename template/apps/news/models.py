from django.db import models


class Feed(models.Model):
    name = models.CharField("ad", max_length=120)
    url = models.URLField("RSS/Atom adresi", max_length=500, unique=True)
    category = models.CharField("varsayılan kategori", max_length=40, default="diger")
    # Metin çıkarma dile göre yapılır (stopword'ler); yanlış dil = boş metin.
    language = models.CharField("dil", max_length=5, default="tr", help_text="ISO kodu: tr, en, de...")
    is_active = models.BooleanField("aktif", default=True)
    etag = models.CharField(max_length=255, blank=True, editable=False)
    last_modified = models.CharField(max_length=255, blank=True, editable=False)
    last_synced_at = models.DateTimeField("son senkronizasyon", null=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "kaynak"
        verbose_name_plural = "kaynaklar"

    def __str__(self):
        return self.name


class Article(models.Model):
    class Sentiment(models.TextChoices):
        POSITIVE = "positive", "Olumlu"
        NEUTRAL = "neutral", "Nötr"
        NEGATIVE = "negative", "Olumsuz"

    feed = models.ForeignKey(Feed, verbose_name="kaynak", on_delete=models.CASCADE, related_name="articles")
    url = models.URLField("adres", max_length=1000, unique=True)
    title = models.CharField("başlık", max_length=500)
    excerpt = models.TextField("RSS özeti", blank=True)  # kartlarda gösterilir (temiz, kısa)
    content = models.TextField("içerik", blank=True)  # tam metin: arama ve AI zenginleştirme için
    image_url = models.URLField("görsel", max_length=1000, blank=True)
    published_at = models.DateTimeField("yayın tarihi", null=True, blank=True, db_index=True)
    # AI zenginleştirme
    summary = models.JSONField("özet maddeleri", default=list, blank=True)
    category = models.CharField("kategori", max_length=40, blank=True, db_index=True)
    sentiment = models.CharField("duygu", max_length=10, choices=Sentiment.choices, blank=True)
    importance = models.PositiveSmallIntegerField("önem (1-10)", null=True, blank=True)
    tags = models.JSONField("etiketler", default=list, blank=True)
    enriched_at = models.DateTimeField("zenginleştirme", null=True, blank=True)
    created_at = models.DateTimeField("eklenme", auto_now_add=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "haber"
        verbose_name_plural = "haberler"

    def __str__(self):
        return self.title
