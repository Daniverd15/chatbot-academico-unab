#!/bin/bash
# Crea las credenciales e importa/activa los workflows en el contenedor de n8n.
# Ejecutar en la EC2 dentro de ~/chatbot (requiere .env y que el owner de n8n ya exista).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
C=$(docker compose ps -q n8n)

# --- credenciales (mismo ID que usan los workflows) ---
DBU=$(python3 - <<'PY'
import os, json, urllib.parse as u
p = u.urlparse(os.environ["DATABASE_URL"])
creds = [
 {"id": "credGeminiUnab01", "name": "Google Gemini (chatbot-unab)", "type": "googlePalmApi",
  "data": {"host": "https://generativelanguage.googleapis.com", "apiKey": os.environ["GEMINI_API_KEY"]}},
 {"id": "credSupabaseUnab1", "name": "Supabase Postgres (chatbot-unab)", "type": "postgres",
  "data": {"host": p.hostname, "port": p.port or 5432, "database": p.path.lstrip("/"), "user": u.unquote(p.username),
           "password": u.unquote(p.password), "ssl": "require", "allowUnauthorizedCerts": True,
           "sshTunnel": False, "maxConnections": 10}},
 {"id": "credMcpBearer0001", "name": "MCP Bearer (chatbot-unab)", "type": "httpBearerAuth",
  "data": {"token": os.environ["MCP_AUTH_TOKEN"]}},
]
print(json.dumps(creds))
PY
)
echo "$DBU" | docker exec -i -u node "$C" sh -c 'cat > /tmp/creds.json'
docker exec -u node "$C" n8n import:credentials --input=/tmp/creds.json
docker exec -u node "$C" rm -f /tmp/creds.json

# --- workflows ---
docker exec -u node "$C" rm -rf /tmp/wf && docker cp n8n/workflows "$C":/tmp/wf
docker exec -u root "$C" chown -R node:node /tmp/wf
docker exec -u node "$C" n8n import:workflow --separate --input=/tmp/wf

# --- publicar: primero los sub-workflows, al final el chat principal que los invoca ---
for ID in wfUnab02General01 wfUnab03Calendar1 wfUnab04Cursos001 wfUnab05Noticias1 wfUnab06AsesorMcp           wfUnab00Ingesta01 wfUnab05Scraper01 wfUnab07AppApi001 wfUnab08Alertas01 wfUnab01ChatMain1; do
  docker exec -u node "$C" n8n publish:workflow --id="$ID" 2>&1 | grep -E "Publishing|rror" || true
done
docker compose restart n8n
echo "Listo. Workflows importados y activos."
