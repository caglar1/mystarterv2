from django.db import models


class Inquiry(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Yeni"
        IN_PROGRESS = "in_progress", "İşlemde"
        CLOSED = "closed", "Kapandı"

    full_name = models.CharField("ad soyad", max_length=150)
    email = models.EmailField("e-posta")
    phone = models.CharField("telefon", max_length=30, blank=True)
    message = models.TextField("mesaj")
    consent_at = models.DateTimeField("KVKK onay zamanı")
    status = models.CharField(
        "durum", max_length=20, choices=Status.choices, default=Status.NEW, db_index=True
    )
    notes = models.TextField("iç notlar", blank=True)
    created_at = models.DateTimeField("oluşturulma", auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "talep"
        verbose_name_plural = "talepler"

    def __str__(self):
        return f"{self.full_name} <{self.email}>"
