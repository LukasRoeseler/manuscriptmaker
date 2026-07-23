"""Generate the CODECHECK / computational-reproducibility badge to match the
family of existing R2 badges (opendata/opencode/openmaterial/preregistered):
a flat-color hexagon with a POINTED top and bottom (flat left/right sides),
filled edge-to-edge in its canvas with no padding — confirmed by measuring
the sibling PNGs directly (all taller than wide, bbox == full canvas) —
with a simple white glyph centered: here, a gear, in the CODECHECK purple.

Usage:  python engine/scripts/make_codecheck_badge.py [width]
Writes: _extensions/r2/resources/badges/codecheck.png
        themes/r2/assets/badges/codecheck.png
        docs/assets/badges/codecheck.png
(and matching .svg siblings, written directly as text)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[2]
PURPLE = (124, 58, 158, 255)      # matches the flat, saturated tone of the other badges
WHITE = (255, 255, 255, 255)

# Regular hexagon, pointy-top/bottom: for "radius" R (center to vertex),
# width = R*sqrt(3), height = 2R. Canvas is sized to exactly this box so
# the hexagon fills it edge-to-edge, matching the sibling badges' bbox.
ASPECT = 2 / math.sqrt(3)   # height / width ≈ 1.1547


def hexagon_points(cx, cy, r):
    """Pointy-top/bottom, flat-left/right hexagon (matches the sibling badges:
    all measured taller than wide, filling their canvas edge-to-edge)."""
    return [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
            for a in (270, 330, 30, 90, 150, 210)]   # 270=top, 90=bottom (image y-down)


def build(scale: int = 8, width: int = 142) -> Image.Image:
    height = round(width * ASPECT)
    W, H = width * scale, height * scale
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = W / 2, H / 2
    R = H / 2   # vertex-to-vertex fills the canvas height exactly

    # Hexagon body — sharp corners (matches the subtle, anti-aliased corners
    # of the sibling open-data/open-code/open-materials/preregistered badges;
    # a naive vertex-circle "rounding" trick bulges outward instead of in,
    # so it is intentionally not used here).
    d.polygon(hexagon_points(cx, cy, R), fill=PURPLE)

    # Gear glyph: N teeth radiating from a ring, plus a punched center hole.
    r_outer, r_inner, r_hole = R * 0.44, R * 0.29, R * 0.13
    teeth, tooth_half_deg = 8, 24
    for i in range(teeth):
        ang = 360 / teeth * i
        quad = []
        for a in (-tooth_half_deg / 2, tooth_half_deg / 2):
            th = math.radians(ang + a)
            quad.append((cx + r_outer * math.cos(th), cy + r_outer * math.sin(th)))
        for a in (tooth_half_deg / 2, -tooth_half_deg / 2):
            th = math.radians(ang + a)
            quad.append((cx + r_inner * math.cos(th), cy + r_inner * math.sin(th)))
        d.polygon(quad, fill=WHITE)
    d.ellipse([cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner], fill=WHITE)
    d.ellipse([cx - r_hole, cy - r_hole, cx + r_hole, cy + r_hole], fill=PURPLE)

    return img.resize((width, height), Image.LANCZOS)


SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}" role="img" aria-label="Computational reproducibility badge">
  <!-- Pointy-top/bottom hexagon matching the open-data/open-code/open-materials/preregistered badge family (all taller than wide, filled edge-to-edge), in CODECHECK purple, with a gear glyph for computational reproducibility. -->
  <path d="{hex_path}" fill="#7C3A9E"/>
  <g fill="#ffffff">{teeth}
    <circle cx="{cx}" cy="{cy}" r="{r_inner:.1f}"/>
  </g>
  <circle cx="{cx}" cy="{cy}" r="{r_hole:.1f}" fill="#7C3A9E"/>
</svg>
"""


def hexagon_svg_path(cx, cy, r):
    # Sharp-corner hexagon (matches the sibling badges' subtle, anti-aliased
    # corners — see the PNG builder's comment for why a rounding trick is skipped).
    pts = hexagon_points(cx, cy, r)
    d = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
    d += [f"L {x:.1f} {y:.1f}" for x, y in pts[1:]]
    d.append("Z")
    return " ".join(d)


def build_svg(width: int = 142) -> str:
    height = round(width * ASPECT)
    cx, cy = width / 2, height / 2
    R = height / 2
    r_outer, r_inner, r_hole = R * 0.44, R * 0.29, R * 0.13
    teeth, tooth_half_deg = 8, 24
    teeth_paths = []
    for i in range(teeth):
        ang = 360 / teeth * i
        quad = []
        for a in (-tooth_half_deg / 2, tooth_half_deg / 2):
            th = math.radians(ang + a)
            quad.append((cx + r_outer * math.cos(th), cy + r_outer * math.sin(th)))
        for a in (tooth_half_deg / 2, -tooth_half_deg / 2):
            th = math.radians(ang + a)
            quad.append((cx + r_inner * math.cos(th), cy + r_inner * math.sin(th)))
        pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in quad)
        teeth_paths.append(f'<polygon points="{pts_str}"/>')
    return SVG_TEMPLATE.format(
        vw=width, vh=height, cx=cx, cy=cy,
        hex_path=hexagon_svg_path(cx, cy, R),
        teeth="\n    ".join(teeth_paths),
        r_inner=r_inner, r_hole=r_hole)


if __name__ == "__main__":
    target_w = int(sys.argv[1]) if len(sys.argv) > 1 else 142
    out_png = build(scale=8, width=target_w)
    svg_text = build_svg(target_w)
    for rel_dir in ("_extensions/r2/resources/badges", "themes/r2/assets/badges", "docs/assets/badges"):
        d = REPO / rel_dir
        d.mkdir(parents=True, exist_ok=True)
        p_png, p_svg = d / "codecheck.png", d / "codecheck.svg"
        out_png.save(p_png)
        p_svg.write_text(svg_text, encoding="utf-8")
        print(f"wrote {p_png} {out_png.size} ({p_png.stat().st_size // 1024} KB) and {p_svg.name}")
