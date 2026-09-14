#!/usr/bin/env python3
"""Deterministic brand asset pipeline from locked master PNGs (Pillow only).

Does NOT redraw or regenerate the octopus artwork. Masters are copied into
``assets/brand/`` and this script only resizes / packs derivatives:

  assets/brand/karrierekrake-app-icon-master.png  (MASTER B — square icon)
  assets/brand/karrierekrake-logo-master.png      (MASTER A — large artwork)

Produces:
  assets/brand/icons/icon-{1024,512,256,128,64,48,32,24,16}.png
  assets/brand/app.ico          (multi-size)
  assets/brand/logo.png         (MASTER A for README / About / onboarding)
  assets/brand/social-preview.png
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "brand"
ICON_MASTER = OUT / "karrierekrake-app-icon-master.png"
LOGO_MASTER = OUT / "karrierekrake-logo-master.png"

# Canonical palette (must match desktop.branding)
NAVY = (19, 34, 56, 255)  # #132238
TEAL = (24, 169, 153, 255)  # #18A999
MARK = (244, 247, 250, 255)
LIGHT_BG = (238, 242, 245, 255)  # #EEF2F5

ICON_SIZES = (1024, 512, 256, 128, 64, 48, 32, 24, 16)
ICO_SIZES = (256, 128, 64, 48, 32, 24, 16)


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


def _resize_square(src: Image.Image, size: int) -> Image.Image:
    """High-quality downscale; keep RGBA."""
    img = src.convert("RGBA")
    if img.size == (size, size):
        return img.copy()
    # For tiny sizes, slightly sharpen readability by centering crop if needed
    if img.width != img.height:
        side = min(img.width, img.height)
        left = (img.width - side) // 2
        top = (img.height - side) // 2
        img = img.crop((left, top, left + side, top + side))
    return img.resize((size, size), Image.Resampling.LANCZOS)


def _write_ico(pngs: dict[int, Image.Image], path: Path) -> None:
    sizes = [s for s in ICO_SIZES if s in pngs]
    if not sizes:
        raise SystemExit("no ICO sizes available")
    # Pillow ICO: largest as base
    base_size = max(sizes)
    base = pngs[base_size].convert("RGBA")
    append = [pngs[s].convert("RGBA") for s in sizes if s != base_size]
    base.save(
        path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=append,
    )


def _logo_from_master(master: Image.Image, max_width: int = 960) -> Image.Image:
    img = master.convert("RGBA")
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize(
            (max_width, max(1, int(img.height * ratio))),
            Image.Resampling.LANCZOS,
        )
    return img


def _social_from_master(master: Image.Image, width: int = 1280, height: int = 640) -> Image.Image:
    """Compose MASTER A onto a navy → soft gradient social card."""
    canvas = Image.new("RGB", (width, height), NAVY[:3])
    draw = ImageDraw.Draw(canvas)
    for y in range(height):
        t = y / max(1, height - 1)
        r = int(NAVY[0] * (1 - t) + 14 * t)
        g = int(NAVY[1] * (1 - t) + 28 * t)
        b = int(NAVY[2] * (1 - t) + 48 * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    art = master.convert("RGBA")
    # Fit artwork into left-ish area leaving room for wordmark on the right
    max_art_w = int(width * 0.52)
    max_art_h = int(height * 0.88)
    ratio = min(max_art_w / art.width, max_art_h / art.height)
    art = art.resize(
        (max(1, int(art.width * ratio)), max(1, int(art.height * ratio))),
        Image.Resampling.LANCZOS,
    )
    ax = 36
    ay = (height - art.height) // 2
    canvas.paste(art, (ax, ay), art)

    # Wordmark (MASTER A already includes text; still add short EN/DE cue on right
    # only when artwork already has brand — keep right panel sparse)
    title = _font(42)
    sub = _font(18)
    tx = int(width * 0.58)
    ty = height // 2 - 40
    draw.text((tx, ty), "Karrierekrake", fill=MARK[:3], font=title)
    # Split wordmark colors: Karriere navy-light, krake teal overlay via second draw
    # Simpler: teal underline + tagline
    draw.rectangle([tx, ty + 52, tx + 160, ty + 56], fill=TEAL[:3])
    draw.text(
        (tx, ty + 68),
        "FINDE. BEWIRB. BEHALTE DEN ÜBERBLICK.",
        fill=(200, 220, 220),
        font=sub,
    )
    draw.text(
        (tx, ty + 100),
        "Lokal · Windows · Dry-Run standard",
        fill=(160, 185, 195),
        font=sub,
    )
    return canvas


def main() -> None:
    if not ICON_MASTER.is_file():
        raise SystemExit(f"missing icon master: {ICON_MASTER}")
    if not LOGO_MASTER.is_file():
        raise SystemExit(f"missing logo master: {LOGO_MASTER}")

    icon_src = Image.open(ICON_MASTER)
    logo_src = Image.open(LOGO_MASTER)

    icons_dir = OUT / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    pngs: dict[int, Image.Image] = {}
    for size in ICON_SIZES:
        mark = _resize_square(icon_src, size)
        target = icons_dir / f"icon-{size}.png"
        mark.save(target, format="PNG", optimize=True)
        pngs[size] = mark
        print(f"wrote {target.relative_to(ROOT)} ({size}x{size})")

    ico = OUT / "app.ico"
    _write_ico(pngs, ico)
    print(f"wrote {ico.relative_to(ROOT)}")

    logo = _logo_from_master(logo_src)
    logo_path = OUT / "logo.png"
    logo.save(logo_path, format="PNG", optimize=True)
    print(f"wrote {logo_path.relative_to(ROOT)} ({logo.width}x{logo.height})")

    social = _social_from_master(logo_src)
    social_path = OUT / "social-preview.png"
    social.save(social_path, format="PNG", optimize=True)
    print(f"wrote {social_path.relative_to(ROOT)}")

    # Tiny-size sanity: ensure 16/24 are not empty / fully transparent
    for s in (16, 24, 32):
        band = pngs[s].get_flattened_data() if hasattr(pngs[s], "get_flattened_data") else list(pngs[s].getdata())
        opaque = sum(1 for p in band if (p[3] if isinstance(p, tuple) else 255) > 32)
        print(f"inspect icon-{s}: opaque_pixels={opaque}/{len(band)}")


if __name__ == "__main__":
    main()
