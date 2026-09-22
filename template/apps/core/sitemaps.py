from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        names = ["pages:home", "pages:about", "pages:services", "pages:contact"]
        if settings.FEATURES.get("maps"):
            names.append("places:map")
        if settings.FEATURES.get("news"):
            names.append("news:list")
        return names

    def location(self, item):
        return reverse(item)


sitemaps = {"static": StaticViewSitemap}
