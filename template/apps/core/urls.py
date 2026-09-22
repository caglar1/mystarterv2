from django.contrib.sitemaps.views import sitemap
from django.urls import path

from . import views
from .sitemaps import sitemaps

app_name = "core"

urlpatterns = [
    path("healthz", views.healthz, name="healthz"),
    path("robots.txt", views.robots_txt, name="robots"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("manifest.webmanifest", views.web_manifest, name="manifest"),
    path("sync/<slug:job>/", views.sync_trigger, name="sync_trigger"),
    path("sync/run/<int:pk>/", views.sync_status, name="sync_status"),
]
