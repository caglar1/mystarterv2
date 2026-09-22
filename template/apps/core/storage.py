from django.contrib.staticfiles.storage import HashedFilesMixin
from whitenoise.storage import CompressedManifestStaticFilesStorage


def _without_source_maps(patterns):
    return tuple(
        (
            extension,
            tuple(p for p in rules if "sourceMappingURL" not in (p[0] if isinstance(p, tuple) else p)),
        )
        for extension, rules in patterns
    )


class StaticFilesStorage(CompressedManifestStaticFilesStorage):
    """WhiteNoise: hash'li dosya adları + gzip/brotli; CSS içindeki url() referansları yeniden yazılır.

    Tek fark: vendor dosyalarının (ör. leaflet.js) `sourceMappingURL` yorumları işlenmez. .map dosyaları
    dağıtılmadığı için aksi halde `collectstatic` "leaflet.js.map bulunamadı" hatasıyla durur.
    """

    patterns = _without_source_maps(HashedFilesMixin.patterns)
