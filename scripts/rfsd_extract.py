#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Шаг 3b: выручка (line_2110, тыс. руб.) по ИНН из архивов РФСД.
Использование: python rfsd_extract.py <rfsd-каталог> <inn-файл> <out.json>
out.json: {инн: {"2021": 13800985, ...}}. Потоковый проход, zip не распаковывается."""
import json, os, sys, zipfile

def main():
    rfsd_dir, inn_file, out = sys.argv[1], sys.argv[2], sys.argv[3]
    inns = set(l.strip() for l in open(inn_file, encoding="utf-8-sig") if l.strip())
    result = {inn: {} for inn in inns}
    for year in (2021, 2022, 2023, 2024, 2025):
        zp = os.path.join(rfsd_dir, f"rfsd_{year}.zip")
        if not os.path.exists(zp):
            print(year, "skip (нет архива)"); continue
        z = zipfile.ZipFile(zp)
        name = [n for n in z.namelist() if n.endswith(".csv")][0]
        raw = z.open(name)
        header = raw.readline().decode("utf-8").rstrip("\r\n").split(";")
        idx_inn, idx_rev = header.index("inn"), header.index("line_2110")
        n_match = 0
        for line in raw:
            p1 = line.find(b";", 0, 20)
            p2 = line.find(b";", p1 + 1, 30)
            inn = line[p1 + 1:p2].decode("ascii", "ignore")
            if inn not in inns:
                continue
            parts = line.rstrip(b"\r\n").decode("utf-8", "replace").split(";")
            if len(parts) <= idx_rev:
                continue
            s = parts[idx_rev].strip().strip('"')
            try:
                v = int(float(s)) if s else None
            except ValueError:
                v = None
            result[inn][str(year)] = v
            n_match += 1
        z.close()
        print(year, "matched", n_match)
    json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
