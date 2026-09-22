from django.contrib.auth import views as auth_views
from django.urls import path
from django.utils.translation import gettext_lazy as _

from . import views

app_name = "accounts"

urlpatterns = [
    path(_("login/"), views.LoginView.as_view(), name="login"),
    path(_("logout/"), auth_views.LogoutView.as_view(), name="logout"),
    path(_("signup/"), views.signup, name="signup"),
    path(_("password/change/"), views.PasswordChangeView.as_view(), name="password_change"),
    path(_("password/reset/"), views.PasswordResetView.as_view(), name="password_reset"),
    path(
        _("password/reset/sent/"),
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        _("password/reset/<uidb64>/<token>/"),
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        _("password/reset/done/"),
        auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),
        name="password_reset_complete",
    ),
]
