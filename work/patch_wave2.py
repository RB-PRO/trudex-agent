#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Волна 2 добора обогащения (12.11.2026): антибан-методика — поисковая выдача
вместо прямых запросов к агрегаторам + верификация сайтов. Накладывается на enrich_final.json."""
import json

PATCH = {
    "5027184820": {"employees": 24, "note": "ССЧ 24 (РБК); 2 совладельца"},
    "7731533053": {"phone": "+74957759477; +74956642688", "note": "телефоны из карточки checko (сниппет выдачи); ССЧ 537 (b2book)"},
    "5009121087": {"employees": 27, "note": "ССЧ 27 (РБК/audit-it); реорганизация-присоединение"},
    "7723763977": {"employees": 475, "site": "pickpoint.ru", "note": "ССЧ 475 (РБК/ВсеГрузоперевозки; ЗЧБ: 105); ИНН 7723763977 на pickpoint.ru/contacts/ (проверено site_verify.py); КУ Бренинг А.Ш., дело А40-90234/2023"},
    "7722753969": {"phone": "+78005503780", "email": "service@vseinstrumenti.ru; zakaz@vseinstrumenti.ru", "site": "vseinstrumenty.ru", "note": "контакты с vseinstrumenti.ru (сниппет: реквизиты ИНН 7722753969; прямой fetch 403)"},
    "5031106912": {"phone": "+74965173078", "note": "телефон из ЗЧБ"},
    "9704241312": {"phone": "+74994031531", "site": "mosgorlombard.ru", "note": "телефон и реквизиты с ИНН 9704241312 на mosgorlombard.ru/o-kompanii/contacts/"},
    "5031137798": {"phone": "+74951655565", "note": "телефон из офиц. ВК-группы (с ИНН 5031137798); бронирование +7 991 099-99-99"},
    "5048028162": {"phone": "+74967223113", "note": "телефон из реестра СРО Мособлстройкомплекс (npmosk.ru)"},
    "9703127818": {"email": "ysk.v.nik@mail.ru", "note": "email companium; телефон из enrich"},
    "7714524933": {"phone": "+74954190499; +74957817341", "email": "contact@controlsystems.ru", "site": "controlsystems.ru", "note": "контакты со страницы controlsystems.ru/contacts (АО «Системы управления», адрес совпадает); держатель реестра АО «НРК-Р.О.С.Т.»"},
    "7723421691": {"email": "nletyagina@estacons.ru", "note": "HR-email, подтверждён на Госуслугах (trudvsem); входит в ГК «ЭСТА Констракшен»"},
    "7729785198": {"site": "monotekstroy.ru", "note": "офиц. сайт (самоназвание на главной); ИНН в тексте страницы не найден — засчитан по однозначности совпадений"},
    "5005065402": {"phone": "+74964412000", "employees": 13, "site": "voskvartal.ru", "note": "диспетчерская +7(496)441-20-00 (МинЖКХ/openaddress); сайт voskvartal.ru указан как офиц. (МинЖКХ); ССЧ 13 (etker21)"},
    "5001158960": {"founders": "Самоделов Александр Владимирович", "note": "учредитель №1 (РБК); всего 2 учредителя (list-org)"},
    "7725449847": {"employees": 48, "note": "ССЧ 48 (list-org)"},
    "5032252063": {"employees": 648, "note": "ССЧ 648 в 2024 (audit-it; конфликт с list-org 390 — взят более свежий)"},
    "7729050901": {"phone": "+74995699999", "email": "rector@ranepa.ru", "note": "контакты ректората с ranepa.ru"},
    "7751188630": {"note": "подан иск о банкротстве (saby) — процедура не введена, по правилам AGENTS.md остаётся «Действующее»"},
    "7730250045": {"note": "ТПП РФ: сайт gazprom-shelfproject.ru, info@gazprom-shelfproject.ru (fetch сайта ошибку — сайт не засчитан)"},
}

enrich = json.load(open("enrich_final.json", encoding="utf-8"))
for inn, patch in PATCH.items():
    e = dict(enrich.get(inn) or {})
    e.update(patch)
    enrich[inn] = e
json.dump(enrich, open("enrich_final.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("patched:", len(PATCH), "enrich total:", len(enrich))
