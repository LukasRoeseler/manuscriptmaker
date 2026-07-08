"""Rasterize the CODECHECK badge (same design as docs/assets/badges/codecheck.svg)
to a crisp high-resolution PNG for consumers that can't embed SVG (pdflatex, OJS).

Usage:  python engine/scripts/make_codecheck_badge.py [size]
Writes: _extensions/r2/resources/badges/codecheck.png
        themes/r2/assets/badges/codecheck.png
        docs/assets/badges/codecheck.png
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
GREEN, DARK, WHITE = (2, 138, 61, 255), (2, 107, 48, 255), (255, 255, 255, 255)


def rot(points, cx, cy, deg):
    a = math.radians(deg)
    return [(cx + (x - cx) * math.cos(a) - (y - cy) * math.sin(a),
             cy + (x - cx) * math.sin(a) + (y - cy) * math.cos(a)) for x, y in points]


def build(scale: int = 8) -> Image.Image:
    # Design space 120 x 148 (matches the SVG viewBox), supersampled by `scale`.
    W, H = 120 * scale, 148 * scale
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = scale
    cx, cy = 60 * s, 60 * s

    # ribbon tails
    d.polygon([(40*s, 86*s), (40*s, 140*s), (60*s, 124*s), (80*s, 140*s), (80*s, 86*s)], fill=DARK)
    # 12-point rosette: three squares rotated 0/30/60 degrees
    sq = [(24*s, 24*s), (96*s, 24*s), (96*s, 96*s), (24*s, 96*s)]
    for ang in (0, 30, 60):
        d.polygon(rot(sq, cx, cy, ang), fill=GREEN)
    # inner rings
    d.ellipse([cx-34*s, cy-34*s, cx+34*s, cy+34*s], fill=WHITE)
    d.ellipse([cx-30*s, cy-30*s, cx+30*s, cy+30*s], fill=GREEN)

    # curved label "CODECHECK" along the top inner arc
    try:
        font = ImageFont.truetype("arialbd.ttf", int(8.5*s))
    except OSError:
        font = ImageFont.load_default(size=int(8.5*s))
    text, radius = "CODECHECK", 23*s
    arc = 130.0                                     # degrees of arc spanned
    for i, ch in enumerate(text):
        ang = -90 - arc/2 + arc * (i + 0.5) / len(text)
        x = cx + radius * math.cos(math.radians(ang))
        y = cy + radius * math.sin(math.radians(ang))
        gsz = 20*s                                  # generous canvas: no clip on rotate
        glyph = Image.new("RGBA", (gsz, gsz), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glyph)
        gd.text((gsz//2, gsz//2), ch, font=font, fill=WHITE, anchor="mm")
        glyph = glyph.rotate(-(ang + 90), resample=Image.BICUBIC, expand=False)
        img.alpha_composite(glyph, (int(x - gsz/2), int(y - gsz/2)))

    # check mark (kept below the label arc)
    pts = [(48, 68), (56, 76), (72, 58)]
    d.line([(x*s, y*s) for x, y in pts], fill=WHITE, width=int(6*s), joint="curve")
    for px, py in pts:                              # round caps
        r = 3*s
        d.ellipse([px*s-r, py*s-r, px*s+r, py*s+r], fill=WHITE)

    target = int(sys.argv[1]) if len(sys.argv) > 1 else 480
    return img.resize((target, int(target * H / W)), Image.LANCZOS)


if __name__ == "__main__":
    out = build()
    for rel in ("_extensions/r2/resources/badges/codecheck.png",
                "themes/r2/assets/badges/codecheck.png",
                "docs/assets/badges/codecheck.png"):
        p = REPO / rel
        out.save(p)
        print(f"wrote {p} ({p.stat().st_size//1024} KB, {out.size[0]}x{out.size[1]})")
