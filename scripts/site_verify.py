#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Шаг 5a: верификация официальных сайтов по ИНН.

Для каждого ИНН перебирает кандидатов-доменов, скачивает страницу и ищет ИНН в HTML.
Сайт засчитывается, только если ИНН найден на странице самого сайта (правило AGENTS.md).

Использование:
  python site_verify.py <candidates.json> <out.json> [--delay 5]

candidates.json: {"<inn>": ["domain1.ru", "domain2.ru"], ...}
out.json: {"<inn>": {"site": "domain.ru", "url": "https://domain.ru/contacts/",
                     "evidence": "found INN ..."}, ...}  — только подтверждённые.

Вежливость: задержка между доменами, один домен = до 3 страниц (/, /contacts, /requisites).
Только стандартная библиотека. Проверено на Python 3.12 (Windows, 12.11.2026).
"""
import json
import re
import sys
import time
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
PATHS = ["/contacts/", "/contact/", "/requisites/", "/about/", "/"]


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        ct = resp.headers.get("Content-Type", "")
        raw = resp.read(400_000)
    text = raw.decode("utf-8", "ignore")
    if not re.search(r"[А-Яа-я]", text):  # windows-1251 fallback
        text = raw.decode("cp1251", "ignore")
    return text if ("text/html" in ct or ct == "" or "<html" in text[:500].lower()) else ""


def find_inn(html, inn):
    if inn in re.sub(r"[\s\xA0]", "", html):
        return True
    # ИНН могут писать с пробелами/префиксом "ИНН"
    return bool(re.search(r"ИНН[^0-9]{0,20}" + inn, html))


def main():
    cand_path, out_path = sys.argv[1], sys.argv[2]
    delay = 5
    if "--delay" in sys.argv:
        delay = int(sys.argv[sys.argv.index("--delay") + 1])
    candidates = json.load(open(cand_path, encoding="utf-8"))
    result = {}
    for inn, domains in candidates.items():
        hit = None
        for domain in domains:
            for path in PATHS:
                url = f"https://{domain}{path}"
                try:
                    html = fetch(url)
                except Exception as ex:
                    print(f"{inn} {url}: {type(ex).__name__}", flush=True)
                    continue
                if html and find_inn(html, inn):
                    hit = {"site": domain, "url": url,
                           "evidence": f"ИНН {inn} на {url}"}
                    print(f"{inn} OK -> {domain} ({path})", flush=True)
                    break
                time.sleep(1)
            if hit:
                break
            time.sleep(delay)
        if hit:
            result[inn] = hit
        else:
            print(f"{inn}: не подтверждён ни один домен", flush=True)
        json.dump(result, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(delay)
    print("подтверждено сайтов:", len(result), "->", out_path)


if __name__ == "__main__":
    main()
