# UNABot · cliente web

Landing + cliente de chat estático (HTML/CSS/JS vanilla, sin build). Pensado para servirse con Caddy en la raíz del sitio.

## Archivos
- `index.html` — landing, login y app
- `assets/styles.css`, `assets/app.js`, `assets/logo.svg`

## Backend
Rutas relativas (mismo origen), que Caddy proxea a n8n añadiendo la API key en el servidor (la página no contiene ninguna clave):
`POST /api/app/login`, `/api/app/dashboard`, `/api/chat`, `/api/app/feedback`.

## Desarrollo sin backend
```
cd web && python -m http.server 8080
# abrir http://localhost:8080/?mock=1   (cuentas U00100001..U00100005, PIN 1234)
```

## Notas
- Credenciales solo en `sessionStorage`; tema en `localStorage`.
- Markdown de las respuestas: escapado HTML previo, enlaces solo http(s) con `rel="noopener noreferrer"`.
- Única dependencia externa: Google Fonts (Poppins).
