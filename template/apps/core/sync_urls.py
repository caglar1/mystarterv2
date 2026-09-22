# Arayüzden tetiklenen senkronizasyon uçları. i18n_patterns içinde: yanıtlar sayfanın dilinde döner.
from django.urls import path

from . import views

app_name = "sync"

urlpatterns = [
    path("<slug:job>/", views.sync_trigger, name="trigger"),
    path("run/<int:pk>/", views.sync_status, name="status"),
]
