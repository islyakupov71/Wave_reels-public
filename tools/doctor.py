# -*- coding: utf-8 -*-
"""Проверка окружения. Пока не всё зелёное — ролик собирать рано."""
import os, sys, subprocess, importlib.util, glob, json
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.join(ROOT,"tools"))
if sys.platform.startswith("win"): os.system("")   # включает ANSI в консоли Windows
OK,BAD,WARN="\033[92m✓\033[0m","\033[91m✗\033[0m","\033[93m!\033[0m"
res=[]
def add(s,name,hint=""): res.append((s,name,hint))

add(OK if sys.version_info>=(3,10) else BAD, "python %d.%d"%sys.version_info[:2], "нужен 3.10+")
for mod,pkg in [("playwright","playwright"),("faster_whisper","faster-whisper"),
                ("numpy","numpy"),("PIL","pillow"),("brotli","brotli"),("imageio_ffmpeg","imageio-ffmpeg")]:
    ok=importlib.util.find_spec(mod) is not None
    add(OK if ok else (WARN if mod=="faster_whisper" else BAD), "пакет %s"%pkg, "" if ok else "pip install %s"%pkg)

try:
    import env as E
    add(OK,"ffmpeg %s"%os.path.basename(E.ffmpeg()))
except SystemExit as e:
    add(BAD,"ffmpeg",str(e))
except Exception as e:
    add(BAD,"ffmpeg",repr(e))

try:
    import env as E
    br=E.chrome()
    add(OK,"браузер %s"%(os.path.basename(br) if br else "chromium из playwright"),
        "" if br else "используется свой chromium — это нормально")
except Exception as e:
    add(BAD,"браузер",repr(e))

hub=os.path.expanduser("~/.cache/huggingface/hub")
has=os.path.isdir(hub) and any("whisper" in d for d in os.listdir(hub))
add(OK if has else WARN,"модель whisper","скачается сама при первой разметке (~1.5 ГБ)")

for f in ["engine/player2.html","engine/build2.py","engine/render2.py",
          "engine/vendor/three.module.min.js","engine/vendor/three.core.min.js",
          "engine/vendor/loaders/GLTFLoader.js","engine/vendor/utils/BufferGeometryUtils.js",
          "assets/models/library.json","assets/fonts/onest_embedded.css","tools/tighten.py","tools/asr.py"]:
    add(OK if os.path.exists(os.path.join(ROOT,f)) else BAD, f, "нет файла")

for d,what,hint in [("assets/icons/index.json","иконки","bash tools/fetch-assets.sh && python3 tools/build_assets.py"),
                    ("assets/maps/maps.json","карты","то же"),
                    ("assets/logos/brands/index.json","логотипы брендов","то же")]:
    p=os.path.join(ROOT,d)
    n=len(json.load(open(p,encoding="utf-8"))) if os.path.exists(p) else 0
    add(OK if n else BAD,"%s: %d"%(what,n),"" if n else hint)

lib=os.path.join(ROOT,"assets/models/library.json")
if os.path.exists(lib):
    L=json.load(open(lib,encoding="utf-8"))
    miss=[k for k,v in L.items() if not os.path.exists(os.path.join(ROOT,"assets/models",v["path"]))]
    add(OK if not miss else BAD,"3D-моделей на месте: %d из %d"%(len(L)-len(miss),len(L)),
        "" if not miss else "нет: %s — bash tools/fetch-models.sh"%", ".join(miss[:5]))

print()
for s,name,hint in res:
    print("  %s %-52s %s"%(s,name,hint if s!=OK else ""))
bad=sum(1 for s,_,_ in res if s==BAD)
print("\n  \033[1mинтерпретатор конвейера: %s\033[0m"%sys.executable)
print("  вызывай именно его — системный python3 обычно без playwright и whisper")
print("\n  \033[1m%s\033[0m\n"%("окружение готово" if not bad else "не готово, проблем: %d"%bad))
sys.exit(1 if bad else 0)
