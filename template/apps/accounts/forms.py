from django.contrib.auth import forms as auth_forms
from django.utils.translation import get_language

from apps.core.forms import SpamProtectedFormMixin, StyledFormMixin

from .models import User
from .tasks import send_password_reset_email


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
        # E-posta worker'da hazırlanıp gönderilir: istek SMTP'yi beklemez ve yanıt süresi adresin kayıtlı olup
        # olmadığını ele vermez. Token (context["token"]) bilerek görev argümanlarına konmaz; worker yenisini
        # üretir, böylece sıfırlama bağlantısı görev tablosunda düz metin durmaz. Dil isteğin dilinden gelir.
        send_password_reset_email.enqueue(
            context["user"].pk,
            context["domain"],
            context["site_name"],
            context["protocol"],
            get_language(),
            subject_template_name,
            email_template_name,
            from_email,
        )


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
