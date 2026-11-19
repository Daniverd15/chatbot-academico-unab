"""
Genera mcp_server/recursos_aprendizaje.json: catálogo curado de recursos abiertos y gratuitos
para la herramienta MCP `ruta_autoaprendizaje`.

Cada recurso se verifica con una petición HTTP real (HEAD y, si falla, GET; status < 400);
los que no responden se descartan y quedan listados en `descartados`.

    python scripts/generar_recursos_aprendizaje.py
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import requests

SALIDA = Path(__file__).resolve().parents[1] / "mcp_server" / "recursos_aprendizaje.json"
UA = {"User-Agent": "Mozilla/5.0 (link-check; recursos-aprendizaje)", "Accept-Language": "es,en;q=0.8"}

# id: (título, proveedor, url, tipo, idioma, horas estimadas)
# tipo ∈ video | curso | libro | práctica
R = {
    # --- Matemáticas ---
    "ka_calc_dif": ("Cálculo diferencial", "Khan Academy en español", "https://es.khanacademy.org/math/differential-calculus", "curso", "es", 30),
    "ka_calc_int": ("Cálculo integral", "Khan Academy en español", "https://es.khanacademy.org/math/integral-calculus", "curso", "es", 30),
    "ka_calc_multi": ("Cálculo multivariable", "Khan Academy en español", "https://es.khanacademy.org/math/multivariable-calculus", "curso", "es", 30),
    "ka_ecdif": ("Ecuaciones diferenciales", "Khan Academy en español", "https://es.khanacademy.org/math/differential-equations", "curso", "es", 20),
    "ka_alg_lin": ("Álgebra lineal", "Khan Academy en español", "https://es.khanacademy.org/math/linear-algebra", "curso", "es", 25),
    "ka_estad": ("Estadística y probabilidad", "Khan Academy en español", "https://es.khanacademy.org/math/statistics-probability", "curso", "es", 35),
    "mit_1801": ("18.01SC Single Variable Calculus", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/", "curso", "en", 60),
    "mit_1802": ("18.02SC Multivariable Calculus", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/18-02sc-multivariable-calculus-fall-2010/", "curso", "en", 60),
    "mit_1803": ("18.03SC Differential Equations", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/18-03sc-differential-equations-fall-2011/", "curso", "en", 60),
    "mit_1806": ("18.06SC Linear Algebra (Gilbert Strang)", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/", "curso", "en", 60),
    "mit_1805": ("18.05 Introduction to Probability and Statistics", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/18-05-introduction-to-probability-and-statistics-spring-2022/", "curso", "en", 50),
    "mit_6042": ("6.042J Mathematics for Computer Science", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/6-042j-mathematics-for-computer-science-fall-2010/", "curso", "en", 60),
    "mit_15053": ("15.053 Optimization Methods in Management Science", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/15-053-optimization-methods-in-management-science-spring-2013/", "curso", "en", 40),
    "os_calc1": ("Cálculo, volumen 1", "OpenStax (Rice University)", "https://openstax.org/details/books/c%C3%A1lculo-volumen-1", "libro", "es", 40),
    "os_calc2": ("Cálculo, volumen 2", "OpenStax (Rice University)", "https://openstax.org/details/books/c%C3%A1lculo-volumen-2", "libro", "es", 40),
    "os_calc3": ("Cálculo, volumen 3", "OpenStax (Rice University)", "https://openstax.org/details/books/c%C3%A1lculo-volumen-3", "libro", "es", 40),
    "os_estad": ("Introducción a la estadística", "OpenStax (Rice University)", "https://openstax.org/details/books/introducci%C3%B3n-estad%C3%ADstica", "libro", "es", 40),
    "yt_3b1b_calc": ("Essence of Calculus (lista de videos)", "3Blue1Brown · YouTube", "https://www.youtube.com/playlist?list=PLZHQObOWTQDMsr9K-rj53DwVRMYO3t5Yr", "video", "en (subtítulos es)", 4),
    "yt_3b1b_alg": ("Essence of Linear Algebra (lista de videos)", "3Blue1Brown · YouTube", "https://www.youtube.com/playlist?list=PLZHQObOWTQDPD3MizzM2xVFitgF8hE_ab", "video", "en (subtítulos es)", 4),
    "yt_3b1b_nn": ("Redes neuronales (lista de videos)", "3Blue1Brown · YouTube", "https://www.youtube.com/playlist?list=PLZHQObOWTQDNU6R1_67000Dx_ZCJB-3pi", "video", "en (subtítulos es)", 3),
    "discrete_oi": ("Discrete Mathematics: An Open Introduction", "Oscar Levin (libro abierto)", "https://discrete.openmathbooks.org/", "libro", "en", 40),
    "seeing_theory": ("Seeing Theory: probabilidad visual", "Brown University", "https://seeing-theory.brown.edu/", "práctica", "en", 5),
    "py_numericos": ("Python Programming and Numerical Methods", "UC Berkeley (libro abierto)", "https://pythonnumericalmethods.studentorg.berkeley.edu/notebooks/Index.html", "libro", "en", 40),
    # --- Física ---
    "ka_fisica": ("Física", "Khan Academy en español", "https://es.khanacademy.org/science/physics", "curso", "es", 40),
    "mit_801": ("8.01SC Classical Mechanics", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/8-01sc-classical-mechanics-fall-2016/", "curso", "en", 60),
    "mit_802": ("8.02 Physics II: Electricity and Magnetism", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/8-02-physics-ii-electricity-and-magnetism-spring-2007/", "curso", "en", 60),
    "os_fis1": ("Física universitaria, volumen 1", "OpenStax (Rice University)", "https://openstax.org/details/books/f%C3%ADsica-universitaria-volumen-1", "libro", "es", 40),
    "os_fis2": ("Física universitaria, volumen 2", "OpenStax (Rice University)", "https://openstax.org/details/books/f%C3%ADsica-universitaria-volumen-2", "libro", "es", 40),
    "phet": ("Simulaciones interactivas PhET", "University of Colorado Boulder", "https://phet.colorado.edu/es/", "práctica", "es", 5),
    # --- Programación ---
    "cs50x": ("CS50x: Introduction to Computer Science", "Harvard University", "https://cs50.harvard.edu/x/", "curso", "en (subtítulos es)", 100),
    "cs50p": ("CS50P: Introduction to Programming with Python", "Harvard University", "https://cs50.harvard.edu/python/", "curso", "en (subtítulos es)", 80),
    "py_tutorial": ("Tutorial oficial de Python", "Python Software Foundation", "https://docs.python.org/es/3/tutorial/", "libro", "es", 15),
    "py_clases": ("Tutorial de Python: clases", "Python Software Foundation", "https://docs.python.org/es/3/tutorial/classes.html", "libro", "es", 3),
    "py_unittest": ("unittest: pruebas unitarias", "Python Software Foundation", "https://docs.python.org/es/3/library/unittest.html", "libro", "es", 2),
    "fcc_python": ("Scientific Computing with Python", "freeCodeCamp", "https://www.freecodecamp.org/learn/scientific-computing-with-python/", "práctica", "en", 300),
    "mit_60001": ("6.0001 Introduction to CS and Programming in Python", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/", "curso", "en", 60),
    "mooc_java": ("Java Programming MOOC", "University of Helsinki", "https://java-programming.mooc.fi/", "curso", "en", 100),
    "exercism_py": ("Python track (ejercicios con mentoría)", "Exercism", "https://exercism.org/tracks/python", "práctica", "en", 30),
    "refactoring_guru": ("Patrones de diseño", "Refactoring.Guru", "https://refactoring.guru/es/design-patterns", "libro", "es", 10),
    "mit_6006": ("6.006 Introduction to Algorithms", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/", "curso", "en", 60),
    "mit_6046": ("6.046J Design and Analysis of Algorithms", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/6-046j-design-and-analysis-of-algorithms-spring-2015/", "curso", "en", 60),
    "visualgo": ("VisuAlgo: estructuras de datos y algoritmos animados", "National University of Singapore", "https://visualgo.net/es", "práctica", "es", 6),
    "open_ds": ("Open Data Structures", "Pat Morin (libro abierto)", "https://opendatastructures.org/", "libro", "en", 30),
    "coursera_algs": ("Algorithms, Part I (modo auditoría)", "Princeton University · Coursera", "https://www.coursera.org/learn/algorithms-part1", "curso", "en", 54),
    "erickson_algs": ("Algorithms (Jeff Erickson)", "University of Illinois (libro abierto)", "https://jeffe.cs.illinois.edu/teaching/algorithms/", "libro", "en", 40),
    "cses": ("CSES Problem Set", "CSES · University of Helsinki", "https://cses.fi/problemset/", "práctica", "en", 30),
    # --- Datos ---
    "pg_tutorial": ("Tutorial de PostgreSQL (documentación oficial)", "PostgreSQL Global Development Group", "https://www.postgresql.org/docs/current/tutorial.html", "libro", "en", 8),
    "pg_tx": ("PostgreSQL: transacciones", "PostgreSQL Global Development Group", "https://www.postgresql.org/docs/current/tutorial-transactions.html", "libro", "en", 1),
    "pg_indices": ("PostgreSQL: índices", "PostgreSQL Global Development Group", "https://www.postgresql.org/docs/current/indexes.html", "libro", "en", 3),
    "cmu_15445": ("15-445/645 Database Systems", "Carnegie Mellon University", "https://15445.courses.cs.cmu.edu/", "curso", "en", 60),
    "sqlbolt": ("SQLBolt: lecciones interactivas de SQL", "SQLBolt", "https://sqlbolt.com/", "práctica", "en", 5),
    "fcc_db": ("Relational Database (PostgreSQL y Bash)", "freeCodeCamp", "https://www.freecodecamp.org/learn/relational-database/", "práctica", "en", 300),
    "ka_sql": ("Introducción a SQL: consulta y gestión de datos", "Khan Academy en español", "https://es.khanacademy.org/computing/computer-programming/sql", "curso", "es", 10),
    "mongodb_univ": ("MongoDB University", "MongoDB", "https://learn.mongodb.com/", "curso", "en", 10),
    "kaggle_learn": ("Kaggle Learn (Python, pandas, ML)", "Kaggle", "https://www.kaggle.com/learn", "práctica", "en", 30),
    "pandas_docs": ("pandas: Getting started", "pandas (NumFOCUS)", "https://pandas.pydata.org/docs/getting_started/index.html", "libro", "en", 5),
    "pdsh": ("Python Data Science Handbook", "Jake VanderPlas (libro abierto)", "https://jakevdp.github.io/PythonDataScienceHandbook/", "libro", "en", 30),
    "cs50ai": ("CS50 AI with Python", "Harvard University", "https://cs50.harvard.edu/ai/", "curso", "en (subtítulos es)", 70),
    "mit_6034": ("6.034 Artificial Intelligence", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/6-034-artificial-intelligence-fall-2010/", "curso", "en", 60),
    "elements_ai": ("Elements of AI", "University of Helsinki", "https://www.elementsofai.com/es/", "curso", "es", 30),
    "google_mlcc": ("Machine Learning Crash Course", "Google for Developers", "https://developers.google.com/machine-learning/crash-course?hl=es-419", "curso", "es", 15),
    "sklearn_guide": ("scikit-learn: User Guide", "scikit-learn", "https://scikit-learn.org/stable/user_guide.html", "libro", "en", 20),
    "coursera_ml": ("Machine Learning Specialization (modo auditoría)", "Stanford · DeepLearning.AI · Coursera", "https://www.coursera.org/specializations/machine-learning-introduction", "curso", "en (subtítulos es)", 90),
    "d2l": ("Dive into Deep Learning", "d2l.ai (libro abierto)", "https://d2l.ai/", "libro", "en", 60),
    # --- Infraestructura ---
    "nand2tetris": ("Nand2Tetris: From NAND to Tetris", "Hebrew University · Nand2Tetris", "https://www.nand2tetris.org/", "curso", "en", 60),
    "mit_6004": ("6.004 Computation Structures", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/6-004-computation-structures-spring-2017/", "curso", "en", 60),
    "ostep": ("Operating Systems: Three Easy Pieces", "University of Wisconsin-Madison", "https://pages.cs.wisc.edu/~remzi/OSTEP/", "libro", "en", 40),
    "missing_semester": ("The Missing Semester of Your CS Education", "MIT CSAIL", "https://missing.csail.mit.edu/", "curso", "en (subtítulos es)", 12),
    "netbook": ("Computer Networks: A Systems Approach", "Peterson & Davie (libro abierto)", "https://book.systemsapproach.org/", "libro", "en", 40),
    "kurose_videos": ("Video lectures de Computer Networking (Kurose & Ross)", "UMass Amherst", "https://gaia.cs.umass.edu/kurose_ross/online_lectures.htm", "video", "en", 25),
    "docker_start": ("Docker: Get started", "Docker", "https://docs.docker.com/get-started/", "práctica", "en", 6),
    "k8s_docs": ("Documentación de Kubernetes", "The Kubernetes Authors", "https://kubernetes.io/es/docs/home/", "libro", "es", 10),
    "aws_skill": ("AWS Skill Builder (cursos gratuitos)", "Amazon Web Services", "https://skillbuilder.aws/", "curso", "en/es", 20),
    "ms_learn_azure": ("Microsoft Learn: Azure", "Microsoft", "https://learn.microsoft.com/es-es/training/azure/", "curso", "es", 20),
    "owasp_top10": ("OWASP Top 10", "OWASP Foundation", "https://owasp.org/www-project-top-ten/", "libro", "en", 4),
    "portswigger": ("Web Security Academy", "PortSwigger", "https://portswigger.net/web-security", "práctica", "en", 40),
    "mit_6858": ("6.858 Computer Systems Security", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/6-858-computer-systems-security-fall-2014/", "curso", "en", 50),
    # --- Ingeniería de software / desarrollo ---
    "mit_6031": ("6.031 Software Construction", "MIT", "https://web.mit.edu/6.031/www/", "curso", "en", 40),
    "git_book": ("Pro Git (libro oficial)", "Git", "https://git-scm.com/book/es/v2", "libro", "es", 12),
    "scrum_guide": ("La Guía de Scrum", "Scrum.org · Scrum Inc.", "https://scrumguides.org/", "libro", "es", 1),
    "atlassian_agile": ("Agile Coach", "Atlassian", "https://www.atlassian.com/es/agile", "libro", "es", 5),
    "twelve_factor": ("The Twelve-Factor App", "12factor.net", "https://12factor.net/es/", "libro", "es", 2),
    "azure_arch": ("Centro de arquitectura de Azure", "Microsoft", "https://learn.microsoft.com/es-es/azure/architecture/", "libro", "es", 10),
    "mdn_learn": ("Aprende desarrollo web", "MDN Web Docs (Mozilla)", "https://developer.mozilla.org/es/docs/Learn", "libro", "es", 40),
    "fcc_web": ("Responsive Web Design", "freeCodeCamp", "https://www.freecodecamp.org/learn/2022/responsive-web-design/", "práctica", "en", 300),
    "odin": ("The Odin Project", "The Odin Project", "https://www.theodinproject.com/", "curso", "en", 100),
    "cs50w": ("CS50W: Web Programming with Python and JavaScript", "Harvard University", "https://cs50.harvard.edu/web/", "curso", "en", 80),
    "rn_docs": ("React Native: documentación", "Meta Open Source", "https://reactnative.dev/docs/getting-started", "libro", "en", 10),
    "expo_docs": ("Expo: documentación y tutorial", "Expo", "https://docs.expo.dev/", "libro", "en", 8),
    "android_courses": ("Android Developers: cursos", "Google", "https://developer.android.com/courses", "curso", "en/es", 30),
    "mit_1040": ("1.040 Project Management", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/1-040-project-management-spring-2009/", "curso", "en", 30),
    # --- Investigación, comunicación, idiomas, humanidades, emprendimiento ---
    "scholar": ("Google Académico", "Google", "https://scholar.google.com/", "práctica", "es", 2),
    "zotero": ("Zotero: gestor de referencias", "Corporation for Digital Scholarship", "https://www.zotero.org/", "práctica", "es", 2),
    "apa": ("Normas APA (guía oficial)", "American Psychological Association", "https://apastyle.apa.org/", "libro", "en", 3),
    "overleaf": ("Aprende LaTeX con Overleaf", "Overleaf", "https://www.overleaf.com/learn", "libro", "en", 5),
    "purdue_owl": ("Purdue Online Writing Lab", "Purdue University", "https://owl.purdue.edu/", "libro", "en", 5),
    "rae_dpd": ("Diccionario panhispánico de dudas", "Real Academia Española", "https://www.rae.es/dpd/", "libro", "es", 2),
    "cvc": ("Centro Virtual Cervantes", "Instituto Cervantes", "https://cvc.cervantes.es/", "libro", "es", 3),
    "bbc_english": ("BBC Learning English", "BBC", "https://www.bbc.co.uk/learningenglish/", "curso", "en", 30),
    "british_council": ("LearnEnglish", "British Council", "https://learnenglish.britishcouncil.org/", "práctica", "en", 30),
    "usalearns": ("USA Learns", "USA Learns", "https://www.usalearns.org/", "curso", "en", 30),
    "justice": ("Justice with Michael Sandel", "Harvard University", "https://justiceharvard.org/", "video", "en (subtítulos es)", 12),
    "mit_15390": ("15.390 New Enterprises", "MIT OpenCourseWare", "https://ocw.mit.edu/courses/15-390-new-enterprises-spring-2013/", "curso", "en", 30),
    "startup_school": ("Startup School", "Y Combinator", "https://www.startupschool.org/", "curso", "en", 20),
    "mit_ocw_search": ("Buscador de cursos MIT OpenCourseWare", "MIT OpenCourseWare", "https://ocw.mit.edu/search/", "curso", "en", 30),
    "yt_mitocw": ("Canal de MIT OpenCourseWare", "MIT OpenCourseWare · YouTube", "https://www.youtube.com/@mitocw", "video", "en", 10),
    "yt_cs50": ("Canal de CS50", "Harvard University · YouTube", "https://www.youtube.com/@cs50", "video", "en", 10),
    # --- Aprender a aprender (transversales) ---
    "aprender_aprender": ("Aprendiendo a aprender (modo auditoría)", "UC San Diego · Coursera", "https://www.coursera.org/learn/aprendiendo-a-aprender", "curso", "es", 15),
    "learning_scientists": ("Six Strategies for Effective Learning", "The Learning Scientists", "https://www.learningscientists.org/downloadable-materials", "libro", "en/es", 2),
    "retrieval_practice": ("Retrieval Practice: guías para estudiantes", "RetrievalPractice.org", "https://www.retrievalpractice.org/", "libro", "en", 2),
    "anki": ("Anki: tarjetas con repetición espaciada", "Anki", "https://apps.ankiweb.net/", "práctica", "es", 2),
}

# curso del plan → recursos en orden de uso sugerido (del más guiado al más profundo)
CURSOS = {
    "ISIS1101": ["ka_calc_dif", "yt_3b1b_calc", "os_calc1", "mit_1801"],
    "ISIS1102": ["ka_alg_lin", "yt_3b1b_alg", "mit_1806"],
    "ISIS1103": ["py_tutorial", "cs50p", "exercism_py", "cs50x", "mit_60001"],
    "ISIS1104": ["missing_semester", "cs50x", "git_book"],
    "ISIS1105": ["rae_dpd", "cvc", "purdue_owl"],
    "ISIS1106": ["british_council", "bbc_english", "usalearns"],
    "ISIS1201": ["ka_calc_int", "os_calc2", "yt_3b1b_calc", "mit_1801"],
    "ISIS1202": ["ka_fisica", "phet", "os_fis1", "mit_801"],
    "ISIS1203": ["py_clases", "refactoring_guru", "py_unittest", "mooc_java", "mit_60001"],
    "ISIS1204": ["mit_6042", "discrete_oi"],
    "ISIS1205": ["british_council", "bbc_english", "usalearns"],
    "ISIS1206": ["justice"],
    "ISIS2301": ["ka_calc_multi", "os_calc3", "mit_1802"],
    "ISIS2302": ["ka_ecdif", "mit_1803", "py_numericos"],
    "ISIS2303": ["visualgo", "mit_6006", "open_ds", "cses"],
    "ISIS2304": ["ka_sql", "sqlbolt", "pg_tutorial", "fcc_db", "cmu_15445"],
    "ISIS2305": ["os_fis2", "phet", "ka_fisica", "mit_802"],
    "ISIS2306": ["british_council", "bbc_english", "usalearns"],
    "ISIS2401": ["ka_estad", "seeing_theory", "os_estad", "mit_1805"],
    "ISIS2402": ["erickson_algs", "coursera_algs", "mit_6046", "cses"],
    "ISIS2403": ["pg_tx", "pg_indices", "cmu_15445", "mongodb_univ"],
    "ISIS2404": ["nand2tetris", "mit_6004"],
    "ISIS2405": ["mit_6031", "git_book", "scrum_guide"],
    "ISIS2406": ["british_council", "bbc_english", "usalearns"],
    "ISIS3501": ["ostep", "missing_semester"],
    "ISIS3502": ["mit_6031", "scrum_guide", "atlassian_agile", "refactoring_guru"],
    "ISIS3503": ["mdn_learn", "fcc_web", "cs50w", "odin"],
    "ISIS3504": ["py_numericos", "mit_1803"],
    "ISIS3505": ["mit_15053"],
    "ISIS3601": ["kurose_videos", "netbook"],
    "ISIS3602": ["kaggle_learn", "pandas_docs", "pdsh"],
    "ISIS3603": ["elements_ai", "cs50ai", "yt_3b1b_nn", "mit_6034"],
    "ISIS3604": ["expo_docs", "rn_docs", "android_courses"],
    "ISIS3605": ["refactoring_guru", "twelve_factor", "azure_arch"],
    "ISIS4701": ["docker_start", "aws_skill", "ms_learn_azure", "k8s_docs"],
    "ISIS4702": ["owasp_top10", "portswigger", "mit_6858"],
    "ISIS4703": ["google_mlcc", "sklearn_guide", "coursera_ml", "d2l"],
    "ISIS4704": ["scrum_guide", "atlassian_agile", "mit_1040"],
    "ISIS4705": ["scholar", "zotero", "apa", "overleaf"],
    "ISIS4707": ["startup_school", "mit_15390"],
    "ISIS4801": ["scholar", "zotero", "overleaf", "apa"],
    "ISIS4802": ["azure_arch", "mit_1040"],
    "ISIS4805": ["justice"],
}

# respaldo por área (database/catalogo.py) para cursos sin lista propia (electivas, práctica…)
AREAS = {
    "Matemáticas": ["ka_calc_dif", "mit_6042"],
    "Física": ["ka_fisica", "phet"],
    "Programación": ["cs50x", "exercism_py"],
    "Datos": ["kaggle_learn", "pg_tutorial"],
    "Infraestructura": ["missing_semester", "docker_start"],
    "Ingeniería de Software": ["mit_6031", "git_book"],
    "Desarrollo": ["mdn_learn", "cs50w"],
    "Gestión": ["atlassian_agile", "mit_1040"],
    "Investigación": ["scholar", "zotero"],
    "Idiomas": ["british_council", "bbc_english"],
    "Comunicación": ["rae_dpd", "purdue_owl"],
    "Humanidades": ["justice"],
    "Electiva": ["mit_ocw_search", "yt_mitocw"],
    "Práctica": ["missing_semester", "git_book"],
    "Institucional": ["aprender_aprender"],
}

TRANSVERSALES = ["aprender_aprender", "learning_scientists", "retrieval_practice", "anki", "yt_cs50"]


def verificar(url: str) -> tuple[bool, int | str]:
    for metodo in ("head", "get"):
        try:
            r = requests.request(metodo, url, headers=UA, timeout=20, allow_redirects=True, stream=True)
            r.close()
            if r.status_code < 400:
                return True, r.status_code
            estado: int | str = r.status_code
        except requests.RequestException as exc:
            estado = type(exc).__name__
    return False, estado


def main() -> None:
    with ThreadPoolExecutor(max_workers=12) as ex:
        res = dict(zip(R, ex.map(lambda k: verificar(R[k][2]), R)))
    ok = {k for k, (v, _) in res.items() if v}
    recursos = {
        k: {"titulo": t, "proveedor": p, "url": u, "tipo": tipo, "idioma": idi, "horas": h}
        for k, (t, p, u, tipo, idi, h) in R.items() if k in ok
    }
    filtra = lambda ids: [i for i in ids if i in ok]  # noqa: E731
    data = {
        "descripcion": "Catálogo curado de recursos abiertos y gratuitos por curso del plan simulado de Ingeniería "
                       "de Sistemas; usado por la herramienta MCP ruta_autoaprendizaje.",
        "verificado": date.today().isoformat(),
        "criterio": "HTTP HEAD/GET con status < 400; los que fallan se descartan.",
        "recursos": recursos,
        "cursos": {c: filtra(ids) for c, ids in CURSOS.items() if filtra(ids)},
        "areas": {a: filtra(ids) for a, ids in AREAS.items() if filtra(ids)},
        "transversales": filtra(TRANSVERSALES),
        "descartados": {R[k][2]: str(e) for k, (v, e) in res.items() if not v},
    }
    SALIDA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(recursos)} recursos verificados, {len(data['descartados'])} descartados → {SALIDA}")
    for u, e in data["descartados"].items():
        print("  descartado:", u, e)


if __name__ == "__main__":
    main()
