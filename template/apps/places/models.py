from django.db import models


class Place(models.Model):
    """OpenStreetMap'ten (Overpass) senkronize edilen bir nokta."""

    osm_id = models.CharField("OSM kimliği", max_length=40, unique=True)  # ör. "node/123456"
    name = models.CharField("ad", max_length=255)
    category = models.CharField("kategori", max_length=60, db_index=True)
    lat = models.FloatField("enlem")
    lng = models.FloatField("boylam")
    address = models.CharField("adres", max_length=255, blank=True)
    phone = models.CharField("telefon", max_length=60, blank=True)
    website = models.URLField("web sitesi", max_length=500, blank=True)
    opening_hours = models.CharField("çalışma saatleri", max_length=255, blank=True)
    tags = models.JSONField("OSM etiketleri", default=dict, blank=True)
    updated_at = models.DateTimeField("güncellenme", auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "yer"
        verbose_name_plural = "yerler"
        indexes = [models.Index(fields=["lat", "lng"], name="place_lat_lng_idx")]

    def __str__(self):
        return self.name

    @property
    def osm_url(self) -> str:
        return f"https://www.openstreetmap.org/{self.osm_id}"
