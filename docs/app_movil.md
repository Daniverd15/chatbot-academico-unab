# Aplicación móvil Android

App en **Expo SDK 58 / React Native 0.88 / React 19 / TypeScript** (`mobile/`), basada en el repositorio `Deployment-Mobile-Yolo` del profesor. Nombre "Chatbot UNAB", paquete Android `co.edu.unab.chatbotacademico`, color primario `#8E00E6`.

La app **no accede a la base de datos ni a Gemini**: solo llama a los webhooks de n8n con una clave de API, el código estudiantil y el PIN.

## 1. Pantallas

| Pantalla | Archivo | Contenido |
|---|---|---|
| Inicio de sesión | `src/screens/LoginScreen.tsx` | Código estudiantil y PIN (4 a 8 dígitos). Muestra la cuenta demo. |
| Inicio | `HomeScreen.tsx` | Tarjetas: **Mi avance** (porcentaje, PGA acumulado y del último periodo, semestre, estado académico, estado de matrícula, riesgo), **¿Por qué?** (explicación del riesgo: barras divergentes por factor, rojo si aumenta y verde si reduce, ancho proporcional a la contribución, valor propio frente a la media del programa; componente `RiskFactors.tsx`), **Alertas** por prioridad, **Competencias digitales** (3 rutas e insignia), **Proyección de grado** (semestres restantes, periodo P50/P90 y cursos de mayor riesgo). Deslizar hacia abajo recarga. |
| Chat | `ChatScreen.tsx` | Conversación con el asistente; sugerencias iniciales (por ejemplo "¿Cómo voy en la carrera?", "¿Cuándo me gradúo?", "¿Qué cursos puedo inscribir?"); respuestas en Markdown; chips con las fuentes citadas; indicador "Mensaje bloqueado" cuando actúan los guardrails; animación de escritura. |
| Plan de estudios | `PlanScreen.tsx` | Semestres con cada curso, créditos, nota de aprobación y estado (Aprobado, Cursando, Reprobado pendiente, Pendiente) con leyenda de colores. |
| Novedades | `NewsScreen.tsx` | Control segmentado **Noticias** / **Calendario**: noticias de la UNAB con tipo y fecha, y próximos eventos académicos. |
| Perfil | `ProfileScreen.tsx` | Datos del estudiante y cierre de sesión. |

Componentes compartidos en `src/components/`: `Badge`, `Card`, `Markdown`, `ProgressBar`, `TabBar`, `TypingDots`. Barra inferior con cuatro pestañas (Inicio, Chat, Plan, Novedades); el perfil se abre desde el encabezado.

## 2. Comportamiento de sesión

- Al iniciar sesión correctamente, `src/storage.ts` guarda `{codigo, pin, nombre}` en **expo-secure-store** (almacenamiento cifrado del dispositivo).
- Al abrir la app intenta un inicio automático con `/app/login`. Si las credenciales ya no son válidas, borra la sesión; si no hay conexión, entra con la sesión guardada y reintenta cargar.
- El historial del chat vive en memoria mientras la sesión esté abierta; la memoria de largo plazo está en el servidor (`n8n_chat_histories`, con `session_id` igual al código).
- Cerrar sesión borra el almacenamiento seguro, los datos y los mensajes.
- Los errores se traducen a mensajes claros en español: 401/403 (clave inválida), servicio no disponible, tiempo agotado (30 s) y sin conexión.

## 3. Contrato de la API

`apiUrl` base: `https://n8n.35-168-41-252.sslip.io/webhook`. Todas las llamadas son `POST` con `Content-Type: application/json` y la cabecera `x-api-key` con la clave de la app (variable `APP_API_KEY` del servidor).

### `POST /app/login`

```json
// solicitud
{ "codigo": "U00100001", "pin": "1234" }
// respuesta correcta
{ "ok": true, "estudiante": { "codigo": "U00100001", "nombre_completo": "...", "programa": "Ingeniería de Sistemas", "cohorte": "2024-1" } }
// respuesta con error de credenciales
{ "ok": false, "mensaje": "Código o PIN incorrectos." }
```

### `POST /app/dashboard`

Solicitud: `{ "codigo": "...", "pin": "..." }`. Respuesta (tipos en `src/types.ts`):

```json
{
  "ok": true,
  "resumen":      { "nombre_completo": "...", "creditos_aprobados": 0, "creditos_totales": 154, "porcentaje_avance": 0.0,
                    "pga_acumulado": 0.0, "pga_ultimo_periodo": 0.0, "semestre_por_creditos": 0,
                    "estado_academico": "Normal", "estado_matricula_actual": "Matriculado", "saldo_pendiente": 0 },
  "alertas":      [ { "prioridad": "ALTA|MEDIA|BAJA|INFO", "tipo": "...", "mensaje": "..." } ],
  "competencias": [ { "ruta": 1, "ruta_nombre": "...", "cumplida": true, "en_curso": false, "detalle": "..." } ],
  "avance":       [ { "semestre": 1, "cursos": [ { "curso_id": "...", "curso": "...", "creditos": 4, "estado": "Aprobado", "nota_aprobacion": 4.0 } ] } ],
  "proyeccion":   { "semestres_restantes_ideal": 0, "periodo_grado_ideal": "...", "proyeccion_probabilistica": { "periodo_grado_p50": "...", "periodo_grado_p90": "...", "cursos_con_mayor_riesgo_de_reprobar": [ { "curso": "...", "prob_reprobar": 0.2 } ] }, "plan_sugerido": [] },
  "riesgo":       { "probabilidad": 0.12, "nivel": "bajo|medio|alto", "explicacion": "...", "factores": [ { "feature": "pga_acumulado", "etiqueta": "PGA acumulado", "valor": 3.8, "media": 3.5, "contribucion": -1.42, "efecto": "reduce" } ] },
  "noticias":     [ { "titulo": "...", "url": "...", "fecha_pub": "...", "tipo": "...", "resumen": "..." } ],
  "calendario":   [ { "categoria": "...", "evento": "...", "fecha_inicio": "...", "fecha_fin": "..." } ]
}
```

Los valores numéricos del ejemplo son marcadores de posición. Esta respuesta la arma el endpoint `/api/dashboard` del servidor MCP (ver [servidor_mcp.md](servidor_mcp.md)).

### `POST /chat`

```json
// solicitud
{ "codigo": "U00100001", "pin": "1234", "mensaje": "¿Cuándo me gradúo?", "session_id": "U00100001" }
// respuesta
{ "respuesta": "texto en Markdown", "intencion": "asesoria_academica", "fuentes": [ { "titulo": "...", "url": "..." } ], "bloqueado": false }
```

## 4. Configuración: `apiUrl` y `apiKey`

Los dos valores los define `mobile/app.config.js`, que los expone en `extra` y la app lee con `expo-constants`. La `apiKey` se toma de la variable de entorno `APP_API_KEY` en el momento de compilar, así que no se escribe en el repositorio:

```json
"extra": {
  "apiUrl": "https://n8n.35-168-41-252.sslip.io/webhook",
  "apiKey": "<valor de APP_API_KEY al compilar>"
}
```

Define `APP_API_KEY` con el valor de tu `.env` antes de compilar o iniciar Expo (por ejemplo `APP_API_KEY=... npx expo start -c`). **No subas el valor al repositorio público.** Si cambias el dominio o la IP, actualiza `apiUrl` (sin barra final) en `mobile/app.config.js`. Tras cambiar la configuración hay que reiniciar Metro (`npx expo start -c`) o recompilar.

## 5. Ejecutar con Expo Go

Requisitos: Node.js 20 o superior, la app **Expo Go** en un celular Android (misma red Wi-Fi que el computador) y el backend en línea.

```bash
cd mobile
npm install
npx expo start
```

Escanea el código QR con Expo Go. Para un emulador: `npm run android`. Inicia sesión con `U00100001` y PIN `1234`. Como el backend usa HTTPS con certificado válido, no se requiere configuración adicional de red.

Verificación de tipos y diagnóstico: `npx tsc --noEmit` y `npx expo-doctor`.

## 6. Generar el APK

### Opción A: local con Gradle

Requiere JDK 21 y Android SDK (Android Studio) con `ANDROID_HOME` configurado. La `apiKey` se inyecta desde la variable `APP_API_KEY` a través de `mobile/app.config.js`, así que debe estar definida en el entorno antes de compilar.

```bash
cd mobile
APP_API_KEY=<valor de tu .env> npx expo prebuild --platform android   # genera la carpeta android/ (excluida de git)
cd android
./gradlew assembleRelease                 # en Windows: gradlew.bat assembleRelease
```

El APK queda en `mobile/android/app/build/outputs/apk/release/app-release.apk`. Por defecto la plantilla firma el *release* con la llave de depuración, suficiente para instalar en un celular y para la demostración (no sirve para publicar en Google Play). Instálalo con `adb install app-release.apk` o copiándolo al teléfono.

### Opción B: EAS Build

```bash
npm install -g eas-cli
eas login
eas build:configure
```

En el `eas.json` generado agrega un perfil que produzca APK:

```json
{ "build": { "preview": { "android": { "buildType": "apk" }, "distribution": "internal" } } }
```

y ejecuta `eas build -p android --profile preview`. Al terminar, EAS entrega un enlace de descarga del APK. Requiere una cuenta de Expo.

## 7. Limitaciones

- La `apiKey` queda dentro del APK: filtra tráfico anónimo pero no es un secreto fuerte; la autenticación real es código + PIN, validados en cada llamada.
- El PIN se conserva en `expo-secure-store` para reautenticar; un diseño de producción usaría tokens de sesión con vencimiento.
- La app depende de que la instancia EC2 esté encendida (Learner Lab la detiene al terminar la sesión; ver [despliegue_aws.md](despliegue_aws.md)).
- Solo se probó el flujo Android; el proyecto contiene configuración para iOS y web que no hace parte de los entregables.
- Los datos que muestra la app son simulados.
