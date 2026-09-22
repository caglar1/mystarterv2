from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Projenin kullanıcı modeli.

    İlk günden özel model kullanmak Django'nun önerisidir: sonradan alan eklemek
    (telefon, şirket, rol...) migration ile kolayca yapılabilir.
    """

    class Meta(AbstractUser.Meta):
        verbose_name = _("user")
        verbose_name_plural = _("users")
