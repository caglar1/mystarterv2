from django.urls import path

from . import views

app_name = "ai"

urlpatterns = [
    path("ozet/", views.summarize, name="summarize"),
    path("ozet/baslat/", views.summarize_start, name="summarize_start"),
    path("ozet/akis/<slug:key>/", views.summarize_stream, name="summarize_stream"),
]
