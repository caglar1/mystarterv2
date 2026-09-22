from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PlacesConfig(AppConfig):
    name = "apps.places"
    verbose_name = _("Places")

    def ready(self):
        from apps.core.sync import register_job

        from .services import sync_default_area

        register_job("places", _("Places (OpenStreetMap / Overpass)"), sync_default_area)
