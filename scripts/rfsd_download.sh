#!/bin/bash
# Шаг 3a: скачивание годовых CSV-архивов РФСД (~250 МБ/год).
# Использование: bash rfsd_download.sh <каталог> [годы...]   (по умолчанию 2021-2025)
# Актуальную версию датасета (VER) смотреть на https://tochno.st/datasets/rfsd
set -e
VER="v20260904"
DIR="${1:?укажите каталог назначения}"; shift
YEARS="$@"; [ -z "$YEARS" ] && YEARS="2021 2022 2023 2024 2025"
mkdir -p "$DIR"
for y in $YEARS; do
  url="https://storage.yandexcloud.net/tochno-st-catalog/FNS/data_rfsd_152_${VER}/by_years/data_152_rfsd_${y}_${VER}_csv.zip"
  out="$DIR/rfsd_${y}.zip"
  if [ ! -s "$out" ]; then
    curl -s -o "$out" "$url"
  fi
  echo "$y: $(du -m "$out" | cut -f1) MB"
done
