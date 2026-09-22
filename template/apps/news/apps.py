from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NewsConfig(AppConfig):
    name = "apps.news"
    verbose_name = _("News")

    def ready(self):
        from apps.core.sync import register_job

        from .pipeline import sync_all

        register_job("news", _("News (RSS + AI summaries)"), sync_all)
