# ============================================================
# eda_oulad.py — EDA Extendido sobre OULAD en MySQL
# Caso Práctico 3 | Ciencia de Datos I
#
# Gráficos generados:
#   1. Bar chart — distribución de final_result
#   2. Bar chart — resultados por módulo
#   3. Bar chart — resultados por nivel educativo
#   4. Boxplot  — score por final_result
#   5. Boxplot  — total_clicks por final_result
#   6. Campana de Gauss — distribución de scores
#   7. Correlación — heatmap de variables numéricas
#   8. Dispersión — score vs total_clicks
#   9. Dispersión — active_days vs avg_score
#  10. Matriz de confusión — modelo básico Pass/Fail
#  11. Scatter por módulo — score vs clicks
#  12. Pivot table — tasa de aprobación por región y educación
#  13. ANOVA y t-test — hallazgos estadísticos
#
# Uso: python eda/eda_oulad.py
# ============================================================

import os
import sys
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Patch
import seaborn as sns
from scipy import stats
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
from sklearn.model_selection import train_test_split
import mysql.connector

# ── Config ────────────────────────────────────────────────────
DB_CONFIG = {
    "host": "localhost", "user": "root",
    "password": "12345678", "database": "oulad", "port": 3306
}

PLOTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'plots')
os.makedirs(PLOTS_DIR, exist_ok=True)

PALETTE = {
    'Distinction': '#2ecc71',
    'Pass':        '#3498db',
    'Fail':        '#e74c3c',
    'Withdrawn':   '#95a5a6'
}
ORDER = ['Distinction', 'Pass', 'Fail', 'Withdrawn']

sns.set_theme(style='whitegrid', palette='muted', font_scale=1.1)
plt.rcParams.update({'figure.dpi': 150, 'savefig.bbox': 'tight'})


# ── Conexión y carga de datos ─────────────────────────────────

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def load_master_data() -> pd.DataFrame:
    """
    Construye el dataset maestro en Python para evitar que MySQL
    use espacio en disco temporal con el GROUP BY de la vista.
    """
    print("📥 Cargando student_info desde MySQL...")
    conn = get_connection()
    df_info = pd.read_sql("SELECT * FROM student_info", conn)
    print(f"   → student_info: {len(df_info):,} filas")

    print("📥 Agregando student_assessment en Python...")
    df_sa = pd.read_sql(
        "SELECT id_student, score FROM student_assessment WHERE score IS NOT NULL",
        conn
    )
    agg_scores = df_sa.groupby('id_student').agg(
        avg_score=('score', 'mean'),
        num_assessments=('score', 'count')
    ).reset_index()
    print(f"   → student_assessment: {len(agg_scores):,} estudiantes")

    print("📥 Agregando student_vle en Python (puede tardar ~1 min)...")
    df_vle = pd.read_sql(
        """SELECT id_student, code_module, code_presentation,
                  sum_click, date_interaction
           FROM student_vle""",
        conn
    )
    agg_vle = df_vle.groupby(['id_student', 'code_module', 'code_presentation']).agg(
        total_clicks=('sum_click', 'sum'),
        active_days=('date_interaction', 'nunique')
    ).reset_index()
    print(f"   → student_vle: {len(agg_vle):,} combinaciones estudiante-módulo")
    conn.close()

    # ── Merge en Python ──────────────────────────────────────────
    print("🔗 Combinando tablas en memoria...")
    df = df_info.merge(agg_scores, on='id_student', how='left')
    df = df.merge(agg_vle,
                  on=['id_student', 'code_module', 'code_presentation'],
                  how='left')

    # Campos ordinales calculados en Python
    df['final_result_ord'] = df['final_result'].map(
        {'Withdrawn': 0, 'Fail': 1, 'Pass': 2, 'Distinction': 3}).fillna(0).astype(int)
    df['gender_ord'] = df['gender'].map({'M': 1, 'F': 2}).fillna(0).astype(int)
    edu_map = {'No Formal quals': 1, 'Lower Than A Level': 2,
               'A Level or Equivalent': 3, 'HE Qualification': 4,
               'Post Graduate Qualification': 5}
    df['highest_education_ord'] = df['highest_education'].map(edu_map).fillna(0).astype(int)
    imd_map = {'0-10%': 1, '10-20': 2, '20-30%': 3, '30-40%': 4, '40-50%': 5,
               '50-60%': 6, '60-70%': 7, '70-80%': 8, '80-90%': 9, '90-100%': 10}
    df['imd_band_ord'] = df['imd_band'].map(imd_map).fillna(0).astype(int)
    df['age_band_ord'] = df['age_band'].map({'0-35': 1, '35-55': 2, '55<=': 3}).fillna(0).astype(int)
    df['disability_ord'] = df['disability'].map({'Y': 1, 'N': 0}).fillna(0).astype(int)

    # Rellenar NaN numéricos
    for col in ['avg_score', 'num_assessments', 'total_clicks', 'active_days']:
        df[col] = df[col].fillna(0)

    print(f"   → Dataset maestro: {len(df):,} registros\n")
    return df

def load_scores() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql("""
        SELECT sa.score, si.final_result, si.code_module,
               si.highest_education, si.gender, si.age_band
        FROM student_assessment sa
        JOIN student_info si ON sa.id_student = si.id_student
        WHERE sa.score IS NOT NULL
    """, conn)
    conn.close()
    return df


# ── Estadísticas descriptivas ─────────────────────────────────

def print_descriptive_stats(df):
    print("=" * 60)
    print("  ESTADÍSTICAS DESCRIPTIVAS")
    print("=" * 60)
    num_cols = ['avg_score', 'total_clicks', 'active_days',
                'studied_credits', 'num_of_prev_attempts',
                'highest_education_ord', 'imd_band_ord']
    existing = [c for c in num_cols if c in df.columns]
    desc = df[existing].describe().round(2)
    print(desc.to_string())

    print("\n📊 Kurtosis (apuntamiento):")
    for col in existing:
        k = df[col].dropna().kurtosis()
        interp = "Leptocúrtica (picos)" if k > 1 else ("Platicúrtica (plana)" if k < -1 else "Mesocúrtica (normal)")
        print(f"   {col:30s}: {k:7.3f}  → {interp}")

    print("\n📊 Distribución de final_result:")
    vc = df['final_result'].value_counts()
    for val, cnt in vc.items():
        pct = cnt / len(df) * 100
        print(f"   {val:15s}: {cnt:6,} ({pct:.1f}%)")


# ── GRÁFICO 1 & 2: Bar charts ─────────────────────────────────

def plot_bar_final_result(df):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Bar 1 — distribución global
    vc = df['final_result'].value_counts()[ORDER]
    colors = [PALETTE[r] for r in ORDER]
    axes[0].bar(ORDER, vc.values, color=colors, edgecolor='white', linewidth=1.2)
    for i, (v, c) in enumerate(zip(ORDER, vc.values)):
        axes[0].text(i, c + 80, f'{c:,}\n({c/len(df)*100:.1f}%)',
                     ha='center', va='bottom', fontsize=10)
    axes[0].set_title('Distribución Global de Resultados\n(final_result)', fontweight='bold')
    axes[0].set_ylabel('Número de estudiantes')
    axes[0].set_ylim(0, vc.max() * 1.18)

    # Bar 2 — por módulo
    pivot = df.groupby(['code_module', 'final_result']).size().unstack(fill_value=0)
    pivot = pivot.reindex(columns=[c for c in ORDER if c in pivot.columns])
    pivot.plot(kind='bar', ax=axes[1], color=[PALETTE[c] for c in pivot.columns],
               edgecolor='white', linewidth=0.8)
    axes[1].set_title('Resultados por Módulo', fontweight='bold')
    axes[1].set_xlabel('Módulo')
    axes[1].set_ylabel('Estudiantes')
    axes[1].tick_params(axis='x', rotation=0)
    axes[1].legend(title='Resultado', bbox_to_anchor=(1.01, 1), loc='upper left')

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, '01_bar_final_result.png')
    plt.savefig(path)
    plt.close()
    print(f"✅ Gráfico 1-2 guardado: {path}")


def plot_bar_education(df):
    edu_order = ['No Formal quals', 'Lower Than A Level', 'A Level or Equivalent',
                 'HE Qualification', 'Post Graduate Qualification']
    pivot = df.groupby(['highest_education', 'final_result']).size().unstack(fill_value=0)
    pivot = pivot.reindex(index=[e for e in edu_order if e in pivot.index])
    pivot = pivot.reindex(columns=[c for c in ORDER if c in pivot.columns])

    # Calcular % por fila
    pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(12, 5))
    pivot_pct.plot(kind='bar', stacked=True, ax=ax,
                   color=[PALETTE[c] for c in pivot_pct.columns],
                   edgecolor='white', linewidth=0.5)
    ax.set_title('Tasa de Resultados por Nivel Educativo (%)', fontweight='bold')
    ax.set_xlabel('Nivel Educativo')
    ax.set_ylabel('Porcentaje (%)')
    ax.tick_params(axis='x', rotation=25)
    ax.legend(title='Resultado', bbox_to_anchor=(1.01, 1), loc='upper left')
    ax.set_ylim(0, 110)

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, '03_bar_education_result.png')
    plt.savefig(path)
    plt.close()
    print(f"✅ Gráfico 3 guardado: {path}")


# ── GRÁFICO 4 & 5: Boxplots ───────────────────────────────────

def plot_boxplots(df):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Boxplot 1 — score por resultado
    df_scores = df[df['avg_score'].notna()]
    data_by_result = [df_scores[df_scores['final_result'] == r]['avg_score'].dropna() for r in ORDER]
    bp = axes[0].boxplot(data_by_result, tick_labels=ORDER, patch_artist=True,
                         medianprops=dict(color='black', linewidth=2))
    for patch, result in zip(bp['boxes'], ORDER):
        patch.set_facecolor(PALETTE[result])
        patch.set_alpha(0.8)
    axes[0].set_title('Distribución de Score Promedio\npor Resultado Final', fontweight='bold')
    axes[0].set_ylabel('Score promedio (%)')
    axes[0].set_xlabel('Resultado Final')

    # Boxplot 2 — clicks por resultado
    df_clicks = df[df['total_clicks'].notna()]
    clip_val = df_clicks['total_clicks'].quantile(0.95)
    df_clicks = df_clicks[df_clicks['total_clicks'] <= clip_val]
    data_clicks = [df_clicks[df_clicks['final_result'] == r]['total_clicks'].dropna() for r in ORDER]
    bp2 = axes[1].boxplot(data_clicks, tick_labels=ORDER, patch_artist=True,
                          medianprops=dict(color='black', linewidth=2))
    for patch, result in zip(bp2['boxes'], ORDER):
        patch.set_facecolor(PALETTE[result])
        patch.set_alpha(0.8)
    axes[1].set_title('Distribución de Clicks Totales en VLE\npor Resultado Final', fontweight='bold')
    axes[1].set_ylabel('Total clicks (sin outliers extremos)')
    axes[1].set_xlabel('Resultado Final')

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, '04_boxplots.png')
    plt.savefig(path)
    plt.close()
    print(f"✅ Gráfico 4-5 guardado: {path}")


# ── GRÁFICO 6: Campana de Gauss ───────────────────────────────

def plot_gaussian(df):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for ax, col, label, unit in [
        (axes[0], 'avg_score',    'Score Promedio', '%'),
        (axes[1], 'total_clicks', 'Clicks Totales en VLE', 'clicks')
    ]:
        data = df[col].dropna()
        if col == 'total_clicks':
            data = data[data <= data.quantile(0.95)]

        mu, sigma = data.mean(), data.std()
        x = np.linspace(data.min(), data.max(), 300)
        y_norm = stats.norm.pdf(x, mu, sigma)

        ax.hist(data, bins=40, density=True, alpha=0.5, color='steelblue',
                edgecolor='white', label='Datos reales')
        ax.plot(x, y_norm, 'r-', linewidth=2.5,
                label=f'Distribución Normal\nμ={mu:.1f}, σ={sigma:.1f}')
        ax.axvline(mu, color='darkred', linestyle='--', linewidth=1.5, label='Media')
        ax.axvline(mu - sigma, color='orange', linestyle=':', linewidth=1.2)
        ax.axvline(mu + sigma, color='orange', linestyle=':', linewidth=1.2, label='±1σ')

        # Kurtosis y skewness
        kurt = data.kurtosis()
        skew = data.skew()
        ax.set_title(f'Distribución de {label}\nKurtosis={kurt:.2f}  |  Asimetría={skew:.2f}',
                     fontweight='bold')
        ax.set_xlabel(f'{label} ({unit})')
        ax.set_ylabel('Densidad')
        ax.legend(fontsize=9)

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, '06_gaussian_distribution.png')
    plt.savefig(path)
    plt.close()
    print(f"✅ Gráfico 6 guardado: {path}")


# ── GRÁFICO 7: Correlación ────────────────────────────────────

def plot_correlation(df):
    num_cols = ['avg_score', 'total_clicks', 'active_days', 'num_assessments',
                'studied_credits', 'num_of_prev_attempts',
                'highest_education_ord', 'imd_band_ord',
                'age_band_ord', 'disability_ord', 'final_result_ord']
    existing = [c for c in num_cols if c in df.columns]
    corr = df[existing].corr()

    fig, ax = plt.subplots(figsize=(12, 10))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, ax=ax, annot=True, fmt='.2f',
                cmap='RdYlGn', center=0, vmin=-1, vmax=1,
                linewidths=0.5, linecolor='white',
                cbar_kws={'shrink': 0.8})
    ax.set_title('Matriz de Correlación — Variables OULAD', fontweight='bold', fontsize=14)
    plt.xticks(rotation=40, ha='right')
    plt.yticks(rotation=0)

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, '07_correlation_matrix.png')
    plt.savefig(path)
    plt.close()
    print(f"✅ Gráfico 7 guardado: {path}")
    return corr


# ── GRÁFICO 8 & 9: Scatter ────────────────────────────────────

def plot_scatter(df):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    colors = df['final_result'].map(PALETTE)

    # Scatter 1 — score vs clicks
    sample = df[df['avg_score'].notna() & df['total_clicks'].notna()].sample(
        min(3000, len(df)), random_state=42)
    sc1 = axes[0].scatter(sample['total_clicks'], sample['avg_score'],
                          c=sample['final_result'].map(PALETTE),
                          alpha=0.5, s=20, edgecolors='none')
    # Línea de tendencia
    x, y = sample['total_clicks'].values, sample['avg_score'].values
    m, b, r, p, _ = stats.linregress(x, y)
    xr = np.linspace(x.min(), x.max(), 200)
    axes[0].plot(xr, m*xr + b, 'k--', linewidth=1.5, label=f'r={r:.2f}  p<0.001')
    axes[0].set_title('Score vs. Clicks en VLE', fontweight='bold')
    axes[0].set_xlabel('Total clicks en VLE')
    axes[0].set_ylabel('Score promedio (%)')
    axes[0].legend()
    patches = [Patch(color=PALETTE[r], label=r) for r in ORDER if r in df['final_result'].values]
    axes[0].legend(handles=patches + [plt.Line2D([0],[0], color='k', linestyle='--', label=f'Tendencia r={r:.2f}')],
                   fontsize=8)

    # Scatter 2 — active_days vs avg_score
    sample2 = df[df['avg_score'].notna() & df['active_days'].notna()].sample(
        min(3000, len(df)), random_state=42)
    axes[1].scatter(sample2['active_days'], sample2['avg_score'],
                    c=sample2['final_result'].map(PALETTE),
                    alpha=0.5, s=20, edgecolors='none')
    x2, y2 = sample2['active_days'].values, sample2['avg_score'].values
    m2, b2, r2, _, _ = stats.linregress(x2, y2)
    xr2 = np.linspace(x2.min(), x2.max(), 200)
    axes[1].plot(xr2, m2*xr2 + b2, 'k--', linewidth=1.5)
    axes[1].set_title('Días Activos en VLE vs. Score', fontweight='bold')
    axes[1].set_xlabel('Días activos en el VLE')
    axes[1].set_ylabel('Score promedio (%)')
    patches2 = [Patch(color=PALETTE[r], label=r) for r in ORDER if r in df['final_result'].values]
    axes[1].legend(handles=patches2, fontsize=8)

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, '08_scatter_plots.png')
    plt.savefig(path)
    plt.close()
    print(f"✅ Gráfico 8-9 guardado: {path}")


# ── GRÁFICO 10: Matriz de Confusión ──────────────────────────

def plot_confusion_matrix(df):
    # Clasificación binaria: Pass+Distinction=1, Fail+Withdrawn=0
    df2 = df[df['avg_score'].notna() & df['total_clicks'].notna() &
             df['active_days'].notna()].copy()
    df2['outcome'] = df2['final_result'].isin(['Pass', 'Distinction']).astype(int)

    features = ['avg_score', 'total_clicks', 'active_days',
                'num_of_prev_attempts', 'studied_credits',
                'highest_education_ord', 'imd_band_ord', 'age_band_ord']
    features = [f for f in features if f in df2.columns]
    df2 = df2[features + ['outcome']].dropna()

    X = df2[features]
    y = df2['outcome']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)

    clf = LogisticRegression(max_iter=1000, random_state=42)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)

    cm = confusion_matrix(y_test, y_pred)
    accuracy = (cm[0,0] + cm[1,1]) / cm.sum()

    fig, ax = plt.subplots(figsize=(7, 6))
    disp = ConfusionMatrixDisplay(cm, display_labels=['No aprueba', 'Aprueba'])
    disp.plot(ax=ax, cmap='Blues', colorbar=False)
    ax.set_title(f'Matriz de Confusión — Regresión Logística\nAccuracy = {accuracy:.2%}',
                 fontweight='bold')

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, '10_confusion_matrix.png')
    plt.savefig(path)
    plt.close()
    print(f"✅ Gráfico 10 guardado: {path}")
    return accuracy, cm


# ── GRÁFICO 11: Scatter por módulo ───────────────────────────

def plot_scatter_by_module(df):
    modules = df['code_module'].unique()
    n = len(modules)
    cols = 3
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(15, rows * 4))
    axes = axes.flatten()

    for i, mod in enumerate(sorted(modules)):
        sub = df[(df['code_module'] == mod) &
                 df['avg_score'].notna() & df['total_clicks'].notna()]
        sub = sub.sample(min(500, len(sub)), random_state=42)
        axes[i].scatter(sub['total_clicks'], sub['avg_score'],
                        c=sub['final_result'].map(PALETTE), alpha=0.5, s=15)
        axes[i].set_title(f'Módulo {mod}', fontweight='bold', fontsize=10)
        axes[i].set_xlabel('Total clicks', fontsize=8)
        axes[i].set_ylabel('Score %', fontsize=8)

    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    patches = [Patch(color=PALETTE[r], label=r) for r in ORDER]
    fig.legend(handles=patches, loc='lower right', ncol=4, fontsize=9)
    fig.suptitle('Score vs. Clicks por Módulo', fontweight='bold', fontsize=14)
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, '11_scatter_by_module.png')
    plt.savefig(path)
    plt.close()
    print(f"✅ Gráfico 11 guardado: {path}")


# ── GRÁFICO 12: Pivot table heatmap ──────────────────────────

def plot_pivot_heatmap(df):
    edu_order = ['No Formal quals', 'Lower Than A Level', 'A Level or Equivalent',
                 'HE Qualification', 'Post Graduate Qualification']

    df2 = df.copy()
    df2['pass_flag'] = df2['final_result'].isin(['Pass', 'Distinction']).astype(int)

    pivot = df2.pivot_table(
        values='pass_flag', index='highest_education',
        columns='final_result', aggfunc='mean'
    ) * 100

    pivot = pivot.reindex(index=[e for e in edu_order if e in pivot.index])
    pivot = pivot.reindex(columns=[c for c in ORDER if c in pivot.columns])

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.heatmap(pivot, ax=ax, annot=True, fmt='.1f', cmap='YlOrRd',
                linewidths=0.5, linecolor='white',
                cbar_kws={'label': '% de estudiantes'})
    ax.set_title('Tasa de Resultados (%) por Nivel Educativo\n(Pivot Table)', fontweight='bold')
    ax.set_xlabel('Resultado Final')
    ax.set_ylabel('Nivel Educativo')
    plt.xticks(rotation=15)
    plt.yticks(rotation=0)

    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, '12_pivot_heatmap.png')
    plt.savefig(path)
    plt.close()
    print(f"✅ Gráfico 12 guardado: {path}")


# ── TESTS ESTADÍSTICOS: ANOVA y t-test ───────────────────────

def run_statistical_tests(df):
    print("\n" + "=" * 60)
    print("  TESTS ESTADÍSTICOS")
    print("=" * 60)

    # t-test: score Pass vs Fail
    g_pass = df[df['final_result'] == 'Pass']['avg_score'].dropna()
    g_fail = df[df['final_result'] == 'Fail']['avg_score'].dropna()
    if len(g_pass) > 0 and len(g_fail) > 0:
        t, p = stats.ttest_ind(g_pass, g_fail, equal_var=False)
        print(f"\n📊 t-test: Score (Pass vs Fail)")
        print(f"   Media Pass={g_pass.mean():.2f}  vs  Media Fail={g_fail.mean():.2f}")
        print(f"   t={t:.3f},  p={p:.4e}  → {'Significativo (p<0.05)' if p < 0.05 else 'No significativo'}")

    # t-test: clicks Pass vs Fail
    c_pass = df[df['final_result'] == 'Pass']['total_clicks'].dropna()
    c_fail = df[df['final_result'] == 'Fail']['total_clicks'].dropna()
    if len(c_pass) > 0 and len(c_fail) > 0:
        t2, p2 = stats.ttest_ind(c_pass, c_fail, equal_var=False)
        print(f"\n📊 t-test: Clicks VLE (Pass vs Fail)")
        print(f"   Media Pass={c_pass.mean():.1f}  vs  Media Fail={c_fail.mean():.1f}")
        print(f"   t={t2:.3f},  p={p2:.4e}  → {'Significativo (p<0.05)' if p2 < 0.05 else 'No significativo'}")

    # ANOVA: score por final_result (4 grupos)
    groups = [df[df['final_result'] == r]['avg_score'].dropna() for r in ORDER]
    groups = [g for g in groups if len(g) > 1]
    if len(groups) >= 2:
        f, p_anova = stats.f_oneway(*groups)
        print(f"\n📊 ANOVA de un factor: Score por Resultado Final (4 grupos)")
        print(f"   F={f:.3f},  p={p_anova:.4e}  → {'Significativo (p<0.05)' if p_anova < 0.05 else 'No significativo'}")

    # ANOVA: clicks por nivel educativo
    edu_groups = [df[df['highest_education'] == e]['total_clicks'].dropna()
                  for e in df['highest_education'].unique()]
    edu_groups = [g for g in edu_groups if len(g) > 1]
    if len(edu_groups) >= 2:
        f2, p2_anova = stats.f_oneway(*edu_groups)
        print(f"\n📊 ANOVA: Clicks por Nivel Educativo")
        print(f"   F={f2:.3f},  p={p2_anova:.4e}  → {'Significativo (p<0.05)' if p2_anova < 0.05 else 'No significativo'}")

    # Shapiro-Wilk normalidad en scores (muestra)
    sample_scores = df['avg_score'].dropna().sample(min(500, len(df)), random_state=42)
    w, p_norm = stats.shapiro(sample_scores)
    print(f"\n📊 Test de Normalidad Shapiro-Wilk (avg_score, n=500)")
    print(f"   W={w:.4f},  p={p_norm:.4e}  → {'Distribución NO normal' if p_norm < 0.05 else 'Distribución normal'}")

    return {'ttest_score': (t, p), 'anova_score': (f, p_anova)}


# ── MAIN ──────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  EDA EXTENDIDO — OULAD | Ciencia de Datos I")
    print("=" * 60)

    # Cargar datos
    df = load_master_data()

    # Estadísticas descriptivas
    print_descriptive_stats(df)

    # Generar todos los gráficos
    print("\n📊 Generando gráficos...\n")
    plot_bar_final_result(df)
    plot_bar_education(df)
    plot_boxplots(df)
    plot_gaussian(df)
    corr = plot_correlation(df)
    plot_scatter(df)
    accuracy, cm = plot_confusion_matrix(df)
    plot_scatter_by_module(df)
    plot_pivot_heatmap(df)

    # Tests estadísticos
    tests = run_statistical_tests(df)

    print(f"\n✅ EDA completado. {len(os.listdir(PLOTS_DIR))} gráficos guardados en /plots/")
    print(f"   Accuracy del modelo: {accuracy:.2%}")
    print(f"   Gráficos en: {os.path.abspath(PLOTS_DIR)}\n")


if __name__ == "__main__":
    main()
