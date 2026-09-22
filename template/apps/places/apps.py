from django.apps import AppConfig


class PlacesConfig(AppConfig):
    name = "apps.places"
    verbose_name = "Harita ve yerler"

    def ready(self):
        from apps.core.sync import register_job

        from .services import sync_default_area

        register_job("places", "Yerler (OpenStreetMap / Overpass)", sync_default_area)
