# 🔄 ¿Cómo funciona el archivo de entrenamiento?

## 📋 **Resumen del Proceso**

El archivo `entrenar_modelos.py` ejecuta un **pipeline completo de Machine Learning** que:

1. **Carga** el dataset procesado
2. **Prepara** las features (variables predictoras)
3. **Divide** los datos en train/validation/test
4. **Preprocesa** los datos (imputación, escalado, codificación)
5. **Balancea** las clases (SMOTE + class weights)
6. **Entrena** 3 modelos (Logistic Regression, Random Forest, XGBoost)
7. **Evalúa** los modelos con métricas
8. **Compara** los modelos y selecciona el mejor
9. **Guarda** los modelos y preprocesadores

---

## 🔄 **Flujo Completo del Entrenamiento**

### **PASO 1: Cargar Datos** (`cargar_datos()`)

```python
# Carga el dataset procesado de NHANES
df = cargar_datos()
# Resultado: DataFrame con 12,054 filas y 26 columnas
```

**Qué hace:**
- Lee el archivo `Datasets/nhanes_procesado.csv`
- Verifica que el archivo existe
- Muestra estadísticas del dataset

---

### **PASO 2: Preparar Features** (`preparar_features()`)

```python
# Prepara las variables predictoras (features)
X, y_clasificacion, y_regresion, encoders = preparar_features(df, excluir_leakage=True)
```

**Qué hace:**

1. **Selecciona features numéricas**:
   - `edad`, `peso`, `talla`, `imc`, `cc`
   - `ldl`, `hdl`, `trigliceridos`, `colesterol_total`
   - `pa_sis`, `pa_dia`, `insulina_ayunas`
   - `no_hdl`, `homa_ir`, `tg_hdl_ratio`, `ldl_hdl_ratio`, `aip`

2. **Excluye features que causan data leakage**:
   - ❌ `hba1c` (el target se calcula de esta variable)
   - ❌ `glucosa_ayunas` (también usada en el cálculo del target)

3. **Codifica variables categóricas**:
   - `sexo` ('M', 'F') → `sexo_encoded` (0, 1)
   - `actividad` ('baja', 'moderada', 'alta') → `actividad_encoded` (0, 1, 2)

4. **Prepara targets**:
   - `control_glucemico`: 1 si HbA1c ≥ 7.0, 0 si no
   - `riesgo_metabolico`: score continuo (0-1)

**Resultado:**
- `X`: DataFrame con features preparadas
- `y_clasificacion`: Target de clasificación
- `encoders`: Encoders para codificar categorías

---

### **PASO 3: Dividir Datos** (`dividir_datos()`)

```python
# Divide los datos en train/validation/test
X_train, X_val, X_test, y_train, y_val, y_test = dividir_datos(
    X, y_clasificacion, test_size=0.15, val_size=0.15
)
```

**Qué hace:**

1. **Elimina filas con target faltante**
2. **Divide en 3 conjuntos**:
   - **Train**: 70% (para entrenar el modelo)
   - **Validation**: 15% (para ajustar hiperparámetros)
   - **Test**: 15% (para evaluar el modelo final)

3. **Usa estratificación** (mantiene proporción de clases en cada conjunto)

**Resultado:**
- 3 conjuntos de features (train, val, test)
- 3 conjuntos de targets (train, val, test)

---

### **PASO 4: Imputar Valores Faltantes** (`imputar_valores_faltantes()`)

```python
# Llena valores faltantes (NaN) con la mediana
X_train, X_val, X_test, imputer = imputar_valores_faltantes(X_train, X_val, X_test)
```

**Qué hace:**

1. **Crea un SimpleImputer** con estrategia `median`
2. **Ajusta con train** (calcula la mediana de cada columna)
3. **Transforma train, val y test** (llena NaN con la mediana)

**Ejemplo:**
```python
# Antes:
hdl = [50.0, None, 60.0, None, 55.0]
# Mediana = 55.0

# Después:
hdl = [50.0, 55.0, 60.0, 55.0, 55.0]  # None → 55.0
```

**Resultado:**
- Datos sin valores faltantes
- `imputer`: Objeto guardado para usar después

---

### **PASO 5: Escalar Features** (`escalar_features()`)

```python
# Normaliza valores numéricos (media=0, std=1)
X_train, X_val, X_test, scaler = escalar_features(X_train, X_val, X_test)
```

**Qué hace:**

1. **Crea un StandardScaler**
2. **Ajusta con train** (calcula media y desviación estándar de cada columna)
3. **Transforma train, val y test** (normaliza valores)

**Ejemplo:**
```python
# Antes:
edad = [45, 50, 55, 60, 65]
# Media = 55, Std = 7.07

# Después:
edad_scaled = [-1.41, -0.71, 0.0, 0.71, 1.41]  # Normalizado
```

**Resultado:**
- Datos normalizados (media=0, std=1)
- `scaler`: Objeto guardado para usar después

---

### **PASO 6: Balancear Clases** (`balancear_clases()`)

```python
# Balancea clases desbalanceadas (SMOTE + class weights)
X_train_balanced, y_train_balanced, class_weights = balancear_clases(
    X_train, y_train, usar_smote=True
)
```

**Qué hace:**

1. **Calcula distribución de clases**:
   - Clase 0 (control bueno): 85.3%
   - Clase 1 (control malo): 14.7%

2. **Aplica SMOTE** (Synthetic Minority Over-sampling Technique):
   - Genera muestras sintéticas de la clase minoritaria
   - Balancea las clases al 50%-50%

3. **Calcula class weights**:
   - Peso mayor para la clase minoritaria
   - Usado en los modelos para balancear

**Resultado:**
- Datos balanceados (50%-50%)
- `class_weights`: Pesos para balancear clases

---

### **PASO 7: Entrenar Modelos**

#### **7.1. Logistic Regression** (`entrenar_logistic_regression()`)

```python
modelo_lr, metricas_lr = entrenar_logistic_regression(
    X_train_balanced, y_train_balanced, X_val, y_val, X_test, y_test,
    class_weight=class_weights
)
```

**Qué hace:**

1. **Crea modelo** con hiperparámetros:
   - `C=0.1` (regularización fuerte)
   - `penalty='l2'` (regularización L2)
   - `class_weight=class_weights` (balancear clases)

2. **Entrena** con datos balanceados
3. **Predice** en train, val y test
4. **Calcula métricas**:
   - Accuracy, Precision, Recall, F1-Score, AUC-ROC

**Resultado:**
- Modelo entrenado
- Métricas de rendimiento

---

#### **7.2. Random Forest** (`entrenar_random_forest()`)

```python
modelo_rf, metricas_rf = entrenar_random_forest(
    X_train_balanced, y_train_balanced, X_val, y_val, X_test, y_test,
    class_weight=class_weights
)
```

**Qué hace:**

1. **Crea modelo** con hiperparámetros:
   - `n_estimators=100` (100 árboles)
   - `max_depth=5` (profundidad limitada)
   - `min_samples_split=20` (más muestras por split)
   - `min_samples_leaf=10` (más muestras por hoja)
   - `max_features='sqrt'` (menos features por split)
   - `class_weight=class_weights` (balancear clases)

2. **Entrena** con datos balanceados
3. **Predice** en train, val y test
4. **Calcula métricas** y **feature importance**

**Resultado:**
- Modelo entrenado
- Métricas de rendimiento
- Importancia de features

---

#### **7.3. XGBoost** (`entrenar_xgboost()`)

```python
modelo_xgb, metricas_xgb = entrenar_xgboost(
    X_train_balanced, y_train_balanced, X_val, y_val, X_test, y_test,
    scale_pos_weight=scale_pos_weight
)
```

**Qué hace:**

1. **Crea modelo** con hiperparámetros:
   - `n_estimators=100` (100 árboles)
   - `max_depth=3` (profundidad limitada)
   - `learning_rate=0.1` (tasa de aprendizaje conservadora)
   - `subsample=0.8` (submuestreo)
   - `colsample_bytree=0.8` (submuestreo de features)
   - `reg_alpha=1.0` (regularización L1)
   - `reg_lambda=1.0` (regularización L2)
   - `scale_pos_weight=scale_pos_weight` (balancear clases)

2. **Entrena** con datos balanceados y validación temprana
3. **Predice** en train, val y test
4. **Calcula métricas** y **feature importance**

**Resultado:**
- Modelo entrenado (mejor rendimiento)
- Métricas de rendimiento
- Importancia de features

---

### **PASO 8: Comparar Modelos** (`comparar_modelos()`)

```python
# Compara los 3 modelos y selecciona el mejor
comparacion = comparar_modelos(resultados)
```

**Qué hace:**

1. **Crea DataFrame comparativo** con métricas de los 3 modelos
2. **Ordena por AUC-ROC** (métrica principal)
3. **Selecciona el mejor modelo** (XGBoost)

**Resultado:**
- DataFrame con comparación de modelos
- Mejor modelo identificado

---

### **PASO 9: Guardar Modelos** (`guardar_modelos()`)

```python
# Guarda modelos, preprocesadores y métricas
guardar_modelos(modelos, metricas, imputer, scaler, encoders, comparacion)
```

**Qué hace:**

1. **Genera timestamp** (ej: `20251107_185913`)
2. **Guarda cada modelo** en `.pkl`:
   - `modelo_logistic_regression_20251107_185913.pkl`
   - `modelo_random_forest_20251107_185913.pkl`
   - `modelo_xgboost_20251107_185913.pkl`

3. **Guarda preprocesadores** en `.pkl`:
   - `preprocesadores_20251107_185913.pkl`
   - Contiene: `imputer`, `scaler`, `encoders`

4. **Guarda métricas** en `.json`:
   - `metricas_20251107_185913.json`

5. **Guarda comparación** en `.csv`:
   - `comparacion_modelos_20251107_185913.csv`

**Resultado:**
- Modelos guardados en `ModeloEntrenamiento/`
- Preprocesadores guardados
- Métricas guardadas
- Comparación guardada

---

## 📊 **Resumen del Pipeline**

```
1. Cargar Datos
   ↓
2. Preparar Features (excluir leakage, codificar categorías)
   ↓
3. Dividir Datos (train 70%, val 15%, test 15%)
   ↓
4. Imputar Valores Faltantes (mediana)
   ↓
5. Escalar Features (StandardScaler)
   ↓
6. Balancear Clases (SMOTE + class weights)
   ↓
7. Entrenar Modelos
   ├── Logistic Regression
   ├── Random Forest
   └── XGBoost
   ↓
8. Comparar Modelos (seleccionar mejor)
   ↓
9. Guardar Modelos y Preprocesadores
```

---

## 🎯 **Resultado Final**

Después de ejecutar el script, obtienes:

1. **3 modelos entrenados** (`.pkl`)
2. **Preprocesadores guardados** (`.pkl`)
3. **Métricas de rendimiento** (`.json`)
4. **Comparación de modelos** (`.csv`)

**Mejor modelo**: XGBoost (AUC-ROC: 0.861, Accuracy: 0.786)

---

## 🔧 **Configuración del Script**

### **Variables Configurables:**

- `FEATURES_NUMERICAS`: Variables numéricas a usar
- `FEATURES_CATEGORICAS`: Variables categóricas a usar
- `FEATURES_LEAKAGE`: Variables que causan data leakage
- `TARGET_CLASIFICACION`: Target de clasificación
- `RANDOM_STATE`: Semilla para reproducibilidad (42)

### **Hiperparámetros de Modelos:**

- **Logistic Regression**: `C=0.1`, `penalty='l2'`
- **Random Forest**: `max_depth=5`, `min_samples_split=20`
- **XGBoost**: `max_depth=3`, `learning_rate=0.1`, `reg_alpha=1.0`, `reg_lambda=1.0`

---

## 📝 **Cómo Ejecutar el Script**

```bash
# Desde el directorio del proyecto
cd ApartadoInteligente/Entrenamiento
python entrenar_modelos.py
```

**Tiempo estimado**: 2-5 minutos (dependiendo del hardware)

---

## ✅ **Checklist de Ejecución**

- [ ] Dataset procesado disponible (`nhanes_procesado.csv`)
- [ ] Dependencias instaladas (`requirements_ml.txt`)
- [ ] XGBoost instalado (`pip install xgboost`)
- [ ] imbalanced-learn instalado (`pip install imbalanced-learn`)
- [ ] Ejecutar script: `python entrenar_modelos.py`
- [ ] Verificar modelos guardados en `ModeloEntrenamiento/`

---

## 🎯 **Conclusión**

El script `entrenar_modelos.py` ejecuta un **pipeline completo de Machine Learning** que:

1. Prepara los datos correctamente
2. Entrena 3 modelos diferentes
3. Evalúa y compara los modelos
4. Guarda el mejor modelo y sus preprocesadores

**El resultado es un modelo XGBoost entrenado y listo para usar en producción.**

