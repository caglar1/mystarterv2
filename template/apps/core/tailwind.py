"""Tailwind CSS standalone CLI: sabit sürüm + SHA-256 doğrulaması (Node.js gerekmez).

Sürüm yükseltmek için: TAILWIND_VERSION'ı değiştirin ve CHECKSUMS'u
https://github.com/tailwindlabs/tailwindcss/releases/download/v<sürüm>/sha256sums.txt
dosyasındaki değerlerle güncelleyin.
"""

import hashlib
import os
import platform
import stat
import urllib.request
from pathlib import Path

from django.conf import settings

TAILWIND_VERSION = "4.3.3"
CHECKSUMS = {
    "tailwindcss-linux-arm64": "55fd0b241214eff3de1e8ee4f22796662f2d2e7a49bcfca7477cfd0bac398195",
    "tailwindcss-linux-arm64-musl": "71ea4be79c9de9827545682df3e040053fb535d37c71ed2cfdedf9385a0868e0",
    "tailwindcss-linux-x64": "dc61b3ac6b8c9ca874c0cc4c57b2409791a64c5540404ca5f5367360babc313a",
    "tailwindcss-linux-x64-musl": "a04d34ceacc8f52cbe8920ad846cdeb61d3d0021dba32db0d1f77c9d9fad7a6c",
    "tailwindcss-macos-arm64": "cdf646702987a743464dff4d9c60fd4480d1c1e73dd819a9a67f1078815dce9d",
    "tailwindcss-macos-x64": "7922e0953f2110c05976e3bf58f14e643d90427575e766b7d433f5f80cbee7e1",
    "tailwindcss-windows-x64.exe": "e0e260ce048014e9268f6237ff18f8ccf02cef521cbd0ae04e82c2cdf7aa3955",
}


class TailwindError(RuntimeError):
    pass


def asset_name() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
    if system == "darwin":
        return f"tailwindcss-macos-{arch}"
    if system == "windows":
        return "tailwindcss-windows-x64.exe"
    if system == "linux":
        musl = os.path.exists("/etc/alpine-release")
        return f"tailwindcss-linux-{arch}" + ("-musl" if musl else "")
    raise TailwindError(f"Desteklenmeyen platform: {system}/{machine}")


def binary_path() -> Path:
    return Path(settings.BASE_DIR) / ".bin" / f"{asset_name()}-{TAILWIND_VERSION}"


def install(force: bool = False) -> Path:
    path = binary_path()
    if path.exists() and not force:
        return path
    name = asset_name()
    url = f"https://github.com/tailwindlabs/tailwindcss/releases/download/v{TAILWIND_VERSION}/{name}"
    with urllib.request.urlopen(url, timeout=120) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != CHECKSUMS[name]:
        raise TailwindError(f"SHA-256 uyuşmuyor: {name} ({digest})")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def command(*, watch: bool = False, minify: bool = True) -> list[str]:
    args = [str(install()), "-i", str(settings.TAILWIND_INPUT), "-o", str(settings.TAILWIND_OUTPUT)]
    if watch:
        args.append("--watch=always")
    if minify:
        args.append("--minify")
    return args
