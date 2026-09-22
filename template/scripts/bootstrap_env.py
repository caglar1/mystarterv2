"""İlk kurulum yardımcısı: .env oluşturur (rastgele SECRET_KEY ile) ve uv varsa uv.lock üretir.

Hem Copier kurulum sonrası görevi hem de `make setup` tarafından çağrılır; tekrar çalıştırmak güvenlidir
(mevcut .env'e dokunmaz). Yalnızca standart kütüphane kullanır.
"""

from __future__ import annotations

import secrets
import shutil
import string
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    env_file = ROOT / ".env"
    if env_file.exists():
        print(".env zaten var, dokunulmadı.")
    else:
        alphabet = string.ascii_letters + string.digits + "!@#%^&*(-_=+)"
        secret = "".join(secrets.choice(alphabet) for _ in range(64))
        content = (ROOT / ".env.example").read_text()
        content = content.replace("SECRET_KEY=", f"SECRET_KEY={secret}", 1)
        content = content.replace("DEBUG=False", "DEBUG=True", 1)
        env_file.write_text(content)
        print(".env oluşturuldu (DEBUG=True, rastgele SECRET_KEY).")

    uv = shutil.which("uv")
    if not (ROOT / "uv.lock").exists() and uv:
        subprocess.run([uv, "lock", "--quiet"], cwd=ROOT, check=False)  # noqa: S603
        print("uv.lock oluşturuldu.")


if __name__ == "__main__":
    main()
