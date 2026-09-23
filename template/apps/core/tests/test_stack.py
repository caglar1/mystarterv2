"""Onaylı stack denetimi (AGENTS.md → "Stack genişletme onayı").

pyproject.toml, vendor.json dosyaları, Dockerfile, compose.yaml ve GitHub Actions'taki her bağımlılık
approved-stack.toml'da olmalı. Böylece yapay zeka ajanı hangi araçla çalışırsa çalışsın (Claude Code,
Cursor, Codex...) kullanıcıya sormadan stack'i genişletirse `make check` ve CI kırılır.
"""

import json
import re
import tomllib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
HINT = (
    "\n\nBunlar approved-stack.toml'da yok. Kullanıcıya AGENTS.md → 'Stack genişletme onayı' mesajıyla sor; "
    "approved-stack.toml'u yalnızca açık onaydan sonra güncelle, bu testi değiştirme."
)

FROM_RE = re.compile(
    r"^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+(\S+))?", re.IGNORECASE | re.MULTILINE
)
COPY_FROM_RE = re.compile(r"\bCOPY\s+[^\n]*--from=(\S+)", re.IGNORECASE)
IMAGE_RE = re.compile(r"^\s*(?:-\s*)?image:\s*[\"']?([^\s\"'#]+)", re.MULTILINE)
USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*[\"']?([^@\s\"'#]+)", re.MULTILINE)


def _toml(name: str) -> dict:
    return tomllib.loads((BASE_DIR / name).read_text(encoding="utf-8"))


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _package(requirement: str) -> str:
    """'django-anymail[resend]>=15.2' -> 'django-anymail' (PEP 503 adı)."""
    return _normalize(re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", requirement.strip()).group(0))


def _image(reference: str) -> str:
    """'ghcr.io/astral-sh/uv:0.12.17' -> 'ghcr.io/astral-sh/uv', 'python:${V}-slim' -> 'python'."""
    name = reference.split("@", 1)[0]
    head, _, tail = name.rpartition(":")
    return head if head and "/" not in tail else name


def _workflows() -> list[Path]:
    return sorted([*BASE_DIR.glob(".github/workflows/*.yml"), *BASE_DIR.glob(".github/workflows/*.yaml")])


def test_python_dependencies_are_approved():
    pyproject = _toml("pyproject.toml")
    groups = _toml("approved-stack.toml")["python"].values()
    approved = {_normalize(name) for names in groups for name in names}
    sections = {"dependencies": pyproject["project"].get("dependencies", [])}
    for extra, requirements in pyproject["project"].get("optional-dependencies", {}).items():
        sections[f"optional-dependencies.{extra}"] = requirements
    for group, requirements in pyproject.get("dependency-groups", {}).items():
        sections[f"dependency-groups.{group}"] = requirements
    unapproved = [
        f"pyproject.toml [{section}]: {requirement}"
        for section, requirements in sections.items()
        for requirement in requirements
        if isinstance(requirement, str) and _package(requirement) not in approved
    ]
    assert not unapproved, "Onaysız Python paketi:\n" + "\n".join(unapproved) + HINT


def test_vendor_files_are_approved():
    approved = _toml("approved-stack.toml")["vendor"]
    unapproved = []
    for manifest in sorted([*BASE_DIR.glob("apps/*/vendor.json"), *BASE_DIR.glob("assets/vendor.json")]):
        for entry in json.loads(manifest.read_text(encoding="utf-8"))["files"]:
            name, version = entry["name"], str(entry["version"])
            major = version.lstrip("v").split(".")[0]
            where = f"{manifest.relative_to(BASE_DIR)}: {name} {version}"
            if name not in approved:
                unapproved.append(f"{where} (listede yok)")
            elif str(approved[name]) != major:
                unapproved.append(f"{where} (onaylı majör sürüm: {approved[name]})")
    assert not unapproved, "Onaysız vendor dosyası:\n" + "\n".join(unapproved) + HINT


def test_docker_images_are_approved():
    approved = set(_toml("approved-stack.toml")["docker"]["images"])
    own_image = _toml("pyproject.toml")["project"]["name"]  # compose'ta derlenen projenin kendi imajı
    found: dict[str, str] = {}
    dockerfile = BASE_DIR / "Dockerfile"
    if dockerfile.exists():
        text = dockerfile.read_text(encoding="utf-8")
        stages = {match.group(2).lower() for match in FROM_RE.finditer(text) if match.group(2)}
        for reference in [match.group(1) for match in FROM_RE.finditer(text)] + COPY_FROM_RE.findall(text):
            if reference.lower() not in stages:
                found.setdefault(_image(reference), "Dockerfile")
    for path in [BASE_DIR / "compose.yaml", *_workflows()]:
        if path.exists():
            for reference in IMAGE_RE.findall(path.read_text(encoding="utf-8")):
                if _image(reference) != own_image:
                    found.setdefault(_image(reference), str(path.relative_to(BASE_DIR)))
    unapproved = sorted(f"{source}: {image}" for image, source in found.items() if image not in approved)
    assert not unapproved, "Onaysız Docker imajı:\n" + "\n".join(unapproved) + HINT


def test_github_actions_are_approved():
    approved = set(_toml("approved-stack.toml")["ci"]["actions"])
    unapproved = sorted(
        {
            f"{path.relative_to(BASE_DIR)}: {action}"
            for path in _workflows()
            for action in USES_RE.findall(path.read_text(encoding="utf-8"))
            if not action.startswith("./") and action not in approved
        }
    )
    assert not unapproved, "Onaysız GitHub Actions eylemi:\n" + "\n".join(unapproved) + HINT


def test_parsers_see_what_they_should():
    """Denetim sessizce boş dönmesin: bilinen bağımlılıkları gerçekten buluyor mu?"""
    assert _package("django-anymail[resend]>=15.2") == "django-anymail"
    assert _package("Django_HTMX>=1.29") == "django-htmx"
    assert _image("python:${PYTHON_VERSION}-slim-trixie") == "python"
    assert _image("ghcr.io/astral-sh/uv:0.12.17") == "ghcr.io/astral-sh/uv"
    assert _image("localhost:5000/app") == "localhost:5000/app"
    dockerfile = (BASE_DIR / "Dockerfile").read_text(encoding="utf-8")
    assert "python" in {_image(match.group(1)) for match in FROM_RE.finditer(dockerfile)}
    assert "ghcr.io/astral-sh/uv" in {_image(reference) for reference in COPY_FROM_RE.findall(dockerfile)}
    workflow_actions = {action for path in _workflows() for action in USES_RE.findall(path.read_text())}
    assert "actions/checkout" in workflow_actions
