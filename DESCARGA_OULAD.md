# Cómo descargar el dataset OULAD

## Opción A — Sitio oficial (recomendado)
1. Ve a: https://analyse.kmi.open.ac.uk/open_dataset
2. Haz clic en **"Download dataset"**
3. Descarga el ZIP (~100 MB)
4. Extrae los 7 archivos CSV dentro de la carpeta: `caso_practico_3/data/`

## Opción B — Kaggle (si el sitio oficial falla)
1. Ve a: https://www.kaggle.com/datasets/anlgrbz/student-demographics-online-education-dataoulad
2. Descarga el dataset
3. Extrae los CSV en `caso_practico_3/data/`

## Archivos esperados en la carpeta data/
```
data/
├── assessments.csv
├── courses.csv
├── studentAssessment.csv
├── studentInfo.csv
├── studentRegistration.csv
├── studentVle.csv
└── vle.csv
```

## Verificar la descarga
Una vez descargados, ejecuta:
```bash
python etl/etl_pipeline.py --check
```
