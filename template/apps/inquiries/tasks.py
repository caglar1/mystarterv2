from django.conf import settings
from django.core.mail import send_mail
from django.tasks import task
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.translation import gettext as _

from .models import Inquiry


@task
def send_inquiry_emails(inquiry_id: int) -> None:
    """Ekibe bildirim + müşteriye otomatik onay e-postası (worker'da çalışır).

    Worker'da istek (ve dolayısıyla aktif dil) yoktur; müşteri e-postası formun doldurulduğu
    dilde, ekip e-postası sitenin varsayılan dilinde gönderilir.
    """
    inquiry = Inquiry.objects.get(pk=inquiry_id)
    context = {"inquiry": inquiry, "site_name": settings.SITE_NAME}

    if settings.NOTIFICATION_EMAILS:
        with translation.override(settings.LANGUAGE_CODE):
            send_mail(
                subject=_("New quote request: %(name)s") % {"name": inquiry.full_name},
                message=render_to_string("inquiries/email/notify_team.txt", context),
                from_email=None,
                recipient_list=settings.NOTIFICATION_EMAILS,
            )

    with translation.override(inquiry.language):
        send_mail(
            subject=_("%(site)s: we received your request") % {"site": settings.SITE_NAME},
            message=render_to_string("inquiries/email/confirm_customer.txt", context),
            from_email=None,
            recipient_list=[inquiry.email],
        )
