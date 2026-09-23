from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Inquiry


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "phone", "status", "has_attachment", "created_at"]
    list_filter = ["status", "created_at"]
    list_editable = ["status"]
    search_fields = ["full_name", "email", "message"]
    # Ek, korumalı indirme bağlantısıyla gösterilir: dosyalar `private/` altında, doğrudan sunulmuyor.
    exclude = ["attachment"]
    readonly_fields = ["created_at", "consent_at", "attachment_link"]
    date_hierarchy = "created_at"

    @admin.display(description=_("attachment"), boolean=True)
    def has_attachment(self, obj: Inquiry) -> bool:
        return bool(obj.attachment)

    @admin.display(description=_("attachment"))
    def attachment_link(self, obj: Inquiry):
        if not obj.attachment:
            return "—"
        url = reverse("inquiries:attachment", args=[obj.pk])
        return format_html('<a href="{}" download>{}</a>', url, _("Download"))
