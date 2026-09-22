"""Test ayarları: prod'a yakın (DEBUG=False) ama hızlı ve dış bağımlılıksız."""

import os

os.environ.update(
    {
        "DOTENV_PATH": "/dev/null",  # yerel .env testleri etkilemesin
        "DEBUG": "False",
        "SECRET_KEY": "test-" + "x" * 60,
        "ALLOWED_HOSTS": "testserver,localhost",
        "SECURE_SSL_REDIRECT": "False",
        "EMAIL_PROVIDER": "console",
        "LLM_API_KEY": "test-key",
    }
)

from .settings import *  # noqa: F403

TASKS = {"default": {"BACKEND": "django.tasks.backends.immediate.ImmediateBackend"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
FORM_MIN_SUBMIT_SECONDS = 0
# collectstatic çalıştırılmadan WhiteNoise'un STATIC_ROOT uyarısı vermemesi için
WHITENOISE_AUTOREFRESH = True

# Testler projenin dil seçiminden bağımsız olsun: kaynak dil (İngilizce) kökte, diğerleri önekli.
# Böylece `tr,en` seçilmiş bir projede de assertion'lar aynı kalır; çeviriler test_i18n.py'de denetlenir.
LANGUAGES = [("en", "English"), *[(code, name) for code, name in LANGUAGES if code != "en"]]  # noqa: F405
LANGUAGE_CODE = "en"
