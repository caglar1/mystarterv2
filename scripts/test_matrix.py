"""Şablonu farklı seçenek kombinasyonlarıyla üretir ve her birini doğrular.

    uv run --with copier python scripts/test_matrix.py              # tüm kombinasyonlar
    uv run --with copier python scripts/test_matrix.py --only full-postgres --keep
    TEST_DATABASE_URL=postgres://postgres:test@localhost:5432/postgres \
        uv run --with copier python scripts/test_matrix.py          # postgres kombinasyonları gerçek DB'de

Her kombinasyon için: copier copy -> uv sync -> vendor sha256 -> ruff -> makemigrations --check -> pytest
(-> --css verilirse Tailwind derlemesi).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OFF = {"use_maps": False, "use_llm": False, "use_news": False, "use_kanban": False, "use_ui_kit": False}
COMBOS: dict[str, dict] = {
    "minimal-sqlite": {**OFF, "database": "sqlite"},
    "full-postgres": {
        "use_maps": True,
        "use_llm": True,
        "use_news": True,
        "use_kanban": True,
        "use_ui_kit": True,
        "database": "postgres",
    },
    "maps-carto": {**OFF, "use_maps": True, "map_tiles": "carto", "database": "sqlite"},
    "maps-pmtiles": {**OFF, "use_maps": True, "map_tiles": "pmtiles", "database": "postgres"},
    "llm-openai": {**OFF, "use_llm": True, "llm_provider": "openai", "database": "sqlite"},
    "news-llm": {**OFF, "use_llm": True, "use_news": True, "database": "sqlite"},
    "kanban-uikit": {**OFF, "use_kanban": True, "use_ui_kit": True, "database": "sqlite"},
    # Diller: Türkçe kökte (/hakkimizda/, /en/about/) ve tek dil (dil seçici/hreflang yok)
    "turkish-root": {**OFF, "use_kanban": True, "languages": "tr,en", "database": "sqlite"},
    "english-only": {**OFF, "languages": "en", "database": "sqlite"},
}


def run(cmd: list[str], cwd: Path, env: dict | None = None) -> tuple[bool, str]:
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, check=False)  # noqa: S603
    return result.returncode == 0, (result.stdout + result.stderr)[-3000:]


def check_combo(name: str, answers: dict, workdir: Path, *, css: bool) -> list[tuple[str, bool, str]]:
    target = workdir / name
    data = ["--data", f"project_name=Matris {name}", "--data", "author_email=matris@starterpack.test"]
    for key, value in answers.items():
        data += ["--data", f"{key}={str(value).lower() if isinstance(value, bool) else value}"]
    uvx = shutil.which("uvx") or "uvx"
    results = []
    # --vcs-ref HEAD: son etiketi değil çalışma ağacını test et (yayınlanmamış değişiklikler dahil)
    copier_cmd = [uvx, "copier", "copy", "--trust", "--defaults", "--quiet", "--vcs-ref", "HEAD"]
    ok, out = run([*copier_cmd, *data, str(ROOT), str(target)], ROOT)
    results.append(("copier copy", ok, out))
    if not ok:
        return results

    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.test_settings"}
    env.pop("VIRTUAL_ENV", None)
    if answers.get("database") == "postgres" and os.environ.get("TEST_DATABASE_URL"):
        env["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

    steps = [
        ("uv sync", ["uv", "sync", "--quiet"]),
        ("vendor sha256", ["uv", "run", "python", "scripts/vendor.py", "check"]),
        ("ruff check", ["uv", "run", "ruff", "check", "."]),
        ("ruff format", ["uv", "run", "ruff", "format", "--check", "."]),
        ("makemigrations --check", ["uv", "run", "python", "manage.py", "makemigrations", "--check", "--dry-run"]),
        ("pytest", ["uv", "run", "pytest", "-q", "--create-db"]),
    ]
    if css:
        steps.append(("tailwind build", ["uv", "run", "python", "manage.py", "tailwind", "build"]))
    for label, cmd in steps:
        ok, out = run(cmd, target, env)
        results.append((label, ok, out))
        if not ok:
            return results

    # Testler İngilizce'yi kökte zorlar; burada projenin GERÇEK ayarlarıyla (ör. tr,en) sayfalar açılır.
    real_env = {**env, "DJANGO_SETTINGS_MODULE": "config.settings"}
    real_env.pop("DATABASE_URL", None)
    for label, cmd in [
        ("migrate (gerçek ayarlar)", ["uv", "run", "python", "manage.py", "migrate", "-v0"]),
        ("smoke (her dil)", ["uv", "run", "python", "manage.py", "shell", "-c", SMOKE]),
    ]:
        ok, out = run(cmd, target, real_env)
        results.append((label, ok, out))
        if not ok:
            break
    return results


SMOKE = """
from django.conf import settings
from django.test import Client
from django.urls import reverse
from django.utils import translation

client = Client(HTTP_HOST="localhost")
for code, _name in settings.LANGUAGES:
    with translation.override(code):
        url = reverse("pages:about")
    response = client.get(url)
    assert response.status_code == 200, (url, response.status_code)
    assert f'<html lang="{code}"' in response.content.decode(), url
    print(code, url)
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", choices=sorted(COMBOS), help="yalnızca bu kombinasyon(lar)")
    parser.add_argument("--keep", action="store_true", help="üretilen projeleri silme")
    parser.add_argument("--css", action="store_true", help="Tailwind derlemesini de dene (ağ gerekir)")
    args = parser.parse_args()

    names = args.only or list(COMBOS)
    workdir = Path(tempfile.mkdtemp(prefix="starterpack-matrix-"))
    failed = []
    for name in names:
        started = time.monotonic()
        results = check_combo(name, COMBOS[name], workdir, css=args.css)
        passed = all(ok for _, ok, _ in results)
        summary = " | ".join(f"{label}: {'ok' if ok else 'HATA'}" for label, ok, _ in results)
        db = "postgres" if COMBOS[name].get("database") == "postgres" and os.environ.get("TEST_DATABASE_URL") else "sqlite"
        print(f"[{'OK ' if passed else 'HATA'}] {name:16} ({db}, {time.monotonic() - started:5.1f} sn) {summary}")
        if not passed:
            failed.append(name)
            print(results[-1][2])

    if args.keep:
        print(f"Projeler: {workdir}")
    else:
        shutil.rmtree(workdir, ignore_errors=True)
    print(f"\n{len(names) - len(failed)}/{len(names)} kombinasyon başarılı")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
