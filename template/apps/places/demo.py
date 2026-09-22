from .models import Place

# Harita boş görünmesin diye örnek noktalar (gerçek veri için: python manage.py sync places)
DEMO = [
    ("demo/1", "Örnek Eczane Sultanahmet", "pharmacy", 41.0056, 28.9768),
    ("demo/2", "Örnek Klinik Eminönü", "clinic", 41.0171, 28.9706),
    ("demo/3", "Örnek Hastane Cağaloğlu", "hospital", 41.0115, 28.9756),
    ("demo/4", "Örnek Diş Kliniği Beyazıt", "dentist", 41.0105, 28.9641),
    ("demo/5", "Örnek Eczane Karaköy", "pharmacy", 41.0245, 28.9771),
    ("demo/6", "Örnek Aile Hekimi Kumkapı", "doctors", 41.0033, 28.9625),
]


def seed() -> str:
    created = 0
    for osm_id, name, category, lat, lng in DEMO:
        _, was_created = Place.objects.get_or_create(
            osm_id=osm_id, defaults={"name": name, "category": category, "lat": lat, "lng": lng}
        )
        created += was_created
    return f"{created} örnek yer eklendi"
