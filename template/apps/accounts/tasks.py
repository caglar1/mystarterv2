from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.tasks import task
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import User


@task
def send_password_reset_email(
    user_id: int,
    domain: str,
    site_name: str,
    protocol: str,
    language: str,
    subject_template_name: str,
    email_template_name: str,
    from_email: str | None = None,
) -> None:
    """Şifre sıfırlama e-postasını worker'da hazırlar ve gönderir.

    Bağlantıdaki token burada üretilir: görev argümanlarında yalnızca kullanıcı kimliği olduğu için
    sıfırlama bağlantısı görev kuyruğu tablosuna ve veritabanı yedeklerine düşmez.
    """
    user = User._default_manager.filter(pk=user_id, is_active=True).first()
    if user is None or not user.has_usable_password():
        return
    email = getattr(user, User.get_email_field_name())
    if not email:
        return
    context = {
        "email": email,
        "domain": domain,
        "site_name": site_name,
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "user": user,
        "token": default_token_generator.make_token(user),
        "protocol": protocol,
        "project_name": settings.SITE_NAME,
    }
    with translation.override(language):
        subject = "".join(render_to_string(subject_template_name, context).splitlines())
        body = render_to_string(email_template_name, context)
    send_mail(subject=subject, message=body, from_email=from_email, recipient_list=[email])
