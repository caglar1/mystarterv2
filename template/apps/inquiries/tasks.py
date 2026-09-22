from django.conf import settings
from django.core.mail import send_mail
from django.tasks import task
from django.template.loader import render_to_string

from .models import Inquiry


@task
def send_inquiry_emails(inquiry_id: int) -> None:
    """Ekibe bildirim + müşteriye otomatik onay e-postası (worker'da çalışır)."""
    inquiry = Inquiry.objects.get(pk=inquiry_id)
    context = {"inquiry": inquiry, "site_name": settings.SITE_NAME}

    if settings.NOTIFICATION_EMAILS:
        send_mail(
            subject=f"Yeni teklif talebi: {inquiry.full_name}",
            message=render_to_string("inquiries/email/notify_team.txt", context),
            from_email=None,
            recipient_list=settings.NOTIFICATION_EMAILS,
        )

    send_mail(
        subject=f"{settings.SITE_NAME}: talebinizi aldık",
        message=render_to_string("inquiries/email/confirm_customer.txt", context),
        from_email=None,
        recipient_list=[inquiry.email],
    )
