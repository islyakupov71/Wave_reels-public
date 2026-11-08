# -*- coding: utf-8 -*-
"""Присланный логотип → файл нужного размера для кадра 1080×1920.

    python tools/logo_hires.py <вход.png> <выход.png> <высота в кадре, px>

Размер файла и есть размер логотипа в кадре: `.imgv img` картинку не
растягивает, у неё только потолок. Поэтому целевая высота задаётся в пикселях.

Дальше всё решает край входного файла, и путей два.

**Край уже сглажен** (в файле есть полупрозрачные пиксели по контуру) — файл
честный, трогать его содержимое незачем. Нужен только правильный ресемплинг:
цвет домножается на альфу, размер меняется, потом альфа делится обратно. Без
этого прозрачные пиксели затягивают свой цвет в кромку, и по контуру появляется
ореол — та же беда, что была у старого файла, только наведённая нами.

**Край рубленый** (альфа только 0 и 255) — так выглядит логотип, снятый со
страницы: контур ступеньками, а крайний ряд пикселей подмешан к белому фону, с
которого картинку вырезали. Растягивать такой файл нельзя, увеличение честно
увеличит и ступеньки. Он пересобирается из трёх слоёв, каждый масштабируется
тем способом, который для него верен:

* **подложка** — линейный градиент, коэффициенты снимаются регрессией с самих
  пикселей; считается прямо в целевом разрешении, то есть точно;
* **знак** (белые буквы) и **силуэт** — двухцветные маски: увеличиваем,
  сглаживаем, режем по 0.5 и оставляем узкую кромку сглаживания. Ступеньки
  исчезают, форма остаётся ровно той же;
* белая кайма не переносится вовсе: цвет под ней берётся из градиента.

Это не перерисовка чужого знака от руки, а пересчёт настоящего файла: ни одна
линия не двигается, меняется только то, как посчитан край.
"""
import sys, os
import numpy as np
from PIL import Image, ImageFilter

SRC = sys.argv[1]
DST = sys.argv[2]
TARGET_H = float(sys.argv[3]) if len(sys.argv) > 3 else None

im = Image.open(SRC).convert("RGBA")
a = np.array(im).astype(float)
rgb, al = a[..., :3], a[..., 3]
H, W = al.shape
solid = al > 127
F = (TARGET_H / H) if TARGET_H else 2.0

if not solid.any():
    raise SystemExit("в файле нет непрозрачных пикселей")

# ── путь для честного файла: только ресемплинг с домноженной альфой ──
# Сглаженный край даёт полупрозрачные пиксели вдоль всего контура; их число
# сравниваем с длиной самого контура, чтобы не спутать сглаживание с парой
# случайных точек внутри знака.
edge = solid & ~(np.roll(solid, 1, 0) & np.roll(solid, -1, 0) &
                 np.roll(solid, 1, 1) & np.roll(solid, -1, 1))
soft = int(((al > 0) & (al < 255)).sum())
if soft >= 0.25 * max(int(edge.sum()), 1):
    W2, H2 = max(1, int(round(W * F))), max(1, int(round(H * F)))
    pm = np.dstack([rgb * (al[..., None] / 255.0), al]).round().clip(0, 255).astype(np.uint8)
    big = np.array(Image.fromarray(pm, "RGBA").resize((W2, H2), Image.LANCZOS)).astype(float)
    a2 = big[..., 3:4]
    out = np.dstack([np.clip(big[..., :3] / np.maximum(a2 / 255.0, 1e-6), 0, 255), a2])
    Image.fromarray(out.round().astype(np.uint8), "RGBA").save(DST, optimize=True)
    print("%s → %s | край уже сглажен (%d полупрозрачных на %d контурных), "
          "только ресемплинг | %dx%d → %dx%d"
          % (os.path.basename(SRC), os.path.basename(DST), soft, int(edge.sum()), W, H, W2, H2))
    sys.exit()

def erode(mask, n):
    """Сжать маску на n пикселей: убираем кромку, подмешанную к фону."""
    m = mask.copy()
    for _ in range(n):
        e = m.copy()
        e[1:, :] &= m[:-1, :]; e[:-1, :] &= m[1:, :]
        e[:, 1:] &= m[:, :-1]; e[:, :-1] &= m[:, 1:]
        m = e
    return m

core = erode(solid, 2)                      # чистая середина, без каймы
ys, xs = np.mgrid[0:H, 0:W].astype(float)

# ── слой 1: градиент подложки ────────────────────────────────────────
# Фон — самые тёмные пиксели середины; знак поверх него светлее по всем каналам.
lum = rgb.mean(2)
thr = np.percentile(lum[core], 50)
back = core & (lum < max(thr, np.percentile(lum[core], 20) + 1))
A = np.c_[xs[back], ys[back], np.ones(int(back.sum()))]
coef, resid = [], []
for ch in range(3):
    c, *_ = np.linalg.lstsq(A, rgb[..., ch][back], rcond=None)
    coef.append(c)
    resid.append(float(np.abs(A @ c - rgb[..., ch][back]).mean()))
coef = np.array(coef)
print("градиент подложки: остаток по каналам %s" % np.round(resid, 2))
if max(resid) > 6:
    print("  ! подложка плохо ложится на линейный градиент — проверь результат глазами")

def plane(x, y):
    """Цвет подложки в исходных координатах (x, y)."""
    return np.stack([coef[ch][0] * x + coef[ch][1] * y + coef[ch][2] for ch in range(3)], -1)

# ── слой 2: знак поверх подложки ─────────────────────────────────────
# Покрытие = насколько пиксель ушёл от подложки к белому.
base = plane(xs, ys)
cover = np.clip(((rgb - base) / np.maximum(255.0 - base, 1e-6)).min(2), 0, 1)
cover[~core] = 0                            # кайму за знак не принимаем

# ── пересчёт масок в целевое разрешение ──────────────────────────────
W2, H2 = int(round(W * F)), int(round(H * F))

def upscale_mask(m):
    """Двухцветную маску увеличиваем через сглаживание и порог: ступеньки
    исчезают, а край получает кромку шириной меньше пикселя."""
    img = Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8), "L")
    big = img.resize((W2, H2), Image.BICUBIC)
    big = big.filter(ImageFilter.GaussianBlur(0.75 * F))     # сгладить ступеньки
    v = np.array(big).astype(float) / 255.0
    v = np.clip((v - 0.5) * (2.6 * F) + 0.5, 0, 1)           # обратно в резкий край
    v = np.array(Image.fromarray((v * 255).astype(np.uint8), "L")
                 .filter(ImageFilter.GaussianBlur(0.45))) / 255.0
    return v

alpha2 = upscale_mask(solid.astype(float))
sign2 = upscale_mask(cover)

x2 = (np.arange(W2) + 0.5) / F - 0.5
y2 = (np.arange(H2) + 0.5) / F - 0.5
gx, gy = np.meshgrid(x2, y2)
base2 = plane(gx, gy)

out = base2 * (1 - sign2[..., None]) + 255.0 * sign2[..., None]
res = np.dstack([np.clip(out, 0, 255), np.clip(alpha2 * 255, 0, 255)]).astype(np.uint8)
Image.fromarray(res, "RGBA").save(DST, optimize=True)

soft = int(((alpha2 > 0.02) & (alpha2 < 0.98)).sum())
print("%s → %s | %dx%d → %dx%d | сглаженных пикселей на контуре %d"
      % (os.path.basename(SRC), os.path.basename(DST), W, H, W2, H2, soft))
