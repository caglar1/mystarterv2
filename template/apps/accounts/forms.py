from django.contrib.auth import forms as auth_forms
from django.template.loader import render_to_string

from apps.core.forms import SpamProtectedFormMixin, StyledFormMixin

from .models import User
from .tasks import send_email


class LoginForm(StyledFormMixin, auth_forms.AuthenticationForm):
    pass


class PasswordChangeForm(StyledFormMixin, auth_forms.PasswordChangeForm):
    pass


class PasswordResetForm(StyledFormMixin, auth_forms.PasswordResetForm):
    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        # E-posta istek içinde (kullanıcının dilinde) hazırlanır, gönderimi worker yapar: istek SMTP'yi
        # beklemez ve yanıt süresi, adresin kayıtlı olup olmadığını ele vermez.
        subject = "".join(render_to_string(subject_template_name, context).splitlines())
        body = render_to_string(email_template_name, context)
        send_email.enqueue(subject, body, from_email, [to_email])


class SetPasswordForm(StyledFormMixin, auth_forms.SetPasswordForm):
    pass


class SignupForm(SpamProtectedFormMixin, StyledFormMixin, auth_forms.UserCreationForm):
    class Meta(auth_forms.UserCreationForm.Meta):
        model = User
        fields = ["username", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # E-postasız hesap şifresini sıfırlayamaz.
        self.fields["email"].required = True
