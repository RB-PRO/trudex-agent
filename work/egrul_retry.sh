#!/bin/bash
# Цикл повторов ЕГРЮЛ: пока есть пустые записи и не вышло время — перезапускаем fetch.
cd "$(dirname "$0")"
DEADLINE=$(( $(date +%s) + 2400 ))  # 40 минут
: > egrul_retry.log
while [ $(date +%s) -lt $DEADLINE ]; do
  python -X utf8 ../scripts/egrul_fetch.py inn_missing.txt egrul_fix.jsonl >> egrul_retry.log 2>&1
  ok=$(python -X utf8 -c "
import json,sys
n=0
for l in open('egrul_fix.jsonl',encoding='utf-8'):
    st=json.loads(l)
    if (st.get('resp') or {}).get('rows'): n+=1
print(n)")
  echo "$(date +%H:%M:%S) ok=$ok/34" >> egrul_retry.log
  [ "$ok" -ge 34 ] && break
  sleep 170
done
echo "retry loop finished, ok=$ok" >> egrul_retry.log
