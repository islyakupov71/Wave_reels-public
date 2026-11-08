# -*- coding: utf-8 -*-
"""Собирает self-contained player.html:
   whisper-слова  ->  выравнивание на эталонный текст  ->  якоря сценария -> секунды."""
import json, re, base64, difflib, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scenario import GROUND_TRUTH, SCENES, CHAPTERS, HOOK, HOOK_UNTIL

BUILD = os.path.dirname(os.path.abspath(__file__))
SP = os.path.dirname(BUILD)
AUDIO_DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 67.08

norm = lambda s: re.sub(r"[^\wёЁ]+", "", s.lower().replace("ё", "е"))

# ---------- 1. эталонные слова ----------
truth = [w for w in re.split(r"\s+", GROUND_TRUTH.strip()) if norm(w)]

# ---------- 2. слова из whisper ----------
raw = json.load(open(f"{SP}/words_raw.json", encoding="utf-8"))
hyp = [w for w in raw if norm(w["w"])]

# ---------- 3. выравнивание ----------
sm = difflib.SequenceMatcher(None, [norm(w) for w in truth], [norm(w["w"]) for w in hyp], autojunk=False)
words = [None] * len(truth)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        for k in range(i2 - i1):
            h = hyp[j1 + k]
            words[i1 + k] = {"w": truth[i1 + k], "s": h["s"], "e": h["e"]}
    elif tag in ("replace", "delete"):
        # растягиваем доступный интервал на пропущенные эталонные слова
        s = hyp[j1]["s"] if j1 < len(hyp) else (hyp[-1]["e"] if hyp else 0)
        e = hyp[j2 - 1]["e"] if j2 - 1 >= j1 and j2 - 1 < len(hyp) else s
        if j2 <= j1:
            s = hyp[j1 - 1]["e"] if j1 > 0 else 0
            e = hyp[j1]["s"] if j1 < len(hyp) else s + 0.25
        n = i2 - i1
        for k in range(n):
            words[i1 + k] = {"w": truth[i1 + k],
                             "s": round(s + (e - s) * k / n, 3),
                             "e": round(s + (e - s) * (k + 1) / n, 3)}
miss = sum(1 for w in words if w is None)
# добиваем дырки
for i, w in enumerate(words):
    if w is None:
        prev = next((words[j]["e"] for j in range(i - 1, -1, -1) if words[j]), 0)
        nxt = next((words[j]["s"] for j in range(i + 1, len(words)) if words[j]), prev + 0.3)
        words[i] = {"w": truth[i], "s": round(prev, 3), "e": round(max(nxt, prev + 0.1), 3)}
# монотонность
for i in range(1, len(words)):
    if words[i]["s"] < words[i - 1]["e"]:
        words[i]["s"] = words[i - 1]["e"]
    if words[i]["e"] <= words[i]["s"]:
        words[i]["e"] = words[i]["s"] + 0.08

matched = sum(1 for tag, i1, i2, _, _ in sm.get_opcodes() if tag == "equal" for _ in range(i2 - i1))
print(f"эталон {len(truth)} слов | whisper {len(hyp)} | совпало {matched} ({100*matched/len(truth):.1f}%) | достроено {len(truth)-matched}")

# ---------- 4. якоря ----------
keys = [norm(w["w"]) for w in words]
def anchor(phrase, _cache={}):
    toks = [norm(t) for t in phrase.split() if norm(t)]
    for i in range(len(keys) - len(toks) + 1):
        if keys[i:i + len(toks)] == toks:
            return words[i]["s"]
    raise SystemExit(f"ЯКОРЬ НЕ НАЙДЕН: {phrase!r}")

scenes = []
for sc in SCENES:
    o = {k: sc[k] for k in ("id", "theme", "chapter", "eyebrow", "title")}
    o["eyebrow"] = o["eyebrow"].upper()
    o["at"] = round(anchor(sc["at"]), 3)
    o["blocks"] = []
    for b in sc.get("blocks", []):
        nb = dict(b)
        nb["at"] = round(anchor(b["at"]), 3)
        o["blocks"].append(nb)
    scenes.append(o)

for i in range(1, len(scenes)):
    if scenes[i]["at"] <= scenes[i - 1]["at"]:
        raise SystemExit(f"сцены не по порядку: {scenes[i-1]['id']} -> {scenes[i]['id']}")

print("\nсцены:")
for i, s in enumerate(scenes):
    end = scenes[i + 1]["at"] if i + 1 < len(scenes) else AUDIO_DUR
    print(f"  {s['at']:6.2f} → {end:6.2f}  ({end-s['at']:5.2f}s) {s['theme']:5} {s['id']:8} {s['eyebrow']}")
    for b in s["blocks"]:
        print(f"           {b['at']:6.2f}   · {b['type']}")

CFG = {"duration": round(AUDIO_DUR, 3), "hook": HOOK,
       "hookUntil": round(anchor(HOOK_UNTIL), 3), "chapters": CHAPTERS}

# ---------- 5. сборка ----------
b64 = lambda p: "data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()
html = open(f"{BUILD}/player.html", encoding="utf-8").read()
html = (html
        .replace("__FONT_CSS__", open(f"{BUILD}/assets/onest_embedded.css", encoding="utf-8").read())
        .replace("__LOGO_BADGE__", b64(f"{BUILD}/assets/wave_badge.png"))
        .replace("__WORDS__", json.dumps(words, ensure_ascii=False))
        .replace("__SCENARIO__", json.dumps(scenes, ensure_ascii=False))
        .replace("__CFG__", json.dumps(CFG, ensure_ascii=False)))
open(f"{BUILD}/out.html", "w", encoding="utf-8").write(html)
json.dump(words, open(f"{SP}/words.json", "w"), ensure_ascii=False, indent=1)
print("\nout.html: %.0f KB | hookUntil %.2fs | duration %.2fs" % (len(html) / 1024, CFG["hookUntil"], CFG["duration"]))
