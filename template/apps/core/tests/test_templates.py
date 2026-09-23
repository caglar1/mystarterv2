"""Sıkı CSP'yi ve Alpine CSP build'ini bozan kalıpları şablon kaynağında yakalar.

Bu hatalar pytest'te görünmez: sayfa 200 döner ama tarayıcı kodu sessizce engeller (yalnızca konsolda
CSP uyarısı çıkar). Yapay zeka ajanları bu kalıpları alışkanlıkla yazdığı için kaynak burada taranır.
Kurallar: AGENTS.md madde 6, 7 ve 11.
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

# (desen, açıklama). Etiket içi desenler `<etiket ...>` sınırını aşmaz.
TEMPLATE_RULES = [
    (
        re.compile(r"<script\b(?![^>]*\b(?:src|nonce)=)(?![^>]*type=\"application/(?:ld\+)?json\")[^>]*>"),
        "nonce'suz satır içi <script>: kodu static/<app>/*.js'e taşı ya da nonce=\"{{ csp_nonce }}\" ekle",
    ),
    (
        re.compile(r"<script\b(?=[^>]*\bsrc=[\"']?(?:https?:)?//)[^>]*>"),
        "CDN'den <script>: dosyayı apps/<app>/vendor.json ile ekle (önce stack onayı)",
    ),
    (
        re.compile(r"<link\b(?=[^>]*\bstylesheet\b)(?=[^>]*\bhref=[\"']?(?:https?:)?//)[^>]*>"),
        "CDN'den stil dosyası: CSP yalnızca kendi alan adından stile izin verir",
    ),
    (re.compile(r"<style\b"), "<style> bloğu: stiller assets/css/app.css'e (Tailwind) yazılır"),
    (re.compile(r"<[a-zA-Z][^>]*\sstyle="), "style= niteliği CSP'de engellenir: Tailwind sınıfı kullan"),
    (re.compile(r"<[a-zA-Z][^>]*\son[a-z]+="), "onclick= gibi satır içi olay: Alpine @olay kullan"),
    (re.compile(r"\bhx-on[:-]"), "hx-on eval gerektirir (htmx allowEval kapalı): Alpine @olay kullan"),
    (re.compile(r"javascript:"), "javascript: adresi CSP'de engellenir"),
    (
        re.compile(r"\bx-data=\"(?![A-Za-z_$][\w$]*\")[^\"]*\""),
        'x-data yalnızca Alpine.data ile kayıtlı bileşen adı alır (x-data="tabs"); başlangıç değeri data-*',
    ),
    (
        re.compile(r"\s(?:x-[\w:.-]+|@[\w:.-]+|:[\w.-]+)=\"[^\"]*(?:=>|`)[^\"]*\""),
        "Alpine CSP build ok fonksiyonu ve template literal çalıştırmaz: mantığı Alpine.data bileşenine taşı",
    ),
]

SCRIPT_RULES = [
    (re.compile(r"\beval\(|\bnew Function\("), "eval / new Function CSP'de engellenir ('unsafe-eval' yok)"),
]


def _violations(paths, rules, root: Path = BASE_DIR) -> list[str]:
    found = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for pattern, message in rules:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                found.append(f"{path.relative_to(root)}:{line}: {message}")
    return found


def _templates() -> list[Path]:
    return sorted([*BASE_DIR.glob("templates/**/*.html"), *BASE_DIR.glob("apps/*/templates/**/*.html")])


def _scripts() -> list[Path]:
    return sorted(path for path in BASE_DIR.glob("apps/*/static/**/*.js") if "vendor" not in path.parts)


def test_templates_follow_csp_rules():
    assert _templates(), "Şablon bulunamadı; BASE_DIR yanlış olabilir"
    violations = _violations(_templates(), TEMPLATE_RULES)
    assert not violations, "CSP kuralına aykırı şablon kodu:\n" + "\n".join(violations)


def test_scripts_do_not_use_eval():
    violations = _violations(_scripts(), SCRIPT_RULES)
    assert not violations, "CSP kuralına aykırı JS:\n" + "\n".join(violations)


def test_rules_catch_common_mistakes(tmp_path):
    """Desenlerin gerçekten yakaladığını sına: her örnek en az bir kurala takılmalı."""
    bad = [
        "<script>alert(1)</script>",
        '<script src="https://cdn.example.com/lib.js"></script>',
        '<link rel="stylesheet" href="https://cdn.example.com/lib.css">',
        "<style>.a { color: red }</style>",
        '<div style="display:none"></div>',
        '<button onclick="go()">x</button>',
        '<button hx-on:click="go()">x</button>',
        '<a href="javascript:void(0)">x</a>',
        '<div x-data="{ open: false }"></div>',
        '<button @click="() => go()">x</button>',
        '<span x-text="`Merhaba ${ad}`"></span>',
    ]
    good = [
        '<script nonce="{{ csp_nonce }}">var a = 1;</script>',
        "<script src=\"{% static 'core/js/app.js' %}\" defer></script>",
        '<div x-data="tabs" data-tab="bir"><button @click="show(\'bir\')">x</button></div>',
        "<button :class=\"is('bir') && 'tab-active'\" x-show=\"is('bir')\">x</button>",
        '<button x-on:click="close" class="btn">x</button>',
    ]
    for index, snippet in enumerate(bad):
        path = tmp_path / f"bad{index}.html"
        path.write_text(snippet)
        assert _violations([path], TEMPLATE_RULES, root=tmp_path), f"yakalanmadı: {snippet}"
    for index, snippet in enumerate(good):
        path = tmp_path / f"good{index}.html"
        path.write_text(snippet)
        assert not _violations([path], TEMPLATE_RULES, root=tmp_path), f"yanlış alarm: {snippet}"
