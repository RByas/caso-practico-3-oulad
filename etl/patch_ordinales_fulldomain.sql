-- ============================================================
-- patch_ordinales_fulldomain.sql
-- Caso Práctico 3 | Ciencia de Datos I
--
-- Aplica, sobre la base 'oulad' YA MONTADA y con datos cargados:
--   1. Campos ordinales generados (*_ord) en las tablas reales
--   2. Tablas FullDomain: domain_assessment_type, domain_activity_type
--   3. Vista maestra v_student_master
--
-- Es IDEMPOTENTE: se puede correr varias veces sin error.
-- No recarga datos; solo añade estructura.
--
-- Uso:
--   mysql -u root -p oulad < etl/patch_ordinales_fulldomain.sql
-- ============================================================

USE oulad;

-- ------------------------------------------------------------
-- Helper: añade una columna generada solo si no existe
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS add_generated_col;
DELIMITER $$
CREATE PROCEDURE add_generated_col(
    IN p_table VARCHAR(64),
    IN p_col   VARCHAR(64),
    IN p_ddl   TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = p_table
          AND COLUMN_NAME  = p_col
    ) THEN
        SET @sql = CONCAT('ALTER TABLE `', p_table, '` ADD COLUMN ', p_ddl);
        PREPARE st FROM @sql;
        EXECUTE st;
        DEALLOCATE PREPARE st;
    END IF;
END$$
DELIMITER ;

-- ------------------------------------------------------------
-- 1. ORDINALES
-- ------------------------------------------------------------

-- assessments.assessment_type_ord
CALL add_generated_col('assessments', 'assessment_type_ord',
  "assessment_type_ord TINYINT GENERATED ALWAYS AS (
     CASE assessment_type WHEN 'TMA' THEN 1 WHEN 'CMA' THEN 2 WHEN 'Exam' THEN 3 ELSE 0 END
   ) STORED");

-- vle.activity_type_ord
CALL add_generated_col('vle', 'activity_type_ord',
  "activity_type_ord TINYINT GENERATED ALWAYS AS (
     CASE activity_type
       WHEN 'resource' THEN 1 WHEN 'oucontent' THEN 2 WHEN 'url' THEN 3
       WHEN 'homepage' THEN 4 WHEN 'subpage' THEN 5 WHEN 'glossary' THEN 6
       WHEN 'forumng' THEN 7 WHEN 'oucollaborate' THEN 8 WHEN 'dataplus' THEN 9
       WHEN 'quiz' THEN 10 WHEN 'ouelluminate' THEN 11 WHEN 'sharedsubpage' THEN 12
       WHEN 'questionnaire' THEN 13 WHEN 'page' THEN 14 WHEN 'externalquiz' THEN 15
       WHEN 'ouwiki' THEN 16 WHEN 'dualpane' THEN 17 WHEN 'repeatactivity' THEN 18
       WHEN 'folder' THEN 19 WHEN 'htmlactivity' THEN 20 ELSE 0 END
   ) STORED");

-- student_info: 6 ordinales
CALL add_generated_col('student_info', 'gender_ord',
  "gender_ord TINYINT GENERATED ALWAYS AS (
     CASE gender WHEN 'M' THEN 1 WHEN 'F' THEN 2 ELSE 0 END
   ) STORED");

CALL add_generated_col('student_info', 'highest_education_ord',
  "highest_education_ord TINYINT GENERATED ALWAYS AS (
     CASE highest_education
       WHEN 'No Formal quals' THEN 1 WHEN 'Lower Than A Level' THEN 2
       WHEN 'A Level or Equivalent' THEN 3 WHEN 'HE Qualification' THEN 4
       WHEN 'Post Graduate Qualification' THEN 5 ELSE 0 END
   ) STORED");

CALL add_generated_col('student_info', 'imd_band_ord',
  "imd_band_ord TINYINT GENERATED ALWAYS AS (
     CASE imd_band
       WHEN '0-10%' THEN 1 WHEN '10-20' THEN 2 WHEN '20-30%' THEN 3
       WHEN '30-40%' THEN 4 WHEN '40-50%' THEN 5 WHEN '50-60%' THEN 6
       WHEN '60-70%' THEN 7 WHEN '70-80%' THEN 8 WHEN '80-90%' THEN 9
       WHEN '90-100%' THEN 10 ELSE 0 END
   ) STORED");

CALL add_generated_col('student_info', 'age_band_ord',
  "age_band_ord TINYINT GENERATED ALWAYS AS (
     CASE age_band WHEN '0-35' THEN 1 WHEN '35-55' THEN 2 WHEN '55<=' THEN 3 ELSE 0 END
   ) STORED");

CALL add_generated_col('student_info', 'disability_ord',
  "disability_ord TINYINT GENERATED ALWAYS AS (
     CASE disability WHEN 'Y' THEN 1 WHEN 'N' THEN 0 ELSE 0 END
   ) STORED");

CALL add_generated_col('student_info', 'final_result_ord',
  "final_result_ord TINYINT GENERATED ALWAYS AS (
     CASE final_result WHEN 'Withdrawn' THEN 0 WHEN 'Fail' THEN 1
       WHEN 'Pass' THEN 2 WHEN 'Distinction' THEN 3 ELSE 0 END
   ) STORED");

DROP PROCEDURE IF EXISTS add_generated_col;

-- ------------------------------------------------------------
-- 2. FULLDOMAIN — catálogos de dominio completo
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS domain_assessment_type (
    assessment_type      VARCHAR(10)  NOT NULL,
    assessment_type_ord  TINYINT      NOT NULL,
    description          VARCHAR(100) NOT NULL,
    PRIMARY KEY (assessment_type)
);

INSERT IGNORE INTO domain_assessment_type VALUES
    ('TMA',  1, 'Tutor Marked Assessment — evaluación calificada por tutor'),
    ('CMA',  2, 'Computer Marked Assessment — evaluación automatizada'),
    ('Exam', 3, 'Final Exam — examen final presencial');

CREATE TABLE IF NOT EXISTS domain_activity_type (
    activity_type     VARCHAR(30)  NOT NULL,
    activity_type_ord TINYINT      NOT NULL,
    category          VARCHAR(20)  NOT NULL COMMENT 'content|collaboration|assessment|navigation',
    description       VARCHAR(150) NOT NULL,
    PRIMARY KEY (activity_type)
);

INSERT IGNORE INTO domain_activity_type VALUES
    ('resource',       1,  'content',       'Material estático descargable'),
    ('oucontent',      2,  'content',       'Contenido interactivo de la OU'),
    ('url',            3,  'content',       'Enlace externo'),
    ('homepage',       4,  'navigation',    'Página de inicio del módulo'),
    ('subpage',        5,  'navigation',    'Subpágina del módulo'),
    ('glossary',       6,  'content',       'Glosario de términos'),
    ('forumng',        7,  'collaboration', 'Foro de discusión'),
    ('oucollaborate',  8,  'collaboration', 'Herramienta colaborativa OU'),
    ('dataplus',       9,  'content',       'Datos y estadísticas interactivos'),
    ('quiz',          10,  'assessment',    'Cuestionario de autoevaluación'),
    ('ouelluminate',  11,  'collaboration', 'Sesión virtual en vivo'),
    ('sharedsubpage', 12,  'navigation',    'Subpágina compartida entre módulos'),
    ('questionnaire', 13,  'assessment',    'Encuesta o cuestionario'),
    ('page',          14,  'content',       'Página web del módulo'),
    ('externalquiz',  15,  'assessment',    'Quiz externo al sistema OU'),
    ('ouwiki',        16,  'collaboration', 'Wiki colaborativa'),
    ('dualpane',      17,  'navigation',    'Vista de doble panel'),
    ('repeatactivity',18,  'content',       'Actividad repetible'),
    ('folder',        19,  'content',       'Carpeta de recursos'),
    ('htmlactivity',  20,  'content',       'Actividad HTML interactiva');

-- FK opcionales hacia los catálogos FullDomain (ignoran error si ya existen)
-- (Se omiten ON DELETE para no romper cargas; descomentar si se desea integridad estricta)

-- ------------------------------------------------------------
-- 3. VISTA MAESTRA
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW v_student_master AS
SELECT
    si.id_student, si.code_module, si.code_presentation,
    si.gender, si.gender_ord, si.region,
    si.highest_education, si.highest_education_ord,
    si.imd_band, si.imd_band_ord,
    si.age_band, si.age_band_ord,
    si.num_of_prev_attempts, si.studied_credits,
    si.disability, si.disability_ord,
    si.final_result, si.final_result_ord,
    AVG(sa.score)                       AS avg_score,
    COUNT(sa.id_assessment)             AS num_assessments,
    SUM(sv.sum_click)                   AS total_clicks,
    COUNT(DISTINCT sv.date_interaction) AS active_days
FROM student_info si
LEFT JOIN student_assessment sa ON si.id_student = sa.id_student
LEFT JOIN student_vle sv
    ON si.id_student = sv.id_student
   AND si.code_module = sv.code_module
   AND si.code_presentation = sv.code_presentation
GROUP BY
    si.id_student, si.code_module, si.code_presentation,
    si.gender, si.gender_ord, si.region,
    si.highest_education, si.highest_education_ord,
    si.imd_band, si.imd_band_ord,
    si.age_band, si.age_band_ord,
    si.num_of_prev_attempts, si.studied_credits,
    si.disability, si.disability_ord,
    si.final_result, si.final_result_ord;

-- ------------------------------------------------------------
-- 4. VERIFICACIÓN
-- ------------------------------------------------------------
SELECT 'Ordinales en student_info:' AS info;
SHOW COLUMNS FROM student_info LIKE '%\_ord';
SELECT 'Tablas FullDomain:' AS info;
SHOW TABLES LIKE 'domain\_%';
SELECT 'Vista maestra (existencia, sin ejecutarla):' AS info;
SELECT TABLE_NAME, TABLE_TYPE
FROM information_schema.VIEWS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'v_student_master';
