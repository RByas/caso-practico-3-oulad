# ============================================================
# etl_pipeline.py — Pipeline ETL para OULAD → MySQL
# Caso Práctico 3 | Ciencia de Datos I
#
# Pasos:
#   1. EXTRACT  — lee los 7 CSV del OULAD
#   2. TRANSFORM — limpieza, imputación, validación
#   3. LOAD      — inserta en MySQL (oulad DB)
#
# Uso:
#   python etl_pipeline.py            # ETL completo
#   python etl_pipeline.py --check    # solo verifica archivos
# ============================================================

import os
import sys
import time
import argparse
import pandas as pd
import mysql.connector
from mysql.connector import Error

# ── Configuración ─────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "12345678",
    "database": "oulad",
    "port":     3306
}

DATA_DIR  = os.path.join(os.path.dirname(__file__), '..', 'data')
SCHEMA_SQL = os.path.join(os.path.dirname(__file__), 'schema.sql')

# Mapeo nombre_archivo → nombre_tabla
CSV_TABLE_MAP = {
    "courses.csv":            "courses",
    "assessments.csv":        "assessments",
    "vle.csv":                "vle",
    "studentInfo.csv":        "student_info",
    "studentRegistration.csv":"student_registration",
    "studentAssessment.csv":  "student_assessment",
    "studentVle.csv":         "student_vle",
}

# ── Helpers ───────────────────────────────────────────────────

def log(msg, level="INFO"):
    icons = {"INFO": "ℹ️ ", "OK": "✅", "WARN": "⚠️ ", "ERR": "❌", "STEP": "🔷"}
    print(f"[{level}] {icons.get(level,'')} {msg}")

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

# ============================================================
# EXTRACT
# ============================================================

def extract(filename):
    """Lee un CSV del OULAD y retorna un DataFrame."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        log(f"Archivo no encontrado: {path}", "ERR")
        return None
    df = pd.read_csv(path)
    log(f"Extraído {filename}: {df.shape[0]:,} filas × {df.shape[1]} columnas", "OK")
    return df

# ============================================================
# TRANSFORM
# ============================================================

def transform_courses(df):
    df = df.drop_duplicates()
    df.columns = ['code_module', 'code_presentation', 'module_presentation_length']
    df['module_presentation_length'] = pd.to_numeric(df['module_presentation_length'], errors='coerce').fillna(0).astype(int)
    return df

def transform_assessments(df):
    df = df.drop_duplicates()
    df.columns = ['code_module', 'code_presentation', 'id_assessment', 'assessment_type', 'date_due', 'weight']
    df['date_due'] = pd.to_numeric(df['date_due'], errors='coerce')
    df['weight']   = pd.to_numeric(df['weight'],   errors='coerce')
    valid_types = ['TMA', 'CMA', 'Exam']
    df['assessment_type'] = df['assessment_type'].where(df['assessment_type'].isin(valid_types), 'TMA')
    return df

def transform_vle(df):
    df = df.drop_duplicates(subset=['id_site'])
    df.columns = ['id_site', 'code_module', 'code_presentation', 'activity_type', 'week_from', 'week_to']
    df['activity_type'] = df['activity_type'].fillna('resource').str.strip()
    df['week_from'] = pd.to_numeric(df['week_from'], errors='coerce')
    df['week_to']   = pd.to_numeric(df['week_to'],   errors='coerce')
    return df

def transform_student_info(df):
    df = df.drop_duplicates()
    df.columns = ['code_module', 'code_presentation', 'id_student', 'gender',
                  'region', 'highest_education', 'imd_band', 'age_band',
                  'num_of_prev_attempts', 'studied_credits', 'disability', 'final_result']
    # Limpiar valores
    df['gender']            = df['gender'].fillna('M').str.strip()
    df['region']            = df['region'].fillna('Unknown').str.strip()
    df['highest_education'] = df['highest_education'].fillna('No Formal quals').str.strip()
    df['imd_band']          = df['imd_band'].fillna('50-60%').str.strip()
    df['age_band']          = df['age_band'].fillna('0-35').str.strip()
    df['disability']        = df['disability'].fillna('N').str.strip()
    df['final_result']      = df['final_result'].fillna('Withdrawn').str.strip()
    df['num_of_prev_attempts'] = pd.to_numeric(df['num_of_prev_attempts'], errors='coerce').fillna(0).astype(int)
    df['studied_credits']      = pd.to_numeric(df['studied_credits'],      errors='coerce').fillna(60).astype(int)
    # Reordenar columnas para la tabla
    return df[['id_student', 'code_module', 'code_presentation', 'gender',
               'region', 'highest_education', 'imd_band', 'age_band',
               'num_of_prev_attempts', 'studied_credits', 'disability', 'final_result']]

def transform_student_registration(df):
    df = df.drop_duplicates()
    df.columns = ['code_module', 'code_presentation', 'id_student',
                  'date_registration', 'date_unregistration']
    df['date_registration']   = pd.to_numeric(df['date_registration'],   errors='coerce')
    df['date_unregistration'] = pd.to_numeric(df['date_unregistration'], errors='coerce')
    return df[['id_student', 'code_module', 'code_presentation',
               'date_registration', 'date_unregistration']]

def transform_student_assessment(df):
    df = df.drop_duplicates(subset=['id_assessment', 'id_student'])
    df.columns = ['id_assessment', 'id_student', 'date_submitted', 'is_banked', 'score']
    df['date_submitted'] = pd.to_numeric(df['date_submitted'], errors='coerce')
    df['is_banked']      = pd.to_numeric(df['is_banked'],      errors='coerce').fillna(0).astype(int)
    df['score']          = pd.to_numeric(df['score'],          errors='coerce')
    # Cap outliers: score entre 0 y 100
    df['score'] = df['score'].clip(0, 100)
    return df

def transform_student_vle(df):
    df = df.drop_duplicates()
    df.columns = ['code_module', 'code_presentation', 'id_student', 'id_site', 'date', 'sum_click']
    df['sum_click'] = pd.to_numeric(df['sum_click'], errors='coerce').fillna(0).astype(int)
    # Cap outliers al percentil 98
    cap = int(df['sum_click'].quantile(0.98))
    df['sum_click'] = df['sum_click'].clip(0, cap)
    df = df.rename(columns={'date': 'date_interaction'})
    return df[['id_student', 'id_site', 'code_module', 'code_presentation', 'date_interaction', 'sum_click']]


TRANSFORM_MAP = {
    "courses.csv":            transform_courses,
    "assessments.csv":        transform_assessments,
    "vle.csv":                transform_vle,
    "studentInfo.csv":        transform_student_info,
    "studentRegistration.csv":transform_student_registration,
    "studentAssessment.csv":  transform_student_assessment,
    "studentVle.csv":         transform_student_vle,
}

# ============================================================
# LOAD
# ============================================================

def create_database_schema():
    """Ejecuta el schema.sql para crear la BD y tablas usando multi=True."""
    log("Creando esquema en MySQL...", "STEP")

    # Paso 1: crear la BD si no existe (sin seleccionarla)
    cfg = {k: v for k, v in DB_CONFIG.items() if k != 'database'}
    conn0 = mysql.connector.connect(**cfg)
    cur0 = conn0.cursor()
    cur0.execute("CREATE DATABASE IF NOT EXISTS oulad CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn0.commit()
    cur0.close()
    conn0.close()

    # Paso 2: crear tablas directamente desde Python (robusto en todas las versiones)
    _create_schema_fallback()

    # Paso 3: aplicar ordinales generados + tablas FullDomain (idempotente)
    apply_ordinals_and_domains()


def _create_schema_fallback():
    """Método alternativo: crea las tablas esenciales directamente en Python."""
    log("Creando tablas via DDL directo Python...", "STEP")
    conn = get_connection()
    cursor = conn.cursor()

    ddl_statements = [
        """CREATE TABLE IF NOT EXISTS courses (
            code_module VARCHAR(10) NOT NULL,
            code_presentation VARCHAR(10) NOT NULL,
            module_presentation_length INT NOT NULL,
            PRIMARY KEY (code_module, code_presentation)
        ) ENGINE=InnoDB""",

        """CREATE TABLE IF NOT EXISTS assessments (
            id_assessment INT NOT NULL,
            code_module VARCHAR(10) NOT NULL,
            code_presentation VARCHAR(10) NOT NULL,
            assessment_type VARCHAR(10) NOT NULL,
            date_due INT NULL,
            weight FLOAT NULL,
            PRIMARY KEY (id_assessment),
            CONSTRAINT fk_assess_course
                FOREIGN KEY (code_module, code_presentation)
                REFERENCES courses (code_module, code_presentation)
                ON UPDATE CASCADE ON DELETE RESTRICT
        ) ENGINE=InnoDB""",

        """CREATE TABLE IF NOT EXISTS vle (
            id_site INT NOT NULL,
            code_module VARCHAR(10) NOT NULL,
            code_presentation VARCHAR(10) NOT NULL,
            activity_type VARCHAR(30) NOT NULL,
            week_from SMALLINT NULL,
            week_to SMALLINT NULL,
            PRIMARY KEY (id_site),
            CONSTRAINT fk_vle_course
                FOREIGN KEY (code_module, code_presentation)
                REFERENCES courses (code_module, code_presentation)
                ON UPDATE CASCADE ON DELETE RESTRICT
        ) ENGINE=InnoDB""",

        """CREATE TABLE IF NOT EXISTS student_info (
            id_student INT NOT NULL,
            code_module VARCHAR(10) NOT NULL,
            code_presentation VARCHAR(10) NOT NULL,
            gender VARCHAR(5) NOT NULL,
            region VARCHAR(50) NOT NULL,
            highest_education VARCHAR(50) NOT NULL,
            imd_band VARCHAR(10) NULL,
            age_band VARCHAR(10) NOT NULL,
            num_of_prev_attempts TINYINT NOT NULL DEFAULT 0,
            studied_credits SMALLINT NOT NULL,
            disability VARCHAR(5) NOT NULL,
            final_result VARCHAR(15) NOT NULL,
            PRIMARY KEY (id_student, code_module, code_presentation),
            CONSTRAINT fk_sinfo_course
                FOREIGN KEY (code_module, code_presentation)
                REFERENCES courses (code_module, code_presentation)
                ON UPDATE CASCADE ON DELETE RESTRICT
        ) ENGINE=InnoDB""",

        """CREATE TABLE IF NOT EXISTS student_registration (
            id_student INT NOT NULL,
            code_module VARCHAR(10) NOT NULL,
            code_presentation VARCHAR(10) NOT NULL,
            date_registration INT NULL,
            date_unregistration INT NULL,
            PRIMARY KEY (id_student, code_module, code_presentation),
            CONSTRAINT fk_sreg_course
                FOREIGN KEY (code_module, code_presentation)
                REFERENCES courses (code_module, code_presentation)
                ON UPDATE CASCADE ON DELETE RESTRICT
        ) ENGINE=InnoDB""",

        """CREATE TABLE IF NOT EXISTS student_assessment (
            id_assessment INT NOT NULL,
            id_student INT NOT NULL,
            date_submitted INT NULL,
            is_banked TINYINT(1) NOT NULL DEFAULT 0,
            score FLOAT NULL,
            PRIMARY KEY (id_assessment, id_student),
            CONSTRAINT fk_sassess
                FOREIGN KEY (id_assessment)
                REFERENCES assessments (id_assessment)
                ON UPDATE CASCADE ON DELETE RESTRICT
        ) ENGINE=InnoDB""",

        """CREATE TABLE IF NOT EXISTS student_vle (
            id_student INT NOT NULL,
            id_site INT NOT NULL,
            code_module VARCHAR(10) NOT NULL,
            code_presentation VARCHAR(10) NOT NULL,
            date_interaction INT NOT NULL,
            sum_click INT NOT NULL DEFAULT 0,
            PRIMARY KEY (id_student, id_site, date_interaction),
            CONSTRAINT fk_svle_vle
                FOREIGN KEY (id_site) REFERENCES vle (id_site)
                ON UPDATE CASCADE ON DELETE RESTRICT,
            CONSTRAINT fk_svle_course
                FOREIGN KEY (code_module, code_presentation)
                REFERENCES courses (code_module, code_presentation)
                ON UPDATE CASCADE ON DELETE RESTRICT,
            INDEX idx_svle_student (id_student),
            INDEX idx_svle_module  (code_module, code_presentation)
        ) ENGINE=InnoDB""",

        # Vista maestra para EDA
        """CREATE OR REPLACE VIEW v_student_master AS
        SELECT
            si.id_student, si.code_module, si.code_presentation,
            si.gender, si.region, si.highest_education,
            si.imd_band, si.age_band,
            si.num_of_prev_attempts, si.studied_credits,
            si.disability, si.final_result,
            CASE si.final_result
                WHEN 'Withdrawn'   THEN 0 WHEN 'Fail'        THEN 1
                WHEN 'Pass'        THEN 2 WHEN 'Distinction'  THEN 3
                ELSE 0 END AS final_result_ord,
            CASE si.gender WHEN 'M' THEN 1 WHEN 'F' THEN 2 ELSE 0 END AS gender_ord,
            CASE si.highest_education
                WHEN 'No Formal quals'             THEN 1
                WHEN 'Lower Than A Level'           THEN 2
                WHEN 'A Level or Equivalent'        THEN 3
                WHEN 'HE Qualification'             THEN 4
                WHEN 'Post Graduate Qualification'  THEN 5
                ELSE 0 END AS highest_education_ord,
            CASE si.imd_band
                WHEN '0-10%'  THEN 1 WHEN '10-20'  THEN 2 WHEN '20-30%' THEN 3
                WHEN '30-40%' THEN 4 WHEN '40-50%' THEN 5 WHEN '50-60%' THEN 6
                WHEN '60-70%' THEN 7 WHEN '70-80%' THEN 8 WHEN '80-90%' THEN 9
                WHEN '90-100%' THEN 10 ELSE 0 END AS imd_band_ord,
            CASE si.age_band
                WHEN '0-35' THEN 1 WHEN '35-55' THEN 2 WHEN '55<=' THEN 3
                ELSE 0 END AS age_band_ord,
            CASE si.disability WHEN 'Y' THEN 1 ELSE 0 END AS disability_ord,
            AVG(sa.score)           AS avg_score,
            COUNT(sa.id_assessment) AS num_assessments,
            SUM(sv.sum_click)       AS total_clicks,
            COUNT(DISTINCT sv.date_interaction) AS active_days
        FROM student_info si
        LEFT JOIN student_assessment sa ON si.id_student = sa.id_student
        LEFT JOIN student_vle sv
            ON si.id_student = sv.id_student
            AND si.code_module = sv.code_module
            AND si.code_presentation = sv.code_presentation
        GROUP BY si.id_student, si.code_module, si.code_presentation,
            si.gender, si.region, si.highest_education, si.imd_band,
            si.age_band, si.num_of_prev_attempts, si.studied_credits,
            si.disability, si.final_result"""
    ]

    for stmt in ddl_statements:
        try:
            cursor.execute(stmt)
            conn.commit()
        except Error as e:
            if e.errno not in (1050, 1060, 1061, 1062, 1091):
                log(f"  DDL Warning: {e}", "WARN")

    cursor.close()
    conn.close()
    log("Tablas creadas correctamente (fallback).", "OK")

def apply_ordinals_and_domains():
    """Añade columnas ordinales generadas (*_ord) y tablas FullDomain.
    Idempotente: solo crea lo que falte. Cumple el requisito de
    ordinales + FullDomain (ASSESS y VLE) en el DBMS."""
    log("Aplicando ordinales + FullDomain...", "STEP")
    conn = get_connection()
    cursor = conn.cursor()

    # (tabla, columna, expresión generada)
    ordinals = [
        ("assessments", "assessment_type_ord",
         "CASE assessment_type WHEN 'TMA' THEN 1 WHEN 'CMA' THEN 2 WHEN 'Exam' THEN 3 ELSE 0 END"),
        ("vle", "activity_type_ord",
         ("CASE activity_type WHEN 'resource' THEN 1 WHEN 'oucontent' THEN 2 WHEN 'url' THEN 3 "
          "WHEN 'homepage' THEN 4 WHEN 'subpage' THEN 5 WHEN 'glossary' THEN 6 WHEN 'forumng' THEN 7 "
          "WHEN 'oucollaborate' THEN 8 WHEN 'dataplus' THEN 9 WHEN 'quiz' THEN 10 WHEN 'ouelluminate' THEN 11 "
          "WHEN 'sharedsubpage' THEN 12 WHEN 'questionnaire' THEN 13 WHEN 'page' THEN 14 WHEN 'externalquiz' THEN 15 "
          "WHEN 'ouwiki' THEN 16 WHEN 'dualpane' THEN 17 WHEN 'repeatactivity' THEN 18 WHEN 'folder' THEN 19 "
          "WHEN 'htmlactivity' THEN 20 ELSE 0 END")),
        ("student_info", "gender_ord",
         "CASE gender WHEN 'M' THEN 1 WHEN 'F' THEN 2 ELSE 0 END"),
        ("student_info", "highest_education_ord",
         ("CASE highest_education WHEN 'No Formal quals' THEN 1 WHEN 'Lower Than A Level' THEN 2 "
          "WHEN 'A Level or Equivalent' THEN 3 WHEN 'HE Qualification' THEN 4 "
          "WHEN 'Post Graduate Qualification' THEN 5 ELSE 0 END")),
        ("student_info", "imd_band_ord",
         ("CASE imd_band WHEN '0-10%' THEN 1 WHEN '10-20' THEN 2 WHEN '20-30%' THEN 3 WHEN '30-40%' THEN 4 "
          "WHEN '40-50%' THEN 5 WHEN '50-60%' THEN 6 WHEN '60-70%' THEN 7 WHEN '70-80%' THEN 8 "
          "WHEN '80-90%' THEN 9 WHEN '90-100%' THEN 10 ELSE 0 END")),
        ("student_info", "age_band_ord",
         "CASE age_band WHEN '0-35' THEN 1 WHEN '35-55' THEN 2 WHEN '55<=' THEN 3 ELSE 0 END"),
        ("student_info", "disability_ord",
         "CASE disability WHEN 'Y' THEN 1 WHEN 'N' THEN 0 ELSE 0 END"),
        ("student_info", "final_result_ord",
         ("CASE final_result WHEN 'Withdrawn' THEN 0 WHEN 'Fail' THEN 1 WHEN 'Pass' THEN 2 "
          "WHEN 'Distinction' THEN 3 ELSE 0 END")),
    ]

    for table, col, expr in ordinals:
        cursor.execute(
            """SELECT 1 FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s""",
            (DB_CONFIG["database"], table, col))
        if cursor.fetchone():
            continue
        try:
            cursor.execute(
                f"ALTER TABLE `{table}` ADD COLUMN `{col}` TINYINT "
                f"GENERATED ALWAYS AS ({expr}) STORED")
            conn.commit()
        except Error as e:
            log(f"  Ordinal {table}.{col}: {e}", "WARN")

    # FullDomain
    domain_ddl = [
        """CREATE TABLE IF NOT EXISTS domain_assessment_type (
            assessment_type VARCHAR(10) NOT NULL,
            assessment_type_ord TINYINT NOT NULL,
            description VARCHAR(100) NOT NULL,
            PRIMARY KEY (assessment_type)) ENGINE=InnoDB""",
        """CREATE TABLE IF NOT EXISTS domain_activity_type (
            activity_type VARCHAR(30) NOT NULL,
            activity_type_ord TINYINT NOT NULL,
            category VARCHAR(20) NOT NULL,
            description VARCHAR(150) NOT NULL,
            PRIMARY KEY (activity_type)) ENGINE=InnoDB""",
    ]
    for stmt in domain_ddl:
        cursor.execute(stmt)
    conn.commit()

    cursor.execute("""INSERT IGNORE INTO domain_assessment_type VALUES
        ('TMA',1,'Tutor Marked Assessment'),
        ('CMA',2,'Computer Marked Assessment'),
        ('Exam',3,'Final Exam')""")
    activity_rows = [
        ('resource',1,'content','Material estático descargable'),
        ('oucontent',2,'content','Contenido interactivo de la OU'),
        ('url',3,'content','Enlace externo'),
        ('homepage',4,'navigation','Página de inicio del módulo'),
        ('subpage',5,'navigation','Subpágina del módulo'),
        ('glossary',6,'content','Glosario de términos'),
        ('forumng',7,'collaboration','Foro de discusión'),
        ('oucollaborate',8,'collaboration','Herramienta colaborativa OU'),
        ('dataplus',9,'content','Datos y estadísticas interactivos'),
        ('quiz',10,'assessment','Cuestionario de autoevaluación'),
        ('ouelluminate',11,'collaboration','Sesión virtual en vivo'),
        ('sharedsubpage',12,'navigation','Subpágina compartida'),
        ('questionnaire',13,'assessment','Encuesta o cuestionario'),
        ('page',14,'content','Página web del módulo'),
        ('externalquiz',15,'assessment','Quiz externo'),
        ('ouwiki',16,'collaboration','Wiki colaborativa'),
        ('dualpane',17,'navigation','Vista de doble panel'),
        ('repeatactivity',18,'content','Actividad repetible'),
        ('folder',19,'content','Carpeta de recursos'),
        ('htmlactivity',20,'content','Actividad HTML interactiva'),
    ]
    cursor.executemany(
        "INSERT IGNORE INTO domain_activity_type VALUES (%s,%s,%s,%s)", activity_rows)
    conn.commit()

    cursor.close()
    conn.close()
    log("Ordinales + FullDomain aplicados.", "OK")


def load_dataframe(df, table_name, chunk_size=5000):
    """Carga un DataFrame en MySQL en chunks usando INSERT IGNORE."""
    if df is None or df.empty:
        log(f"DataFrame vacío, saltando tabla {table_name}", "WARN")
        return

    conn = get_connection()
    cursor = conn.cursor()

    cols = list(df.columns)
    placeholders = ', '.join(['%s'] * len(cols))
    col_names    = ', '.join([f'`{c}`' for c in cols])
    sql = f"INSERT IGNORE INTO `{table_name}` ({col_names}) VALUES ({placeholders})"

    total = len(df)
    loaded = 0
    t0 = time.time()

    for start in range(0, total, chunk_size):
        chunk = df.iloc[start:start + chunk_size]
        # Convertir NaN a None para MySQL
        rows = [
            tuple(None if pd.isna(v) else v for v in row)
            for row in chunk.itertuples(index=False)
        ]
        cursor.executemany(sql, rows)
        conn.commit()
        loaded += len(rows)
        pct = loaded / total * 100
        print(f"\r  → {table_name}: {loaded:,}/{total:,} ({pct:.1f}%) — {time.time()-t0:.1f}s", end='')

    print()
    cursor.close()
    conn.close()
    log(f"Tabla {table_name} cargada: {loaded:,} filas", "OK")

# ============================================================
# MAIN PIPELINE
# ============================================================

def check_files():
    """Verifica que todos los CSV estén presentes."""
    log("Verificando archivos CSV del OULAD...", "STEP")
    all_ok = True
    for fname in CSV_TABLE_MAP:
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            size_mb = os.path.getsize(path) / 1024 / 1024
            log(f"  {fname:35s} {size_mb:7.1f} MB", "OK")
        else:
            log(f"  {fname:35s} ¡NO ENCONTRADO!", "ERR")
            all_ok = False
    if not all_ok:
        log("Descarga los archivos y colócalos en la carpeta data/", "WARN")
        log("Ver: DESCARGA_OULAD.md", "WARN")
    return all_ok

def run_etl():
    """Ejecuta el pipeline ETL completo."""
    log("=" * 55, "STEP")
    log("  PIPELINE ETL — OULAD → MySQL", "STEP")
    log("=" * 55, "STEP")

    # Verificar archivos
    if not check_files():
        log("Pipeline abortado. Faltan archivos CSV.", "ERR")
        sys.exit(1)

    # Crear schema
    create_database_schema()

    # Orden de carga respetando FK
    load_order = [
        "courses.csv",
        "assessments.csv",
        "vle.csv",
        "studentInfo.csv",
        "studentRegistration.csv",
        "studentAssessment.csv",
        "studentVle.csv",
    ]

    t_total = time.time()
    for fname in load_order:
        table = CSV_TABLE_MAP[fname]
        log(f"Procesando: {fname} → {table}", "STEP")

        df = extract(fname)
        if df is None:
            continue

        df = TRANSFORM_MAP[fname](df)
        log(f"  Transformado: {df.shape[0]:,} filas limpias", "INFO")

        chunk = 1000 if fname == "studentVle.csv" else 5000
        load_dataframe(df, table, chunk_size=chunk)

    elapsed = time.time() - t_total
    log(f"Pipeline ETL completado en {elapsed:.1f} segundos.", "OK")
    log("Base de datos 'oulad' lista para el EDA.", "OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETL Pipeline OULAD → MySQL")
    parser.add_argument("--check", action="store_true", help="Solo verifica archivos CSV")
    args = parser.parse_args()

    if args.check:
        check_files()
    else:
        run_etl()
