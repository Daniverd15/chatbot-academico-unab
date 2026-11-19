export type Prioridad = 'ALTA' | 'MEDIA' | 'BAJA' | 'INFO';

export interface Estudiante {
  codigo: string;
  nombre_completo: string;
  programa: string;
  cohorte: string | number;
}

export interface LoginResponse {
  ok: boolean;
  mensaje?: string;
  estudiante?: Estudiante;
}

export interface Resumen {
  codigo?: string;
  nombre_completo?: string;
  email?: string;
  programa?: string;
  cohorte?: string | number;
  semestre_por_creditos?: number;
  creditos_aprobados?: number;
  creditos_totales?: number;
  creditos_pendientes?: number;
  porcentaje_avance?: number;
  pga_acumulado?: number | null;
  pga_ultimo_periodo?: number | null;
  estado_academico?: string | null;
  estado_matricula_actual?: string | null;
  saldo_pendiente?: number | null;
  cursos_en_curso?: number;
  creditos_en_curso?: number;
}

export interface Alerta {
  prioridad: Prioridad;
  tipo?: string;
  mensaje: string;
}

export interface Competencia {
  ruta: 1 | 2 | 3;
  ruta_nombre: string;
  cumplida: boolean;
  en_curso: boolean;
  detalle: string | null;
}

export type EstadoCurso = 'Aprobado' | 'Cursando' | 'Reprobado (pendiente)' | 'Pendiente';

export interface CursoAvance {
  curso_id: string | number;
  curso: string;
  creditos: number;
  estado: EstadoCurso;
  nota_aprobacion: number | null;
}

export interface SemestreAvance {
  semestre: number;
  cursos: CursoAvance[];
}

export interface Proyeccion {
  semestres_restantes_ideal?: number;
  periodo_grado_ideal?: string;
  proyeccion_probabilistica?: {
    periodo_grado_p50?: string;
    periodo_grado_p90?: string;
    cursos_con_mayor_riesgo_de_reprobar?: { curso: string; prob_reprobar: number }[];
  } | null;
  plan_sugerido?: { periodo: string; creditos: number; cursos: string[] }[];
}

export interface FactorRiesgo {
  feature: string;
  /** Nombre legible de la variable, p. ej. "PGA acumulado". */
  etiqueta: string;
  /** Valor del estudiante. */
  valor: number;
  /** Media del programa (datos de entrenamiento del modelo). */
  media: number;
  /** Aporte al log-odds: coeficiente · valor estandarizado. */
  contribucion: number;
  efecto: 'aumenta' | 'reduce';
}

export interface Riesgo {
  probabilidad: number;
  nivel: 'bajo' | 'medio' | 'alto';
  modelo?: string;
  intercepto?: number;
  /** Factores ordenados por |contribución| (explicabilidad del modelo). */
  factores?: FactorRiesgo[];
  explicacion?: string;
}

export interface Noticia {
  titulo: string;
  url: string;
  fecha_pub?: string | null;
  tipo?: string | null;
  resumen?: string | null;
  /** Tema asignado por el scraper multifuente (database/06_noticias_temas.sql). Puede no llegar aún. */
  tema?: TemaNoticia | string | null;
  /** Medio que publicó la noticia (p. ej. "UNAB", "ENTER.CO", "El Tiempo"). */
  fuente_nombre?: string | null;
}

export type TemaNoticia = 'educacion' | 'tecnologia' | 'ingenieria_sistemas' | 'institucional';

export interface EventoCalendario {
  categoria?: string | null;
  evento: string;
  fecha_inicio?: string | null;
  fecha_fin?: string | null;
}

export interface PgaPeriodo {
  periodo_id: string;
  pga_periodo: number;
  estado_academico?: string;
  creditos_aprobados?: number;
}

export interface RecursoAprendizaje {
  titulo: string;
  proveedor?: string;
  url: string;
  tipo: 'video' | 'curso' | 'libro' | 'práctica' | string;
  idioma?: string;
  /** Horas estimadas para completar el recurso. */
  horas?: number;
}

export interface CursoFoco {
  curso_id: string;
  curso: string;
  tipo: 'cursando' | 'repitencia' | 'preparacion' | 'refuerzo' | string;
  motivo: string;
  horas_semana: number;
  objetivo: string;
  recursos: RecursoAprendizaje[];
}

/** Resumen de la ruta de autoaprendizaje personalizada (herramienta MCP ruta_autoaprendizaje). */
export interface RutaAutoaprendizaje {
  semanas: number;
  horas_semana: number;
  cursos_foco: CursoFoco[];
  estrategias: { nombre: string; como: string }[];
  consejos?: string[];
  hitos: { semana: number; hito: string }[];
  apoyo_unab: { servicio: string; para: string }[];
}

export interface Dashboard {
  ok: boolean;
  mensaje?: string;
  resumen?: Resumen | null;
  alertas?: Alerta[] | null;
  competencias?: Competencia[] | null;
  avance?: SemestreAvance[] | null;
  proyeccion?: Proyeccion | null;
  riesgo?: Riesgo | null;
  noticias?: Noticia[] | null;
  calendario?: EventoCalendario[] | null;
  historial_pga?: PgaPeriodo[] | null;
  autoaprendizaje?: RutaAutoaprendizaje | null;
}

export interface Fuente {
  titulo: string;
  url: string;
}

export interface ChatResponse {
  respuesta: string;
  intencion?: string;
  fuentes?: Fuente[];
  bloqueado?: boolean;
  log_id?: number | null;
}

export interface Credenciales {
  codigo: string;
  pin: string;
}

export interface Sesion extends Credenciales {
  nombre: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'bot';
  text: string;
  ts: number;
  fuentes?: Fuente[];
  bloqueado?: boolean;
  intencion?: string;
  logId?: number | null;
  esError?: boolean;
  voto?: 'up' | 'down';
  votoError?: boolean;
}
