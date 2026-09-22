"""İlk kurulum yardımcısı: .env oluşturur (rastgele SECRET_KEY ile) ve uv varsa uv.lock üretir.

Hem Copier kurulum sonrası görevi hem de `make setup` tarafından çağrılır; tekrar çalıştırmak güvenlidir
(mevcut .env'e dokunmaz). Yalnızca standart kütüphane kullanır.

`--git`: proje henüz bir git deposunda değilse depo açar ve ilk commit'i atar (Copier yalnızca ilk kurulumda
çağırır; `copier update` yalnızca git'teki projelerde çalışır).
"""

from __future__ import annotations

import secrets
import shutil
import string
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def ensure_env_and_lock() -> None:
    env_file = ROOT / ".env"
    if env_file.exists():
        print(".env zaten var, dokunulmadı.")
    else:
        alphabet = string.ascii_letters + string.digits + "!@#%^&*(-_=+)"
        secret = "".join(secrets.choice(alphabet) for _ in range(64))
        content = (ROOT / ".env.example").read_text()
        content = content.replace("SECRET_KEY=", f"SECRET_KEY={secret}", 1)
        content = content.replace("DEBUG=False", "DEBUG=True", 1)
        # Postgres projelerinde compose bu parolayı zorunlu tutar; rastgele bir değerle başlasın.
        db_password = secrets.token_urlsafe(24)
        content = content.replace("POSTGRES_PASSWORD=\n", f"POSTGRES_PASSWORD={db_password}\n", 1)
        env_file.write_text(content)
        print(".env oluşturuldu (DEBUG=True, rastgele SECRET_KEY).")

    uv = shutil.which("uv")
    if not (ROOT / "uv.lock").exists() and uv:
        subprocess.run([uv, "lock", "--quiet"], cwd=ROOT, check=False)  # noqa: S603
        print("uv.lock oluşturuldu.")


def init_git() -> None:
    git = shutil.which("git")
    if not git:
        print("git bulunamadı; depo açılmadı (`copier update` için git gerekir).")
        return

    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run([git, *args], cwd=ROOT, capture_output=True, text=True, check=False)  # noqa: S603

    if run("rev-parse", "--is-inside-work-tree").returncode == 0:
        print("Proje zaten bir git deposunda; git'e dokunulmadı.")
        return
    run("init", "--quiet", "--initial-branch=main")
    run("add", "--all")
    commit = run("commit", "--quiet", "--message", "Starterpack v2 ile oluşturuldu")
    if commit.returncode == 0:
        print("git deposu açıldı, ilk commit atıldı.")
    else:
        # En sık neden: git kullanıcı adı/e-postası tanımlı değil. Depo yine de açık.
        print("git deposu açıldı ama ilk commit atılamadı; `git add -A && git commit` ile siz atın.")


def main() -> None:
    ensure_env_and_lock()
    if "--git" in sys.argv[1:]:
        init_git()


if __name__ == "__main__":
    main()
