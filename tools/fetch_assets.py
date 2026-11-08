# -*- coding: utf-8 -*-
"""Качает исходники плоской графики в кэш. Работает и на Windows, и на Linux.

    python tools/fetch_assets.py        скачать
    python tools/build_assets.py        отобрать нужное в assets/

Сами наборы в репозиторий не кладём — 60 МБ ради двух сотен файлов не нужны.
Кэш: ~/.cache/wave-reels-vendor (переопределяется переменной WAVE_VENDOR).

Лицензии: lucide ISC, tabler MIT, simple-icons CC0, world-atlas ISC
(данные Natural Earth — public domain). Всё пригодно для коммерции.
"""
import os, shutil, subprocess, sys, urllib.request

CACHE = os.environ.get("WAVE_VENDOR", os.path.expanduser("~/.cache/wave-reels-vendor"))

REPOS = [
    ("lucide",      "https://github.com/lucide-icons/lucide.git",           "icons"),
    ("tabler",      "https://github.com/tabler/tabler-icons.git",           "icons/outline"),
    ("simpleicons", "https://github.com/simple-icons/simple-icons.git",     "icons"),
]
GEO = ["countries-110m", "countries-50m"]


def sparse(name, url, sub):
    dst = os.path.join(CACHE, name)
    if os.path.isdir(os.path.join(dst, ".git")):
        print("  %-12s уже в кэше" % name)
    else:
        shutil.rmtree(dst, ignore_errors=True)
        print("  %-12s качаю..." % name, flush=True)
        try:
            subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none",
                            "--sparse", url, dst],
                           check=True, capture_output=True)
            subprocess.run(["git", "sparse-checkout", "set", sub],
                           cwd=dst, check=True, capture_output=True)
        except FileNotFoundError:
            sys.exit("нет git в PATH — поставь git")
        except subprocess.CalledProcessError as e:
            print("  %-12s НЕ УДАЛОСЬ: %s" % (name, e.stderr.decode("utf-8", "replace")[:200]))
            return
    n = sum(len([f for f in fs if f.endswith(".svg")])
            for _, _, fs in os.walk(os.path.join(dst, sub)))
    print("  %-12s %5d svg" % (name, n))


def main():
    os.makedirs(os.path.join(CACHE, "geo"), exist_ok=True)
    print("кэш:", CACHE)
    for name, url, sub in REPOS:
        sparse(name, url, sub)
    for f in GEO:
        p = os.path.join(CACHE, "geo", f + ".json")
        if os.path.exists(p):
            print("  %-12s уже в кэше" % f)
            continue
        print("  %-12s качаю..." % f, flush=True)
        urllib.request.urlretrieve("https://cdn.jsdelivr.net/npm/world-atlas@2/%s.json" % f, p)
        print("  %-12s %.0f КБ" % (f, os.path.getsize(p) / 1024))
    print("\nготово. дальше: python tools/build_assets.py")


if __name__ == "__main__":
    main()
