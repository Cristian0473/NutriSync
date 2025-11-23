# 🧠 Entrenamiento de Modelos ML - NutriSync

Sistema de entrenamiento de modelos de Machine Learning para recomendación nutricional personalizada en pacientes con diabetes tipo 2.

---

## 📁 Estructura del Proyecto

```
Entrenamiento/
├── 📂 Scripts/                    # Scripts de procesamiento y entrenamiento
│   ├── procesar_nhanes_multi_anio.py    # Procesar datos NHANES de múltiples años
│   ├── entrenar_modelos.py              # Entrenar modelos ML
│   └── analizar_dataset.py              # Analizar dataset procesado
│
├── 📂 Datasets/                   # Datos NHANES
│   ├── 2013-2014/                 # Archivos .XPT del año 2013-2014
│   ├── 2015-2016/                 # Archivos .XPT del año 2015-2016
│   ├── 2017-2018/                 # Archivos .XPT del año 2017-2018
│   ├── 2021-2023/                 # Archivos .XPT del año 2021-2023
│   ├── nhanes_procesado.csv       # Dataset procesado (12,054 filas)
│   ├── nhanes_procesado.json      # Dataset procesado (muestra)
│   └── nhanes_metadatos.json      # Metadatos del dataset
│
├── 📂 Modelos/                    # Modelos entrenados
│   ├── Produccion/                # Modelo en producción (XGBoost)
│   │   ├── modelo_xgboost_20251107_185913.pkl
│   │   └── preprocesadores_20251107_185913.pkl
│   └── Historial/                 # Modelos anteriores (backup)
│
├── 📂 Docs/                       # Documentación
│   ├── README.md                  # Este archivo
│   ├── README_MULTI_ANIO.md      # Guía de procesamiento multi-año
│   ├── RESULTADOS_PROCESAMIENTO.md    # Resultados del procesamiento
│   ├── COMPARACION_MODELOS_ANTES_DESPUES.md  # Comparación de modelos
│   ├── ESTRATEGIA_MODELOS.md     # Estrategia de uso de modelos
│   ├── SELECCION_MODELO.md       # Selección del modelo final
│   ├── MEJORAR_MODELOS.md        # Estrategias para mejorar modelos
│   ├── ESTADO_ALGORITMOS.md      # Estado actual de algoritmos
│   └── ...
│
└── requirements_ml.txt            # Dependencias Python para ML
```

---

## 🚀 Inicio Rápido

### 1. Instalar Dependencias

```bash
pip install -r requirements_ml.txt
```

### 2. Procesar Datos NHANES

```bash
cd Scripts
python procesar_nhanes_multi_anio.py
```

**Resultado**: Genera `Datasets/nhanes_procesado.csv` con 12,054 filas.

### 3. Entrenar Modelos

```bash
cd Scripts
python entrenar_modelos.py
```

**Resultado**: Genera modelos en `Modelos/Produccion/`.

### 4. Analizar Dataset

```bash
cd Scripts
python analizar_dataset.py
```

---

## 📊 Modelo en Producción

### **XGBoost** (Mejor Modelo)

- **Archivo**: `Modelos/Produccion/modelo_xgboost_20251107_185913.pkl`
- **Preprocesadores**: `Modelos/Produccion/preprocesadores_20251107_185913.pkl`

### Métricas del Modelo

| Métrica | Valor | Estado |
|---------|-------|--------|
| **AUC-ROC** | 0.861 | ✅ Excelente |
| **F1-Score** | 0.522 | ✅ Bueno |
| **Accuracy** | 0.786 | ✅ Bueno |
| **Recall** | 0.765 | ✅ Muy bueno |
| **Precision** | 0.396 | ⚠️ Aceptable |

### Feature Importance (Top 5)

1. **HOMA-IR** (0.1970) - Resistencia a la insulina
2. **HDL** (0.1266) - Colesterol bueno
3. **Insulina en ayunas** (0.1250) - Nivel de insulina
4. **Circunferencia de cintura** (0.0851) - Obesidad abdominal
5. **Presión arterial sistólica** (0.0742) - Hipertensión

---

## 📋 Scripts Disponibles

### `procesar_nhanes_multi_anio.py`
Procesa archivos NHANES de múltiples años y los combina en un solo dataset.

**Características**:
- ✅ Detección automática de carpetas de años
- ✅ Unificación BPX/BPXO (auscultatorio vs oscilométrico)
- ✅ Mapeo de variables NHANES a formato del sistema
- ✅ Creación de variables derivadas (IMC, LDL, HOMA-IR, etc.)
- ✅ Filtrado de pacientes con DM2 y prediabetes

**Uso**:
```bash
python Scripts/procesar_nhanes_multi_anio.py
```

### `entrenar_modelos.py`
Entrena modelos de Machine Learning (Logistic Regression, Random Forest, XGBoost).

**Características**:
- ✅ Manejo de clases desbalanceadas (SMOTE)
- ✅ Validación cruzada estratificada
- ✅ Evaluación de métricas (AUC-ROC, F1-Score, Precision, Recall)
- ✅ Feature importance
- ✅ Guardado de modelos y preprocesadores

**Uso**:
```bash
python Scripts/entrenar_modelos.py
```

### `analizar_dataset.py`
Analiza el dataset procesado y muestra estadísticas.

**Uso**:
```bash
python Scripts/analizar_dataset.py
```

---

## 📚 Documentación

### Documentos Principales

- **README.md** (este archivo): Guía general del proyecto
- **README_MULTI_ANIO.md**: Guía detallada de procesamiento multi-año
- **RESULTADOS_PROCESAMIENTO.md**: Resultados del procesamiento de datos
- **COMPARACION_MODELOS_ANTES_DESPUES.md**: Comparación de modelos antes/después
- **ESTRATEGIA_MODELOS.md**: Estrategia de uso de modelos (solo XGBoost)
- **SELECCION_MODELO.md**: Justificación de selección del modelo final
- **MEJORAR_MODELOS.md**: Estrategias para mejorar modelos
- **ESTADO_ALGORITMOS.md**: Estado actual de algoritmos en el sistema

---

## 🔧 Configuración

### Variables de Entorno

No se requieren variables de entorno. Los scripts usan rutas relativas.

### Estructura de Datos

El dataset procesado (`nhanes_procesado.csv`) contiene:
- **12,054 filas** (pacientes con DM2 y prediabetes)
- **26 columnas** (variables clínicas, antropométricas y derivadas)
- **4 años** de datos NHANES (2013-2014, 2015-2016, 2017-2018, 2021-2023)

---

## 📈 Resultados Actuales

### Dataset Procesado
- **Total de filas**: 12,054
- **Años incluidos**: 4 (2013-2014, 2015-2016, 2017-2018, 2021-2023)
- **Método BP**: Auscultatorio (5,732) + Oscilométrico (6,322)

### Modelo XGBoost
- **AUC-ROC**: 0.861 ✅
- **F1-Score**: 0.522 ✅
- **Recall**: 0.765 ✅
- **Accuracy**: 0.786 ✅

---

## 🔄 Próximos Pasos

1. ✅ **Modelo entrenado** - XGBoost listo
2. 🔄 **Integrar con motor de recomendación** - Usar modelo en producción
3. 🔄 **Validar con datos reales** - Probar con pacientes del hospital
4. 🔄 **Monitorear en producción** - Recopilar feedback y mejorar

---

## 📝 Notas

- **Modelo en producción**: Solo XGBoost (mejor rendimiento)
- **Modelos no usados**: Logistic Regression y Random Forest (Accuracy muy bajo)
- **Backup**: Modelos anteriores guardados en `Modelos/Historial/`
- **Documentación**: Todos los archivos .md están en `Docs/`

---

## 🐛 Troubleshooting

### Error: "Archivo no encontrado"
- Verifica que las carpetas de años estén en `Datasets/`
- Verifica que los archivos .XPT estén en las carpetas correctas

### Error: "No se encontraron archivos DEMO"
- No es crítico, el script funciona sin archivos DEMO
- El filtro de edad se omite si no hay archivos DEMO

### Warning: "joblib/loky physical cores"
- No es crítico, puede ignorarse
- SMOTE funciona correctamente a pesar del warning

---

## 📞 Contacto

Para preguntas o problemas, revisar la documentación en `Docs/` o los scripts en `Scripts/`.
