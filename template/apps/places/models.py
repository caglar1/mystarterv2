from django.db import models
from django.utils.translation import gettext_lazy as _


class Place(models.Model):
    """OpenStreetMap'ten (Overpass) senkronize edilen bir nokta."""

    osm_id = models.CharField(_("OSM id"), max_length=40, unique=True)  # ör. "node/123456"
    name = models.CharField(_("name"), max_length=255)
    category = models.CharField(_("category"), max_length=60, db_index=True)
    lat = models.FloatField(_("latitude"))
    lng = models.FloatField(_("longitude"))
    address = models.CharField(_("address"), max_length=255, blank=True)
    phone = models.CharField(_("phone"), max_length=60, blank=True)
    website = models.URLField(_("website"), max_length=500, blank=True)
    opening_hours = models.CharField(_("opening hours"), max_length=255, blank=True)
    tags = models.JSONField(_("OSM tags"), default=dict, blank=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("place")
        verbose_name_plural = _("places")
        indexes = [models.Index(fields=["lat", "lng"], name="place_lat_lng_idx")]

    def __str__(self):
        return self.name

    @property
    def osm_url(self) -> str:
        return f"https://www.openstreetmap.org/{self.osm_id}"
