from django.core.mail import send_mail
from django.tasks import task


@task
def send_email(subject: str, body: str, from_email: str | None, recipient_list: list[str]) -> None:
    """Hazır bir e-postayı gönderir (worker'da). Metin istekte, doğru dilde render edilmiş olmalı."""
    send_mail(subject=subject, message=body, from_email=from_email, recipient_list=recipient_list)
