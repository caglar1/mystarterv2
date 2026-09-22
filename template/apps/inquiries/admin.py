from django.contrib import admin

from .models import Inquiry


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "phone", "status", "created_at"]
    list_filter = ["status", "created_at"]
    list_editable = ["status"]
    search_fields = ["full_name", "email", "message"]
    readonly_fields = ["created_at", "consent_at"]
    date_hierarchy = "created_at"
