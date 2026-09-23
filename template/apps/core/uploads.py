"""Yüklenen dosyalar: hedef yol ve doğrulama.

MEDIA_ROOT altında iki önek vardır:
- `public/`  — herkese açık dosyalar; canlıda Caddy `/media/public/...` adresinden sunar.
- `private/` — yalnızca yetkili kullanıcıya, bir Django view'ı üzerinden verilir; doğrudan sunulmaz.

Varsayılan `private/` olmalıdır; bir dosyanın herkese açık olması bilinçli bir karardır.
Dosya adları UUID ile yeniden yazılır: kullanıcıdan gelen ad diske hiç yazılmaz (yol kaçışı,
çakışma ve adı tahmin ederek indirme engellenir).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from pathlib import PurePath

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

# Uzantı -> dosyanın başlaması gereken baytlar. Tarayıcının bildirdiği content_type'a güvenilmez.
MAGIC_BYTES: dict[str, tuple[bytes, ...]] = {
    "pdf": (b"%PDF",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "gif": (b"GIF87a", b"GIF89a"),
    "webp": (b"RIFF",),
    # Office belgeleri ve zip aynı kapsayıcıdır.
    "docx": (b"PK\x03\x04",),
    "xlsx": (b"PK\x03\x04",),
    "pptx": (b"PK\x03\x04",),
    "zip": (b"PK\x03\x04",),
}


def extension_of(filename: str) -> str:
    return PurePath(filename).suffix.lower().lstrip(".")[:10]


@deconstructible
class UploadPath:
    """`upload_to` için: `<önek>/<yıl>/<ay>/<uuid>.<uzantı>`."""

    def __init__(self, prefix: str):
        self.prefix = prefix.strip("/")

    def __call__(self, instance, filename: str) -> str:
        extension = extension_of(filename)
        name = f"{uuid.uuid4().hex}.{extension}" if extension else uuid.uuid4().hex
        return f"{self.prefix}/{timezone.now():%Y/%m}/{name}"

    def __eq__(self, other) -> bool:
        return isinstance(other, UploadPath) and other.prefix == self.prefix


@deconstructible
class UploadValidator:
    """Boyut, uzantı ve dosyanın ilk baytlarını denetler (model alanı `validators` listesinde)."""

    def __init__(self, max_mb: float, extensions: Sequence[str]):
        self.max_mb = max_mb
        self.extensions = tuple(sorted(item.lower().lstrip(".") for item in extensions))

    def __call__(self, file) -> None:
        extension = extension_of(file.name or "")
        if extension not in self.extensions:
            raise ValidationError(
                _("Unsupported file type. Allowed: %(types)s."),
                code="extension",
                params={"types": ", ".join(self.extensions)},
            )
        if file.size > self.max_mb * 1024 * 1024:
            raise ValidationError(
                _("The file is too large (at most %(limit)s MB)."),
                code="size",
                params={"limit": f"{self.max_mb:g}"},
            )
        signatures = MAGIC_BYTES.get(extension)
        if signatures:
            position = file.tell() if hasattr(file, "tell") else 0
            file.seek(0)
            head = file.read(max(len(signature) for signature in signatures))
            file.seek(position)
            if not any(head.startswith(signature) for signature in signatures):
                raise ValidationError(_("The file content does not match its extension."), code="content")

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, UploadValidator)
            and other.max_mb == self.max_mb
            and other.extensions == self.extensions
        )
