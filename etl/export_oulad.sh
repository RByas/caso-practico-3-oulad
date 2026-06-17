#!/usr/bin/env bash
# ============================================================
# export_oulad.sh — Dump / export-import de la base 'oulad'
# Caso Práctico 3 | Ciencia de Datos I
#
# Genera un dump completo (esquema + datos + vistas + rutinas)
# que sirve como evidencia de entrega y permite reproducir la BD.
#
# Uso:
#   ./etl/export_oulad.sh            # exporta a db/oulad_dump.sql
#   ./etl/export_oulad.sh import     # importa db/oulad_dump.sql
# ============================================================

set -euo pipefail

DB_NAME="oulad"
DB_USER="root"
DB_HOST="localhost"
DB_PORT="3306"

# Carpeta de salida (db/ junto a la raíz del proyecto)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$SCRIPT_DIR/../db"
DUMP_FILE="$OUT_DIR/oulad_dump.sql"

mkdir -p "$OUT_DIR"

ACTION="${1:-export}"

if [ "$ACTION" = "export" ]; then
    echo "📦 Exportando base '$DB_NAME' → $DUMP_FILE"
    # Redirección por stdout (no --result-file) para que cualquier error de
    # mysqldump sea visible y no deje un archivo vacío silenciosamente.
    # Se omite --events (suele requerir privilegios que el usuario no tiene).
    if mysqldump \
        -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p \
        --databases "$DB_NAME" \
        --routines --triggers \
        --single-transaction --quick \
        --set-gtid-purged=OFF \
        --default-character-set=utf8mb4 > "$DUMP_FILE"; then
        if [ -s "$DUMP_FILE" ]; then
            echo "✅ Dump generado: $DUMP_FILE"
            echo "   Tamaño: $(du -h "$DUMP_FILE" | cut -f1)"
        else
            echo "❌ El dump quedó vacío. Revisa el error de mysqldump arriba."
            exit 1
        fi
    else
        echo "❌ mysqldump falló. Verifica usuario/contraseña/privilegios."
        exit 1
    fi

elif [ "$ACTION" = "import" ]; then
    echo "📥 Importando $DUMP_FILE → MySQL"
    mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p < "$DUMP_FILE"
    echo "✅ Base '$DB_NAME' restaurada."

else
    echo "Uso: $0 [export|import]"
    exit 1
fi
