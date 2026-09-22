from django.contrib import admin

from .models import Place


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "address", "phone", "updated_at"]
    list_filter = ["category"]
    search_fields = ["name", "address", "osm_id"]
    readonly_fields = ["osm_id", "tags", "updated_at"]
