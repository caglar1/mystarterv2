from django.contrib import admin

from .models import Article, Feed


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    list_display = ["name", "url", "category", "language", "is_active", "last_synced_at"]
    list_editable = ["is_active"]
    list_filter = ["is_active", "category"]
    search_fields = ["name", "url"]


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ["title", "feed", "category", "sentiment", "importance", "published_at"]
    list_filter = ["feed", "category", "sentiment"]
    search_fields = ["title", "url"]
    date_hierarchy = "published_at"
    readonly_fields = ["created_at", "enriched_at"]
