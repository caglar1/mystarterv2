"""Çeviri dosyalarını günceller ve derler (GNU gettext gerekir: brew/apt install gettext).

    uv run python scripts/messages.py          # tüm diller (settings.LANGUAGES, İngilizce kaynak hariç)
    uv run python scripts/messages.py de       # yeni dil ekle / yalnızca bu dil

Her uygulamanın kendi `apps/<app>/locale/` klasörü vardır (modül silinince çevirileri de gider);
`templates/` ve `config/` metinleri kökteki `locale/` klasörüne yazılır.
Sonra .po dosyalarındaki boş `msgstr ""` satırlarını doldurun ve betiği tekrar çalıştırın (derleme için).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from django.utils.translation import to_locale  # dil kodu -> klasör adı (pt-br -> pt_BR)

ROOT = Path(__file__).resolve().parent.parent
SOURCE_LANGUAGE = "en"  # kaynak metinler İngilizce; bu dil için .po gerekmez
COMMON = ["--no-obsolete", "--no-location"]


def manage(*args: str, cwd: Path) -> None:
    subprocess.run([sys.executable, str(ROOT / "manage.py"), *args], cwd=cwd, check=True)  # noqa: S603


def languages() -> list[str]:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ.setdefault("DEBUG", "True")
    sys.path.insert(0, str(ROOT))
    import django
    from django.conf import settings

    django.setup()
    return [code for code, _name in settings.LANGUAGES if code != SOURCE_LANGUAGE]


def main() -> None:
    codes = sys.argv[1:] or languages()
    if not codes:
        print("Çevrilecek dil yok (yalnızca kaynak dil tanımlı).")
        return
    # Django klasör adını bekler: makemessages -l pt-br "geçersiz" der ve o dili atlar.
    flags = [arg for code in codes for arg in ("-l", to_locale(code))]

    for app in sorted(p for p in (ROOT / "apps").iterdir() if (p / "apps.py").exists()):
        (app / "locale").mkdir(exist_ok=True)
        manage("makemessages", *flags, *COMMON, cwd=app)

    (ROOT / "locale").mkdir(exist_ok=True)
    ignores = [
        arg
        for pattern in ("apps/*", ".venv/*", "static/*", "staticfiles/*", "docs/*", "scripts/*")
        for arg in ("--ignore", pattern)
    ]
    manage("makemessages", *flags, *COMMON, *ignores, cwd=ROOT)
    manage("compilemessages", "--ignore", ".venv", cwd=ROOT)
    print("Tamam. Boş msgstr kalmadığından emin olun: `make check` çeviri testini de çalıştırır.")


if __name__ == "__main__":
    main()
