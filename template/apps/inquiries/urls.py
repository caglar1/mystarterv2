from django.urls import path

from . import views

app_name = "inquiries"

urlpatterns = [
    path("gonder/", views.submit, name="submit"),
]
