from django.contrib.auth import forms as auth_forms

from apps.core.forms import SpamProtectedFormMixin, StyledFormMixin

from .models import User


class LoginForm(StyledFormMixin, auth_forms.AuthenticationForm):
    pass


class PasswordChangeForm(StyledFormMixin, auth_forms.PasswordChangeForm):
    pass


class PasswordResetForm(StyledFormMixin, auth_forms.PasswordResetForm):
    pass


class SetPasswordForm(StyledFormMixin, auth_forms.SetPasswordForm):
    pass


class SignupForm(SpamProtectedFormMixin, StyledFormMixin, auth_forms.UserCreationForm):
    class Meta(auth_forms.UserCreationForm.Meta):
        model = User
        fields = ["username", "email"]
