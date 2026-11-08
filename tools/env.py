# -*- coding: utf-8 -*-
"""Где что лежит. Единственное место, которое знает про разницу Windows и Linux.

Конвейер должен одинаково работать и там, и там, поэтому пути к ffmpeg
и к браузеру ищутся, а не прописываются.

    from env import ffmpeg, chrome, launch_args
"""
import os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIN = sys.platform.startswith("win")


def ffmpeg():
    """Порядок: переменная окружения → tools/ffmpeg_path.txt → imageio → PATH."""
    p = os.environ.get("WAVE_FFMPEG")
    if p and os.path.exists(p):
        return p

    txt = os.path.join(ROOT, "tools", "ffmpeg_path.txt")
    if os.path.exists(txt):
        p = open(txt, encoding="utf-8").read().strip()
        # файл переезжает вместе с проектом, поэтому чужой путь молча пропускаем
        if p and os.path.exists(p):
            return p

    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass

    p = shutil.which("ffmpeg")
    if p:
        return p
    raise SystemExit("ffmpeg не найден: pip install imageio-ffmpeg "
                     "или задай путь в переменной WAVE_FFMPEG")


CHROMES_WIN = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
CHROMES_NIX = [
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium", "/usr/bin/chromium-browser", "/snap/bin/chromium",
]


def chrome():
    """Путь к настоящему Chrome или None — тогда playwright возьмёт свой chromium."""
    p = os.environ.get("WAVE_CHROME")
    if p and os.path.exists(p):
        return p
    for p in (CHROMES_WIN if WIN else CHROMES_NIX):
        if p and os.path.exists(p):
            return p
    return None


def launch_args():
    """Флаги запуска браузера: одинаковый растр кадра на любой машине."""
    a = ["--force-device-scale-factor=1", "--hide-scrollbars",
         "--disable-lcd-text", "--font-render-hinting=none",
         "--force-color-profile=srgb",
         "--disable-gpu", "--enable-unsafe-swiftshader"]
    if not WIN:
        a.insert(0, "--no-sandbox")        # под root в контейнере иначе не стартует
    return a


def launch_kwargs():
    """Готовый набор для p.chromium.launch(**launch_kwargs())."""
    kw = {"args": launch_args()}
    ex = chrome()
    if ex:
        kw["executable_path"] = ex
    return kw


if __name__ == "__main__":
    print("платформа :", "Windows" if WIN else sys.platform)
    print("корень    :", ROOT)
    print("python    :", sys.executable)
    print("ffmpeg    :", ffmpeg())
    print("браузер   :", chrome() or "свой chromium из playwright")
