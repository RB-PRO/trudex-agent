#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Шаг 2a: обогащение с агрегатора checko.ru по списку ИНН.

Использование: python checko_fetch.py <inn-файл> <out_dir>

Для каждого ИНН открывает https://checko.ru/search?query=<ИНН> (редирект на
карточку /company/<ogrn>), парсит: название, ОГРН/ИНН, статус, дату регистрации,
руководителя (должность + ФИО), учредителей, телефоны, email, сайт, блок ЕФРСБ,
блок арбитражных дел, выручку по годам из JS-графика отчетности (code 2110).

Сырой HTML кэшируется в <out_dir>/html/<inn>.html (повторный запуск не дергает сайт).
Итог: <out_dir>/checko_enrich.json  {инн: {поля}}.

Вежливый режим: задержка между запросами, при 429 — пауза с повторами.
Только стандартная библиотека. Проверено на Python 3.12 (Windows, 12.11.2026).
"""
import html as html_mod
import json
import os
import re
import sys
import time
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
MONTHS = {"января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5,
          "июня": 6, "июля": 7, "августа": 8, "сентября": 9, "октября": 10,
          "ноября": 11, "декабря": 12}
PROC_KEYWORDS = ("введении процедуры", "введена процедура", "наблюдение",
                 "конкурсное производство", "внешнее управление",
                 "реструктуризация долгов", "финансовый управляющий",
                 "процедура банкротства")
CASE_KEYWORDS = ("дело о банкротстве", "заявление о банкротстве",
                 "банкротстве по заявлению")


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


def get_card(inn, cache_dir):
    path = os.path.join(cache_dir, f"{inn}.html")
    if os.path.exists(path) and os.path.getsize(path) > 5000:
        return open(path, encoding="utf-8").read()
    for attempt in range(4):
        try:
            body = fetch(f"https://checko.ru/search?query={inn}")
            open(path, "w", encoding="utf-8").write(body)
            return body
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                wait = 20 * (attempt + 1)
                print(f"{inn}: 429, пауза {wait} с", flush=True)
                time.sleep(wait)
            else:
                raise
    return None


def clean(s):
    return html_mod.unescape(re.sub(r"<[^>]+>", " ", s or "")).replace("\xa0", " ").strip()


def parse_date(s):
    m = re.search(r"(\d{1,2})\s+(\S+)\s+(\d{4})", s or "")
    if not m or m.group(2) not in MONTHS:
        return ""
    return f"{int(m.group(1)):02d}.{MONTHS[m.group(2)]:02d}.{m.group(3)}"


def get_url(url, cache_path):
    if cache_path and os.path.exists(cache_path) and os.path.getsize(cache_path) > 2000:
        return open(cache_path, encoding="utf-8").read()
    for attempt in range(4):
        try:
            body = fetch(url)
            if cache_path:
                open(cache_path, "w", encoding="utf-8").write(body)
            return body
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                wait = 20 * (attempt + 1)
                print(f"{url}: 429, пауза {wait} с", flush=True)
                time.sleep(wait)
            else:
                raise
    return None


def parse_founders_page(h):
    """Полный список действующих учредителей со страницы /founders."""
    sect = re.search(r'id="founders"(.*?)(?:Экс-учредители|id="history")', h, re.S)
    scope = sect.group(1) if sect else h[:8000]
    founders = re.findall(r'href="/(?:person|company)/[^"]+"[^>]*>([^<]+)</a>', scope)
    seen, out = set(), []
    for f in founders:
        f = clean(f)
        if f and f not in seen:
            seen.add(f)
            out.append(f)
    return out


def parse_card(h, inn):
    rec = {"inn": inn}
    m = re.search(r'<h1 id="cn"[^>]*>(.*?)</h1>', h, re.S)
    rec["name"] = clean(m.group(1)) if m else ""
    m = re.search(r'id="copy-ogrn"[^>]*>(\d+)<', h)
    rec["ogrn"] = m.group(1) if m else ""
    m = re.search(r'id="copy-inn"[^>]*>([\d]+)<', h)
    rec["card_inn"] = m.group(1) if m else ""
    m = re.search(r'<div class="text-\w+ fw-600">([^<]{3,80})</div>', h)
    rec["status"] = clean(m.group(1)) if m else ""
    m = re.search(r'Дата регистрации</div>\s*<div>([^<]+)</div>', h)
    rec["reg_date"] = parse_date(m.group(1)) if m else ""
    # руководитель: первое упоминание /person/ (карточка действующего)
    m = re.search(r'href="/person/[\d]+"[^>]*>([^<]+)</a>', h)
    rec["director"] = clean(m.group(1)) if m else ""
    rec["director_role"] = ""
    if m:
        before = h[max(0, m.start() - 1500):m.start()]
        roles = re.findall(r'<div class="fw-700">([^<]{3,60})</div>', before)
        if roles:
            rec["director_role"] = clean(roles[-1])
    # учредители: активная вкладка секции #founders (на карточке — первые 3)
    fsec = re.search(r'id="founders" class="x-section"(.*?)<div class="x-section" id="gov"', h, re.S)
    scope = fsec.group(1) if fsec else h
    tab = re.search(r'id="founders-tab-1"(.*?)(?:id="founders-tab-2"|</table>)', scope, re.S)
    scope = tab.group(1) if tab else scope[:6000]
    founders = re.findall(r'href="/(?:person|company)/[^"]+"[^>]*>([^<]+)</a>', scope)
    seen, rec["founders"] = set(), []
    for f in founders:
        f = clean(f)
        if f and f not in seen:
            seen.add(f)
            rec["founders"].append(f)
    # заявленное число учредителей в навигации
    mn = re.search(r'id="founders"[^>]*>\s*<h2[^>]*>\s*<a[^>]*>\s*Учредители.*?</a>\s*</h2>', h, re.S)
    mc = re.search(r'/founders"[^>]*>\s*Все учредители\s*\((\d+)\)', h)
    if not mc:
        mc = re.search(r'href="/company/[^"]+/founders">\s*Учредители\s*<span class="count">(\d+)<', h)
    rec["founders_total"] = int(mc.group(1)) if mc else len(rec["founders"])
    # контакты
    rec["phones"] = sorted(set(re.findall(r'href="tel:([+\d\s()\-]+)"', h)))
    rec["emails"] = sorted(set(re.findall(r'href="mailto:([^"]+)"', h)))
    rec["site"] = ""
    ms = re.search(r'Сайт\s*[—-]\s*<a[^>]+href="https?://([^"/]+)', h)
    if not ms:
        ms = re.search(r'Сайт</[^>]+>\s*<a[^>]+href="https?://([^"/]+)', h)
    if ms:
        rec["site"] = ms.group(1)
    # ЕФРСБ
    efr = re.search(r'ЕФРСБ \(реестр банкротств\)(.*?)id="bank-account-blocking-section"', h, re.S)
    etxt = clean(efr.group(1)) if efr else ""
    rec["efrsb_text"] = re.sub(r"\s+", " ", etxt)[:400]
    low = etxt.lower()
    if "нет сообщений о банкротстве" in low:
        rec["efrsb"] = "clean"
    elif any(k in low for k in PROC_KEYWORDS):
        rec["efrsb"] = "procedure"
    else:
        rec["efrsb"] = "mention"
    # арбитраж: флаг дела о банкротстве
    arb = re.search(r'Арбитражные дела</div>(.{0,400}?)</div>', h, re.S)
    atxt = clean(arb.group(1)) if arb else ""
    rec["arb_text"] = re.sub(r"\s+", " ", atxt)[:250]
    rec["arb_bankruptcy_case"] = any(k in (atxt + h[:0]).lower() for k in CASE_KEYWORDS)
    # выручка по годам из JS-графика (копейки -> тыс. руб.)
    rec["revenue"] = {}
    mc = re.search(r'if\(code==="2110"\)series=\[\[(.+?)\]\]', h, re.S)
    ml = re.search(r'function draw_fs_chart\(code\)\{\s*const labels=\[([^\]]+)\]', h, re.S)
    if mc and ml:
        years = re.findall(r"'(\d{4})'", ml.group(1))
        vals = re.findall(r"value:'(-?\d+)'", mc.group(1))
        for y, v in zip(years, vals):
            if 2021 <= int(y) <= 2025 and int(v) > 0:
                rec["revenue"][y] = int(v) // 1000
    return rec


def main():
    inn_file, out_dir = sys.argv[1], sys.argv[2]
    founders_pass = "--founders" in sys.argv
    delay = 20
    if "--delay" in sys.argv:
        delay = int(sys.argv[sys.argv.index("--delay") + 1])
    cache_dir = os.path.join(out_dir, "html")
    os.makedirs(cache_dir, exist_ok=True)
    inns = [l.strip() for l in open(inn_file, encoding="utf-8-sig") if l.strip()]
    out_path = os.path.join(out_dir, "checko_enrich.json")
    result = {}
    if os.path.exists(out_path):
        result = json.load(open(out_path, encoding="utf-8"))
    if founders_pass:
        todo = [i for i in inns
                if result.get(i, {}).get("ogrn")
                and not result[i].get("error")
                and result[i].get("founders_total", 0) > len(result[i].get("founders", []))]
        print(f"добор учредителей: {len(todo)} компаний", flush=True)
        for n, inn in enumerate(todo, 1):
            try:
                url = f"https://checko.ru/company/{result[inn]['ogrn']}/founders"
                body = get_url(url, os.path.join(cache_dir, f"{inn}.founders.html"))
                full = parse_founders_page(body)
                if full:
                    result[inn]["founders"] = full
                print(f"{n}/{len(todo)} {inn}: учредителей {len(result[inn]['founders'])}", flush=True)
            except Exception as ex:
                print(f"{n}/{len(todo)} {inn}: ERROR {ex}", flush=True)
            json.dump(result, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            if n < len(todo):
                time.sleep(delay)
        print("добор завершен")
        return
    for n, inn in enumerate(inns, 1):
        if inn in result and result[inn].get("name"):
            print(f"{n}/{len(inns)} {inn}: кэш", flush=True)
            continue
        try:
            body = get_card(inn, cache_dir)
            rec = parse_card(body, inn)
            if rec["card_inn"] and rec["card_inn"] != inn:
                print(f"{n}/{len(inns)} {inn}: ИНН не сошелся ({rec['card_inn']})", flush=True)
            result[inn] = rec
            print(f"{n}/{len(inns)} {inn}: {rec['name'][:40]} | {rec['status'][:24]} | "
                  f"учр {len(rec['founders'])} | efrsb {rec['efrsb']}", flush=True)
        except Exception as ex:
            result[inn] = {"inn": inn, "error": str(ex)}
            print(f"{n}/{len(inns)} {inn}: ERROR {ex}", flush=True)
        json.dump(result, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if n < len(inns):
            time.sleep(delay)
    print("готово:", len(result), "записей ->", out_path)


if __name__ == "__main__":
    main()
