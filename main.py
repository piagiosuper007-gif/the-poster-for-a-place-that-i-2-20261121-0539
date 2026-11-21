#!/usr/bin/env python3
"""VELMARA - a travel poster for a place that does not exist.

Stdlib-only Python 3.13. Writes /output/entry.png (1024x1024, PNG).
Scene: a sunset over a calm sea, one lighthouse on a rocky islet,
and the invented place name VELMARA set large across the sky.
Deterministic: every value is fixed or from a seeded RNG.
"""
import os
import random
import struct
import zlib

W, H = 1024, 1024
HORIZON = 640
OUT = "/output/entry.png"

rng = random.Random(20261121)

# ---------------------------------------------------------------- canvas
buf = bytearray(W * H * 3)


def row_bytes(y):
    return y * W * 3


def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = row_bytes(y) + x * 3
        buf[i], buf[i + 1], buf[i + 2] = c


def blend(x, y, c, a):
    """Alpha-blend colour c (0..1 alpha) onto the pixel at x, y."""
    if 0 <= x < W and 0 <= y < H:
        i = row_bytes(y) + x * 3
        buf[i] = int(buf[i] * (1 - a) + c[0] * a)
        buf[i + 1] = int(buf[i + 1] * (1 - a) + c[1] * a)
        buf[i + 2] = int(buf[i + 2] * (1 - a) + c[2] * a)


def hline(y, x0, x1, c):
    if y < 0 or y >= H:
        return
    x0 = max(0, x0)
    x1 = min(W - 1, x1)
    if x1 < x0:
        return
    i = row_bytes(y) + x0 * 3
    n = x1 - x0 + 1
    buf[i:i + n * 3] = bytes(c) * n


def fill_rect(x0, y0, x1, y1, c):
    for y in range(max(0, y0), min(H, y1 + 1)):
        hline(y, x0, x1, c)


def fill_circle(cx, cy, r, c):
    r2 = r * r
    for y in range(max(0, cy - r), min(H, cy + r + 1)):
        dy = y - cy
        dx = int((r2 - dy * dy) ** 0.5)
        hline(y, cx - dx, cx + dx, c)


def fill_poly(pts, c):
    """Scanline fill of a simple polygon (list of (x, y))."""
    ys = [p[1] for p in pts]
    y0, y1 = max(0, min(ys)), min(H - 1, max(ys))
    n = len(pts)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x0, ya = pts[i]
            x1, yb = pts[(i + 1) % n]
            if (ya <= y < yb) or (yb <= y < ya):
                t = (y + 0.5 - ya) / (yb - ya)
                xs.append(x0 + t * (x1 - x0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            hline(y, int(xs[k]), int(xs[k + 1]), c)


def stamp(cx, cy, r, c):
    fill_circle(cx, cy, r, c)


def thick_line(x0, y0, x1, y1, w, c):
    """A line with round caps, drawn as stamped circles along it."""
    r = max(1, w // 2)
    dx, dy = x1 - x0, y1 - y0
    length = max(1, int((dx * dx + dy * dy) ** 0.5))
    steps = max(1, length * 2 // max(1, r))
    for s in range(steps + 1):
        t = s / steps
        stamp(int(x0 + dx * t), int(y0 + dy * t), r, c)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_c(c0, c1, t):
    return (int(lerp(c0[0], c1[0], t)),
            int(lerp(c0[1], c1[1], t)),
            int(lerp(c0[2], c1[2], t)))


def gradient(y, y0, y1, stops):
    """Multi-stop vertical gradient. stops: [(pos0..1, colour), ...]."""
    t = (y - y0) / max(1, y1 - y0)
    t = min(1.0, max(0.0, t))
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        if t <= p1:
            return lerp_c(c0, c1, (t - p0) / max(1e-9, p1 - p0))
    return stops[-1][1]


# ---------------------------------------------------------------- sky
SKY = [(0.00, (20, 28, 51)),
       (0.35, (61, 43, 88)),
       (0.60, (122, 63, 102)),
       (0.80, (198, 90, 107)),
       (1.00, (240, 152, 90))]
for y in range(0, HORIZON):
    hline(y, 0, W - 1, gradient(y, 0, HORIZON, SKY))

# stars, fading in towards the top of the sky
for _ in range(110):
    sx = rng.randint(0, W - 1)
    sy = int(rng.random() ** 1.6 * 330)
    b = rng.randint(150, 255)
    fade = 1.0 - sy / 420.0
    if fade <= 0:
        continue
    v = int(b * fade)
    col = (min(255, v + 40), min(255, v + 40), min(255, v + 60))
    put(sx, sy, col)
    if rng.random() < 0.35:
        put(sx + 1, sy, col)
        put(sx, sy + 1, col)

# ---------------------------------------------------------------- sun + glow
SUN = (350, 540)
SKY_AT_SUN = gradient(SUN[1], 0, HORIZON, SKY)
for r, mix in ((140, 0.88), (115, 0.72), (95, 0.50)):
    fill_circle(SUN[0], SUN[1], r, lerp_c((255, 223, 158), SKY_AT_SUN, mix))
fill_circle(SUN[0], SUN[1], 80, (255, 223, 158))
fill_circle(SUN[0], SUN[1], 62, (255, 232, 180))

# ---------------------------------------------------------------- far ridge
fill_poly([(0, HORIZON), (0, 600), (90, 585), (180, 612), (260, 575),
           (360, 605), (470, 580), (560, 610), (660, 615), (760, 622),
           (860, 610), (950, 612), (1024, 595), (1024, HORIZON)],
          (67, 40, 79))

# ---------------------------------------------------------------- sea
SEA = [(0.00, (42, 74, 92)),
       (0.50, (22, 48, 63)),
       (1.00, (10, 24, 38))]
for y in range(HORIZON, H):
    hline(y, 0, W - 1, gradient(y, HORIZON, H, SEA))

# sun reflection: broken amber dashes widening towards the viewer
for y in range(HORIZON + 18, H - 8, 12):
    depth = (y - HORIZON) / (H - HORIZON)
    hw = int(26 + depth * 150)
    cx = SUN[0] + int(rng.randint(-6, 6))
    sea = gradient(y, HORIZON, H, SEA)
    glow = lerp_c((242, 166, 90), sea, 0.35 + depth * 0.45)
    # split the dash into two or three pieces with gaps
    x = cx - hw
    while x < cx + hw:
        seg = rng.randint(18, 55)
        hline(y, x, min(cx + hw, x + seg), glow)
        hline(y + 1, x, min(cx + hw, x + seg), glow)
        x += seg + rng.randint(10, 30)

# faint horizontal swell lines on the sea
for _ in range(46):
    wy = rng.randint(HORIZON + 30, H - 10)
    wx = rng.randint(0, W - 220)
    wl = rng.randint(40, 200)
    sea = gradient(wy, HORIZON, H, SEA)
    line_c = (min(255, sea[0] + 26), min(255, sea[1] + 34),
              min(255, sea[2] + 38))
    hline(wy, wx, wx + wl, line_c)

# ---------------------------------------------------------------- islet + lighthouse
fill_poly([(640, HORIZON), (665, 600), (700, 585), (745, 578),
           (790, 590), (820, 612), (835, HORIZON)], (29, 20, 48))
# rock highlights on the waterline
fill_poly([(655, 640), (700, 622), (760, 622), (820, 640)], (38, 28, 60))

TOWER_TOP, TOWER_BOT = 455, 585
# tapered tower, cream white
fill_poly([(707, TOWER_BOT), (715, TOWER_TOP), (745, TOWER_TOP),
           (753, TOWER_BOT)], (245, 234, 210))
# two rust-red bands
fill_poly([(710, 540), (750, 540), (751, 522), (709, 522)], (122, 59, 59))
fill_poly([(713, 498), (747, 498), (748, 482), (712, 482)], (122, 59, 59))
# gallery deck + lamp room + dome
fill_rect(708, 440, 752, 455, (36, 26, 51))
fill_rect(718, 418, 742, 440, (255, 210, 122))
fill_poly([(714, 418), (730, 402), (746, 418)], (36, 26, 51))
fill_circle(730, 400, 4, (36, 26, 51))
# lamp glow
for r, mix in ((46, 0.88), (30, 0.68), (18, 0.40)):
    fill_circle(730, 429, r, lerp_c((255, 210, 122),
                                    gradient(429, 0, HORIZON, SKY), mix))
fill_rect(718, 418, 742, 440, (255, 210, 122))

# light beam sweeping right across the dusk sky
BEAM = (255, 230, 168)
bx0, by0 = 742, 429
beam_pts = [(bx0, by0 - 6), (1010, 468), (1010, 545), (bx0, by0 + 6)]
# point-in-triangle blend, factor fading with distance from the lamp
minx, maxx = 742, 1010
miny, maxy = 415, 550


def _sign(px, py, ax, ay, bx, by):
    return (px - bx) * (ay - by) - (ax - bx) * (py - by)


for yy in range(miny, maxy + 1):
    for xx in range(minx, maxx + 1):
        d1 = _sign(xx, yy, beam_pts[0][0], beam_pts[0][1],
                   beam_pts[1][0], beam_pts[1][1])
        d2 = _sign(xx, yy, beam_pts[1][0], beam_pts[1][1],
                   beam_pts[2][0], beam_pts[2][1])
        d3 = _sign(xx, yy, beam_pts[2][0], beam_pts[2][1],
                   beam_pts[3][0], beam_pts[3][1])
        d4 = _sign(xx, yy, beam_pts[3][0], beam_pts[3][1],
                   beam_pts[0][0], beam_pts[0][1])
        inside = ((d1 >= 0 and d2 >= 0 and d3 >= 0 and d4 >= 0) or
                  (d1 <= 0 and d2 <= 0 and d3 <= 0 and d4 <= 0))
        if inside:
            dist = (xx - bx0) / (maxx - bx0)
            blend(xx, yy, BEAM, 0.30 * (1 - dist) + 0.04)

# ---------------------------------------------------------------- foreground headlands
fill_poly([(0, H), (0, 860), (120, 820), (260, 880), (330, H)], (18, 13, 36))
fill_poly([(W, H), (W, 920), (900, 960), (860, H)], (18, 13, 36))

# ---------------------------------------------------------------- birds
BIRDS = [(200, 180), (262, 212), (700, 150), (762, 186), (824, 158),
         (330, 250), (880, 210)]
for bx, by in BIRDS:
    thick_line(bx - 11, by - 6, bx, by, 3, (42, 31, 69))
    thick_line(bx, by, bx + 11, by - 6, 3, (42, 31, 69))

# ---------------------------------------------------------------- the place name
# Stroke font on a 5x7 grid (x 0..4, y 0..6, y down). One polyline list
# per glyph; a second list holds extra strokes.
FONT = {
    "V": [[(0, 0), (2, 6), (4, 0)]],
    "E": [[(4, 0), (0, 0), (0, 6), (4, 6)], [(0, 3), (3, 3)]],
    "L": [[(0, 0), (0, 6), (4, 6)]],
    "M": [[(0, 6), (0, 0), (2, 3), (4, 0), (4, 6)]],
    "A": [[(0, 6), (2, 0), (4, 6)], [(1, 4), (3, 4)]],
    "R": [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 3), (0, 3)],
          [(2, 3), (4, 6)]],
}


def draw_text(text, x0, y0, unit, stroke, colour):
    """Draw text with the stroke font. unit = px per grid unit."""
    x = x0
    for ch in text:
        for poly in FONT[ch]:
            pts = [(x + px * unit, y0 + py * unit) for px, py in poly]
            for i in range(len(pts) - 1):
                thick_line(int(pts[i][0]), int(pts[i][1]),
                           int(pts[i + 1][0]), int(pts[i + 1][1]),
                           stroke, colour)
        x += 5 * unit + int(unit * 1.1)


NAME = "VELMARA"
UNIT = 22
text_w = len(NAME) * 5 * UNIT + (len(NAME) - 1) * int(UNIT * 1.1)
tx = (W - text_w) // 2
ty = 130
draw_text(NAME, tx + 6, ty + 8, UNIT, 16, (30, 22, 54))   # soft shadow
draw_text(NAME, tx, ty, UNIT, 16, (255, 233, 196))        # cream letters

# ---------------------------------------------------------------- thin poster frame
FRAME = (217, 160, 91)
for x in range(26, W - 26):
    put(x, 26, FRAME)
    put(x, 27, FRAME)
    put(x, H - 27, FRAME)
    put(x, H - 26, FRAME)
for y in range(26, H - 26):
    put(26, y, FRAME)
    put(27, y, FRAME)
    put(W - 27, y, FRAME)
    put(W - 26, y, FRAME)


# ---------------------------------------------------------------- PNG encode
def chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    c += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return c


def main():
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += buf[y * W * 3:(y + 1) * W * 3]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(png)
    print(f"wrote {OUT}: {len(png)} bytes, {W}x{H}")


if __name__ == "__main__":
    main()
