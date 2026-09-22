from django.utils import timezone

from .models import Inquiry

DEMO = [
    ("Ayşe Yılmaz", "ayse@example.com", "Kurumsal web sitemizi yenilemek istiyoruz."),
    ("Mehmet Demir", "mehmet@example.com", "Randevu sistemi için teklif rica ediyorum."),
    ("Zeynep Kaya", "zeynep@example.com", "Mevcut uygulamamız için bakım desteği arıyoruz."),
]


def seed() -> str:
    created = 0
    for full_name, email, message in DEMO:
        _, was_created = Inquiry.objects.get_or_create(
            email=email,
            defaults={"full_name": full_name, "message": message, "consent_at": timezone.now()},
        )
        created += was_created
    return f"{created} demo talep eklendi"
