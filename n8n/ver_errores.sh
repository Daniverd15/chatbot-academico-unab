#!/bin/bash
# Muestra los mensajes de error de las últimas ejecuciones fallidas de n8n (ejecutar en la EC2).
N=${1:-3}
for ID in $(docker exec chatbot-postgres-n8n-1 psql -U n8n -d n8n -Atc "select id from execution_entity where status='error' order by id desc limit $N"); do
  echo "=== ejecución $ID · $(docker exec chatbot-postgres-n8n-1 psql -U n8n -d n8n -Atc "select \"workflowId\" from execution_entity where id=$ID")"
  docker exec chatbot-postgres-n8n-1 psql -U n8n -d n8n -Atc "select data from execution_data where \"executionId\"=$ID" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read())
seen = set()
for x in d:
    if isinstance(x, str) and 25 < len(x) and any(w in x for w in ('Error', 'error', 'rror:', 'not ', 'Cannot', 'invalid', 'does not', 'failed')):
        t = x[:420].replace('\n', ' ')
        if t[:80] not in seen and not t.lstrip().startswith(('at ', 'const ', '//')):
            seen.add(t[:80]); print('  -', t)
" | head -8
done
