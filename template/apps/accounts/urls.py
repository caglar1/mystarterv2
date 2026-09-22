from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("giris/", views.LoginView.as_view(), name="login"),
    path("cikis/", auth_views.LogoutView.as_view(), name="logout"),
    path("kayit/", views.signup, name="signup"),
    path("sifre/degistir/", views.PasswordChangeView.as_view(), name="password_change"),
    path("sifre/sifirla/", views.PasswordResetView.as_view(), name="password_reset"),
    path(
        "sifre/sifirla/gonderildi/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "sifre/sifirla/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "sifre/sifirla/tamam/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
