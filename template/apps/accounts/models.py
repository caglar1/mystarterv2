from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Projenin kullanıcı modeli.

    İlk günden özel model kullanmak Django'nun önerisidir: sonradan alan eklemek
    (telefon, şirket, rol...) migration ile kolayca yapılabilir.
    """

    class Meta(AbstractUser.Meta):
        verbose_name = "kullanıcı"
        verbose_name_plural = "kullanıcılar"
