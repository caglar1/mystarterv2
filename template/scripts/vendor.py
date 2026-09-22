"""Vendor (3. parti) JS/CSS dosyalarını sabit sürümlerle indirir ve SHA-256 ile doğrular.

Her uygulama kendi `vendor.json` dosyasını taşır (ör. apps/core/vendor.json), böylece
bir modül silindiğinde onun vendor dosyaları da onunla birlikte gider.

Kullanım:
    python scripts/vendor.py check    # dosyalar mevcut ve hash'leri doğru mu?
    python scripts/vendor.py sync     # eksik/bozuk dosyaları indir, hash'i doğrula
    python scripts/vendor.py lock     # (sürüm yükseltme sonrası) dosyaları indir, yeni hash'leri yaz

Yalnızca standart kütüphane kullanır.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFESTS = sorted([*ROOT.glob("apps/*/vendor.json"), *ROOT.glob("assets/vendor.json")])


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download(url: str) -> bytes:
    if not url.startswith("https://"):
        raise ValueError(f"Yalnızca https adresleri indirilebilir: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "starterpack-vendor/2"})  # noqa: S310
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        return response.read()


def entries():
    for manifest in MANIFESTS:
        data = json.loads(manifest.read_text())
        for entry in data["files"]:
            yield manifest, data, entry


def main(command: str) -> int:
    if command not in {"check", "sync", "lock"}:
        print(__doc__)
        return 2

    failures = 0
    changed_manifests: dict[Path, dict] = {}
    for manifest, data, entry in entries():
        dest = ROOT / entry["dest"]
        current = dest.read_bytes() if dest.exists() else None
        ok = current is not None and sha256(current) == entry.get("sha256")

        if command == "check":
            status = "ok" if ok else ("eksik" if current is None else "HASH UYUŞMUYOR")
            print(f"[{status}] {entry['name']} {entry['version']} -> {entry['dest']}")
            failures += not ok
            continue

        if ok and command == "sync":
            continue

        payload = download(entry["url"])
        digest = sha256(payload)
        if command == "sync" and digest != entry["sha256"]:
            print(f"[HATA] {entry['name']}: hash manifest ile uyuşmuyor ({entry['url']})")
            failures += 1
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)
        if command == "lock":
            entry["sha256"] = digest
            changed_manifests[manifest] = data
        print(f"[indirildi] {entry['name']} {entry['version']} -> {entry['dest']}")

    for manifest, data in changed_manifests.items():
        manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
