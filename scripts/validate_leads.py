#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Проверка leads_result.json по leads_schema.json (без jsonschema).
Использование: python validate_leads.py <leads_result.json>"""
import json, re, sys

REQ = ["inn", "name", "phone", "email", "director_last", "director_first", "director_middle",
       "revenue_2021", "revenue_2022", "revenue_2023", "revenue_2024", "revenue_2025", "revenue_2026",
       "revenue_2027", "revenue_2028", "revenue_2029", "reg_date", "site", "employees", "founders",
       "bankruptcy_stage"]

def main():
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    errs = []
    if not isinstance(data, list):
        print("Файл должен быть массивом"); sys.exit(1)
    for i, r in enumerate(data):
        inn = r.get("inn", f"#{i}")
        for k in REQ:
            if k not in r:
                errs.append(f"{inn}: нет поля {k}")
        if not re.match(r"^\d{10}(\d{2})?$", r.get("inn", "")):
            errs.append(f"{inn}: ИНН не по паттерну")
        rd = r.get("reg_date", "")
        if rd and not re.match(r"^\d{2}\.\d{2}\.\d{4}$", rd):
            errs.append(f"{inn}: reg_date '{rd}' не ДД.ММ.ГГГГ")
        if r.get("bankruptcy_stage") not in ("В стадии банкротства", "В стадии ликвидации", "Действующее"):
            errs.append(f"{inn}: стадия вне enum")
        for y in range(2021, 2030):
            v = r.get(f"revenue_{y}")
            if v is not None and not isinstance(v, int):
                errs.append(f"{inn}: revenue_{y} не целое")
        if r.get("employees") is not None and not isinstance(r["employees"], int):
            errs.append(f"{inn}: employees не целое")
        for k in ("name", "phone", "email", "site", "founders", "director_last", "director_first", "director_middle"):
            if not isinstance(r.get(k), str):
                errs.append(f"{inn}: {k} не строка")
    print("записей:", len(data))
    if errs:
        print("ОШИБКИ:")
        print("\n".join(errs[:50]))
        sys.exit(1)
    print("OK")

if __name__ == "__main__":
    main()
