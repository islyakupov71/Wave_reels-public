# -*- coding: utf-8 -*-
"""Приёмка готового ролика по нормативам формата.

    python3 tools/check.py render/out/03-tri-puti.mp4
"""
import sys, os, subprocess, tempfile, glob, shutil, wave
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from env import ffmpeg
FF = ffmpeg()
VIDEO = sys.argv[1]

OK, BAD = "\033[92m✓\033[0m", "\033[91m✗\033[0m"
rows = []
def check(name, val, lo=None, hi=None, fmt="%.2f", ref=""):
    good = (lo is None or val >= lo) and (hi is None or val <= hi)
    rows.append((good, name, fmt % val, ref))
    return good

tmp = tempfile.mkdtemp()
try:
    dur = float(subprocess.run([FF, "-i", VIDEO], capture_output=True, text=True).stderr
                .split("Duration: ")[1].split(",")[0].split(":")[-1]) + \
          60 * int(subprocess.run([FF, "-i", VIDEO], capture_output=True, text=True).stderr
                   .split("Duration: ")[1].split(",")[0].split(":")[1])

    # ── движение ────────────────────────────────────────────────────────────
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-i", VIDEO,
                    "-vf", "scale=90:160", "-q:v", "2", f"{tmp}/f_%05d.jpg"], check=True)
    fs = sorted(glob.glob(f"{tmp}/f_*.jpg"))
    A = [np.asarray(Image.open(f).convert("L"), dtype=np.int16) for f in fs]
    d = np.array([np.abs(A[i] - A[i - 1]).mean() for i in range(1, len(A))])

    def events(thr):
        above = d > thr; ev = []; i = 0
        while i < len(above):
            if above[i]:
                j = i
                while j < len(above) and above[j]: j += 1
                ev.append(i / 30); i = j
            else: i += 1
        g = np.diff(ev) if len(ev) > 1 else np.array([dur])
        return len(ev) / (dur / 60), g.max()

    pm_fine, gap_fine = events(0.8)
    pm_mid,  gap_mid  = events(1.2)
    check("события/мин (мелкие)", pm_fine, lo=50, fmt="%.1f", ref="референс 64.5")
    check("события/мин (средние)", pm_mid, lo=44, fmt="%.1f", ref="референс 44.8")
    check("макс. дыра, мелкий порог, с", gap_fine, hi=2.5, ref="референс 2.87")
    check("макс. дыра, средний порог, с", gap_mid, hi=2.9, ref="референс 2.87")

    # ── заполненность ───────────────────────────────────────────────────────
    ink = []
    for f in fs[::max(1, len(fs) // 24)]:
        subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-ss",
                        "%.2f" % (fs.index(f) / 30), "-i", VIDEO, "-frames:v", "1",
                        "-y", f"{tmp}/hi.png"], check=True)
        a = np.asarray(Image.open(f"{tmp}/hi.png").convert("L"), dtype=float)
        gx = np.abs(np.diff(a, axis=1)); gy = np.abs(np.diff(a, axis=0))
        m = np.zeros_like(a, bool); m[:, :-1] |= gx > 12; m[:-1, :] |= gy > 12
        ink.append(100 * m.mean())
    check("чернил в кадре, %", float(np.mean(ink)), lo=4.0, ref="референс 5.36")

    # ── речь ────────────────────────────────────────────────────────────────
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-i", VIDEO,
                    "-ac", "1", "-ar", "16000", "-y", f"{tmp}/a.wav"], check=True)
    w = wave.open(f"{tmp}/a.wav"); sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    hop = int(sr * 0.01); fr = a[:len(a) // hop * hop].reshape(-1, hop)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-9)
    v = db > -34.0
    check("речь в хронометраже, %", 100 * v.mean(), lo=85, fmt="%.1f", ref="референс 92")

finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n  \033[1m%s\033[0m — %.1f с\n" % (os.path.basename(VIDEO), dur))
w1 = max(len(r[1]) for r in rows)
for good, name, val, ref in rows:
    print("  %s %-*s %10s   %s" % (OK if good else BAD, w1, name, val, ref))
bad = sum(1 for r in rows if not r[0])
print("\n  \033[1m%s\033[0m\n" % ("всё в нормативе" if not bad else
      "не дотянуло пунктов: %d — доложи об этом честно" % bad))
sys.exit(0)
