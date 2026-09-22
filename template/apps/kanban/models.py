from django.conf import settings
from django.db import models


class Board(models.Model):
    name = models.CharField("ad", max_length=120)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="sahibi", on_delete=models.CASCADE, related_name="boards"
    )
    created_at = models.DateTimeField("oluşturulma", auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "pano"
        verbose_name_plural = "panolar"

    def __str__(self):
        return self.name


class Card(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "Yapılacak"
        DOING = "doing", "Yapılıyor"
        DONE = "done", "Tamamlandı"

    board = models.ForeignKey(Board, verbose_name="pano", on_delete=models.CASCADE, related_name="cards")
    title = models.CharField("başlık", max_length=200)
    description = models.TextField("açıklama", blank=True)
    status = models.CharField("durum", max_length=10, choices=Status.choices, default=Status.TODO)
    position = models.PositiveIntegerField("sıra", default=0)
    created_at = models.DateTimeField("oluşturulma", auto_now_add=True)
    updated_at = models.DateTimeField("güncellenme", auto_now=True)

    class Meta:
        ordering = ["status", "position", "id"]
        verbose_name = "kart"
        verbose_name_plural = "kartlar"
        indexes = [models.Index(fields=["board", "status", "position"], name="kanban_card_order_idx")]

    def __str__(self):
        return self.title
