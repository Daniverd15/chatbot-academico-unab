# Scraper de noticias multifuente

`scraper/scraper_noticias.py` trae las **noticias del día sobre educación, tecnología e ingeniería de sistemas**, más las novedades institucionales de la UNAB. Cada noticia se guarda en `chatbot.noticia` con su **fuente** (`fuente_nombre`), su **fecha real de publicación** (`fecha_pub`) y su **tema** (`tema`). El agente (workflow 05 y la herramienta MCP `noticias_recientes`) y la pestaña **Noticias** de la app leen esa tabla.

## 1. Fuentes

| Fuente | Cómo se consulta | Tema sugerido |
|---|---|---|
| UNAB (unab.edu.co) | API REST de WordPress por categorías y búsquedas; si falla, se parsea el HTML de la categoría Estudiantes | `institucional` |
| Google News: `"ingeniería de sistemas" OR "ingeniería de software" OR programadores Colombia` | RSS `news.google.com/rss/search?...&hl=es-419&gl=CO&ceid=CO:es-419` con `when:Nd` | `ingenieria_sistemas` |
| Google News: `"desarrollo de software" OR ciberseguridad OR "ciencia de datos" Colombia` | igual | `ingenieria_sistemas` |
| Google News: `"educación superior" Colombia` | igual | `educacion` |
| Google News: `universidades OR estudiantes OR Mineducación Colombia educación` | igual | `educacion` |
| Google News: `tecnología "inteligencia artificial"` | igual | `tecnologia` |
| Semana · Educación | RSS `semana.com/arc/outboundfeeds/rss/category/educacion/` | `educacion` |
| El Tiempo · Tecnósfera | RSS `eltiempo.com/rss/tecnosfera.xml` | `tecnologia` |
| ENTER.CO | RSS `enter.co/feed/` | `tecnologia` |
| Impacto TIC | RSS `impactotic.co/feed/` | `tecnologia` |
| Xataka | RSS `feeds.weblogssl.com/xataka2` | `tecnologia` |
| WWWhat's new | RSS `wwwhatsnew.com/feed/` | `tecnologia` |

Todas las fuentes se probaron el 19 de noviembre de 2026 y respondieron 200 con RSS 2.0 válido. Se descartaron Universia (403), El Espectador (su XML no es válido) y Genbeta (la mayoría de sus notas son de estilo de vida).

En Google News el medio real se toma de la etiqueta `<source>` (por ejemplo "El Tiempo", "Caracol Radio", "ELHERALDO.CO") y se quita el sufijo " - Medio" del titular. Se descartan las publicaciones de redes sociales (Facebook, YouTube, X, etc.) porque no son medios con fuente verificable.

El XML se parsea con `xml.etree` de la biblioteca estándar (RSS 2.0 y Atom), así que no hay dependencias nuevas. Una fuente caída no detiene a las demás.

## 2. Filtros y limpieza

- **Recencia:** solo noticias publicadas en los últimos `--dias` días (3 por defecto). La fecha sale de `pubDate`, `published`/`updated` (Atom) o `dc:date`, y se normaliza a UTC.
- **Máximo 15 noticias por fuente** en cada ejecución.
- **Resumen limpio:** se quita el HTML y los pies del tipo "La entrada … se publicó primero en …". En Google News la descripción solo repite el titular, así que el resumen queda vacío.
- **Medios generalistas:** de los feeds de tecnología (ENTER.CO, Xataka, etc.) solo se guardan las notas con al menos una palabra clave de los temas. También se descartan las comerciales (ofertas, Black Friday, descuentos).
- **Deduplicación:** por URL y por titular normalizado, porque Google News repite la misma nota en varias consultas. En la base, las noticias externas usan `ON CONFLICT (url)` y las de la UNAB `ON CONFLICT (noticia_id)`.
- **Ids:** la UNAB usa el id del post de WordPress. Las externas usan un hash estable de la URL (≥ 10¹²), así que nunca chocan con los ids de WordPress.

## 3. Clasificación por tema

Las reglas son de palabras clave con peso (`TEMAS` en el script) y el titular cuenta doble. La consulta o el feed de origen suma **+2** a su tema sugerido, y en caso de empate gana el tema sugerido.

| Tema | Palabras clave (resumen) |
|---|---|
| `ingenieria_sistemas` | ingeniería de sistemas/software, programación, desarrollador, software, ciberseguridad, ciencia de datos, bases de datos, algoritmos, DevOps, nube, Python, API, machine learning, hackatón |
| `tecnologia` | tecnología, inteligencia artificial/IA, ChatGPT, Gemini, robots, chips, smartphones, Apple/Google/Microsoft, 5G, internet, digital, videojuegos, apps |
| `educacion` | educación, Mineducación, ICETEX, Saber 11/Pro, acreditación, universidad, colegio, docentes, estudiantes, becas, matrícula, SENA, rector |
| `institucional` | noticias de unab.edu.co |

Las noticias de la **UNAB** quedan como `institucional`, salvo que el titular sea claramente de otro tema: puntaje ≥ 4 para tecnología o ingeniería, o ≥ 5 para educación (casi toda noticia UNAB menciona estudiantes o la universidad).

Además del tema se conservan el `tipo` (curso, convocatoria, certificación, evento, general) y la `relevancia` (palabras clave con decaimiento de 90 días). Las externas suman a la relevancia +1,5 si son de ingeniería, +1,0 si son de educación y +0,5 si son de tecnología.

## 4. Base de datos

`database/06_noticias_temas.sql` es aditivo e idempotente y se ejecuta después de `05_memoria_chat.sql` en `load_database.py`. Hace lo siguiente:

- añade `tema TEXT` con `CHECK (tema IN ('educacion','tecnologia','ingenieria_sistemas','institucional'))`;
- añade `fuente_nombre TEXT`;
- marca las noticias que ya existían como `institucional` / `UNAB`;
- crea el índice `ix_noticia_tema_fecha (tema, fecha_pub DESC)`.

`mcp_readonly` ya tenía `SELECT` sobre todas las tablas de `chatbot`. Si las columnas nuevas no existen, el scraper inserta como antes, sin `tema` ni `fuente_nombre`.

## 5. Ejecución y frecuencia

```bash
python scraper/scraper_noticias.py                  # UNAB (180 días) + RSS (3 días) → chatbot.noticia
python scraper/scraper_noticias.py --embed          # además vectoriza en el RAG las nuevas con relevancia ≥ 1.0
python scraper/scraper_noticias.py --dias 1 --dry-run
python scraper/scraper_noticias.py --fuentes rss    # solo medios externos (o --fuentes unab)
```

| Opción | Por defecto | Uso |
|---|---|---|
| `--dias N` | 3 | ventana de las fuentes RSS |
| `--dias-unab N` | 180 | ventana de unab.edu.co (el comportamiento anterior) |
| `--fuentes` | `todas` | `todas`, `unab` o `rss` |
| `--embed` | no | vectoriza las noticias nuevas (metadato `fuente` = medio y `tema`) |
| `--dry-run` | no | solo muestra, no escribe en la base |

**Frecuencia:** cada 12 horas (`0 */12 * * *` con cron). El workflow 05b de n8n, también cada 12 horas, solo consulta la API de WordPress de la UNAB. Ver la nota en [workflows_n8n.md](workflows_n8n.md).

## 6. Resultado real (19 de noviembre de 2026)

Ejecución: `python scraper/scraper_noticias.py`. Resultado: 197 noticias obtenidas tras deduplicar, 118 nuevas y **201 filas** en `chatbot.noticia`, de 56 medios distintos.

| Tema | Noticias | Publicadas hoy (hora Colombia) | Más reciente (hora Colombia) |
|---|---:|---:|---|
| `tecnologia` | 51 | 38 | 2026-11-19 17:01 |
| `educacion` | 32 | 9 | 2026-11-19 15:35 |
| `ingenieria_sistemas` | 27 | 7 | 2026-11-19 14:58 |
| `institucional` | 91 | 4 | 2026-11-19 16:20 |

Ejemplos reales:

| Titular | Fuente | Fecha | Tema |
|---|---|---|---|
| GFT abre cerca de 200 vacantes en Colombia para ingenieros de sistemas, desarrolladores y expertos en DevOps | ENTER.CO | 2026-11-19 | `ingenieria_sistemas` |
| Programa de Ingeniería de Sistemas de la UCC de Ibagué logra acreditación de alta calidad | Emisora Ondas de Ibagué | 2026-11-18 | `ingenieria_sistemas` |
| Renuevan acreditación de alta calidad de Universidad del Norte por diez años | ELHERALDO.CO | 2026-11-19 | `educacion` |
| La ministra de Educación, Ilva Myriam Hoyos, pide a Hacienda recortar $386.173 millones de su presupuesto de inversión para 2026 | El Tiempo | 2026-11-17 | `educacion` |
| Tareas escolares e inteligencia artificial en Colombia: ¿hasta dónde deberían ayudar los padres a sus hijos? | Semana · Educación | 2026-11-17 | `educacion` |
| Meta y MinTIC firman acuerdo para combatir el reclutamiento digital y formar a miles de colombianos | Impacto TIC | 2026-11-18 | `tecnologia` |
| iPhone 18 y iPhone Air 2 llegarían en marzo de 2027 | ENTER.CO | 2026-11-19 | `tecnologia` |
| Graduada UNAB obtiene Premio Nacional de Periodismo Simón Bolívar 2026 | UNAB | 2026-11-19 | `institucional` |

## 7. En la app

La pestaña **Noticias** muestra:

- chips de filtro (Todas, Educación, Tecnología, Ingeniería de sistemas, UNAB), cada uno con su conteo;
- el medio y la fecha exacta de cada noticia ("Hoy · 10:35", "Ayer · 18:02" o "17 nov 2026");
- una insignia verde **Hoy** en las noticias publicadas hoy.

Si el dashboard todavía no envía `tema` o `fuente_nombre`, la app infiere el tema por la URL y el titular, y usa el dominio de la URL como fuente.
