# -*- coding: utf-8 -*-
"""Подбор иконки по русскому слову.

    python3 tools/icons.py склад возврат      что есть под эти слова
    python3 tools/icons.py --groups            все группы и что в них
    python3 tools/icons.py --all               весь список

Ищет по русским описаниям из assets/icons/index.json. Ключ, который печатается
слева, и есть значение поля `icon=` в сценарии.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDX = os.path.join(ROOT, "assets", "icons", "index.json")

if not os.path.exists(IDX):
    sys.exit("нет assets/icons/index.json — bash tools/fetch-assets.sh && python3 tools/build_assets.py")
I = json.load(open(IDX, encoding="utf-8"))
args = sys.argv[1:]


def show(keys):
    for k in keys:
        print("  %-16s %-11s %s" % (k, I[k]["group"], I[k]["ru"]))


if not args:
    sys.exit(__doc__)

if args[0] == "--all":
    show(sorted(I)); print("\nвсего %d" % len(I)); sys.exit()

if args[0] == "--groups":
    g = {}
    for k, v in I.items(): g.setdefault(v["group"], []).append(k)
    for name in sorted(g):
        print("\n%s (%d)" % (name, len(g[name])))
        print("  " + ", ".join(sorted(g[name])))
    sys.exit()

qs = [a.lower().replace("ё", "е") for a in args]
hits = []
for k, v in I.items():
    hay = (k + " " + v["ru"] + " " + v["group"]).lower().replace("ё", "е")
    score = sum(3 if q == k else (2 if q in hay.split() else (1 if q in hay else 0)) for q in qs)
    if score: hits.append((score, k))
hits.sort(key=lambda x: (-x[0], x[1]))

if not hits:
    print("ничего по запросу %r." % " ".join(args))
    print("посмотри группы: python3 tools/icons.py --groups")
    print("если нужной иконки нет — добавь её в словарь ICONS в tools/build_assets.py")
    print("(наборы lucide 1768 и tabler 5130 уже лежат в ~/.cache/wave-reels-vendor)")
else:
    show([k for _, k in hits[:20]])
    print("\nнайдено %d" % len(hits))
