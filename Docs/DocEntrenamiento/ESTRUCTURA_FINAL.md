# 📁 Estructura Final del Proyecto de Entrenamiento ML

## Estructura Organizada

```
ApartadoInteligente/Entrenamiento/
├── 📂 Scripts/                    # Scripts de procesamiento y entrenamiento
│   ├── procesar_nhanes_multi_anio.py    # Procesar datos NHANES de múltiples años
│   ├── entrenar_modelos.py              # Entrenar modelos ML
│   ├── analizar_dataset.py              # Analizar dataset procesado
│   └── organizar_archivos.py            # Script de organización (este archivo)
│
├── 📂 Docs/                       # Documentación
│   ├── README_MULTI_ANIO.md            # Guía de procesamiento multi-año
│   ├── RESULTADOS_PROCESAMIENTO.md     # Resultados del procesamiento
│   ├── COMPARACION_MODELOS_ANTES_DESPUES.md  # Comparación de modelos
│   ├── ESTRATEGIA_MODELOS.md           # Estrategia de uso de modelos
│   ├── SELECCION_MODELO.md             # Selección del modelo final
│   ├── MEJORAR_MODELOS.md              # Estrategias para mejorar modelos
│   ├── ESTADO_ALGORITMOS.md            # Estado actual de algoritmos
│   ├── COMPARACION_RESULTADOS.md       # Comparación de resultados
│   ├── ANALISIS_RESULTADOS.md          # Análisis de resultados
│   └── ESTRATEGIAS_DATASET_PEQUEÑO.md  # Estrategias para dataset pequeño
│
├── 📂 Modelos/                    # Modelos entrenados
│   ├── Produccion/              # Modelo en producción (XGBoost)
│   │   ├── modelo_xgboost_20251107_185913.pkl
│   │   ├── preprocesadores_20251107_185913.pkl
│   │   ├── metricas_20251107_185913.json
│   │   └── comparacion_modelos_20251107_185913.csv
│   └── Historial/                # Modelos anteriores (backup)
│       ├── modelo_*_20251107_014940.*
│       ├── modelo_*_20251107_015122.*
│       └── modelo_*_20251107_015516.*
│
├── 📂 Datasets/                   # Datos NHANES
│   ├── 2013-2014/                # Archivos .XPT del año 2013-2014
│   ├── 2015-2016/                # Archivos .XPT del año 2015-2016
│   ├── 2017-2018/                # Archivos .XPT del año 2017-2018
│   ├── 2021-2023/                # Archivos .XPT del año 2021-2023
│   ├── nhanes_procesado.csv      # Dataset procesado (12,054 filas)
│   ├── nhanes_procesado.json     # Dataset procesado (muestra)
│   └── nhanes_metadatos.json     # Metadatos del dataset
│
├── README.md                      # Documentación principal
└── requirements_ml.txt            # Dependencias Python para ML
```

---

## 📋 Archivos por Categoría

### ✅ Scripts Necesarios
- `procesar_nhanes_multi_anio.py` - Procesar datos NHANES
- `entrenar_modelos.py` - Entrenar modelos ML
- `analizar_dataset.py` - Analizar dataset

### ✅ Documentación Necesaria
- `README.md` - Documentación principal
- `README_MULTI_ANIO.md` - Guía de procesamiento multi-año
- `RESULTADOS_PROCESAMIENTO.md` - Resultados del procesamiento
- `COMPARACION_MODELOS_ANTES_DESPUES.md` - Comparación de modelos
- `ESTRATEGIA_MODELOS.md` - Estrategia de uso de modelos
- `SELECCION_MODELO.md` - Selección del modelo final

### ✅ Modelos Necesarios
- `Modelos/Produccion/modelo_xgboost_20251107_185913.pkl` - Modelo en producción
- `Modelos/Produccion/preprocesadores_20251107_185913.pkl` - Preprocesadores

### ❌ Archivos No Necesarios (Eliminados/Movidos)
- `procesar_nhanes.py` - Versión antigua (reemplazada por multi_anio)
- Modelos anteriores - Movidos a `Modelos/Historial/`
- Documentación duplicada - Organizada en `Docs/`

---

## 🚀 Cómo Usar la Estructura Organizada

### 1. Procesar Datos
```bash
python Scripts/procesar_nhanes_multi_anio.py
```

### 2. Entrenar Modelos
```bash
python Scripts/entrenar_modelos.py
```

### 3. Analizar Dataset
```bash
python Scripts/analizar_dataset.py
```

### 4. Usar Modelo en Producción
```python
import pickle
from pathlib import Path

# Cargar modelo
modelo_path = Path("Modelos/Produccion/modelo_xgboost_20251107_185913.pkl")
preprocesadores_path = Path("Modelos/Produccion/preprocesadores_20251107_185913.pkl")

with open(modelo_path, 'rb') as f:
    modelo = pickle.load(f)

with open(preprocesadores_path, 'rb') as f:
    preprocesadores = pickle.load(f)
```

---

## 📝 Notas

- **Modelo en producción**: Solo XGBoost (mejor rendimiento)
- **Modelos no usados**: Logistic Regression y Random Forest (Accuracy muy bajo)
- **Backup**: Modelos anteriores guardados en `Modelos/Historial/`
- **Documentación**: Todos los archivos .md están en `Docs/`
- **Scripts**: Todos los scripts .py están en `Scripts/`

