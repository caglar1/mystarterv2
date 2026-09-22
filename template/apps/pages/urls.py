from django.conf import settings
from django.urls import path
from django.utils.translation import gettext_lazy as _

from . import views

app_name = "pages"

urlpatterns = [
    path("", views.home, name="home"),
    path(_("about/"), views.about, name="about"),
    path(_("services/"), views.services, name="services"),
    path(_("contact/"), views.contact, name="contact"),
    path(_("privacy/"), views.privacy, name="privacy"),
]

if settings.FEATURES["ui_kit"]:
    urlpatterns.append(path("dev/ui-kit/", views.ui_kit, name="ui_kit"))
