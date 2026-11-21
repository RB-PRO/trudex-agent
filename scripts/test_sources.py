#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Префлайт-тест: проверка доступности источников перед прогоном обогащения.

Запускать ПЕРЕД каждым проходом (шаг 0 пайплайна): убеждаемся, что сайты-источники
живы, не отдают 429/капчу и не подменены заглушкой провайдера. Если источник
упал — агент точечно меняет тактику по таблице рекомендаций ниже, а не ломится
в стену (см. AGENTS.md «Как не получить бан»).

Использование: python test_sources.py [--quick]
  --quick  — только критичные источники (эталон + топ-агрегаторы)

Коды выхода: 0 — все критичные OK; 1 — есть падения (см. рекомендации).
Только стандартная библиотека. Проверено на Python 3.12 (Windows, 21.11.2026).
"""
import sys
import time
import urllib.request
import urllib.error

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# (ключ, URL, маркер-подстрока в HTML, критичность, рекомендация при падении)
SOURCES = [
    ("egrul.nalog.ru", "https://egrul.nalog.ru/", "search-result", True,
     "ФНС лежит: пауза 30+ мин, дальше по кругу; фолбэк эталона — агрегаторы "
     "со сверкой по ИНН (как в проходе 12.11.2026)"),
    ("checko.ru", "https://checko.ru/search?query=7705034202", "ПепсиКо", True,
     "429/бан: пауза минимум 30 мин, не дожимать; работать по кэшу work/*/checko/html; "
     "контакты добирать через zachestnyibiznes/list-org/e-ecolog"),
    ("rusprofile.ru", "https://www.rusprofile.ru/id/11846218", "Трикапласт", True,
     "прямые заходы минимизировать; данные брать из сниппетов выдачи"),
    ("zachestnyibiznes.ru", "https://zachestnyibiznes.ru/company/ul/1197746465146_7751167101_OOO-TRIKAPLAST",
     "ТРИКАПЛАСТ", True,
     "телефоны/долги в карточке; при блоке — сниппеты выдачи по «\"<ИНН>\" телефон»"),
    ("list-org.com", "https://www.list-org.com/company/12364574", "ТРИКАПЛАСТ", True,
     "ССЧ и контакты; при блоке — audit-it/saby"),
    ("audit-it.ru", "https://www.audit-it.ru/contragent/1197746465146_ooo-trikaplast",
     "ТРИКАПЛАСТ", False, "досье/выручка; при блоке — rusprofile/testfirm"),
    ("saby.ru", "https://saby.ru/profile/7751167101-507401001", "Трикапласт", False,
     "карточки и сигналы (иск о банкротстве и т.п.)"),
    ("companies.rbc.ru", "https://companies.rbc.ru/id/1197746465146-obschestvo-s-ogranichennoj-otvetstvennostyu-trikaplast/",
     "ТРИКАПЛАСТ", False, "выручка/ССЧ из сниппетов"),
    ("fedresurs.ru", "https://fedresurs.ru/companies/6da7e1e9-8fe5-4b13-8a82-185b16715f11",
     "ПРОФИТ", False, "ЕФРСБ и карточки ЮЛ (контакты указывает сама компания)"),
    ("trudvsem.ru", "https://trudvsem.ru/company/1187746523909", "СТРОЙНИК", False,
     "email подтверждён через Госуслуги; при блоке — hh/superjob"),
    ("tochno.st", "https://tochno.st/datasets/rfsd", "РФСД", False,
     "выручка РФСД: сверить VER в rfsd_download.sh с этой страницей"),
    ("spark-interfax.ru", "https://spark-interfax.ru/moskovskaya-oblast-podolsk/ooo-trikaplast-inn-7751167101-ogrn-1197746465146-8eb57daf73e05e32e0531c9aa8c0bf86",
     "ТРИКАПЛАСТ", False, "демо-данные бесплатны; часть полей платная"),
    ("kontur.ru (focus)", "https://focus.kontur.ru/entity?query=1197746465146",
     "Трикапласт", False, "каталоги рейтингов по выручке — ССЧ/выручка в сниппетах"),
    ("b2b.house", "https://b2b.house/companies/", "Компании", False,
     "каталог; при блоке — companium"),
    ("e-ecolog.ru", "https://e-ecolog.ru/phone/+74957308345", "ТТС", False,
     "телефонный справочник; обратный поиск номера"),
]

CAPTCHA_HINTS = ("captcha", "капча", "are you a robot", "cloudflare", "доступ ограничен",
                 "проверяем ваш браузер")


def check(key, url, marker, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(120_000).decode("utf-8", "ignore")
            code = resp.status
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}", ""
    except Exception as ex:
        return type(ex).__name__, ""
    low = body.lower()
    if any(h in low for h in CAPTCHA_HINTS):
        return "капча/бан", ""
    if code != 200:
        return f"HTTP {code}", ""
    if marker and marker.lower() not in low:
        # 200 без маркера: для критичных — фейл, для прочих — предупреждение
        return ("маркер не найден" if critical else "OK (без маркера)"), ""
    return "OK", ""


def main():
    quick = "--quick" in sys.argv
    rows, fails = [], False
    for key, url, marker, critical, advice in SOURCES:
        if quick and not critical:
            continue
        status, _ = check(key, url, marker)
        rows.append((key, status, critical, advice))
        print(f"{'!' if critical else ' '} {key:24} {status}", flush=True)
        if status != "OK" and critical:
            fails = True
        time.sleep(2)
    bad = [r for r in rows if r[1] != "OK"]
    print()
    if bad:
        print("Падения и тактика:")
        for key, status, critical, advice in bad:
            print(f"  - {key}: {status} -> {advice}")
    else:
        print("Все проверенные источники доступны. Можно запускать пайплайн.")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
