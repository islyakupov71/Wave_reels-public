# -*- coding: utf-8 -*-
"""Собирает библиотеку плоской графики из скачанных источников.

    python tools/fetch_assets.py      # сначала качает исходники в кэш
    python tools/build_assets.py      # потом отбирает нужное в assets/

Что делает:
  1. отбирает иконки из lucide/tabler, кладёт в assets/icons/ с русским индексом
  2. отбирает логотипы известных брендов из simple-icons в assets/logos/brands/
  3. разбирает TopoJSON и печёт карты в assets/maps/ как готовые SVG-пути

Иконки приходят с `stroke="currentColor"` — цвет задаёт плеер, перекрашивать не надо.
"""
import json, os, re, shutil, sys, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.environ.get("WAVE_VENDOR", os.path.expanduser("~/.cache/wave-reels-vendor"))


def wopen(path):
    """Пишем всегда LF. Иначе питон на Windows подставляет CRLF, и собранные
    индексы отличаются от собранных на Linux — при одинаковом содержимом."""
    return open(path, "w", encoding="utf-8", newline="\n")

# ──────────────────────────────────────────────────────────────────────
# 1. ИКОНКИ
# ключ → (файл в наборе, набор, русские слова для поиска, тематическая группа)
# ──────────────────────────────────────────────────────────────────────
ICONS = {
 # транспорт и доставка
 "truck":        ("truck",              "lucide", "фура грузовик доставка автоперевозка",     "транспорт"),
 "van":          ("truck-electric",     "lucide", "фургон развозка последняя миля",           "транспорт"),
 "ship":         ("ship",               "lucide", "судно контейнеровоз море фрахт",           "транспорт"),
 "plane":        ("plane",              "lucide", "самолёт авиа авиаперевозка",               "транспорт"),
 "plane-takeoff":("plane-takeoff",      "lucide", "вылет отправка авиа",                      "транспорт"),
 "train":        ("train-front",        "lucide", "поезд жд вагон железная дорога",           "транспорт"),
 "forklift":     ("forklift",           "lucide", "погрузчик склад техника",                  "транспорт"),
 "container":    ("container",          "lucide", "контейнер морской тара",                   "транспорт"),
 "route":        ("route",              "lucide", "маршрут путь цепочка плечо",               "транспорт"),
 "map-pin":      ("map-pin",            "lucide", "точка город адрес пункт",                  "транспорт"),
 "navigation":   ("navigation",         "lucide", "направление курс навигация",               "транспорт"),
 "milestone":    ("milestone",          "lucide", "веха этап указатель",                      "транспорт"),

 # склад и товар
 "package":      ("package",            "lucide", "коробка посылка единица товара",           "склад"),
 "package-open": ("package-open",       "lucide", "вскрытая коробка приёмка распаковка",      "склад"),
 "package-check":("package-check",      "lucide", "принято проверено оприходовано",           "склад"),
 "package-x":    ("package-x",          "lucide", "брак отказ невыкуп возврат",               "склад"),
 "boxes":        ("boxes",              "lucide", "партия штабель запас остатки",             "склад"),
 "warehouse":    ("warehouse",          "lucide", "склад фулфилмент хранение",                "склад"),
 "archive":      ("archive",            "lucide", "архив длительное хранение",                "склад"),
 "conveyor":     ("briefcase-conveyor-belt", "lucide", "конвейер линия сортировка",           "склад"),
 "scan":         ("scan-line",          "lucide", "сканирование считывание кода",             "склад"),
 "scan-barcode": ("scan-barcode",       "lucide", "штрихкод сканер маркировка",               "склад"),
 "qr":           ("qr-code",            "lucide", "куар код дата матрикс маркировка",         "склад"),
 "barcode":      ("barcode",            "lucide", "штрихкод ean артикул",                     "склад"),
 "tag":          ("tag",                "lucide", "этикетка ярлык артикул",                   "склад"),
 "clipboard":    ("clipboard-list",     "lucide", "опись инвентаризация чеклист",             "склад"),
 "recycle":      ("recycle",            "lucide", "возврат оборот переработка",               "склад"),

 # торговля
 "store":        ("store",              "lucide", "магазин розница точка продаж",             "торговля"),
 "shopping-cart":("shopping-cart",      "lucide", "корзина заказ покупка",                    "торговля"),
 "shopping-bag": ("shopping-bag",       "lucide", "покупка пакет чек",                        "торговля"),
 "cash-register":("cash-register",      "tabler", "касса пробитие чек",                       "торговля"),
 "receipt":      ("receipt",            "lucide", "чек квитанция фискальный документ",        "торговля"),
 "credit-card":  ("credit-card",        "lucide", "оплата карта эквайринг",                   "торговля"),
 "percent":      ("percent",            "lucide", "процент скидка комиссия ставка",           "торговля"),
 "megaphone":    ("megaphone",          "lucide", "реклама продвижение ставка кампания",      "торговля"),
 "star":         ("star",               "lucide", "рейтинг отзыв оценка",                     "торговля"),
 "users":        ("users",              "lucide", "покупатели аудитория клиенты",             "торговля"),

 # деньги
 "ruble":        ("russian-ruble",      "lucide", "рубль деньги сумма",                       "деньги"),
 "ruble-receipt":("receipt-russian-ruble","lucide","чек в рублях сумма расхода",              "деньги"),
 "coins":        ("coins",              "lucide", "монеты выручка оборот",                    "деньги"),
 "banknote":     ("banknote",           "lucide", "купюра выплата деньги",                    "деньги"),
 "wallet":       ("wallet",             "lucide", "кошелёк бюджет остаток",                   "деньги"),
 "piggy-bank":   ("piggy-bank",         "lucide", "накопления экономия резерв",               "деньги"),
 "calculator":   ("calculator",         "lucide", "расчёт юнит экономика посчитать",          "деньги"),
 "scale":        ("scale",              "lucide", "весы баланс сопоставление",                "деньги"),
 "landmark":     ("landmark",           "lucide", "банк госорган казна",                      "деньги"),

 # аналитика
 "chart-line":   ("trending-up",        "lucide", "рост тренд вверх динамика",                "аналитика"),
 "chart-down":   ("trending-down",      "lucide", "падение снижение вниз убыток",             "аналитика"),
 "chart-bar":    ("chart-column",       "lucide", "столбцы график сравнение",                 "аналитика"),
 "chart-pie":    ("chart-pie",          "lucide", "доли структура пирог",                     "аналитика"),
 "activity":     ("activity",           "lucide", "активность пульс показатель",              "аналитика"),
 "gauge":        ("gauge",              "lucide", "шкала показатель загрузка",                "аналитика"),
 "target":       ("target",             "lucide", "цель норматив попадание",                  "аналитика"),
 "layers":       ("layers",             "lucide", "слои уровни разложение",                   "аналитика"),
 "table":        ("table-2",            "lucide", "таблица отчёт свод",                       "аналитика"),
 "database":     ("database",           "lucide", "база данных реестр система",               "аналитика"),

 # документы и право
 "file-text":    ("file-text",          "lucide", "документ декларация бумага",               "документы"),
 "file-check":   ("file-check",         "lucide", "документ принят согласован",               "документы"),
 "file-x":       ("file-x",             "lucide", "документ отклонён ошибка",                 "документы"),
 "files":        ("files",              "lucide", "пачка документов комплект",                "документы"),
 "stamp":        ("stamp",              "lucide", "печать штамп заверение",                   "документы"),
 "signature":    ("signature",          "lucide", "подпись эцп заверение",                    "документы"),
 "book":         ("book-open",          "lucide", "закон правило регламент",                  "документы"),
 "gavel":        ("gavel",              "lucide", "суд штраф санкция закон",                  "документы"),
 "shield":       ("shield",             "lucide", "защита гарантия безопасность",             "документы"),
 "shield-check": ("shield-check",       "lucide", "проверено подтверждено легально",          "документы"),
 "shield-alert": ("shield-alert",       "lucide", "риск нарушение угроза",                    "документы"),
 "badge-check":  ("badge-check",        "lucide", "сертификат подтверждение знак",            "документы"),
 "fingerprint":  ("fingerprint",        "tabler", "уникальность идентификация след",          "документы"),
 "id-card":      ("id-card",            "lucide", "паспорт удостоверение карточка",           "документы"),
 "key":          ("key-round",          "lucide", "ключ проверки криптоподпись доступ",       "документы"),
 "lock":         ("lock",               "lucide", "закрыто защита блокировка",                "документы"),

 # время
 "clock":        ("clock",              "lucide", "время часы срок",                          "время"),
 "timer":        ("timer",              "lucide", "таймер обратный отсчёт дедлайн",           "время"),
 "hourglass":    ("hourglass",          "lucide", "песочные часы ожидание простой",           "время"),
 "calendar":     ("calendar-days",      "lucide", "календарь дата период",                    "время"),
 "calendar-x":   ("calendar-x-2",       "lucide", "просрочка срыв срока",                     "время"),
 "history":      ("history",            "tabler", "история было раньше",                      "время"),
 "alarm":        ("alarm-clock",        "lucide", "будильник напоминание срочно",             "время"),

 # состояние и оценка
 "check":        ("check",              "lucide", "да верно есть галка",                      "оценка"),
 "check-circle": ("circle-check-big",   "lucide", "выполнено подтверждено",                   "оценка"),
 "x":            ("x",                  "lucide", "нет отказ крест",                          "оценка"),
 "x-circle":     ("circle-x",           "lucide", "не выполнено отклонено",                   "оценка"),
 "minus-circle": ("circle-minus",       "lucide", "исключено вычет минус",                    "оценка"),
 "alert":        ("triangle-alert",     "lucide", "внимание предупреждение риск",             "оценка"),
 "info":         ("info",               "lucide", "справка пояснение",                        "оценка"),
 "help":         ("circle-question-mark","lucide","вопрос неясность",                         "оценка"),
 "ban":          ("ban",                "lucide", "запрет нельзя блокировка",                 "оценка"),
 "eye":          ("eye",                "lucide", "видно прозрачность наблюдение",            "оценка"),
 "eye-off":      ("eye-off",            "lucide", "не видно скрыто тень",                     "оценка"),
 "search":       ("search",             "lucide", "поиск проверка разбор",                    "оценка"),
 "zoom-in":      ("zoom-in",            "lucide", "разбираем подробно увеличение",            "оценка"),
 "thumbs-up":    ("thumbs-up",          "lucide", "хорошо плюс одобрение",                    "оценка"),
 "thumbs-down":  ("thumbs-down",        "lucide", "плохо минус неодобрение",                  "оценка"),
 "flame":        ("flame",              "lucide", "горит срочно горячее",                     "оценка"),
 "snowflake":    ("snowflake",          "lucide", "заморозка стоп холод",                     "оценка"),

 # схемы и связи
 "arrow-right":  ("arrow-right",        "lucide", "стрелка вправо переход",                   "схема"),
 "arrow-down":   ("arrow-down",         "lucide", "стрелка вниз следствие",                   "схема"),
 "arrow-left-right":("arrow-left-right","lucide", "туда обратно обмен",                       "схема"),
 "corner-down":  ("corner-down-right",  "lucide", "ветка ответвление",                        "схема"),
 "split":        ("split",              "lucide", "развилка два пути выбор",                  "схема"),
 "merge":        ("merge",              "lucide", "слияние сведение",                         "схема"),
 "workflow":     ("workflow",           "lucide", "процесс блок схема этапы",                 "схема"),
 "git-branch":   ("git-branch",         "lucide", "ветвление варианты сценарии",              "схема"),
 "network":      ("network",            "lucide", "сеть связи участники",                     "схема"),
 "link":         ("link",               "lucide", "связь звено цепочка",                      "схема"),
 "repeat":       ("repeat",             "lucide", "повтор цикл оборот",                       "схема"),
 "refresh":      ("refresh-cw",         "lucide", "обновление пересчёт",                      "схема"),
 "filter":       ("funnel",             "lucide", "воронка отбор фильтр",                     "схема"),
 "list-ordered": ("list-ordered",       "lucide", "шаги по порядку нумерация",                "схема"),

 # производство и государство
 "factory":      ("factory",            "lucide", "завод производство изготовитель",          "прочее"),
 "building":     ("building-2",         "lucide", "компания офис юрлицо",                     "прочее"),
 "globe":        ("globe",              "lucide", "мир импорт международный",                 "прочее"),
 "flag":         ("flag",               "lucide", "страна флаг отметка",                      "прочее"),
 "cpu":          ("cpu",                "lucide", "система технология цифра",                 "прочее"),
 "server":       ("server",             "lucide", "сервер реестр хранилище",                  "прочее"),
 "smartphone":   ("smartphone",         "lucide", "телефон приложение покупатель",            "прочее"),
 "monitor":      ("monitor",            "lucide", "экран личный кабинет интерфейс",           "прочее"),
 "bot":          ("bot",                "lucide", "робот автоматизация алгоритм",             "прочее"),
 "settings":     ("settings",           "lucide", "настройка механизм шестерня",              "прочее"),
 "wrench":       ("wrench",             "lucide", "починка настройка инструмент",             "прочее"),
 "lightbulb":    ("lightbulb",          "lucide", "идея вывод инсайт",                        "прочее"),
 "brain":        ("brain",              "lucide", "понимание логика мышление",                "прочее"),
 "user-check":   ("user-check",         "lucide", "проверенный участник продавец",            "прочее"),
 "team":         ("users",              "lucide", "сотрудники персонал команда штат люди",   "прочее"),
 "handshake":    ("handshake",          "lucide", "сделка договор партнёр",                   "прочее"),
 "trophy":       ("trophy",             "lucide", "результат победа лучший",                  "прочее"),
}

# логотипы брендов из simple-icons (CC0). Российских маркетплейсов там нет —
# их файлы приносит пользователь, см. assets/logos/brands/README.md
BRANDS = {
 "telegram": "телеграм", "whatsapp": "вотсап", "vk": "вконтакте",
 "youtube": "ютуб", "tiktok": "тикток", "instagram": "инстаграм",
 "dhl": "дхл", "fedex": "федекс", "ups": "юпиэс", "maersk": "маерск",
 "alibabadotcom": "алибаба", "aliexpress": "алиэкспресс", "amazon": "амазон",
 "ebay": "ибей", "shopify": "шопифай", "wechat": "вичат", "alipay": "алипей",
 "visa": "виза", "mastercard": "мастеркард", "paypal": "пейпал",
 "1password": "", "googlemaps": "гугл карты", "yandexcloud": "яндекс облако",
}

# ──────────────────────────────────────────────────────────────────────


def build_icons():
    out = os.path.join(ROOT, "assets", "icons")
    os.makedirs(out, exist_ok=True)
    src = {"lucide": os.path.join(CACHE, "lucide", "icons"),
           "tabler": os.path.join(CACHE, "tabler", "icons", "outline")}
    index, missing = {}, []
    for key, (fname, pack, ru, group) in ICONS.items():
        p = os.path.join(src[pack], fname + ".svg")
        if not os.path.exists(p):
            missing.append("%s (%s/%s)" % (key, pack, fname)); continue
        svg = open(p, encoding="utf-8").read()
        body = re.sub(r"</?svg[^>]*>", "", svg).strip()
        body = re.sub(r"\s+", " ", body)
        wopen(os.path.join(out, key + ".svg")).write(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round">%s</svg>' % body)
        index[key] = {"ru": ru, "group": group, "pack": pack}
    json.dump(index, wopen(os.path.join(out, "index.json")),
              ensure_ascii=False, indent=1, sort_keys=True)
    print("иконок: %d" % len(index), ("| НЕ НАЙДЕНЫ: " + ", ".join(missing)) if missing else "")
    return missing


def build_brands():
    out = os.path.join(ROOT, "assets", "logos", "brands")
    os.makedirs(out, exist_ok=True)
    src = os.path.join(CACHE, "simpleicons", "icons")
    index, missing = {}, []
    for key, ru in BRANDS.items():
        p = os.path.join(src, key + ".svg")
        if not os.path.exists(p):
            missing.append(key); continue
        shutil.copy(p, os.path.join(out, key + ".svg"))
        index[key] = {"ru": ru, "license": "CC0-1.0", "source": "simple-icons"}
    json.dump(index, wopen(os.path.join(out, "index.json")),
              ensure_ascii=False, indent=1, sort_keys=True)
    print("логотипов: %d" % len(index), ("| нет: " + ", ".join(missing)) if missing else "")


# ── TopoJSON без библиотек ────────────────────────────────────────────
def topo_arcs(topo):
    """Дельта-декодирование дуг и обратное квантование в градусы."""
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    out = []
    for arc in topo["arcs"]:
        x = y = 0; pts = []
        for dx, dy in arc:
            x += dx; y += dy
            pts.append((x * sx + tx, y * sy + ty))
        out.append(pts)
    return out


def rings_of(geom, arcs):
    """Список колец (списков точек) для Polygon/MultiPolygon."""
    def ring(idxs):
        pts = []
        for i in idxs:
            a = arcs[~i][::-1] if i < 0 else arcs[i]
            pts.extend(a if not pts else a[1:])
        return pts
    if geom["type"] == "Polygon":
        return [ring(r) for r in geom["arcs"]]
    if geom["type"] == "MultiPolygon":
        return [ring(r) for poly in geom["arcs"] for r in poly]
    return []


def albers(lon, lat, lon0=100.0, lat0=55.0, p1=50.0, p2=70.0):
    """Коническая равновеликая Альберса — узнаваемая форма России."""
    r = math.radians
    p1, p2, lat0, lat = r(p1), r(p2), r(lat0), r(lat)
    n = 0.5 * (math.sin(p1) + math.sin(p2))
    if abs(n) < 1e-9: n = 1e-9
    C = math.cos(p1) ** 2 + 2 * n * math.sin(p1)
    rho = math.sqrt(max(C - 2 * n * math.sin(lat), 0)) / n
    rho0 = math.sqrt(max(C - 2 * n * math.sin(lat0), 0)) / n
    th = n * r(lon - lon0)
    return rho * math.sin(th), rho0 - rho * math.cos(th)


def miller(lon, lat):
    """Миллер — мир целиком без полярного раздувания Меркатора."""
    y = 1.25 * math.log(math.tan(math.pi / 4 + 0.4 * math.radians(lat)))
    return math.radians(lon), -y


def to_svg(rings, project, pad=2.0, width=1000.0, min_area=None):
    """Кольца в градусах → путь SVG, нормированный в бокс шириной width."""
    proj = [[project(*p) for p in ring] for ring in rings]
    if min_area:
        def area(r):
            return abs(sum(r[i][0] * r[i-1][1] - r[i-1][0] * r[i][1]
                           for i in range(len(r)))) / 2
        big = max((area(r) for r in proj), default=0)
        proj = [r for r in proj if area(r) >= big * min_area]
    xs = [p[0] for r in proj for p in r]; ys = [p[1] for r in proj for p in r]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    k = (width - 2 * pad) / max(x1 - x0, 1e-9)
    h = (y1 - y0) * k + 2 * pad
    jump = width * 0.28         # разрыв шире этого — шов 180-го меридиана, а не берег
    d = []
    for r in proj:
        seg, prev = [], None
        for x, y in r:
            X, Y = (x - x0) * k + pad, (y - y0) * k + pad
            if prev is None:
                seg.append("M%.1f %.1f" % (X, Y))
            elif abs(X - prev[0]) > jump:
                seg.append("Z M%.1f %.1f" % (X, Y))
            elif abs(X - prev[0]) < 0.35 and abs(Y - prev[1]) < 0.35:
                continue                       # выкидываем точки тоньше полпикселя
            else:
                seg.append("L%.1f %.1f" % (X, Y))
            prev = (X, Y)
        d.append(" ".join(seg) + "Z")
    return " ".join(d), round(width, 1), round(h, 1), (x0, y0, k, pad)


CITIES = {   # опорные точки для маршрутов и кластеров
 "Москва": (37.62, 55.75),        "Санкт-Петербург": (30.32, 59.94),
 "Казань": (49.12, 55.79),        "Нижний Новгород": (44.00, 56.33),
 "Екатеринбург": (60.60, 56.84),  "Новосибирск": (82.93, 55.03),
 "Красноярск": (92.87, 56.01),    "Иркутск": (104.28, 52.29),
 "Хабаровск": (135.08, 48.48),    "Владивосток": (131.89, 43.12),
 "Краснодар": (38.98, 45.04),     "Ростов-на-Дону": (39.72, 47.23),
 "Самара": (50.15, 53.20),        "Уфа": (55.97, 54.74),
 "Челябинск": (61.40, 55.16),     "Пермь": (56.23, 58.01),
 "Волгоград": (44.52, 48.71),     "Воронеж": (39.20, 51.67),
 "Калининград": (20.45, 54.71),   "Мурманск": (33.08, 68.97),
 "Владимир": (40.41, 56.13),      "Тула": (37.62, 54.20),
 "Омск": (73.37, 54.99),          "Тюмень": (65.53, 57.15),
 "Якутск": (129.73, 62.03),       "Сочи": (39.73, 43.60),
 # зарубежные узлы для «путей из Китая»
 "Пекин": (116.41, 39.90),        "Шанхай": (121.47, 31.23),
 "Гуанчжоу": (113.26, 23.13),     "Урумчи": (87.62, 43.83),
 "Стамбул": (28.98, 41.01),       "Дубай": (55.27, 25.20),
 "Алматы": (76.89, 43.24),        "Минск": (27.56, 53.90),
}


def build_maps():
    out = os.path.join(ROOT, "assets", "maps")
    os.makedirs(out, exist_ok=True)
    res = {}

    for name, fn in (("110m", "countries-110m.json"), ("50m", "countries-50m.json")):
        p = os.path.join(CACHE, "geo", fn)
        if not os.path.exists(p):
            print("нет %s — пропускаю" % fn); continue
        topo = json.load(open(p))
        arcs = topo_arcs(topo)
        geoms = topo["objects"]["countries"]["geometries"]

        if name == "50m":
            ru = next((g for g in geoms if g.get("properties", {}).get("name") == "Russia"), None)
            if ru:
                rings = rings_of(ru, arcs)
                # Чукотка уезжает за 180-й меридиан — сшиваем сдвигом
                rings = [[(l + 360 if l < -20 else l, b) for l, b in r] for r in rings]
                # min_area достаточно мелкий, чтобы уцелел Калининград
                d, w, h, (x0, y0, k, pad) = to_svg(rings, albers, width=1000.0, min_area=0.0006)
                res["russia"] = {"d": d, "w": w, "h": h, "proj": "albers",
                                 "note": "Россия, Альберса, 50m"}
                pts = {}
                for city, (lon, lat) in CITIES.items():
                    x, y = albers(lon + 360 if lon < -20 else lon, lat)
                    pts[city] = [round((x - x0) * k + pad, 1), round((y - y0) * k + pad, 1)]
                res["russia"]["cities"] = pts

        if name == "110m":
            rings = []
            for g in geoms:
                # Антарктида в цилиндрической проекции — полоса во всю ширину кадра
                if g.get("properties", {}).get("name") == "Antarctica":
                    continue
                rings.extend(rings_of(g, arcs))
            rings = [r for r in rings if len(r) > 8]
            d, w, h, (x0, y0, k, pad) = to_svg(rings, miller, width=1000.0)
            res["world"] = {"d": d, "w": w, "h": h, "proj": "miller",
                            "note": "мир, Миллер, 110m"}
            pts = {}
            for city, (lon, lat) in CITIES.items():
                x, y = miller(lon, lat)
                pts[city] = [round((x - x0) * k + pad, 1), round((y - y0) * k + pad, 1)]
            res["world"]["cities"] = pts

    json.dump(res, wopen(os.path.join(out, "maps.json")),
              ensure_ascii=False, separators=(",", ":"))
    for k, v in res.items():
        print("карта %-7s %.0f×%.0f, путь %d символов, городов %d"
              % (k, v["w"], v["h"], len(v["d"]), len(v.get("cities", {}))))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("all", "icons"):  build_icons()
    if what in ("all", "brands"): build_brands()
    if what in ("all", "maps"):   build_maps()
