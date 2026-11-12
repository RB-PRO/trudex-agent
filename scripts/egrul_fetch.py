#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Шаг 1: эталон по ИНН с egrul.nalog.ru.
Использование: python egrul_fetch.py <inn-файл> <out.jsonl>
Каждая строка out.jsonl: {"inn": ..., "resp": {"rows": [...]}} или {"inn": ..., "error": ...}."""
import json, sys, time, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
BASE = "https://egrul.nalog.ru"


def req(url, data=None):
    r = urllib.request.Request(url, data=data, headers={
        "User-Agent": UA, "Referer": BASE + "/index.html",
        "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    inn_file, out = sys.argv[1], sys.argv[2]
    inns = [l.strip() for l in open(inn_file, encoding="utf-8-sig") if l.strip()]
    with open(out, "w", encoding="utf-8") as f:
        for inn in inns:
            rec = {"inn": inn}
            try:
                t = req(BASE + "/", f"vyp3CaptchaToken=&page=&query={inn}&region=&PreventChromeAutocomplete=".encode()).get("t")
                if not t:
                    rec["error"] = "no_token"
                else:
                    # ФНС часто отдает {"rows": []}, если результат еще не готов — повторяем GET с тем же токеном.
                    for attempt in range(4):
                        time.sleep(2 + attempt)
                        resp = req(f"{BASE}/search-result/{t}")
                        if resp.get("rows"):
                            rec["resp"] = resp
                            break
                    else:
                        rec["resp"] = resp  # последний ответ (rows: []) — для отладки
            except Exception as ex:
                rec["error"] = str(ex)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            print(inn, "ok" if (rec.get("resp") or {}).get("rows") else rec.get("error", "empty"), flush=True)
            time.sleep(2)


if __name__ == "__main__":
    main()
