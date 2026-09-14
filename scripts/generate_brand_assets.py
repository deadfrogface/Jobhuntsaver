#!/usr/bin/env python3
"""Deterministic brand asset generator (Pillow only — no network / AI).

Produces:
  assets/brand/icons/icon-{16,24,32,48,64,128,256}.png
  assets/brand/app.ico
  assets/brand/logo.png
  assets/brand/social-preview.png
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "brand"

# Match desktop.branding colors
PRIMARY = (31, 107, 92, 255)  # #1F6B5C
PRIMARY_DARK = (20, 61, 72, 255)  # #143D48
ACCENT = (196, 92, 38, 255)  # #C45C26
MARK = (244, 247, 250, 255)
SLATE = (28, 36, 48, 255)
LIGHT_BG = (240, 244, 247, 255)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ):
        path = Path(name)
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _draw_mark(size: int) -> Image.Image:
    """Abstract anchor + horizon mark (no letters required at tiny sizes)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = max(1, size // 16)
    # Rounded square background
    draw.rounded_rectangle(
        [pad, pad, size - pad - 1, size - pad - 1],
        radius=max(2, size // 6),
        fill=PRIMARY_DARK,
    )
    # Horizon band
    mid_y = int(size * 0.58)
    band_h = max(2, size // 10)
    draw.rounded_rectangle(
        [pad * 3, mid_y, size - pad * 3 - 1, mid_y + band_h],
        radius=band_h // 2,
        fill=PRIMARY,
    )
    # Anchor stem
    cx = size // 2
    stem_w = max(2, size // 12)
    top = pad * 3 + size // 10
    draw.rectangle([cx - stem_w // 2, top, cx + stem_w // 2, mid_y + band_h], fill=MARK)
    # Anchor ring
    ring_r = max(3, size // 7)
    draw.ellipse(
        [cx - ring_r, top - ring_r // 3, cx + ring_r, top + ring_r * 2 - ring_r // 3],
        outline=MARK,
        width=max(1, size // 16),
    )
    # Flukes
    fluke = max(4, size // 5)
    y = mid_y + band_h // 2
    draw.polygon(
        [(cx, y), (cx - fluke, y + fluke // 2), (cx - stem_w, y)],
        fill=ACCENT,
    )
    draw.polygon(
        [(cx, y), (cx + fluke, y + fluke // 2), (cx + stem_w, y)],
        fill=ACCENT,
    )
    return img


def _logo(width: int = 640, height: int = 160) -> Image.Image:
    img = Image.new("RGBA", (width, height), LIGHT_BG)
    mark = _draw_mark(height - 24)
    img.paste(mark, (20, 12), mark)
    draw = ImageDraw.Draw(img)
    title = _font(max(28, height // 3))
    sub = _font(max(14, height // 8))
    draw.text((height + 12, height // 5), "Stellenanker", fill=SLATE, font=title)
    draw.text(
        (height + 14, height // 5 + height // 3 + 4),
        "Lokale Jobsuche für Deutschland",
        fill=PRIMARY_DARK,
        font=sub,
    )
    return img


def _social(width: int = 1280, height: int = 640) -> Image.Image:
    img = Image.new("RGB", (width, height), LIGHT_BG)
    draw = ImageDraw.Draw(img)
    # Soft diagonal atmosphere
    for y in range(height):
        t = y / max(1, height - 1)
        r = int(240 * (1 - t) + 20 * t)
        g = int(244 * (1 - t) + 61 * t)
        b = int(247 * (1 - t) + 72 * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    # Accent curve
    for i in range(40):
        x0 = int(width * 0.55 + math.sin(i / 6) * 20)
        draw.ellipse(
            [x0 + i * 8, height // 3 + i * 4, width + 80, height + 40],
            outline=(31, 107, 92, 40),
            width=2,
        )
    mark = _draw_mark(180)
    img.paste(mark, (80, height // 2 - 90), mark)
    title = _font(72)
    sub = _font(28)
    body = _font(22)
    draw.text((300, height // 2 - 90), "Stellenanker", fill=MARK, font=title)
    draw.text(
        (304, height // 2 - 10),
        "Lokale Jobsuche & Bewerbungen für Deutschland",
        fill=MARK,
        font=sub,
    )
    draw.text(
        (304, height // 2 + 40),
        "Kein Cloud-Konto · Dry-Run standard · Daten bleiben auf dem PC",
        fill=(200, 220, 220),
        font=body,
    )
    return img


def _write_ico(pngs: dict[int, Image.Image], path: Path) -> None:
    # Pillow ICO: pass largest as base and sizes list
    sizes = sorted(pngs)
    base = pngs[sizes[-1]].convert("RGBA")
    base.save(
        path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=[pngs[s].convert("RGBA") for s in sizes[:-1]],
    )


def main() -> None:
    icons_dir = OUT / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    pngs: dict[int, Image.Image] = {}
    for size in (16, 24, 32, 48, 64, 128, 256):
        mark = _draw_mark(size)
        target = icons_dir / f"icon-{size}.png"
        mark.save(target, format="PNG", optimize=True)
        pngs[size] = mark
        print(f"wrote {target.relative_to(ROOT)}")
    ico = OUT / "app.ico"
    _write_ico(pngs, ico)
    print(f"wrote {ico.relative_to(ROOT)}")
    logo = _logo()
    logo_path = OUT / "logo.png"
    logo.save(logo_path, format="PNG", optimize=True)
    print(f"wrote {logo_path.relative_to(ROOT)}")
    social = _social()
    social_path = OUT / "social-preview.png"
    social.save(social_path, format="PNG", optimize=True)
    print(f"wrote {social_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
