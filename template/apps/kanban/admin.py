from django.contrib import admin

from .models import Board, Card


class CardInline(admin.TabularInline):
    model = Card
    extra = 0
    fields = ["title", "status", "position"]


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "created_at"]
    search_fields = ["name", "owner__username"]
    inlines = [CardInline]
