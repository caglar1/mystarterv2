from django.apps import AppConfig


class NewsConfig(AppConfig):
    name = "apps.news"
    verbose_name = "Haberler"

    def ready(self):
        from apps.core.sync import register_job

        from .pipeline import sync_all

        register_job("news", "Haberler (RSS + AI özet)", sync_all)
