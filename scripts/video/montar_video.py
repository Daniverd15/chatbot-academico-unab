"""
Monta el video de demostración (1920x1080) a partir de las grabaciones del emulador.

    python scripts/video/montar_video.py <carpeta_clips> <salida.mp4>

Cada escena = grabación del teléfono (izquierda) + panel explicativo (derecha).
Las escenas de chat se graban en dos partes (pregunta / respuesta); la espera del
modelo no se graba y se indica en pantalla con la latencia real medida.
Requiere: pillow, imageio-ffmpeg (incluye ffmpeg).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parents[2]
FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1920, 1080, 30
FUENTES = RAIZ / "mobile/node_modules/@expo-google-fonts/poppins"
MORADO, MORADO2, NARANJA, BLANCO = (124, 20, 214), (26, 12, 52), (255, 166, 0), (255, 255, 255)
GRIS = (196, 186, 222)

TEL_H = 960                      # alto del teléfono en pantalla
TEL_W = round(672 * TEL_H / 1496)
TEL_X, TEL_Y = 190, (H - TEL_H) // 2
PANEL_X = TEL_X + TEL_W + 130


def fuente(peso: str, tam: int) -> ImageFont.FreeTypeFont:
    nombre = {"r": "400Regular", "m": "500Medium", "sb": "600SemiBold", "b": "700Bold", "xb": "800ExtraBold"}[peso]
    p = FUENTES / nombre / f"Poppins_{nombre}.ttf"
    try:
        return ImageFont.truetype(str(p), tam)
    except OSError:
        return ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", tam)


def fondo() -> Image.Image:
    img = Image.new("RGB", (W, H), MORADO2)
    d = ImageDraw.Draw(img)
    for y in range(H):  # degradado vertical
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip((44, 10, 92), (14, 8, 30))))
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse((W - 700, -350, W + 300, 550), fill=120)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    img.paste(Image.new("RGB", (W, H), (150, 40, 255)), (0, 0), glow)
    d = ImageDraw.Draw(img)
    d.rectangle((0, H - 8, W, H), fill=NARANJA)
    return img


def envolver(texto: str, f: ImageFont.FreeTypeFont, ancho: int) -> list[str]:
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = (actual + " " + palabra).strip()
        if f.getlength(prueba) <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    return lineas + [actual] if actual else lineas


def chip(d: ImageDraw.ImageDraw, xy, texto, f, bg, fg=BLANCO, pad=(18, 8)):
    x, y = xy
    w = f.getlength(texto) + pad[0] * 2
    h = f.size + pad[1] * 2 + 6
    d.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=bg)
    d.text((x + pad[0], y + pad[1]), texto, font=f, fill=fg)
    return x + w


def panel(n: int, total: int, titulo: str, puntos: list[str], etiquetas: list[str], nota: str | None) -> Image.Image:
    img = fondo()
    d = ImageDraw.Draw(img)
    # sombra del teléfono
    sombra = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sombra).rounded_rectangle((TEL_X - 6, TEL_Y + 14, TEL_X + TEL_W + 6, TEL_Y + TEL_H + 26), radius=46, fill=150)
    img.paste((5, 2, 12), (0, 0), sombra.filter(ImageFilter.GaussianBlur(28)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((TEL_X - 12, TEL_Y - 12, TEL_X + TEL_W + 12, TEL_Y + TEL_H + 12), radius=48, fill=(20, 20, 26))
    x, y = PANEL_X, 150
    chip(d, (x, y), f"ESCENA {n} DE {total}", fuente("sb", 22), (255, 255, 255, 0) and (70, 30, 120), NARANJA)
    y += 80
    for linea in envolver(titulo, fuente("b", 58), W - PANEL_X - 110):
        d.text((x, y), linea, font=fuente("b", 58), fill=BLANCO)
        y += 74
    y += 22
    fp = fuente("r", 31)
    for p in puntos:
        d.ellipse((x, y + 14, x + 14, y + 28), fill=NARANJA)
        for i, linea in enumerate(envolver(p, fp, W - PANEL_X - 150)):
            d.text((x + 34, y), linea, font=fp, fill=(232, 226, 245))
            y += 44
        y += 16
    y += 10
    cx = x
    for e in etiquetas:
        fin = chip(d, (cx, y), e, fuente("m", 22), (90, 40, 150), (235, 225, 255))
        cx = fin + 12
        if cx > W - 260:
            cx, y = x, y + 56
    if nota:
        fy = H - 150
        d.rounded_rectangle((x, fy, W - 110, fy + 70), radius=18, fill=(255, 166, 0, 255))
        d.text((x + 26, fy + 15), nota, font=fuente("sb", 27), fill=(40, 16, 70))
    d.text((x, H - 58), "UNABot · Chatbot de apoyo académico con n8n · Ciencia de Datos UNAB", font=fuente("r", 20), fill=GRIS)
    return img


def tarjeta(titulo: str, sub: str, lineas: list[str], imagen: Path | None = None) -> Image.Image:
    img = fondo()
    d = ImageDraw.Draw(img)
    if imagen and imagen.exists():
        im = Image.open(imagen).convert("RGB")
        k = min(1560 / im.width, (620 if lineas else 740) / im.height)
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        ix, iy = (W - im.width) // 2, 270
        d.rounded_rectangle((ix - 10, iy - 10, ix + im.width + 10, iy + im.height + 10), radius=20, fill=(255, 255, 255))
        img.paste(im, (ix, iy))
        y0 = 50
    else:
        y0 = 300
    ft, fs = fuente("xb", 76), fuente("m", 34)
    d.text(((W - ft.getlength(titulo)) / 2, y0), titulo, font=ft, fill=BLANCO)
    d.text(((W - fs.getlength(sub)) / 2, y0 + 110), sub, font=fs, fill=NARANJA)
    fl = fuente("r", 30)
    y = y0 + 190 if not imagen else 270 + im.height + 40
    for l in lineas:
        d.text(((W - fl.getlength(l)) / 2, y), l, font=fl, fill=(230, 222, 248))
        y += 48
    return img


def mascara_redondeada(path: Path):
    m = Image.new("L", (TEL_W, TEL_H), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, TEL_W - 1, TEL_H - 1), radius=38, fill=255)
    m.save(path)


def duracion(path: Path) -> float:
    salida = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True, errors="ignore").stderr
    h, m, seg = salida.split("Duration: ")[1].split(",")[0].split(":")
    return int(h) * 3600 + int(m) * 60 + float(seg)


def run(args):
    subprocess.run([FF, "-loglevel", "error", "-y", *args], check=True)


def seg_tarjeta(png: Path, out: Path, dur: float):
    run(["-loop", "1", "-t", str(dur), "-i", str(png), "-f", "lavfi", "-t", str(dur), "-i", "anullsrc=r=48000:cl=stereo",
         "-vf", f"fps={FPS},format=yuv420p,fade=in:0:12,fade=out:st={dur-0.4}:d=0.4",
         "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-c:a", "aac", "-shortest", str(out)])


def seg_escena(png: Path, clips: list[Path], out: Path, mascara: Path, velocidad: float = 1.0, recorte_ini: float = 0.0):
    # concatena las partes del teléfono, ajusta velocidad y compone sobre el panel
    entradas, filtros = [], []
    for i, c in enumerate(clips):
        entradas += ["-i", str(c)]
        filtros.append(f"[{i}:v]fps={FPS},scale={TEL_W}:{TEL_H},setsar=1[c{i}]")
    n = len(clips)
    cadena = "".join(f"[c{i}]" for i in range(n))
    filtros.append(f"{cadena}concat=n={n}:v=1:a=0[tel0]")
    filtros.append(f"[tel0]trim=start={recorte_ini},setpts=(PTS-STARTPTS)/{velocidad}[tel1]")
    filtros.append(f"[{n+1}:v]format=gray[m];[tel1]format=rgba[t];[t][m]alphamerge[tel]")
    filtros.append(f"[{n}:v][tel]overlay={TEL_X}:{TEL_Y}:shortest=1,format=yuv420p,fade=in:0:10[v]")
    run([*entradas, "-loop", "1", "-i", str(png), "-loop", "1", "-i", str(mascara),
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-filter_complex", ";".join(filtros), "-map", "[v]", "-map", f"{n+2}:a",
         "-t", f"{(sum(duracion(c) for c in clips) - recorte_ini) / velocidad:.2f}",
         "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-r", str(FPS), "-c:a", "aac", str(out)])


def main(clips_dir: Path, salida: Path):
    tmp = clips_dir / "_montaje"
    tmp.mkdir(exist_ok=True)
    mascara = tmp / "mascara.png"
    mascara_redondeada(mascara)

    def lat(nombre):
        f = clips_dir / f"{nombre}_lat.txt"
        v = f.read_text().strip() if f.exists() else ""
        # el archivo guarda la espera después de la parte (a), que ya incluye ~4 s desde el envío
        return f"Respuesta en ≈{int(v) + 4} s · espera recortada en el video" if v.isdigit() and int(v) >= 2 else None

    escenas = [
        ("01_login_inicio", ["01_login_inicio"], "Inicio de sesión y tablero personal",
         ["El estudiante entra con su código y PIN; n8n valida contra Supabase.",
          "Avance, PGA y estado académico según el art. 24 del Reglamento UNAB.",
          "Riesgo explicable: qué factores suben o bajan la probabilidad del modelo.",
          "Evolución del PGA, alertas, rutas del CCD y proyección de grado (Monte Carlo)."],
         ["App Android · Expo", "Workflow 07", "Vistas analíticas SQL", "XAI"], None),
        ("02_asesoria", ["02_asesoria_a", "02_asesoria_b"], "Asesoría académica con agente MCP",
         ["El clasificador de intención envía la pregunta al agente asesor (workflow 06).",
          "El agente llama herramientas del servidor FastMCP en AWS: estado, cursos habilitados, proyección.",
          "Recomienda cursos por impacto en prerrequisitos y tasa de reprobación."],
         ["Ruteo por intención", "Clientes MCP", "FastMCP :9000", "Gemini flash-lite"], lat("02_asesoria")),
        ("03_rag", ["03_rag_a", "03_rag_b"], "RAG institucional del CCD",
         ["Búsqueda vectorial en pgvector (gemini-embedding-001, 3072 d, HNSW).",
          "Responde con documentos reales del Centro de Competencias Digitales.",
          "Evaluación: hit@1 0.95 en recuperación y fidelidad 0.985 en generación."],
         ["Workflow 02", "Supabase + pgvector", "LLM-as-judge"], lat("03_rag")),
        ("04_calendario", ["04_calendario_a", "04_calendario_b"], "Calendario académico en Google Sheets",
         ["Detección de intención › lectura en vivo de la hoja de cálculo.",
          "Calcula cuántos días faltan y si la inscripción está abierta.",
          "Si la hoja no responde, usa la tabla de respaldo en la base de datos."],
         ["Workflow 03", "Google Sheets"], lat("04_calendario")),
        ("05_cursos", ["05_cursos_a", "05_cursos_b"], "Historial personalizado",
         ["¿Qué cursos de competencias digitales he tomado? — consulta a la base sintética tipo COSMOS.",
          "Rutas cumplidas y pendientes para la insignia, con recomendaciones de la oferta vigente."],
         ["Workflow 04", "academico.cd_inscripcion"], lat("05_cursos")),
        ("06_noticias", ["06_noticias_a", "06_noticias_b"], "Noticias y convocatorias",
         ["Scraper programado cada 12 h sobre la API WordPress de unab.edu.co.",
          "Las noticias se guardan en Supabase y el chatbot responde con las más recientes."],
         ["Workflows 05 y 05b", "Web scraping"], lat("06_noticias")),
        ("07_guardrail", ["07_guardrail_a", "07_guardrail_b"], "Guardrails: seguridad y privacidad",
         ["Un intento de inyección para ver notas de otro estudiante es bloqueado.",
          "Guardrails de entrada (jailbreak, NSFW, PII, secretos) y de salida; códigos ajenos enmascarados."],
         ["Guardrails n8n", "Auditoría en conversacion_log"], lat("07_guardrail")),
        ("08_memoria", ["08_memoria_a", "08_memoria_b"], "Memoria persistente",
         ["El historial vive en Supabase (Postgres Chat Memory) y sobrevive entre sesiones.",
          "Se guardan solo los turnos de texto para que el historial sea siempre válido para el modelo."],
         ["n8n_chat_histories"], lat("08_memoria")),
        ("09_plan_novedades", ["09_plan_novedades"], "Ruta de autoaprendizaje y noticias del día",
         ["Plan semanal personalizado: cursos foco según repitencia y riesgo, horas por semana y recursos abiertos verificados.",
          "Noticias del día de educación, tecnología e ingeniería de sistemas (UNAB + 11 feeds RSS) con medio y fecha, filtrables por tema.",
          "Calendario académico con días restantes."],
         ["MCP: ruta_autoaprendizaje", "Scraper multifuente", "Workflow 05b"], None),
    ]
    escenas = [e for e in escenas if all((clips_dir / f"{c}.mp4").exists() for c in e[1])]
    total = len(escenas)
    partes = []

    intro = tmp / "intro.png"
    tarjeta("UNABot", "Chatbot de apoyo académico con n8n",
            ["Ingeniería de Sistemas · Ciencia de Datos · Universidad Autónoma de Bucaramanga",
             "n8n · FastMCP · Supabase + pgvector · Gemini · AWS EC2 · App Android"]).save(intro)
    seg_tarjeta(intro, tmp / "s00.mp4", 6)
    partes.append(tmp / "s00.mp4")

    arq = tmp / "arq.png"
    tarjeta("Arquitectura", "App › Caddy (HTTPS) › n8n › servidor MCP / Supabase / Gemini",
            [], RAIZ / "docs/img/presentacion_arquitectura.jpg").save(arq)
    seg_tarjeta(arq, tmp / "s01.mp4", 7)
    partes.append(tmp / "s01.mp4")

    for i, (clave, clips, titulo, puntos, etiquetas, nota) in enumerate(escenas, 1):
        png = tmp / f"{clave}.png"
        panel(i, total, titulo, puntos, etiquetas, nota).save(png)
        out = tmp / f"e{i:02d}.mp4"
        if out.exists() and out.stat().st_mtime > max((clips_dir / f"{c}.mp4").stat().st_mtime for c in clips):
            partes.append(out)  # ya renderizada con las grabaciones actuales
            continue
        seg_escena(png, [clips_dir / f"{c}.mp4" for c in clips], out, mascara, velocidad=1.15)
        partes.append(out)
        print("escena", i, titulo)

    extra = tmp / "extra.png"
    tarjeta("Más allá de la app", "Observatorio académico · cliente web · alertas tempranas",
            ["Streamlit: riesgo explicable, cuellos de botella, calidad del RAG y alertas tempranas"],
            RAIZ / "docs/img/observatorio_panorama.jpg").save(extra)
    seg_tarjeta(extra, tmp / "s98.mp4", 7)
    partes.append(tmp / "s98.mp4")

    fin = tmp / "fin.png"
    tarjeta("Gracias", "github.com/Daniverd15/chatbot-academico-unab",
            ["Web: unabot.35-168-41-252.sslip.io", "Observatorio: observatorio.35-168-41-252.sslip.io",
             "Cuenta demo: U00100002 · PIN 1234"]).save(fin)
    seg_tarjeta(fin, tmp / "s99.mp4", 6)
    partes.append(tmp / "s99.mp4")

    lista = tmp / "lista.txt"
    lista.write_text("".join(f"file '{p.as_posix()}'\n" for p in partes), encoding="utf-8")
    run(["-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", "-movflags", "+faststart", str(salida)])
    print("listo:", salida)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
