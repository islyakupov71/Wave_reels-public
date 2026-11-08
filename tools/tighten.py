# -*- coding: utf-8 -*-
"""Подтяжка озвучки под норматив формата.

Две независимые проблемы решаются по отдельности:
  1) слишком длинные паузы  -> режем тишину, оставляя короткий вдох
  2) медленная артикуляция  -> atempo без изменения высоты голоса

Границы абзацев сохраняем чуть длиннее — по ним встают смены сцен.

atempo зажат потолком MAX_TEMPO (выше — слышно). Если комфортной обрезки пауз
и потолка atempo вместе не хватает до целевого темпа (ElevenLabs v3 ненадёжно
слушается Speed на генерации), паузы дожимаются бинарным поиском до KEEP_*_MIN —
темп всегда должен попадать в норматив без переписи озвучки.
"""
import subprocess, sys, os, wave, tempfile, numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env import ffmpeg

FF = ffmpeg()
TMP = tempfile.mkdtemp(prefix="tighten_")

SRC        = sys.argv[1]
DST        = sys.argv[2]
TARGET_WPM = float(sys.argv[3]) if len(sys.argv) > 3 else 170.0
NWORDS     = int(sys.argv[4])   if len(sys.argv) > 4 else 169

KEEP_SHORT_MAX = 0.16   # пауза внутри фразы -> столько оставляем в комфортном режиме
KEEP_SHORT_MIN = 0.08   # тот же зазор, когда одного atempo не хватает до темпа
KEEP_LONG_MAX  = 0.30   # пауза между абзацами (была > BOUNDARY) -> столько в комфортном режиме
KEEP_LONG_MIN  = 0.20   # граница абзаца остаётся заметно длиннее короткой даже в сжатом режиме
BOUNDARY   = 0.62   # с какой длины пауза считается границей абзаца
THR_DB     = -34.0
MAX_TEMPO  = 1.18   # выше — слышно; дальше жмём паузы, а не atempo

def load(path):
    tmp = os.path.join(TMP, "in.wav")
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-i", path,
                    "-ac", "1", "-ar", "48000", "-y", tmp], check=True)
    w = wave.open(tmp)
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return a, w.getframerate()

def voiced_mask(a, sr, hop_s=0.01):
    hop = int(sr * hop_s)
    fr = a[:len(a) // hop * hop].reshape(-1, hop)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-9)
    v = db > THR_DB
    for i in range(1, len(v) - 1):            # затыкаем одиночные дырки
        if not v[i] and v[i - 1] and v[i + 1]:
            v[i] = True
    return v, hop

def stats(a, sr, label):
    v, hop = voiced_mask(a, sr)
    dur = len(a) / sr
    print("  %-10s %.2f с | речь %.1f%% | %.1f слов/мин" % (label, dur, 100 * v.mean(), NWORDS / (dur / 60)))
    return dur

a, sr = load(SRC)
print("исходник:"); d0 = stats(a, sr, "было")

# ── 1. режем паузы, при нехватке темпа дожимая их бинарным поиском ───────────
v, hop = voiced_mask(a, sr)
segs, i = [], 0
while i < len(v):
    j = i
    while j < len(v) and v[j] == v[i]:
        j += 1
    segs.append((v[i], i * hop, min(j * hop, len(a))))
    i = j

need = NWORDS / TARGET_WPM * 60

def trim(keep_short, keep_long):
    out, cut = [], 0.0
    for is_voice, s, e in segs:
        if is_voice:
            out.append(a[s:e])
            continue
        dur = (e - s) / sr
        keep = keep_long if dur > BOUNDARY else keep_short
        if dur <= keep:
            out.append(a[s:e]); continue
        # оставляем половину зазора с каждой стороны — стык не щёлкает
        n = int(keep * sr / 2)
        out.append(np.concatenate([a[s:s + n], a[e - n:e]]))
        cut += dur - keep
    return np.concatenate(out), cut

def duration_at(alpha):
    ks = KEEP_SHORT_MAX - alpha * (KEEP_SHORT_MAX - KEEP_SHORT_MIN)
    kl = KEEP_LONG_MAX - alpha * (KEEP_LONG_MAX - KEEP_LONG_MIN)
    a2, _ = trim(ks, kl)
    return len(a2) / sr

# alpha=0 — комфортные паузы. Не хватает даже с потолком atempo -> бинарным
# поиском дожимаем паузы (не дальше KEEP_*_MIN), а не задираем atempo выше MAX_TEMPO.
alpha = 0.0
if duration_at(0.0) / MAX_TEMPO > need:
    lo, hi = 0.0, 1.0
    for _ in range(20):
        mid = (lo + hi) / 2
        if duration_at(mid) / MAX_TEMPO > need:
            lo = mid
        else:
            hi = mid
    alpha = hi

keep_short = KEEP_SHORT_MAX - alpha * (KEEP_SHORT_MAX - KEEP_SHORT_MIN)
keep_long = KEEP_LONG_MAX - alpha * (KEEP_LONG_MAX - KEEP_LONG_MIN)
a2, cut = trim(keep_short, keep_long)
if alpha > 0.001:
    print("  темпа не хватало -> паузы дожаты: короткая %.2f с, граница абзаца %.2f с"
          % (keep_short, keep_long))
print("  вырезано тишины: %.1f с" % cut)
d1 = stats(a2, sr, "без пауз")

tmp2 = os.path.join(TMP, "trim.wav")
with wave.open(tmp2, "w") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((np.clip(a2, -1, 1) * 32767).astype(np.int16).tobytes())

# ── 2. добираем темп ─────────────────────────────────────────────────────────
tempo = min(MAX_TEMPO, max(1.0, d1 / need))
print("  нужно %.1f с -> atempo %.3f%s" % (need, tempo, "  (упёрлись в потолок)" if tempo >= MAX_TEMPO else ""))

af = "atempo=%.4f," % tempo if tempo > 1.001 else ""
subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-i", tmp2,
                "-af", af + "loudnorm=I=-14:TP=-1.5:LRA=9",
                "-c:a", "libmp3lame", "-b:a", "256k", "-y", DST], check=True)

b, sr2 = load(DST)
print("итог:"); stats(b, sr2, "стало")
print("->", DST)
