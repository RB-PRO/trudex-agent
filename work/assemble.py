#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Сборка leads-результата из checko+РФСД+ручных данных (обход недоступного API ФНС).

Использование: python work/assemble.py
Вход:  work/checko/checko_enrich.json, work/rfsd_revenue.json, work/manual_enrich.json
Выход: work/egrul_raw.jsonl, work/enrich.json, work/revenue_merged.json
Затем: python scripts/build_result.py work/egrul_raw.jsonl work/enrich.json work/revenue_merged.json <out.json>
"""
import json
import re

STATUS_MAP = [
    ("действующ", ""),
    ("ликвидирован", "Ликвидировано"),
    ("процессе ликвидации", "В процессе ликвидации"),
    ("реорганиз", "Реорганизация"),
    ("присоединен", "Реорганизация"),
    ("банкрот", "В процессе банкротства"),
    ("исключен", "Исключено из ЕГРЮЛ"),
    ("прекращ", "Прекращение деятельности"),
]


def map_status(s):
    s = (s or "").lower()
    for key, val in STATUS_MAP:
        if key in s:
            return val
    return ""


def fmt_phone(p):
    d = re.sub(r"\D", "", p)
    if d.startswith("8") and len(d) == 11:
        d = "7" + d[1:]
    if d.startswith("7") and len(d) == 11:
        return "+" + d
    if len(d) == 10:
        return "+7" + d
    return ""


def main():
    checko = json.load(open("work/checko/checko_enrich.json", encoding="utf-8"))
    rfsd = json.load(open("work/rfsd_revenue.json", encoding="utf-8"))
    manual = json.load(open("work/manual_enrich.json", encoding="utf-8"))
    inns = [l.strip() for l in open("../лиды/10.11.2026/martInspections_inn.txt", encoding="utf-8-sig") if l.strip()]

    egrul_lines, enrich, revenue_merged = [], {}, {}
    for inn in inns:
        c = checko.get(inn, {})
        err = c.get("error")
        name = c.get("name", "") if not err else ""
        if name:
            role = c.get("director_role") or "Директор"
            g = f"{role}: {c.get('director', '')}" if c.get("director") else ""
            row = {"c": name, "g": g, "r": c.get("reg_date", ""),
                   "e": map_status(c.get("status", "")), "k": ""}
            egrul_lines.append(json.dumps({"inn": inn, "resp": {"rows": [row]}}, ensure_ascii=False))
        else:
            egrul_lines.append(json.dumps({"inn": inn, "resp": {"rows": []}}, ensure_ascii=False))
        # enrich
        e = {}
        m = manual.get(inn, {})
        founders = c.get("founders", []) if not err else []
        total = c.get("founders_total", len(founders)) if not err else 0
        if founders:
            fstr = "; ".join(founders)
            if total and total > len(founders):
                fstr += f" (всего {total} учредителей)"
            e["founders"] = fstr
        phones = [fmt_phone(p) for p in (c.get("phones", []) if not err else [])]
        phones = [p for p in phones if p]
        if m.get("phone"):
            for p in m["phone"].split("; "):
                fp = fmt_phone(p)
                if fp and fp not in phones:
                    phones.append(fp)
        if phones:
            e["phone"] = "; ".join(phones)
        emails = list(c.get("emails", []) if not err else [])
        if m.get("email"):
            for x in m["email"].split("; "):
                if x not in emails:
                    emails.append(x)
        if emails:
            e["email"] = "; ".join(emails)
        site = m.get("site") or (c.get("site", "") if not err else "")
        if site:
            e["site"] = site
        if m.get("employees") is not None:
            e["employees"] = m["employees"]
        efrsb = m.get("efrsb") or (c.get("efrsb") if not err else None)
        if efrsb and efrsb != "clean":
            e["efrsb"] = efrsb
        status_l = (c.get("status", "") if not err else "").lower()
        if "реорганиз" in status_l or "присоединен" in status_l:
            e["reorg"] = True
        if m.get("note"):
            e["note"] = m["note"]
        enrich[inn] = e
        # выручка: РФСД приоритет, checko добор
        merged = {}
        rf = rfsd.get(inn, {})
        ck = c.get("revenue", {}) if not err else {}
        for y in ("2021", "2022", "2023", "2024", "2025"):
            v = rf.get(y)
            if v is None:
                v = ck.get(y)
            if v is not None:
                merged[y] = v
        revenue_merged[inn] = merged

    open("work/egrul_raw.jsonl", "w", encoding="utf-8").write("\n".join(egrul_lines) + "\n")
    json.dump(enrich, open("work/enrich.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(revenue_merged, open("work/revenue_merged.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("egrul_raw:", len(egrul_lines), "enrich:", len(enrich), "revenue:", sum(1 for v in revenue_merged.values() if v))


if __name__ == "__main__":
    main()
