from django.conf import settings
from django.db import models


class SyncRun(models.Model):
    """Dış kaynaklardan veri senkronizasyonlarının (Overpass, RSS...) kaydı.

    Hem cron ile çalışan yönetim komutları hem de arayüzdeki "Şimdi senkronize et" butonu
    aynı kaydı kullanır; arayüz HTMX ile bu kaydın durumunu sorgular.
    """

    class Status(models.TextChoices):
        QUEUED = "queued", "Sırada"
        RUNNING = "running", "Çalışıyor"
        SUCCESS = "success", "Başarılı"
        FAILED = "failed", "Hatalı"

    job = models.CharField("görev", max_length=50, db_index=True)
    status = models.CharField("durum", max_length=10, choices=Status.choices, default=Status.QUEUED)
    items = models.PositiveIntegerField("öge sayısı", default=0)
    message = models.TextField("mesaj", blank=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="başlatan", null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField("oluşturulma", auto_now_add=True)
    started_at = models.DateTimeField("başlangıç", null=True, blank=True)
    finished_at = models.DateTimeField("bitiş", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "senkronizasyon"
        verbose_name_plural = "senkronizasyonlar"

    def __str__(self):
        return f"{self.job} #{self.pk} ({self.get_status_display()})"

    @property
    def is_finished(self) -> bool:
        return self.status in {self.Status.SUCCESS, self.Status.FAILED}

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None
