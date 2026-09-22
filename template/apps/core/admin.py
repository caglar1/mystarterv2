from django.contrib import admin

from .models import SyncRun


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = ["job", "status", "items", "triggered_by", "created_at", "finished_at"]
    list_filter = ["job", "status"]
    readonly_fields = [f.name for f in SyncRun._meta.fields]

    def has_add_permission(self, request):
        return False
