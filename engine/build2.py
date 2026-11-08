# -*- coding: utf-8 -*-
"""Сборка out2.html: whisper-слова -> выравнивание на эталон -> якоря -> секунды.
Данные кладём в window.* ДО модульного скрипта плеера."""
import json, re, difflib, sys, os, importlib.util

ENG = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ENG)

scen_path = sys.argv[1]
words_raw = sys.argv[2]
duration = float(sys.argv[3])

spec = importlib.util.spec_from_file_location("scen", scen_path)
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)

norm = lambda s: re.sub(r"[^\wёЁ]+", "", s.lower().replace("ё", "е"))
VOWELS = "аеёиоуыэюяaeiouy"
syllables = lambda w: max(1, sum(1 for ch in w.lower() if ch in VOWELS))
truth = [w for w in re.split(r"\s+", S.GROUND_TRUTH.strip()) if norm(w)]
hyp = [w for w in json.load(open(words_raw, encoding="utf-8")) if norm(w["w"])]

sm = difflib.SequenceMatcher(None, [norm(w) for w in truth], [norm(w["w"]) for w in hyp], autojunk=False)
words = [None] * len(truth)
matched = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        for k in range(i2 - i1):
            h = hyp[j1 + k]; words[i1 + k] = {"w": truth[i1 + k], "s": h["s"], "e": h["e"]}
        matched += i2 - i1
    elif tag in ("replace", "delete"):
        s = hyp[j1]["s"] if j1 < len(hyp) else (hyp[-1]["e"] if hyp else 0)
        e = hyp[j2 - 1]["e"] if j1 <= j2 - 1 < len(hyp) else s
        if j2 <= j1:
            s = hyp[j1 - 1]["e"] if j1 > 0 else 0
            e = hyp[j1]["s"] if j1 < len(hyp) else s + 0.25
        # Внутри несовпавшего куска время делим по слогам, а не поровну:
        # whisper пишет числа цифрами («240 000» вместо «двести сорок тысяч»),
        # и такие куски — треть текста. Поровну «сто» получало бы столько же,
        # сколько «пятьдесят», и подсветка уезжала от голоса на четверть секунды.
        n = i2 - i1
        ws = [syllables(truth[i]) for i in range(i1, i2)]
        tot = sum(ws)
        acc = 0
        for k in range(n):
            s0 = s + (e - s) * acc / tot
            acc += ws[k]
            words[i1 + k] = {"w": truth[i1 + k], "s": round(s0, 3),
                             "e": round(s + (e - s) * acc / tot, 3)}
for i, w in enumerate(words):
    if w is None:
        prev = next((words[j]["e"] for j in range(i - 1, -1, -1) if words[j]), 0)
        nxt = next((words[j]["s"] for j in range(i + 1, len(words)) if words[j]), prev + 0.3)
        words[i] = {"w": truth[i], "s": round(prev, 3), "e": round(max(nxt, prev + 0.1), 3)}
for i in range(1, len(words)):
    if words[i]["s"] < words[i - 1]["e"]: words[i]["s"] = words[i - 1]["e"]
    if words[i]["e"] <= words[i]["s"]: words[i]["e"] = words[i]["s"] + 0.08

print("эталон %d слов | распознано %d | совпало %d (%.1f%%)" % (
    len(truth), len(hyp), matched, 100 * matched / len(truth)))

# Ищем якорь по сплошной нормализованной строке, а не по токенам:
# так «Семь» находится внутри «Семь-двенадцать», а пунктуация и дефисы не мешают.
flat, owner = "", []
for i, w in enumerate(words):
    n = norm(w["w"])
    flat += n; owner += [i] * len(n)

def anchor(phrase):
    p = norm(phrase)
    if not p: raise SystemExit("ПУСТОЙ ЯКОРЬ")
    k = flat.find(p)
    if k < 0: raise SystemExit("ЯКОРЬ НЕ НАЙДЕН: %r" % phrase)
    if flat.find(p, k + 1) >= 0:
        print("   ! якорь %r встречается несколько раз — беру первый" % phrase)
    return words[owner[k]]["s"]

VISUALS = {"model", "flow", "icons", "stack", "map", "donut",
           "columns", "timeline", "code", "image", "line"}

scenes = []
for sc in S.SCENES:
    o = {k: sc.get(k) for k in ("id", "theme", "chapter", "eyebrow", "title")}
    o["eyebrow"] = (o["eyebrow"] or "").upper()
    o["at"] = round(anchor(sc["at"]), 3)

    # `hero=dict(model=...)` — старая запись для 3D, живёт как частный случай visual
    v = sc.get("visual") or (dict(sc["hero"], type="model") if sc.get("hero") else None)
    if v:
        if v.get("type") not in VISUALS:
            raise SystemExit("сцена %s: неизвестный носитель %r (есть: %s)"
                             % (sc["id"], v.get("type"), ", ".join(sorted(VISUALS))))
        v = dict(v)
        if v.get("at"): v["at"] = round(anchor(v["at"]), 3)
        o["visual"] = v

    o["blocks"] = [dict(b, at=round(anchor(b["at"]), 3)) for b in sc.get("blocks", [])]
    scenes.append(o)
for i in range(1, len(scenes)):
    if scenes[i]["at"] <= scenes[i - 1]["at"]:
        raise SystemExit("сцены не по порядку: %s -> %s" % (scenes[i-1]["id"], scenes[i]["id"]))

print("\nсцены:")
for i, s in enumerate(scenes):
    end = scenes[i + 1]["at"] if i + 1 < len(scenes) else duration
    print("  %6.2f → %6.2f (%4.1fs) %-5s %-12s %-30s %s" % (
        s["at"], end, end - s["at"], s["theme"], s["id"],
        s["eyebrow"][:30], s.get("visual", {}).get("type", "—")))
gaps = [scenes[i+1]["at"] - scenes[i]["at"] for i in range(len(scenes)-1)]
print("\nсцен %d | средняя %.1f с | самая длинная %.1f с" % (len(scenes), sum(gaps)/len(gaps), max(gaps + [duration - scenes[-1]["at"]])))

CFG = {"duration": round(duration, 3), "hook": S.HOOK,
       "hookUntil": round(anchor(S.HOOK_UNTIL), 3), "chapters": S.CHAPTERS}

html = open(f"{ENG}/player2.html", encoding="utf-8").read()
data = ("<script>window.WORDS=%s;window.SCENARIO=%s;window.CFG=%s;</script>\n" % (
    json.dumps(words, ensure_ascii=False), json.dumps(scenes, ensure_ascii=False),
    json.dumps(CFG, ensure_ascii=False)))
html = html.replace('<script type="module">', data + '<script type="module">', 1)
open(f"{ENG}/out2.html", "w", encoding="utf-8").write(html)
print("\nout2.html собран (%.0f KB), hookUntil %.2f с" % (len(html) / 1024, CFG["hookUntil"]))
