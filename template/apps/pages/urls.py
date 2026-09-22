from django.conf import settings
from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("", views.home, name="home"),
    path("hakkimizda/", views.about, name="about"),
    path("hizmetler/", views.services, name="services"),
    path("iletisim/", views.contact, name="contact"),
    path("kvkk/", views.privacy, name="privacy"),
]

if settings.FEATURES["ui_kit"]:
    urlpatterns.append(path("dev/ui-kit/", views.ui_kit, name="ui_kit"))
