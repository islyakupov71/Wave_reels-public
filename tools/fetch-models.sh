#!/usr/bin/env bash
# Перекачивает 3D-модели, если папка assets/models пустая.
# Все паки Kenney — CC0. Самолёт с poly.pizza — CC-BY, см. ATTRIBUTION.md
set -u
cd "$(dirname "$0")/.." || exit 1
mkdir -p assets/models/_zip assets/models/polypizza

declare -A PACKS=(
  [car-kit]="https://kenney.nl/media/pages/assets/car-kit/1a312ec241-1775131960/kenney_car-kit.zip"
  [train-kit]="https://kenney.nl/media/pages/assets/train-kit/cf8521d625-1727040883/kenney_train-kit.zip"
  [watercraft-kit]="https://kenney.nl/media/pages/assets/watercraft-kit/a335cfed49-1713519620/kenney_watercraft-pack.zip"
  [factory-kit]="https://kenney.nl/media/pages/assets/factory-kit/edaac9d4f6-1777639602/kenney_factory-kit_3.0.zip"
  [mini-market]="https://kenney.nl/media/pages/assets/mini-market/463f38da51-1729865423/kenney_mini-market.zip"
)
for name in "${!PACKS[@]}"; do
  [ -d "assets/models/$name" ] && { echo "$name уже есть"; continue; }
  echo "качаю $name ..."
  # сеть бывает капризной — три попытки
  for i in 1 2 3; do
    curl -sSL --max-time 180 -A "Mozilla/5.0" "${PACKS[$name]}" -o "assets/models/_zip/$name.zip" && break
    echo "  попытка $i не прошла, повтор"
  done
  python3 -c "import zipfile;zipfile.ZipFile('assets/models/_zip/$name.zip').extractall('assets/models/$name')" \
    && echo "  ok" || echo "  РАСПАКОВКА НЕ УДАЛАСЬ"
done

if [ ! -f assets/models/polypizza/plane-b.glb ]; then
  echo "качаю самолёт (CC-BY, dook / poly.pizza) ..."
  curl -sSL --max-time 120 "https://static.poly.pizza/1faa14d6-dee8-4bcc-a001-44d49b5a4866.glb.br" \
    -o assets/models/polypizza/plane-b.glb.br
  python3 - <<'PY'
import brotli
d=open("assets/models/polypizza/plane-b.glb.br","rb").read()
try: out=brotli.decompress(d)
except Exception: out=d
open("assets/models/polypizza/plane-b.glb","wb").write(out)
print("  ok, %.0f KB"%(len(out)/1024))
PY
fi
echo; python3 tools/doctor.py
