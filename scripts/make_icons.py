"""Şablon geliştirme aracı: PWA/favicon ikonlarını ve OG görselini üretir.

Üretilen dosyalar template/apps/core/static/core/icons/ altına yazılır ve repoya eklenir.
Kendi logonuzla değiştirmek için bu dosyaları doğrudan üzerine yazmanız yeterli.

    uv run --with pillow python scripts/make_icons.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "template" / "apps" / "core" / "static" / "core" / "icons"
PRIMARY = (30, 64, 175)
WHITE = (255, 255, 255)


def sparkle(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float) -> None:
    w = r * 0.28
    points = [(cx, cy - r), (cx + w, cy - w), (cx + r, cy), (cx + w, cy + w),
              (cx, cy + r), (cx - w, cy + w), (cx - r, cy), (cx - w, cy - w)]
    draw.polygon(points, fill=WHITE)


def icon(size: int, *, maskable: bool = False) -> Image.Image:
    scale = 4
    big = size * scale
    image = Image.new("RGB" if maskable else "RGBA", (big, big), PRIMARY if maskable else (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if not maskable:
        draw.rounded_rectangle([0, 0, big - 1, big - 1], radius=big * 0.22, fill=PRIMARY)
    radius = big * (0.26 if maskable else 0.34)
    sparkle(draw, big / 2, big / 2, radius)
    sparkle(draw, big * 0.74, big * 0.27, radius * 0.3)
    return image.resize((size, size), Image.LANCZOS)


def og_cover() -> Image.Image:
    image = Image.new("RGB", (1200, 630), PRIMARY)
    draw = ImageDraw.Draw(image)
    sparkle(draw, 600, 315, 150)
    sparkle(draw, 760, 190, 45)
    return image


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    icon(192).save(OUT / "icon-192.png", optimize=True)
    icon(512).save(OUT / "icon-512.png", optimize=True)
    icon(512, maskable=True).save(OUT / "icon-maskable-512.png", optimize=True)
    icon(180, maskable=True).save(OUT / "apple-touch-icon.png", optimize=True)
    og_cover().save(OUT / "og-cover.png", optimize=True)
    (OUT / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="14" fill="#1e40af"/>'
        '<path fill="#fff" d="M32 10l6.1 15.9L54 32l-15.9 6.1L32 54l-6.1-15.9L10 32l15.9-6.1z"/>'
        '<path fill="#fff" d="M47 11l1.8 4.2L53 17l-4.2 1.8L47 23l-1.8-4.2L41 17l4.2-1.8z"/></svg>\n'
    )
    print(f"İkonlar üretildi: {OUT}")


if __name__ == "__main__":
    main()
