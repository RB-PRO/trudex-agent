# Скрипты пайплайна обогащения лидов

Читается по мере надобности. Основной порядок работы описан в `../AGENTS.md`; здесь — вызов и форматы.

## Порядок запуска

```bash
# 1. Эталон ЕГРЮЛ (шаг 1) — ~2.5 с на ИНН
python egrul_fetch.py <inn-файл> egrul_raw.jsonl

# 2. Выручка РФСД (шаг 3) — требует ~1.3 ГБ трафика на 5 лет, один раз
bash rfsd_download.sh rfsd 2021 2022 2023 2024 2025
python rfsd_extract.py rfsd <inn-файл> rfsd_revenue.json

# 2b. Верификация сайтов (шаг 5): кандидаты-домены по ИНН -> только подтверждённые ИНН
python site_verify.py site_candidates.json sites_verified.json
#   site_candidates.json: {"<inn>": ["domain1.ru", "domain2.ru"], ...}
#   sites_verified.json:  {"<inn>": {"site": "...", "url": "...", "evidence": "..."}, ...}

# 3. Шаги 2, 4, 5 — вручную: веб-поиск по ИНН, карточки checko,
#    Федресурс/КАД, сайты. Найденное складывать в enrich.json (схема ниже).

# 4. Сборка и проверка результата
python build_result.py egrul_raw.jsonl enrich.json rfsd_revenue.json leads_result.json
python validate_leads.py leads_result.json
```

## enrich.json — единый файл ручного обогащения

Ключ — ИНН. Поля (все необязательные, кроме отмеченных):

| поле | тип | значение |
|---|---|---|
| `founders` | string | учредители через `; ` |
| `employees` | int \| null | ССЧ (последний известный год) |
| `efrsb` | string * | `clean` \| `mention` (иск/упоминание) \| `case_pending` (дело в КАД) \| `procedure` (процедура введена) |
| `reorg` | bool | true — реорганизация-присоединение в ЕГРЮЛ |
| `site`, `phone`, `email` | string | только верифицированные по ИНН на сайте |
| `revenue_override` | object | точечные правки выручки: `{"2021": 16500000}`; null сбрасывает год |
| `note` | string | любые заметки |

\* Как заполнять `efrsb`: смотрим блок «ЕФРСБ (реестр банкротств)» в карточке checko. Есть сообщения о введённой процедуре → `procedure`. «В арбитражном суде рассматривается дело о банкротстве», но ЕФРСБ чист → `case_pending`. Только упоминание на Федресурсе → `mention`. Иначе → `clean`.

`build_result.py` сам маппит стадии: `procedure` → «В стадии банкротства», `reorg: true` → «В стадии ликвидации», всё остальное → «Действующее».

## Примечания

- `rfsd_download.sh`: версия датасета зашита как `VER` в начале файла; перед большим прогоном сверьте с https://tochno.st/datasets/rfsd (обновляется несколько раз в год).
- Архивы РФСД после `rfsd_extract.py` можно удалять — всё нужное в `rfsd_revenue.json`.
- Скрипты не требуют pip-зависимостей (только стандартная библиотека Python 3).
