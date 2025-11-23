# 📋 Informe de Organización de Archivos - Entrenamiento ML

## 📊 Análisis de Archivos Actuales

### ✅ **ARCHIVOS A MANTENER EN RAÍZ** (No mover)

1. **`README.md`** ✅
   - **Razón**: Documentación principal del proyecto
   - **Acción**: Mantener en raíz

2. **`requirements_ml.txt`** ✅
   - **Razón**: Dependencias Python necesarias
   - **Acción**: Mantener en raíz

---

### 📝 **ARCHIVOS A MOVER A `Docs/`** (Documentación)

1. **`ANALISIS_RESULTADOS.md`** → `Docs/`
   - **Razón**: Análisis de resultados de modelos
   - **Acción**: Mover

2. **`COMPARACION_MODELOS_ANTES_DESPUES.md`** → `Docs/`
   - **Razón**: Comparación de modelos antes/después
   - **Acción**: Mover

3. **`COMPARACION_RESULTADOS.md`** → `Docs/`
   - **Razón**: Comparación de resultados
   - **Acción**: Mover

4. **`ESTADO_ALGORITMOS.md`** → `Docs/`
   - **Razón**: Estado actual de algoritmos
   - **Acción**: Mover

5. **`ESTRATEGIA_MODELOS.md`** → `Docs/`
   - **Razón**: Estrategia de uso de modelos
   - **Acción**: Mover

6. **`ESTRATEGIAS_DATASET_PEQUEÑO.md`** → `Docs/`
   - **Razón**: Estrategias para dataset pequeño
   - **Acción**: Mover

7. **`ESTRUCTURA_FINAL.md`** → `Docs/`
   - **Razón**: Documentación de estructura final
   - **Acción**: Mover

8. **`MEJORAR_MODELOS.md`** → `Docs/`
   - **Razón**: Estrategias para mejorar modelos
   - **Acción**: Mover

9. **`README_MULTI_ANIO.md`** → `Docs/`
   - **Razón**: Guía de procesamiento multi-año
   - **Acción**: Mover

10. **`RESULTADOS_PROCESAMIENTO.md`** → `Docs/`
    - **Razón**: Resultados del procesamiento
    - **Acción**: Mover

11. **`SELECCION_MODELO.md`** → `Docs/`
    - **Razón**: Selección del modelo final
    - **Acción**: Mover

---

### 🐍 **ARCHIVOS A MOVER A `Scripts/`** (Scripts Python)

1. **`analizar_dataset.py`** → `Scripts/`
   - **Razón**: Script para analizar dataset
   - **Acción**: Mover

2. **`entrenar_modelos.py`** → `Scripts/`
   - **Razón**: Script para entrenar modelos
   - **Acción**: Mover

3. **`procesar_nhanes_multi_anio.py`** → `Scripts/`
   - **Razón**: Script para procesar datos NHANES multi-año
   - **Acción**: Mover

4. **`organizar_archivos.py`** → `Scripts/`
   - **Razón**: Script de organización (opcional, puede borrarse después)
   - **Acción**: Mover o borrar después de usar

---

### ❌ **ARCHIVOS A BORRAR** (No necesarios)

1. **`procesar_nhanes.py`** ❌
   - **Razón**: Versión antigua, reemplazada por `procesar_nhanes_multi_anio.py`
   - **Acción**: **BORRAR**

---

### 🤖 **ARCHIVOS DE MODELOS A ORGANIZAR**

#### **Modelos en Producción** (Último entrenamiento: `20251107_185913`)

**Mover a `Modelos/Produccion/`:**

1. **`modelo_xgboost_20251107_185913.pkl`** ✅
   - **Razón**: Modelo en producción (mejor rendimiento)
   - **Acción**: Mover

2. **`preprocesadores_20251107_185913.pkl`** ✅
   - **Razón**: Preprocesadores del modelo en producción
   - **Acción**: Mover

3. **`metricas_20251107_185913.json`** ✅
   - **Razón**: Métricas del modelo en producción
   - **Acción**: Mover

4. **`comparacion_modelos_20251107_185913.csv`** ✅
   - **Razón**: Comparación de modelos del último entrenamiento
   - **Acción**: Mover

#### **Modelos Antiguos** (Backup - Mover a `Modelos/Historial/`)

**Mover a `Modelos/Historial/`:**

1. **`modelo_logistic_regression_20251107_014940.pkl`** → `Modelos/Historial/`
2. **`modelo_logistic_regression_20251107_015122.pkl`** → `Modelos/Historial/`
3. **`modelo_logistic_regression_20251107_015516.pkl`** → `Modelos/Historial/`
4. **`modelo_logistic_regression_20251107_185913.pkl`** → `Modelos/Historial/`
   - **Razón**: Modelos no usados (Accuracy muy bajo: 0.261)
   - **Acción**: Mover a Historial (backup)

5. **`modelo_random_forest_20251107_014940.pkl`** → `Modelos/Historial/`
6. **`modelo_random_forest_20251107_015122.pkl`** → `Modelos/Historial/`
7. **`modelo_random_forest_20251107_015516.pkl`** → `Modelos/Historial/`
8. **`modelo_random_forest_20251107_185913.pkl`** → `Modelos/Historial/`
   - **Razón**: Modelos no usados (Accuracy muy bajo: 0.329)
   - **Acción**: Mover a Historial (backup)

9. **`modelo_xgboost_20251107_014940.pkl`** → `Modelos/Historial/`
10. **`modelo_xgboost_20251107_015122.pkl`** → `Modelos/Historial/`
11. **`modelo_xgboost_20251107_015516.pkl`** → `Modelos/Historial/`
    - **Razón**: Versiones anteriores del modelo XGBoost
    - **Acción**: Mover a Historial (backup)

12. **`preprocesadores_20251107_014940.pkl`** → `Modelos/Historial/`
13. **`preprocesadores_20251107_015122.pkl`** → `Modelos/Historial/`
14. **`preprocesadores_20251107_015516.pkl`** → `Modelos/Historial/`
    - **Razón**: Preprocesadores de versiones anteriores
    - **Acción**: Mover a Historial (backup)

15. **`metricas_20251107_014940.json`** → `Modelos/Historial/`
16. **`metricas_20251107_015122.json`** → `Modelos/Historial/`
17. **`metricas_20251107_015516.json`** → `Modelos/Historial/`
    - **Razón**: Métricas de versiones anteriores
    - **Acción**: Mover a Historial (backup)

18. **`comparacion_modelos_20251107_014940.csv`** → `Modelos/Historial/`
19. **`comparacion_modelos_20251107_015122.csv`** → `Modelos/Historial/`
20. **`comparacion_modelos_20251107_015516.csv`** → `Modelos/Historial/`
    - **Razón**: Comparaciones de versiones anteriores
    - **Acción**: Mover a Historial (backup)

---

### 📁 **CARPETAS A MANTENER**

1. **`Datasets/`** ✅
   - **Razón**: Contiene datos NHANES y dataset procesado
   - **Acción**: Mantener (no mover)

2. **`ModeloEntrenamiento/`** ⚠️
   - **Razón**: Carpeta temporal, se vaciará después de mover archivos
   - **Acción**: Borrar después de mover todos los archivos

---

## 📋 Resumen de Acciones

### ✅ **Mantener en Raíz** (2 archivos)
- `README.md`
- `requirements_ml.txt`

### 📝 **Mover a `Docs/`** (11 archivos .md)
- Todos los archivos `.md` excepto `README.md`

### 🐍 **Mover a `Scripts/`** (4 archivos .py)
- `analizar_dataset.py`
- `entrenar_modelos.py`
- `procesar_nhanes_multi_anio.py`
- `organizar_archivos.py` (opcional, puede borrarse después)

### ❌ **Borrar** (1 archivo)
- `procesar_nhanes.py` (versión antigua)

### 🤖 **Mover a `Modelos/Produccion/`** (4 archivos)
- `modelo_xgboost_20251107_185913.pkl`
- `preprocesadores_20251107_185913.pkl`
- `metricas_20251107_185913.json`
- `comparacion_modelos_20251107_185913.csv`

### 📦 **Mover a `Modelos/Historial/`** (20 archivos)
- Todos los modelos, preprocesadores, métricas y comparaciones anteriores

### 🗑️ **Borrar Carpeta** (1 carpeta)
- `ModeloEntrenamiento/` (después de mover todos los archivos)

---

## 🎯 Estructura Final Esperada

```
ApartadoInteligente/Entrenamiento/
├── README.md                          ✅ (Mantener)
├── requirements_ml.txt                ✅ (Mantener)
│
├── Scripts/                           📁 (Crear)
│   ├── analizar_dataset.py            📝 (Mover)
│   ├── entrenar_modelos.py            📝 (Mover)
│   ├── procesar_nhanes_multi_anio.py  📝 (Mover)
│   └── organizar_archivos.py          📝 (Mover, opcional)
│
├── Docs/                              📁 (Crear)
│   ├── ANALISIS_RESULTADOS.md         📝 (Mover)
│   ├── COMPARACION_MODELOS_ANTES_DESPUES.md  📝 (Mover)
│   ├── COMPARACION_RESULTADOS.md      📝 (Mover)
│   ├── ESTADO_ALGORITMOS.md           📝 (Mover)
│   ├── ESTRATEGIA_MODELOS.md           📝 (Mover)
│   ├── ESTRATEGIAS_DATASET_PEQUEÑO.md  📝 (Mover)
│   ├── ESTRUCTURA_FINAL.md            📝 (Mover)
│   ├── MEJORAR_MODELOS.md              📝 (Mover)
│   ├── README_MULTI_ANIO.md            📝 (Mover)
│   ├── RESULTADOS_PROCESAMIENTO.md     📝 (Mover)
│   └── SELECCION_MODELO.md             📝 (Mover)
│
├── Modelos/                           📁 (Crear)
│   ├── Produccion/                    📁 (Crear)
│   │   ├── modelo_xgboost_20251107_185913.pkl      🤖 (Mover)
│   │   ├── preprocesadores_20251107_185913.pkl     🤖 (Mover)
│   │   ├── metricas_20251107_185913.json           🤖 (Mover)
│   │   └── comparacion_modelos_20251107_185913.csv 🤖 (Mover)
│   │
│   └── Historial/                     📁 (Crear)
│       └── [20 archivos anteriores]   📦 (Mover)
│
└── Datasets/                          ✅ (Mantener)
    ├── 2013-2014/
    ├── 2015-2016/
    ├── 2017-2018/
    ├── 2021-2023/
    ├── nhanes_procesado.csv
    ├── nhanes_procesado.json
    └── nhanes_metadatos.json
```

---

## ⚠️ Notas Importantes

1. **Modelo en Producción**: Solo XGBoost (`20251107_185913`) se usa en producción
2. **Modelos No Usados**: Logistic Regression y Random Forest tienen Accuracy muy bajo (0.261 y 0.329)
3. **Backup**: Todos los modelos anteriores se guardan en `Historial/` por seguridad
4. **Script Antiguo**: `procesar_nhanes.py` puede borrarse (reemplazado por `multi_anio`)
5. **Carpeta Temporal**: `ModeloEntrenamiento/` se borra después de mover archivos

---

## ✅ Checklist de Organización

- [ ] Crear carpeta `Scripts/`
- [ ] Crear carpeta `Docs/`
- [ ] Crear carpeta `Modelos/Produccion/`
- [ ] Crear carpeta `Modelos/Historial/`
- [ ] Mover 4 scripts Python a `Scripts/`
- [ ] Mover 11 documentos .md a `Docs/`
- [ ] Mover 4 archivos del último modelo a `Modelos/Produccion/`
- [ ] Mover 20 archivos anteriores a `Modelos/Historial/`
- [ ] Borrar `procesar_nhanes.py`
- [ ] Borrar carpeta `ModeloEntrenamiento/` (después de mover todo)

---

**Total de archivos a organizar**: 39 archivos
- **Mantener**: 2
- **Mover**: 35
- **Borrar**: 1 archivo + 1 carpeta

