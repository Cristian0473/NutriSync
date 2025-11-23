# Estrategias para Trabajar con Datasets Pequeños

## Problema: Dataset de 808 filas

El dataset procesado inicialmente tiene **808 filas**, lo cual es **insuficiente** para entrenar modelos complejos como Random Forest o XGBoost de manera óptima.

### Tamaños recomendados para ML

| Modelo | Mínimo recomendado | Óptimo |
|--------|-------------------|--------|
| Logistic Regression | 100-500 | 1,000+ |
| Random Forest | 1,000-5,000 | 5,000+ |
| XGBoost | 1,000-10,000 | 10,000+ |
| Redes Neuronales | 5,000+ | 50,000+ |

## Soluciones Implementadas

### 1. Incluir Prediabetes

**Cambio**: El script ahora incluye pacientes con prediabetes además de DM2 confirmada.

**Criterios Prediabetes**:
- HbA1c: 5.7-6.4%
- Glucosa en ayunas: 100-125 mg/dL

**Impacto esperado**: Aumenta el dataset de ~800 a **2,000-4,000 filas** aproximadamente.

**Justificación clínica**: 
- Los pacientes con prediabetes tienen perfiles metabólicos similares a DM2
- Son relevantes para el modelado de riesgo metabólico
- Permiten entrenar modelos más robustos

### 2. Relajar Umbral de Faltantes

**Cambio**: Umbral aumentado de 30% a 50% de valores faltantes permitidos.

**Impacto**: Mantiene más filas en el dataset final.

**Riesgo**: Más valores faltantes pueden requerir imputación.

## Estrategias Adicionales para Datasets Pequeños

### 3. Validación Cruzada Estratificada

**Implementación**:
```python
from sklearn.model_selection import StratifiedKFold

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
```

**Beneficios**:
- Maximiza el uso de datos limitados
- Reduce sobreajuste
- Proporciona estimaciones más confiables del rendimiento

### 4. Regularización Fuerte

**Para Random Forest**:
```python
RandomForestClassifier(
    max_depth=5,           # Limitar profundidad
    min_samples_split=20,  # Más muestras por split
    min_samples_leaf=10,   # Más muestras por hoja
    max_features='sqrt',   # Menos features por split
    n_estimators=100       # Menos árboles
)
```

**Para XGBoost**:
```python
XGBClassifier(
    max_depth=3,           # Profundidad limitada
    learning_rate=0.1,      # Learning rate conservador
    subsample=0.8,          # Submuestreo
    colsample_bytree=0.8,   # Submuestreo de features
    reg_alpha=1.0,          # Regularización L1
    reg_lambda=1.0          # Regularización L2
)
```

### 5. Modelos Más Simples Primero

**Orden recomendado**:
1. **Logistic Regression** (baseline) - Funciona bien con pocos datos
2. **Random Forest** (con regularización fuerte)
3. **XGBoost** (solo si Random Forest funciona bien)

### 6. Feature Engineering Inteligente

**Crear variables derivadas** (ya implementado):
- Ratios: TG/HDL, LDL/HDL
- Scores: AIP, HOMA-IR, riesgo metabólico
- Interacciones: IMC × HbA1c, edad × glucosa

**Beneficios**: Reduce dimensionalidad y mejora interpretabilidad.

### 7. Data Augmentation Sintética (Opcional)

**Técnicas**:
- **SMOTE** (Synthetic Minority Oversampling Technique)
- **ADASYN** (Adaptive Synthetic Sampling)
- **Bootstrapping** con variación gaussiana

**Implementación**:
```python
from imblearn.over_sampling import SMOTE

smote = SMOTE(random_state=42)
X_resampled, y_resampled = smote.fit_resample(X, y)
```

**Advertencia**: Usar con cuidado en datos clínicos - puede introducir sesgos.

### 8. Transfer Learning (Avanzado)

**Estrategia**: 
- Entrenar modelo base con datos públicos (NHANES completo)
- Fine-tuning con datos específicos del hospital

**Requisitos**: Acceso a datasets públicos más grandes.

## Plan de Acción Recomendado

### Paso 1: Reprocesar con Prediabetes
```bash
python procesar_nhanes.py
```

Esto debería generar un dataset de **2,000-4,000 filas**.

### Paso 2: Análisis Exploratorio
```bash
python analizar_dataset.py
```

Verificar:
- Tamaño final del dataset
- Distribución de clases (control vs mal control)
- Completitud de variables

### Paso 3: Entrenar Modelo Baseline
- Empezar con **Logistic Regression**
- Validación cruzada estratificada (5-fold)
- Métricas: AUC-ROC, Precision, Recall, F1

### Paso 4: Modelos Avanzados (si baseline funciona)
- **Random Forest** con regularización fuerte
- Comparar con baseline
- Solo si mejora significativamente, probar **XGBoost**

### Paso 5: Validación Final
- Hold-out set (20% de datos)
- Métricas finales
- Análisis de importancia de variables

## Métricas de Éxito

**Mínimo aceptable**:
- AUC-ROC > 0.70
- Precision > 0.65
- Recall > 0.60

**Objetivo**:
- AUC-ROC > 0.75
- Precision > 0.70
- Recall > 0.70

## Consideraciones Clínicas

1. **Interpretabilidad**: Priorizar modelos interpretables (Logistic Regression, Random Forest)
2. **Sesgo**: Validar que el modelo no tenga sesgos por edad, sexo, etnia
3. **Validación externa**: Probar con datos del hospital real cuando estén disponibles
4. **Actualización continua**: Re-entrenar con más datos a medida que se acumulen

## Referencias

- **Scikit-learn**: Documentación de validación cruzada
- **XGBoost**: Guía de regularización para datasets pequeños
- **NHANES**: Documentación de variables y criterios diagnósticos

