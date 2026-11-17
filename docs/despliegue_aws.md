# Despliegue en AWS (EC2 + Docker Compose)

Guía para reproducir el despliegue desde cero. Está basada en el repositorio `n8n-workshop` del profesor (n8n en EC2) y adaptada con el servidor MCP, Caddy y Supabase.

## 1. Resultado esperado

| Elemento | Valor |
|---|---|
| Cuenta | AWS Academy Learner Lab, región us-east-1 |
| Instancia | `chatbot-unab`, Ubuntu 24.04, t3.medium, 30 GB gp3, 4 GB de swap |
| IP elástica | 35.168.41.252 |
| Security Group | `chatbot-unab-sg`: TCP 22, 80, 443, 5678, 9000 |
| n8n | `https://n8n.35-168-41-252.sslip.io` |
| Servidor MCP | `https://mcp.35-168-41-252.sslip.io` (endpoint `/mcp`, salud en `/health`) |
| Web + chat y presentación | `https://unabot.35-168-41-252.sslip.io` y `/presentacion/` |
| Observatorio académico | `https://observatorio.35-168-41-252.sslip.io` |
| Base de datos | Supabase (PostgreSQL 17 + pgvector), fuera de la EC2 |

Servicios de Docker Compose: `postgres-n8n` (metadatos de n8n), `n8n`, `mcp-server`, `dashboard` (Observatorio, Streamlit en el puerto 8501) y `caddy`. El cliente web (`web/`) no es un contenedor: Caddy lo sirve como archivos estáticos montados en `/srv/web`.

## 2. Requisitos previos

- Acceso a AWS Academy Learner Lab (botón *Start Lab* y AWS CloudShell).
- Un proyecto de Supabase (región East US) con la contraseña de la base y la cadena del **Session pooler** (Connect → Session pooler; usa IPv4).
- API key de Google Gemini (aistudio.google.com).
- Opcional: una hoja de Google Sheets con el calendario publicada como CSV (Archivo → Compartir → Publicar en la web → CSV). Estado actual: la hoja aún no está publicada; mientras `CALENDAR_SHEET_CSV_URL` esté vacía, el sistema usa la tabla `chatbot.calendario`.
- Un par de llaves SSH propio. Genera uno con `ssh-keygen -t rsa -b 4096` y conserva la llave privada.

## 3. Paso a paso

### Paso 1. Crear la infraestructura con CloudShell

1. Inicia el laboratorio (*Start Lab*) y abre **AWS CloudShell** en us-east-1.
2. Copia `infra/aws_cloudshell_provision.sh` a CloudShell. **Antes de ejecutarlo, reemplaza la llave pública** del script (la línea `echo "ssh-rsa ..." > /tmp/k.pub`) por tu propia llave pública; si dejas la del script no tendrás la llave privada correspondiente y no podrás entrar por SSH.
3. Ejecútalo: `bash aws_cloudshell_provision.sh`.

El script, en orden:

- importa el key pair `chatbot-unab-key`;
- localiza la VPC por defecto y crea (o reutiliza) el Security Group `chatbot-unab-sg` con ingreso desde `0.0.0.0/0` a los puertos 22, 80, 443, 5678 y 9000;
- busca la AMI más reciente de Ubuntu 24.04 (propietario 099720109477);
- lanza una `t3.medium` con disco gp3 de 30 GB, etiqueta `Name=chatbot-unab` y un *user data* que crea 4 GB de swap, instala Docker, agrega `ubuntu` al grupo `docker` y fija la zona horaria `America/Bogota`;
- asigna una **IP elástica** y la imprime junto con el ID de la instancia.

Anota la IP. Los dominios se construyen reemplazando los puntos por guiones: para `35.168.41.252` son `n8n.35-168-41-252.sslip.io`, `mcp.35-168-41-252.sslip.io`, `unabot.35-168-41-252.sslip.io` y `observatorio.35-168-41-252.sslip.io` (sslip.io resuelve cualquier IP embebida en el nombre).

Espera 2–3 minutos a que termine el *user data* y conéctate:

```bash
ssh -i ~/.ssh/<tu-llave-privada> ubuntu@35.168.41.252
docker --version        # debe responder; si no, espera a que termine el user data
```

### Paso 2. Clonar el repositorio y configurar `.env`

```bash
git clone <url-del-repositorio> chatbot-academico-unab
cd chatbot-academico-unab
cp .env.example .env
nano .env
```

Variables (los nombres están en `.env.example`; **no pegues valores reales en el repositorio**):

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | Cadena del Session pooler de Supabase con el usuario `postgres.<project_ref>`; solo para cargar datos |
| `MCP_DB_PASSWORD` | Contraseña que se asignará al rol `mcp_readonly` |
| `MCP_DATABASE_URL` | Misma cadena pero con el usuario `mcp_readonly.<project_ref>` y `MCP_DB_PASSWORD` |
| `GEMINI_API_KEY`, `GEMINI_CHAT_MODEL`, `GEMINI_FAST_MODEL`, `GEMINI_EMBED_MODEL` | Clave y modelos; los modelos por uso están en la tabla de [workflows_n8n.md](workflows_n8n.md#3-modelos) (`gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-embedding-001`) |
| `MCP_AUTH_TOKEN` | Token largo aleatorio para el Bearer del servidor MCP |
| `N8N_VERSION` | Versión de la imagen de n8n (`latest` o una fija, p. ej. 2.47.x) |
| `N8N_DOMAIN`, `MCP_DOMAIN` | `n8n.<IP-con-guiones>.sslip.io` y `mcp.<IP-con-guiones>.sslip.io` |
| `WEB_DOMAIN`, `DASH_DOMAIN` | `unabot.<IP-con-guiones>.sslip.io` (web y presentación) y `observatorio.<IP-con-guiones>.sslip.io` (Observatorio) |
| `DASH_DATABASE_URL` | Opcional: cadena de solo lectura para el Observatorio; si no existe usa `MCP_DATABASE_URL` |
| `N8N_DB_PASSWORD` | Contraseña del Postgres interno de n8n |
| `N8N_ENCRYPTION_KEY` | Clave aleatoria de 32 caracteres para cifrar las credenciales de n8n |
| `APP_API_KEY` | Clave que usa la app móvil en la cabecera `x-api-key` |
| `CALENDAR_SHEET_CSV_URL` | URL del CSV publicado del calendario; vacía mientras la hoja no esté publicada (se usa `chatbot.calendario`) |

Genera valores aleatorios con `openssl rand -hex 24`. Guarda `N8N_ENCRYPTION_KEY`: si se pierde, las credenciales guardadas en n8n no se pueden descifrar.

### Paso 3. Levantar los servicios

```bash
docker compose up -d --build
docker compose ps
```

Caddy solicita los certificados de Let's Encrypt la primera vez (necesita los puertos 80 y 443 abiertos y los dominios resolviendo a la IP). Verifica:

```bash
curl https://mcp.35-168-41-252.sslip.io/health      # {"status":"ok","db":true,...}
```

abre `https://unabot.35-168-41-252.sslip.io` (web) y `https://observatorio.35-168-41-252.sslip.io` (Observatorio), y entra a `https://n8n.35-168-41-252.sslip.io` para crear la cuenta de propietario de n8n. Nota: `/health` responde `db: false` hasta que la base esté cargada (paso 4) y `MCP_DATABASE_URL` sea correcta.

### Paso 4. Cargar la base de datos

Desde tu equipo o desde la EC2 (necesita Python 3.12 y las dependencias):

```bash
python -m venv .venv && source .venv/bin/activate
pip install faker numpy "psycopg[binary]" python-dotenv requests beautifulsoup4 pypdf google-genai
python database/generate_synthetic_data.py --estudiantes 420 --seed 42   # si data/synthetic/ no existe
python database/load_database.py
```

`load_database.py` crea los esquemas, vistas y funciones, carga los CSV con `COPY`, carga el calendario, asigna la contraseña al rol `mcp_readonly` y al final imprime los indicadores del programa y las cuentas demo. Es idempotente: recrea los esquemas `academico` y `chatbot`, **incluida la tabla del RAG**, así que después hay que volver a ingerir (paso 5).

### Paso 5. Ingesta del RAG y noticias

```bash
python rag/fetch_corpus.py           # opcional: ya hay 16 documentos en rag/corpus/md
python rag/ingest.py                 # ~245 fragmentos; puede tardar por la cuota gratuita de Gemini
python scraper/scraper_noticias.py --embed
```

Para ver solo la fragmentación sin gastar cuota: `python rag/ingest.py --dry-run`.

### Paso 6. Importar y activar los workflows de n8n

```bash
bash n8n/setup_n8n.sh
```

El script crea las tres credenciales de n8n (Gemini, Postgres de Supabase y Bearer del MCP), importa los workflows de `n8n/workflows/`, publica primero los sub-workflows y al final el chat, y reinicia n8n. Luego, en el editor de n8n, verifica que los workflows 00, 01, 05b y 07 estén activos y prueba el chat. Detalle en [workflows_n8n.md](workflows_n8n.md).

### Paso 7. Verificar

```bash
# Servidor MCP
curl https://mcp.35-168-41-252.sslip.io/health
python mcp_server/test_client.py https://mcp.35-168-41-252.sslip.io/mcp U00100001

# Login por el puente REST
curl -X POST https://mcp.35-168-41-252.sslip.io/api/login \
  -H "Authorization: Bearer $MCP_AUTH_TOKEN" -H "Content-Type: application/json" \
  -d '{"codigo":"U00100001","pin":"1234"}'

# Chat completo a través de n8n
curl -X POST https://n8n.35-168-41-252.sslip.io/webhook/chat \
  -H "x-api-key: $APP_API_KEY" -H "Content-Type: application/json" \
  -d '{"codigo":"U00100001","pin":"1234","mensaje":"¿Qué es la insignia digital?","session_id":"U00100001"}'
```

Finalmente configura `apiUrl` y `apiKey` en `mobile/app.json` y prueba la app ([app_movil.md](app_movil.md)).

## 4. Learner Lab: la instancia se detiene

AWS Academy Learner Lab **detiene la instancia EC2 cuando termina la sesión del laboratorio** (o se agota el tiempo/presupuesto). Para retomar:

1. Presiona *Start Lab* y espera el indicador verde.
2. La instancia vuelve con la **misma IP elástica**; los dominios `sslip.io` siguen siendo válidos.
3. Los contenedores se reinician solos porque todos tienen `restart: unless-stopped` y Docker arranca con el sistema. Los datos persisten en los volúmenes (`n8n_db`, `n8n_data`, `caddy_data`) y en Supabase.
4. Comprueba con `docker compose ps` y `curl .../health`. Antes de una demostración o evaluación, inicia el laboratorio con anticipación.

Si se elimina la instancia o el laboratorio se reinicia desde cero, hay que repetir los pasos 1–3 y 6 (la base en Supabase sigue disponible).

## 5. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| Caddy no obtiene certificado / error TLS | Puertos 80/443 cerrados, o dominio mal escrito en `.env` | Revisar el Security Group; la IP va con **guiones** (`35-168-41-252`); `docker compose logs caddy` |
| `/health` devuelve `db: false` o `degraded` | `MCP_DATABASE_URL` errónea, rol sin contraseña o base sin cargar | Revisar el usuario `mcp_readonly.<project_ref>`; ejecutar `load_database.py` con `MCP_DB_PASSWORD` definido |
| Error de conexión a Supabase desde la EC2 | Se usó la conexión directa (solo IPv6) | Usar la cadena del **Session pooler** (IPv4) |
| `401 unauthorized` desde n8n al MCP | Token distinto al de `.env` | Recrear la credencial Bearer con el mismo `MCP_AUTH_TOKEN` y reiniciar `docker compose up -d` |
| La app recibe 401/403 | `apiKey` de la app distinta de `APP_API_KEY` | Igualar ambos valores |
| Webhook responde 404 | Workflow inactivo o se usa la URL de prueba (`/webhook-test/`) | Activar el workflow y usar `/webhook/...` |
| Los workflows importados no tienen credenciales | Las credenciales no viajan en el JSON | Crearlas en la interfaz y asignarlas |
| Errores 429 de Gemini | Cuota de la capa gratuita | Esperar; `ingest.py` reintenta con espera exponencial; reducir pruebas seguidas |
| Una ejecución de n8n falla sin mensaje claro | Error en un nodo del workflow | Ejecutar `bash n8n/ver_errores.sh` para ver los errores de las ejecuciones fallidas |
| El RAG no devuelve resultados tras recargar la base | `load_database.py` recrea `rag_documentos` | Ejecutar `rag/ingest.py` y `scraper_noticias.py --embed` |
| Las credenciales de n8n dejaron de funcionar | Cambió `N8N_ENCRYPTION_KEY` | Restaurar la clave original o recrear las credenciales |
| Falta memoria / contenedores se reinician | t3.medium con poca RAM | Confirmar el swap (`swapon --show`); revisar `docker stats` |
| `docker: permission denied` | Sesión SSH abierta antes de que el usuario entrara al grupo `docker` | Cerrar y volver a abrir la sesión |

Comandos útiles:

```bash
docker compose logs -f n8n          # registros de n8n
docker compose logs -f mcp-server   # registros del servidor MCP
docker compose restart mcp-server
docker compose pull && docker compose up -d   # actualizar imágenes (n8n)
```

## 6. Seguridad del despliegue

- Mantén `.env` fuera del repositorio (está en `.gitignore`) y no lo compartas.
- Los puertos 5678 y 9000 están abiertos por conveniencia de las pruebas; en un despliegue real conviene cerrarlos y dejar solo 80/443 (Caddy ya hace el proxy de ambos servicios).
- Rota `MCP_AUTH_TOKEN` y `APP_API_KEY` si se exponen.
