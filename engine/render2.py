# -*- coding: utf-8 -*-
"""Детерминированный рендер v2: 3D через WebGL, отдача по HTTP (CORS для модулей и GLB)."""
import sys, os, subprocess, time, threading, functools, http.server, socketserver
from playwright.sync_api import sync_playwright

ENG = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ENG)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from env import ffmpeg, launch_kwargs

FF = ffmpeg()
PORT = 8791
FPS = 30

mode = sys.argv[1] if len(sys.argv) > 1 else "video"
AUDIO = sys.argv[2]
DUR = float(sys.argv[3])
OUT = sys.argv[4] if len(sys.argv) > 4 else f"{ROOT}/render/out/out2.mp4"
TAIL = 0.5
NFRAMES = int(round((DUR + TAIL) * FPS))


def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    h.log_message = lambda *a, **k: None
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", PORT), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def open_page(p):
    b = p.chromium.launch(**launch_kwargs())
    pg = b.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    pg.on("response", lambda r: errs.append("HTTP %d %s" % (r.status, r.url[-60:])) if r.status >= 400 else None)
    pg.goto(f"http://127.0.0.1:{PORT}/engine/out2.html")
    try:
        pg.wait_for_function("window.__ready===true", timeout=90000)
    except Exception:
        print("СТРАНИЦА НЕ ПОДНЯЛАСЬ:"); [print("  ", e) for e in errs[:8]]; raise
    pg.wait_for_timeout(600)
    return b, pg


srv = serve()
if mode == "samples":
    os.makedirs(f"{ENG}/_s2", exist_ok=True)
    with sync_playwright() as p:
        b, pg = open_page(p)
        for t in [float(x) for x in sys.argv[5].split(",")]:
            pg.evaluate(f"__setTime({t})")
            pg.screenshot(path=f"{ENG}/_s2/t{t:06.2f}.png")
            print("  кадр", t)
        b.close()
    sys.exit()

ff = subprocess.Popen([
    FF, "-hide_banner", "-loglevel", "error", "-y",
    "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
    "-i", AUDIO,
    "-c:v", "libx264", "-preset", "slow", "-crf", "17",
    "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
    "-x264-params", "keyint=60:min-keyint=30",
    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
    "-af", "apad", "-movflags", "+faststart",
    "-t", "%.3f" % (NFRAMES / FPS), OUT,
], stdin=subprocess.PIPE)

t0 = time.time()
with sync_playwright() as p:
    b, pg = open_page(p)
    for i in range(NFRAMES):
        pg.evaluate(f"__setTime({i / FPS:.6f})")
        ff.stdin.write(pg.screenshot(type="png"))
        if i % 150 == 0 and i:
            el = time.time() - t0
            print("кадр %4d/%d  %2.0f%%  %.1f к/с  ~%.0f с осталось" % (
                i, NFRAMES, 100 * i / NFRAMES, i / el, (NFRAMES - i) / (i / el)), flush=True)
    b.close()
ff.stdin.close(); ff.wait()
print("готово за %.0f с -> %s (%.1f MB)" % (time.time() - t0, OUT, os.path.getsize(OUT) / 1e6))
