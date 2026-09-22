from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


class Board(models.Model):
    name = models.CharField(_("name"), max_length=120)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("owner"), on_delete=models.CASCADE, related_name="boards"
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("board")
        verbose_name_plural = _("boards")

    def __str__(self):
        return self.name


class Card(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", pgettext_lazy("kanban column", "To do")
        DOING = "doing", pgettext_lazy("kanban column", "In progress")
        DONE = "done", pgettext_lazy("kanban column", "Done")

    board = models.ForeignKey(Board, verbose_name=_("board"), on_delete=models.CASCADE, related_name="cards")
    title = models.CharField(_("title"), max_length=200)
    description = models.TextField(_("description"), blank=True)
    status = models.CharField(_("status"), max_length=10, choices=Status.choices, default=Status.TODO)
    position = models.PositiveIntegerField(_("position"), default=0)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ["status", "position", "id"]
        verbose_name = _("card")
        verbose_name_plural = _("cards")
        indexes = [models.Index(fields=["board", "status", "position"], name="kanban_card_order_idx")]

    def __str__(self):
        return self.title
