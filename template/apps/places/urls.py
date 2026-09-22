from django.urls import path
from django.utils.translation import gettext_lazy as _

from . import views

app_name = "places"

urlpatterns = [
    path("", views.map_view, name="map"),
    path(_("nearby/"), views.nearby_view, name="nearby"),
]
