from django.contrib.auth import get_user_model

from .services import ensure_starter_board


def seed() -> str:
    users = get_user_model().objects.filter(is_superuser=True)
    for user in users:
        ensure_starter_board(user)
    return f"{users.count()} yönetici için örnek pano (diğer kullanıcılar ilk girişte alır)"
