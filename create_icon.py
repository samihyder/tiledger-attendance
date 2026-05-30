"""
Generate TiLedger Attendance icon — all sizes for Windows .ico + macOS .icns.
Creates assets/icon.ico, assets/icon.png, assets/splash.png

Run once:  python create_icon.py
Requires:  pip install Pillow
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

ASSETS = os.path.join(os.path.dirname(__file__), 'assets')
os.makedirs(ASSETS, exist_ok=True)

# ── Brand colours ─────────────────────────────────────────────────────────────
BG_DARK   = (13,  27,  42)     # deep navy
BG_MID    = (17,  40,  65)     # slightly lighter
ACCENT    = (13, 110, 253)     # Bootstrap primary blue  #0d6efd
ACCENT2   = (102, 178, 255)    # lighter blue highlight
WHITE     = (255, 255, 255)
SILVER    = (200, 215, 230)


def draw_fingerprint(draw: ImageDraw.Draw, cx: int, cy: int,
                     radius: int, color: tuple, line_width: int,
                     num_ridges: int = 9):
    """
    Draw a fingerprint-style pattern: concentric elliptic arcs,
    slightly offset and broken to simulate skin ridges.
    """
    for i in range(num_ridges):
        t      = i / num_ridges             # 0 → 1
        r      = int(radius * (0.12 + 0.88 * t))
        rx     = r
        ry     = int(r * 0.72)              # slightly taller than wide
        ox     = int(3 * math.sin(t * math.pi))   # lateral drift
        oy     = -int(r * 0.08)             # upward drift (core)
        x0, y0 = cx + ox - rx, cy + oy - ry
        x1, y1 = cx + ox + rx, cy + oy + ry

        # Alpha fades: core ridges brighter, outer ones softer
        alpha  = int(255 * (0.35 + 0.65 * (1 - t)))
        fill   = (*color[:3], alpha) if len(color) == 4 else color

        # Draw arc segments with small gaps (natural fingerprint break)
        for arc_start, arc_end in [(20, 160), (200, 340)]:
            draw.arc([x0, y0, x1, y1], arc_start, arc_end,
                     fill=fill, width=max(1, line_width - (i // 3)))


def make_icon(size: int) -> Image.Image:
    """Render the full TiLedger Attendance icon at given pixel size."""
    img  = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, 'RGBA')

    pad  = max(2, size // 32)
    r    = size // 8                        # corner radius

    # ── Rounded rectangle background ──────────────────────────────────────
    draw.rounded_rectangle([pad, pad, size - pad, size - pad],
                           radius=r, fill=(*BG_DARK, 255))

    # ── Fingerprint ────────────────────────────────────────────────────────
    cx     = size // 2
    cy     = int(size * 0.42)
    fpr    = int(size * 0.32)
    lw     = max(1, size // 52)
    ridges = max(5, size // 28)

    # Subtle inner glow only (small, tight)
    glow_r = int(fpr * 0.55)
    for g in range(4, 0, -1):
        ga = int(22 * g)
        draw.ellipse(
            [cx - glow_r * g // 4, cy - glow_r * g // 4,
             cx + glow_r * g // 4, cy + glow_r * g // 4],
            fill=(*ACCENT, ga)
        )

    draw_fingerprint(draw, cx, cy, fpr, (*ACCENT2, 240), lw, ridges)

    # ── "TiLedger" text ───────────────────────────────────────────────────
    if size >= 64:
        font_size     = max(10, size // 9)
        font_sub_size = max(10, font_size // 2)
        try:
            for font_name in [
                '/System/Library/Fonts/Helvetica.ttc',
                '/System/Library/Fonts/SFNSDisplay.ttf',
                'C:/Windows/Fonts/segoeui.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            ]:
                if os.path.exists(font_name):
                    font      = ImageFont.truetype(font_name, font_size)
                    font_sub  = ImageFont.truetype(font_name, font_sub_size)
                    break
            else:
                raise OSError
        except (OSError, IOError):
            font     = ImageFont.load_default()
            font_sub = font

        # "TiLedger" main label
        text = 'TiLedger'
        bbox = draw.textbbox((0, 0), text, font=font)
        tw   = bbox[2] - bbox[0]
        ty   = int(size * 0.79)
        draw.text(((size - tw) // 2, ty), text, fill=WHITE, font=font)

        if size >= 128:
            sub   = 'Attendance'
            sbbox = draw.textbbox((0, 0), sub, font=font_sub)
            sw    = sbbox[2] - sbbox[0]
            sy    = ty + font_size + max(1, size // 64)
            draw.text(((size - sw) // 2, sy), sub, fill=(*SILVER, 200), font=font_sub)

    # ── Accent line under fingerprint ─────────────────────────────────────
    if size >= 48:
        lx0 = int(size * 0.30)
        lx1 = int(size * 0.70)
        ly  = int(size * 0.74)
        lh  = max(1, size // 96)
        draw.rounded_rectangle([lx0, ly, lx1, ly + lh],
                               radius=lh, fill=(*ACCENT, 200))

    return img


def build_ico():
    sizes  = [16, 24, 32, 48, 64, 128, 256]
    images = [make_icon(s) for s in sizes]

    ico_path = os.path.join(ASSETS, 'icon.ico')
    images[-1].save(ico_path, format='ICO',
                    sizes=[(s, s) for s in sizes],
                    append_images=images[:-1])
    print(f'[OK] icon.ico saved  ({len(images)} sizes: {sizes})')

    png_path = os.path.join(ASSETS, 'icon.png')
    images[-1].save(png_path, format='PNG')
    print(f'[OK] icon.png saved  (256×256)')

    return ico_path


def build_splash():
    """1280×720 splash / loading screen shown while Flask starts."""
    w, h = 1280, 720
    img  = Image.new('RGBA', (w, h), (*BG_DARK, 255))
    draw = ImageDraw.Draw(img, 'RGBA')

    # Background gradient bands
    for y in range(h):
        t = y / h
        r = int(BG_DARK[0] + (BG_MID[0] - BG_DARK[0]) * t * 0.5)
        g = int(BG_DARK[1] + (BG_MID[1] - BG_DARK[1]) * t * 0.5)
        b = int(BG_DARK[2] + (BG_MID[2] - BG_DARK[2]) * t * 0.5)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))

    cx, cy = w // 2, int(h * 0.38)

    # Glow
    for g in range(10, 0, -1):
        ga = int(12 * g)
        draw.ellipse([cx - g*18, cy - g*18, cx + g*18, cy + g*18],
                     fill=(*ACCENT, ga))

    draw_fingerprint(draw, cx, cy, 130, (*ACCENT2, 230), 3, 12)

    # Text
    try:
        for fn in ['/System/Library/Fonts/Helvetica.ttc',
                   'C:/Windows/Fonts/segoeui.ttf',
                   '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
            if os.path.exists(fn):
                f_big = ImageFont.truetype(fn, 54)
                f_med = ImageFont.truetype(fn, 28)
                f_sml = ImageFont.truetype(fn, 18)
                break
        else:
            raise OSError
    except (OSError, IOError):
        f_big = f_med = f_sml = ImageFont.load_default()

    # Title
    title  = 'TiLedger Attendance'
    tb     = draw.textbbox((0, 0), title, font=f_big)
    draw.text(((w - (tb[2]-tb[0])) // 2, int(h * 0.60)), title, fill=WHITE, font=f_big)

    # Subtitle
    sub    = 'Biometric · Face · Manual'
    sb     = draw.textbbox((0, 0), sub, font=f_med)
    draw.text(((w - (sb[2]-sb[0])) // 2, int(h * 0.72)), sub,
              fill=(*SILVER, 200), font=f_med)

    # Accent bar
    draw.rounded_rectangle([w//2 - 120, int(h*0.695), w//2 + 120, int(h*0.698)],
                           radius=2, fill=(*ACCENT, 220))

    # Loading line
    msg    = 'Starting…'
    mb     = draw.textbbox((0, 0), msg, font=f_sml)
    draw.text(((w - (mb[2]-mb[0])) // 2, int(h * 0.88)), msg,
              fill=(*SILVER, 120), font=f_sml)

    splash = os.path.join(ASSETS, 'splash.png')
    img.save(splash, 'PNG')
    print(f'[OK] splash.png saved  (1280×720)')
    return splash


if __name__ == '__main__':
    print('Generating TiLedger Attendance icons…')
    build_ico()
    build_splash()
    print('\nDone. Assets saved to:', ASSETS)
    print('Replace assets/icon.ico with your official TiLedger .ico if available.')
