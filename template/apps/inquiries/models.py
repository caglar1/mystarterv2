from django.conf import settings
from django.db import models
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from apps.core.uploads import UploadPath, UploadValidator

# Herkese açık formdan gelen dosyalar: küçük, tanıdık türler ve yalnızca yetkiliye açık klasör.
ATTACHMENT_MAX_MB = 5
ATTACHMENT_EXTENSIONS = ("pdf", "jpg", "jpeg", "png", "docx")


def default_language() -> str:
    # Fonksiyon: migration'a sabit bir dil yazılmasın (her projenin varsayılan dili farklı olabilir).
    return settings.LANGUAGE_CODE


class Inquiry(models.Model):
    class Status(models.TextChoices):
        NEW = "new", _("New")
        IN_PROGRESS = "in_progress", _("In progress")
        CLOSED = "closed", _("Closed")

    full_name = models.CharField(_("full name"), max_length=150)
    email = models.EmailField(_("email"))
    phone = models.CharField(_("phone"), max_length=30, blank=True)
    message = models.TextField(_("message"))
    # Form hangi dilde doldurulduysa e-postalar o dilde gönderilir.
    language = models.CharField(_("language"), max_length=10, default=default_language)
    attachment = models.FileField(
        _("attachment"),
        upload_to=UploadPath("private/inquiries"),
        validators=[UploadValidator(ATTACHMENT_MAX_MB, ATTACHMENT_EXTENSIONS)],
        max_length=255,
        blank=True,
    )
    consent_at = models.DateTimeField(_("consent given at"))
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.NEW, db_index=True
    )
    notes = models.TextField(_("internal notes"), blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("inquiry")
        verbose_name_plural = _("inquiries")

    def __str__(self):
        return f"{self.full_name} <{self.email}>"


@receiver(models.signals.post_delete, sender=Inquiry)
def delete_attachment(sender, instance, **kwargs) -> None:
    """Kayıt silinince eki de diskten sil (KVKK: veri tek yerde kalmasın)."""
    if instance.attachment:
        instance.attachment.delete(save=False)
