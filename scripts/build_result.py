#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Сборка leads_result.json из трех источников.
Использование: python build_result.py <egrul_raw.jsonl> <enrich.json|-> <rfsd_revenue.json|-> <leads_result.json>

Источники:
  egrul_raw.jsonl  — вывод egrul_fetch.py (эталон: название, директор, дата, статус)
  enrich.json      — ручное обогащение с агрегаторов, по ИНН. Схема записи см. README.
  rfsd_revenue.json — вывод rfsd_extract.py. Для годов без данных — null.

Правила сборки (из AGENTS.md):
  - директор из эталона разбивается на ф/и/о; не разбивается -> пустые строки
  - efrsb == "procedure" -> "В стадии банкротства"; reorg == true -> "В стадии ликвидации";
    иначе "Действующее"
  - выручка: РФСД; точечные правки через enrich["revenue_override"] = {"2021": 16500000}
  - revenue_2026..2029 всегда null
"""
import json, re, sys

def split_director(raw):
    m = re.search(r":\s*([^:]+)$", raw or "")
    if not m:
        return "", "", ""
    parts = m.group(1).strip().split()
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1], ""
    return "", "", ""

def main():
    egrul_path, enrich_path, rev_path, out_path = sys.argv[1:5]
    enrich = json.load(open(enrich_path, encoding="utf-8")) if enrich_path != "-" else {}
    revenue = json.load(open(rev_path, encoding="utf-8")) if rev_path != "-" else {}
    result = []
    for line in open(egrul_path, encoding="utf-8"):
        st = json.loads(line)
        inn = st["inn"]
        e = enrich.get(inn, {})
        rec = {"inn": inn}
        rows = (st.get("resp") or {}).get("rows") or []
        if not rows:
            rec.update({"name": "", "phone": "", "email": "", "director_last": "", "director_first": "",
                        "director_middle": "", "revenue_2021": None, "revenue_2022": None, "revenue_2023": None,
                        "revenue_2024": None, "revenue_2025": None, "revenue_2026": None, "revenue_2027": None,
                        "revenue_2028": None, "revenue_2029": None, "reg_date": "", "site": "", "employees": None,
                        "founders": "", "bankruptcy_stage": "Действующее"})
            result.append(rec)
            continue
        r0 = rows[0]
        rv = revenue.get(inn, {})
        override = e.get("revenue_override", {})
        dl, df, dm = split_director(r0.get("g", ""))
        if e.get("efrsb") == "procedure":
            stage = "В стадии банкротства"
        elif e.get("reorg"):
            stage = "В стадии ликвидации"
        else:
            stage = "Действующее"
        rec.update({
            "name": r0.get("c", ""),
            "phone": e.get("phone", "") or "",
            "email": e.get("email", "") or "",
            "director_last": dl, "director_first": df, "director_middle": dm,
            "revenue_2021": override.get("2021", rv.get("2021")),
            "revenue_2022": override.get("2022", rv.get("2022")),
            "revenue_2023": override.get("2023", rv.get("2023")),
            "revenue_2024": override.get("2024", rv.get("2024")),
            "revenue_2025": override.get("2025", rv.get("2025")),
            "revenue_2026": None, "revenue_2027": None, "revenue_2028": None, "revenue_2029": None,
            "reg_date": r0.get("r", ""),
            "site": e.get("site", "") or "",
            "employees": e.get("employees"),
            "founders": e.get("founders", "") or "",
            "bankruptcy_stage": stage,
        })
        result.append(rec)
    json.dump(result, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("records:", len(result))

if __name__ == "__main__":
    main()
