"""
Catálogo académico del programa de Ingeniería de Sistemas (simulado).

La estructura respeta la información pública del programa UNAB (SNIES 1643,
8 semestres + práctica profesional, componentes curriculares del Reglamento
Estudiantil 2019, art. 27) y la oferta real del Centro de Competencias
Digitales (CCD) vigente desde 2026. Los nombres de cursos del plan, créditos y
prerrequisitos son una SIMULACIÓN académica razonable, no el pensum oficial.
"""

PROGRAMA = {
    "programa_id": "ISIS",
    "nombre": "Ingeniería de Sistemas",
    "facultad": "Facultad de Ingeniería",
    "snies": "1643",
    "modalidad": "Presencial",
    "semestres": 9,  # 8 académicos + práctica profesional
    "creditos_totales": 0,  # se calcula
    "max_creditos_sem": 20,
    "titulo_otorgado": "Ingeniero(a) de Sistemas",
}

# (curso_id, nombre, créditos, semestre, componente, área, tipo, dificultad, prerrequisitos)
# prerrequisitos: lista de curso_id o "CRED:n" (créditos aprobados mínimos)
CURSOS = [
    # ---------------- Semestre 1 ----------------
    ("ISIS1101", "Cálculo Diferencial", 4, 1, "Básico", "Matemáticas", "Regular", 0.78, []),
    ("ISIS1102", "Álgebra Lineal", 3, 1, "Básico", "Matemáticas", "Regular", 0.62, []),
    ("ISIS1103", "Fundamentos de Programación", 4, 1, "Específico", "Programación", "Regular", 0.60, []),
    ("ISIS1104", "Introducción a la Ingeniería de Sistemas", 2, 1, "Específico", "Ingeniería de Software", "Regular", 0.20, []),
    ("ISIS1105", "Lectura, Escritura y Oralidad Académica", 2, 1, "Socio-humanístico", "Comunicación", "Regular", 0.25, []),
    ("ISIS1106", "Inglés I", 2, 1, "Instrumental", "Idiomas", "Regular", 0.30, []),
    ("ISIS1107", "Cátedra UNAB y Proyecto de Vida", 1, 1, "Socio-humanístico", "Institucional", "Regular", 0.10, []),
    # ---------------- Semestre 2 ----------------
    ("ISIS1201", "Cálculo Integral", 4, 2, "Básico", "Matemáticas", "Regular", 0.80, ["ISIS1101"]),
    ("ISIS1202", "Física Mecánica", 4, 2, "Básico", "Física", "Regular", 0.72, ["ISIS1101"]),
    ("ISIS1203", "Programación Orientada a Objetos", 4, 2, "Específico", "Programación", "Regular", 0.58, ["ISIS1103"]),
    ("ISIS1204", "Matemáticas Discretas", 3, 2, "Básico", "Matemáticas", "Regular", 0.60, ["ISIS1102"]),
    ("ISIS1205", "Inglés II", 2, 2, "Instrumental", "Idiomas", "Regular", 0.32, ["ISIS1106"]),
    ("ISIS1206", "Ética y Ciudadanía", 2, 2, "Socio-humanístico", "Humanidades", "Regular", 0.15, []),
    # ---------------- Semestre 3 ----------------
    ("ISIS2301", "Cálculo Multivariable", 3, 3, "Básico", "Matemáticas", "Regular", 0.70, ["ISIS1201"]),
    ("ISIS2302", "Ecuaciones Diferenciales", 3, 3, "Básico", "Matemáticas", "Regular", 0.74, ["ISIS1201", "ISIS1102"]),
    ("ISIS2303", "Estructuras de Datos", 4, 3, "Específico", "Programación", "Regular", 0.66, ["ISIS1203"]),
    ("ISIS2304", "Bases de Datos I", 4, 3, "Específico", "Datos", "Regular", 0.50, ["ISIS1203"]),
    ("ISIS2305", "Física Electricidad y Magnetismo", 4, 3, "Básico", "Física", "Regular", 0.75, ["ISIS1202", "ISIS1201"]),
    ("ISIS2306", "Inglés III", 2, 3, "Instrumental", "Idiomas", "Regular", 0.35, ["ISIS1205"]),
    # ---------------- Semestre 4 ----------------
    ("ISIS2401", "Probabilidad y Estadística", 3, 4, "Básico", "Matemáticas", "Regular", 0.62, ["ISIS1201"]),
    ("ISIS2402", "Análisis y Diseño de Algoritmos", 3, 4, "Específico", "Programación", "Regular", 0.70, ["ISIS2303", "ISIS1204"]),
    ("ISIS2403", "Bases de Datos II", 3, 4, "Específico", "Datos", "Regular", 0.52, ["ISIS2304"]),
    ("ISIS2404", "Arquitectura de Computadores", 3, 4, "Específico", "Infraestructura", "Regular", 0.60, ["ISIS2305", "ISIS1204"]),
    ("ISIS2405", "Ingeniería de Software I", 3, 4, "Específico", "Ingeniería de Software", "Regular", 0.45, ["ISIS1203"]),
    ("ISIS2406", "Inglés IV", 2, 4, "Instrumental", "Idiomas", "Regular", 0.38, ["ISIS2306"]),
    # ---------------- Semestre 5 ----------------
    ("ISIS3501", "Sistemas Operativos", 3, 5, "Específico", "Infraestructura", "Regular", 0.58, ["ISIS2404", "ISIS2303"]),
    ("ISIS3502", "Ingeniería de Software II", 3, 5, "Específico", "Ingeniería de Software", "Regular", 0.45, ["ISIS2405"]),
    ("ISIS3503", "Desarrollo de Aplicaciones Web", 3, 5, "Específico", "Desarrollo", "Regular", 0.42, ["ISIS2304", "ISIS1203"]),
    ("ISIS3504", "Métodos Numéricos", 3, 5, "Básico", "Matemáticas", "Regular", 0.60, ["ISIS2302", "ISIS1103"]),
    ("ISIS3505", "Investigación de Operaciones", 3, 5, "Básico", "Matemáticas", "Regular", 0.55, ["ISIS2401", "ISIS1102"]),
    ("ISIS3506", "Electiva Socio-humanística I", 2, 5, "Flexible", "Humanidades", "Electivo", 0.15, []),
    # ---------------- Semestre 6 ----------------
    ("ISIS3601", "Redes de Computadores", 3, 6, "Específico", "Infraestructura", "Regular", 0.55, ["ISIS3501"]),
    ("ISIS3602", "Ciencia de Datos", 3, 6, "Específico", "Datos", "Regular", 0.55, ["ISIS2401", "ISIS2403"]),
    ("ISIS3603", "Inteligencia Artificial", 3, 6, "Específico", "Datos", "Regular", 0.62, ["ISIS2402", "ISIS2401"]),
    ("ISIS3604", "Desarrollo de Aplicaciones Móviles", 3, 6, "Específico", "Desarrollo", "Regular", 0.42, ["ISIS3503"]),
    ("ISIS3605", "Arquitectura de Software", 3, 6, "Específico", "Ingeniería de Software", "Regular", 0.50, ["ISIS3502"]),
    ("ISIS3606", "Electiva Profesional I", 3, 6, "Flexible", "Electiva", "Electivo", 0.35, ["CRED:80"]),
    # ---------------- Semestre 7 ----------------
    ("ISIS4701", "Computación en la Nube e Infraestructura", 3, 7, "Específico", "Infraestructura", "Regular", 0.50, ["ISIS3601"]),
    ("ISIS4702", "Seguridad Informática", 3, 7, "Específico", "Infraestructura", "Regular", 0.55, ["ISIS3601"]),
    ("ISIS4703", "Aprendizaje Automático", 3, 7, "Específico", "Datos", "Regular", 0.65, ["ISIS3602", "ISIS3603"]),
    ("ISIS4704", "Gestión de Proyectos de TI", 3, 7, "Específico", "Gestión", "Regular", 0.35, ["ISIS3502"]),
    ("ISIS4705", "Seminario de Investigación", 2, 7, "Específico", "Investigación", "Regular", 0.35, ["ISIS2401", "CRED:100"]),
    ("ISIS4706", "Electiva Profesional II", 3, 7, "Flexible", "Electiva", "Electivo", 0.35, ["CRED:95"]),
    ("ISIS4707", "Emprendimiento e Innovación", 2, 7, "Socio-humanístico", "Gestión", "Regular", 0.20, []),
    # ---------------- Semestre 8 ----------------
    ("ISIS4801", "Proyecto de Grado", 4, 8, "Específico", "Investigación", "Regular", 0.45, ["ISIS4705"]),
    ("ISIS4802", "Gobierno y Arquitectura Empresarial de TI", 3, 8, "Específico", "Gestión", "Regular", 0.40, ["ISIS4704"]),
    ("ISIS4803", "Electiva Profesional III", 3, 8, "Flexible", "Electiva", "Electivo", 0.35, ["CRED:110"]),
    ("ISIS4804", "Electiva Socio-humanística II", 2, 8, "Flexible", "Humanidades", "Electivo", 0.15, []),
    ("ISIS4805", "Ética Profesional en Ingeniería", 2, 8, "Socio-humanístico", "Humanidades", "Regular", 0.15, ["CRED:100"]),
    # ---------------- Semestre 9 (práctica) ----------------
    ("ISIS5901", "Práctica Profesional", 12, 9, "Práctica", "Práctica", "Regular", 0.20, ["CRED:130", "ISIS3605"]),
]

DESCRIPCIONES = {
    "ISIS1103": "Algoritmia, variables, control de flujo, funciones y resolución de problemas en Python.",
    "ISIS1203": "Clases, objetos, herencia, polimorfismo, patrones básicos y pruebas unitarias.",
    "ISIS2303": "Listas, pilas, colas, árboles, grafos y tablas hash; análisis de complejidad.",
    "ISIS2304": "Modelo entidad-relación, modelo relacional, normalización y SQL.",
    "ISIS2403": "SQL avanzado, transacciones, NoSQL, ETL y bodegas de datos.",
    "ISIS3602": "Ciclo de vida de datos, EDA, visualización, modelos supervisados y despliegue.",
    "ISIS3603": "Búsqueda, representación de conocimiento, redes neuronales y LLMs.",
    "ISIS4703": "Modelos supervisados/no supervisados, validación, MLOps y ética de la IA.",
    "ISIS4701": "AWS/Azure, contenedores, Docker, orquestación e infraestructura como código.",
    "ISIS5901": "Práctica profesional en empresa u organización (requiere 130 créditos aprobados).",
}

REQUISITOS_GRADO = [
    ("CD_RUTAS", "Ruta de Competencias Digitales",
     "Aprobar un curso de cada una de las tres rutas del Centro de Competencias Digitales (CCD)."),
    ("INGLES_B1", "Suficiencia en inglés B1",
     "Acreditar nivel B1 (MCER) mediante prueba institucional o certificado internacional."),
    ("SABER_PRO", "Presentación Saber Pro",
     "Presentar el examen de Estado de calidad de la educación superior Saber Pro (ICFES)."),
    ("PAZ_SALVO", "Paz y salvo institucional",
     "Estar a paz y salvo con biblioteca, cartera y laboratorios."),
]

# Oferta del Centro de Competencias Digitales (información pública UNAB 2026)
CD_CURSOS = [
    # id, nombre, ruta, ruta_nombre, horas, modalidad, vigente, equivale_a, descripción
    ("CD-R1-ID", "Interacción Digital", 1, "Competencias Digitales Básicas", 32, "Virtual", True, None,
     "Navegar de forma segura en internet, verificar fuentes y proteger la información."),
    ("CD-R2-AD", "Habilidades de Analítica Digital", 2, "Analítica y Contenido Digital", 32, "Virtual", True, None,
     "Análisis de datos con hojas de cálculo y tableros, interpretación de indicadores."),
    ("CD-R2-MP", "Marca Personal Digital", 2, "Analítica y Contenido Digital", 32, "Virtual", True, None,
     "Construcción de identidad profesional en redes y plataformas digitales."),
    ("CD-R2-CC", "Creación de Contenidos Digitales", 2, "Analítica y Contenido Digital", 32, "Virtual", True, None,
     "Producción de contenido multimedia y presentaciones efectivas."),
    ("CD-R3-IA", "IA Generativa", 3, "Tecnología Transformativa", 32, "Virtual", True, None,
     "Uso responsable de herramientas de IA generativa, prompting y evaluación crítica."),
    ("CD-R3-ML", "Marco Legal Digital", 3, "Tecnología Transformativa", 32, "Virtual", True, None,
     "Protección de datos, propiedad intelectual y normatividad digital en Colombia."),
    ("CD-R3-CB", "Cuidado y Bienestar Digital", 3, "Tecnología Transformativa", 32, "Virtual", True, None,
     "Salud digital, desconexión, ciberacoso y huella digital."),
    # Oferta anterior a 2026 (homologable)
    ("CD-OLD-CDV", "Cultura Digital y Vida en Línea", 0, "Oferta anterior (hasta 2025)", 24, "Virtual", False, "CD-R1-ID",
     "Curso de la oferta de informática anterior a 2026; se reconoce por Interacción Digital."),
    ("CD-OLD-EXC", "Excel", 0, "Oferta anterior (hasta 2025)", 24, "Virtual", False, "CD-R2-AD",
     "Curso de la oferta anterior; se reconoce por Habilidades de Analítica Digital."),
    ("CD-OLD-PPT", "PowerPoint", 0, "Oferta anterior (hasta 2025)", 16, "Virtual", False, "CD-R2-CC",
     "Curso de la oferta anterior; se reconoce por Creación de Contenidos Digitales."),
    ("CD-OLD-WRD", "Word", 0, "Oferta anterior (hasta 2025)", 16, "Virtual", False, None,
     "Curso de la oferta anterior; no tiene equivalencia directa en la nueva ruta."),
]


def creditos_totales() -> int:
    return sum(c[2] for c in CURSOS)


PROGRAMA["creditos_totales"] = creditos_totales()
