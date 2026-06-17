-- ============================================================
-- schema.sql — DDL para OULAD en MySQL
-- Caso Práctico 3 | Ciencia de Datos I
-- Incluye: PK, FK, Unique Constraints, Campos Ordinales,
--          FullDomain para ASSESS y VLE
-- ============================================================

CREATE DATABASE IF NOT EXISTS oulad
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE oulad;

-- ============================================================
-- 1. COURSES
-- ============================================================
CREATE TABLE IF NOT EXISTS courses (
    code_module              VARCHAR(10)  NOT NULL,
    code_presentation        VARCHAR(10)  NOT NULL,
    module_presentation_length INT        NOT NULL,
    -- PK compuesta
    PRIMARY KEY (code_module, code_presentation)
);

-- ============================================================
-- 2. ASSESSMENTS
-- Includes FullDomain for assessment_type
-- ============================================================
CREATE TABLE IF NOT EXISTS assessments (
    id_assessment            INT          NOT NULL AUTO_INCREMENT,
    code_module              VARCHAR(10)  NOT NULL,
    code_presentation        VARCHAR(10)  NOT NULL,
    assessment_type          VARCHAR(10)  NOT NULL,
    -- Ordinal: TMA=1, CMA=2, Exam=3
    assessment_type_ord      TINYINT      GENERATED ALWAYS AS (
        CASE assessment_type
            WHEN 'TMA'  THEN 1
            WHEN 'CMA'  THEN 2
            WHEN 'Exam' THEN 3
            ELSE 0
        END
    ) STORED,
    date_due                 INT          NULL,
    weight                   FLOAT        NULL,
    PRIMARY KEY (id_assessment),
    CONSTRAINT fk_assess_course
        FOREIGN KEY (code_module, code_presentation)
        REFERENCES courses (code_module, code_presentation)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

-- FullDomain ASSESS: catálogo de tipos de evaluación válidos
CREATE TABLE IF NOT EXISTS domain_assessment_type (
    assessment_type          VARCHAR(10)  NOT NULL,
    assessment_type_ord      TINYINT      NOT NULL,
    description              VARCHAR(100) NOT NULL,
    PRIMARY KEY (assessment_type)
);

INSERT IGNORE INTO domain_assessment_type VALUES
    ('TMA',  1, 'Tutor Marked Assessment — evaluación calificada por tutor'),
    ('CMA',  2, 'Computer Marked Assessment — evaluación automatizada'),
    ('Exam', 3, 'Final Exam — examen final presencial');

-- ============================================================
-- 3. VLE (Virtual Learning Environment)
-- Includes FullDomain for activity_type
-- ============================================================
CREATE TABLE IF NOT EXISTS vle (
    id_site                  INT          NOT NULL,
    code_module              VARCHAR(10)  NOT NULL,
    code_presentation        VARCHAR(10)  NOT NULL,
    activity_type            VARCHAR(30)  NOT NULL,
    -- Ordinal por engagement esperado
    activity_type_ord        TINYINT      GENERATED ALWAYS AS (
        CASE activity_type
            WHEN 'resource'     THEN 1
            WHEN 'oucontent'    THEN 2
            WHEN 'url'          THEN 3
            WHEN 'homepage'     THEN 4
            WHEN 'subpage'      THEN 5
            WHEN 'glossary'     THEN 6
            WHEN 'forumng'      THEN 7
            WHEN 'oucollaborate'THEN 8
            WHEN 'dataplus'     THEN 9
            WHEN 'quiz'         THEN 10
            WHEN 'ouelluminate' THEN 11
            WHEN 'sharedsubpage'THEN 12
            WHEN 'questionnaire'THEN 13
            WHEN 'page'         THEN 14
            WHEN 'externalquiz' THEN 15
            WHEN 'ouwiki'       THEN 16
            WHEN 'dualpane'     THEN 17
            WHEN 'repeatactivity' THEN 18
            WHEN 'folder'       THEN 19
            WHEN 'htmlactivity' THEN 20
            ELSE 0
        END
    ) STORED,
    week_from                SMALLINT     NULL,
    week_to                  SMALLINT     NULL,
    PRIMARY KEY (id_site),
    CONSTRAINT fk_vle_course
        FOREIGN KEY (code_module, code_presentation)
        REFERENCES courses (code_module, code_presentation)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

-- FullDomain VLE: catálogo de tipos de actividad válidos
CREATE TABLE IF NOT EXISTS domain_activity_type (
    activity_type            VARCHAR(30)  NOT NULL,
    activity_type_ord        TINYINT      NOT NULL,
    category                 VARCHAR(20)  NOT NULL COMMENT 'content|collaboration|assessment|navigation',
    description              VARCHAR(150) NOT NULL,
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

-- ============================================================
-- 4. STUDENT INFO
-- ============================================================
CREATE TABLE IF NOT EXISTS student_info (
    id_student               INT          NOT NULL,
    code_module              VARCHAR(10)  NOT NULL,
    code_presentation        VARCHAR(10)  NOT NULL,
    gender                   VARCHAR(5)   NOT NULL,
    -- Ordinal gender: M=1, F=2
    gender_ord               TINYINT      GENERATED ALWAYS AS (
        CASE gender WHEN 'M' THEN 1 WHEN 'F' THEN 2 ELSE 0 END
    ) STORED,
    region                   VARCHAR(50)  NOT NULL,
    highest_education        VARCHAR(50)  NOT NULL,
    -- Ordinal education level
    highest_education_ord    TINYINT      GENERATED ALWAYS AS (
        CASE highest_education
            WHEN 'No Formal quals'                        THEN 1
            WHEN 'Lower Than A Level'                     THEN 2
            WHEN 'A Level or Equivalent'                  THEN 3
            WHEN 'HE Qualification'                       THEN 4
            WHEN 'Post Graduate Qualification'            THEN 5
            ELSE 0
        END
    ) STORED,
    imd_band                 VARCHAR(10)  NULL,
    -- Ordinal IMD band (deprivation index)
    imd_band_ord             TINYINT      GENERATED ALWAYS AS (
        CASE imd_band
            WHEN '0-10%'   THEN 1
            WHEN '10-20'   THEN 2
            WHEN '20-30%'  THEN 3
            WHEN '30-40%'  THEN 4
            WHEN '40-50%'  THEN 5
            WHEN '50-60%'  THEN 6
            WHEN '60-70%'  THEN 7
            WHEN '70-80%'  THEN 8
            WHEN '80-90%'  THEN 9
            WHEN '90-100%' THEN 10
            ELSE 0
        END
    ) STORED,
    age_band                 VARCHAR(10)  NOT NULL,
    -- Ordinal age band
    age_band_ord             TINYINT      GENERATED ALWAYS AS (
        CASE age_band
            WHEN '0-35' THEN 1
            WHEN '35-55' THEN 2
            WHEN '55<='  THEN 3
            ELSE 0
        END
    ) STORED,
    num_of_prev_attempts     TINYINT      NOT NULL DEFAULT 0,
    studied_credits          SMALLINT     NOT NULL,
    disability               VARCHAR(5)   NOT NULL,
    -- Ordinal disability: N=0, Y=1
    disability_ord           TINYINT      GENERATED ALWAYS AS (
        CASE disability WHEN 'Y' THEN 1 WHEN 'N' THEN 0 ELSE 0 END
    ) STORED,
    final_result             VARCHAR(15)  NOT NULL,
    -- Ordinal final result
    final_result_ord         TINYINT      GENERATED ALWAYS AS (
        CASE final_result
            WHEN 'Withdrawn'    THEN 0
            WHEN 'Fail'         THEN 1
            WHEN 'Pass'         THEN 2
            WHEN 'Distinction'  THEN 3
            ELSE 0
        END
    ) STORED,
    PRIMARY KEY (id_student, code_module, code_presentation),
    CONSTRAINT fk_sinfo_course
        FOREIGN KEY (code_module, code_presentation)
        REFERENCES courses (code_module, code_presentation)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

-- ============================================================
-- 5. STUDENT REGISTRATION
-- ============================================================
CREATE TABLE IF NOT EXISTS student_registration (
    id_student               INT          NOT NULL,
    code_module              VARCHAR(10)  NOT NULL,
    code_presentation        VARCHAR(10)  NOT NULL,
    date_registration        INT          NULL,
    date_unregistration      INT          NULL,
    PRIMARY KEY (id_student, code_module, code_presentation),
    CONSTRAINT fk_sreg_course
        FOREIGN KEY (code_module, code_presentation)
        REFERENCES courses (code_module, code_presentation)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

-- ============================================================
-- 6. STUDENT ASSESSMENT
-- ============================================================
CREATE TABLE IF NOT EXISTS student_assessment (
    id_assessment            INT          NOT NULL,
    id_student               INT          NOT NULL,
    date_submitted           INT          NULL,
    is_banked                TINYINT(1)   NOT NULL DEFAULT 0,
    score                    FLOAT        NULL,
    PRIMARY KEY (id_assessment, id_student),
    CONSTRAINT fk_sassess_assessment
        FOREIGN KEY (id_assessment)
        REFERENCES assessments (id_assessment)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

-- ============================================================
-- 7. STUDENT VLE (tabla de hechos — la más grande)
-- ============================================================
CREATE TABLE IF NOT EXISTS student_vle (
    id_student               INT          NOT NULL,
    id_site                  INT          NOT NULL,
    code_module              VARCHAR(10)  NOT NULL,
    code_presentation        VARCHAR(10)  NOT NULL,
    date_interaction         INT          NOT NULL,
    sum_click                INT          NOT NULL DEFAULT 0,
    PRIMARY KEY (id_student, id_site, date_interaction),
    CONSTRAINT fk_svle_vle
        FOREIGN KEY (id_site)
        REFERENCES vle (id_site)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_svle_course
        FOREIGN KEY (code_module, code_presentation)
        REFERENCES courses (code_module, code_presentation)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_svle_student  (id_student),
    INDEX idx_svle_module   (code_module, code_presentation)
);

-- ============================================================
-- INDICES ADICIONALES para rendimiento del EDA
-- ============================================================
CREATE INDEX idx_sinfo_result   ON student_info (final_result);
CREATE INDEX idx_sinfo_module   ON student_info (code_module, code_presentation);
CREATE INDEX idx_sassess_score  ON student_assessment (score);
CREATE INDEX idx_svle_clicks    ON student_vle (sum_click);

-- ============================================================
-- VISTA MAESTRA: une studentInfo + assessment scores + VLE
-- ============================================================
CREATE OR REPLACE VIEW v_student_master AS
SELECT
    si.id_student,
    si.code_module,
    si.code_presentation,
    si.gender,
    si.gender_ord,
    si.region,
    si.highest_education,
    si.highest_education_ord,
    si.imd_band,
    si.imd_band_ord,
    si.age_band,
    si.age_band_ord,
    si.num_of_prev_attempts,
    si.studied_credits,
    si.disability,
    si.disability_ord,
    si.final_result,
    si.final_result_ord,
    AVG(sa.score)           AS avg_score,
    COUNT(sa.id_assessment) AS num_assessments,
    SUM(sv.sum_click)       AS total_clicks,
    COUNT(DISTINCT sv.date_interaction) AS active_days
FROM student_info si
LEFT JOIN student_assessment sa
    ON si.id_student = sa.id_student
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
