from django.urls import path
from django.utils.translation import gettext_lazy as _

from . import views

app_name = "ai"

urlpatterns = [
    path(_("summary/"), views.summarize, name="summarize"),
    path(_("summary/start/"), views.summarize_start, name="summarize_start"),
    path(_("summary/stream/<slug:key>/"), views.summarize_stream, name="summarize_stream"),
]
