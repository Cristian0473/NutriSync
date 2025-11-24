# 🤖 Machine Learning y Algoritmos Inteligentes

## 📋 Índice

1. [Introducción](#introducción)
2. [Modelos de Machine Learning Utilizados](#modelos-de-machine-learning-utilizados)
3. [Modelo 1: Predicción de Respuesta Glucémica](#modelo-1-predicción-de-respuesta-glucémica)
4. [Modelo 2: Selección Personalizada de Alimentos](#modelo-2-selección-personalizada-de-alimentos)
5. [Modelo 3: Optimización de Combinaciones](#modelo-3-optimización-de-combinaciones)
6. [Por qué XGBoost](#por-qué-xgboost)
7. [Flujo de Integración con el Sistema](#flujo-de-integración-con-el-sistema)

---

## 🎯 Introducción

El sistema utiliza **3 modelos de Machine Learning** entrenados con datos reales de pacientes con diabetes tipo 2. Estos modelos permiten:

- **Personalización inteligente** de recomendaciones nutricionales
- **Predicción de respuesta glucémica** a alimentos específicos
- **Selección optimizada** de alimentos según perfil del paciente
- **Evaluación de combinaciones** de alimentos para mejor control glucémico

### Dataset de Entrenamiento

Los modelos fueron entrenados con el **dataset NHANES** (National Health and Nutrition Examination Survey), que incluye:
- **12,054 pacientes** con diabetes tipo 2
- Datos antropométricos, clínicos y nutricionales
- Mediciones de control glucémico (HbA1c, glucosa en ayunas)

---

## 🧠 Modelos de Machine Learning Utilizados

### Resumen de los 3 Modelos

| Modelo | Algoritmo | Tipo | Propósito |
|--------|-----------|------|-----------|
| **Modelo 1** | XGBoost Regressor | Regresión | Predice respuesta glucémica a alimentos |
| **Modelo 2** | XGBoost Classifier | Clasificación | Selecciona alimentos más adecuados |
| **Modelo 3** | Ensemble (XGBoost + Random Forest) | Clasificación | Evalúa calidad de combinaciones |

---

## 📊 Modelo 1: Predicción de Respuesta Glucémica

### **Propósito**

Predice cómo responderá la glucosa en sangre de un paciente específico al consumir un alimento determinado.

### **Algoritmo: XGBoost Regressor**

**XGBoost (eXtreme Gradient Boosting)** es un algoritmo de ensamblado que:
- Combina múltiples árboles de decisión débiles
- Cada árbol corrige los errores del anterior (boosting)
- Usa regularización para evitar sobreajuste
- Optimiza la función de pérdida de manera eficiente

### **Inputs (Features)**

El modelo recibe:

**Features del Paciente:**
- Edad (`age`)
- Sexo (`gender`: 0=Masculino, 1=Femenino)
- IMC (`bmi`)
- Peso (`weight`)
- Talla (`height`)
- HbA1c (`a1c`)
- Glucosa en ayunas (`fasting_glucose`)
- Triglicéridos (`triglycerides`)
- HOMA-IR (`homa_ir`) - si está disponible
- Ratio TG/HDL (`tg_hdl_ratio`) - si está disponible

**Features del Alimento:**
- Calorías (`calories`)
- Carbohidratos (`carbs`)
- Proteínas (`protein`)
- Grasas (`fat`)
- Fibra (`fiber`)
- Ratios por 100 calorías (carbs_per_100cal, protein_per_100cal, etc.)

**Features de Contexto:**
- Hora del día (`hora`)
- Tipo de comida (`meal_type_encoded`: des=0, mm=1, alm=2, mt=3, cena=4)
- Glucosa basal (`glucose_baseline`)
- Tiempo desde última comida (`tiempo_desde_ultima_comida`)

### **Outputs (Predicciones)**

El modelo predice 3 valores:

1. **`glucose_increment`**: Incremento de glucosa en mg/dL
2. **`glucose_peak`**: Pico máximo de glucosa en mg/dL
3. **`time_to_peak`**: Tiempo hasta alcanzar el pico (en minutos)

### **Cómo Funciona**

```python
# Ejemplo de uso
resultado = motor.predecir_respuesta_glucemica(
    perfil=paciente,
    alimento={
        'kcal': 250,
        'cho': 45,
        'pro': 8,
        'fat': 5,
        'fibra': 3
    },
    contexto={
        'tiempo_comida': 'alm',
        'hora': 12,
        'glucose_baseline': 100
    }
)

# Resultado:
# {
#     'glucose_increment': 35.2,  # Aumentará 35.2 mg/dL
#     'glucose_peak': 135.2,      # Pico de 135.2 mg/dL
#     'time_to_peak': 45          # Pico en 45 minutos
# }
```

### **Uso en el Sistema**

El Modelo 1 se usa para:
- **Evaluar alimentos** antes de incluirlos en el plan
- **Priorizar alimentos** con menor impacto glucémico
- **Ajustar cantidades** según respuesta esperada

---

## 🎯 Modelo 2: Selección Personalizada de Alimentos

### **Propósito**

Calcula un **score de idoneidad (0-1)** que indica qué tan adecuado es un alimento para un paciente específico.

### **Algoritmo: XGBoost Classifier**

**XGBoost Classifier** es un clasificador que:
- Predice la probabilidad de que un alimento sea "adecuado" (clase 1) o "no adecuado" (clase 0)
- Usa las mismas ventajas de XGBoost (boosting, regularización)
- Maneja bien clases desbalanceadas

### **Inputs (Features)**

**Features del Paciente:**
- Edad, sexo, IMC
- HbA1c, glucosa en ayunas
- HOMA-IR (si disponible)

**Features del Alimento:**
- Calorías, carbohidratos, proteínas, grasas
- Sodio, azúcar (si disponible)
- Ratios por 100 calorías

**Features de Necesidades:**
- Calorías objetivo
- Carbohidratos objetivo
- Proteínas objetivo
- Grasas objetivo

### **Output**

**Score de idoneidad (0-1)**:
- **0.0 - 0.3**: Alimento poco adecuado ❌
- **0.3 - 0.7**: Alimento moderadamente adecuado ⚠️
- **0.7 - 1.0**: Alimento muy adecuado ✅

### **Cómo Funciona**

```python
# Ejemplo de uso
score = motor.calcular_score_idoneidad_alimento(
    perfil=paciente,
    alimento={
        'kcal': 120,
        'cho': 25,
        'pro': 3,
        'fat': 2,
        'sodio': 150
    },
    necesidades={
        'calorias': 1800,
        'carbs': 225,
        'protein': 135,
        'fat': 60
    }
)

# Resultado: 0.82 (muy adecuado para este paciente)
```

### **Uso en el Sistema**

El Modelo 2 se usa para:
- **Ranking de alimentos**: Ordenar alimentos por idoneidad
- **Filtrado inteligente**: Priorizar alimentos con score > 0.6
- **Personalización**: Seleccionar alimentos específicos para cada paciente

---

## 🔄 Modelo 3: Optimización de Combinaciones

### **Propósito**

Evalúa la **calidad de una combinación de alimentos** (ej: desayuno con 3-4 alimentos) para determinar si es óptima para el control glucémico.

### **Algoritmo: Ensemble (XGBoost + Random Forest)**

**Ensemble** combina:
- **XGBoost Classifier**: Predicción principal
- **Random Forest Classifier**: Validación y robustez
- **Promedio ponderado**: Combina ambas predicciones

**Ventajas del Ensemble:**
- Mayor robustez (menos sensible a outliers)
- Mejor generalización
- Reduce sobreajuste

### **Inputs (Features)**

**Features Agregadas de la Combinación:**
- Suma total de calorías, carbohidratos, proteínas, grasas
- Promedio de índice glucémico
- Diversidad de grupos alimentarios
- Balance nutricional (ratio CHO/PRO/FAT)
- Variedad de texturas/sabores

**Features del Paciente:**
- Mismas que Modelo 1 y 2

**Features de Contexto:**
- Tipo de comida (desayuno, almuerzo, etc.)
- Hora del día

### **Output**

**Score de calidad (0-1)**:
- **0.0 - 0.5**: Combinación subóptima ❌
- **0.5 - 0.7**: Combinación aceptable ⚠️
- **0.7 - 1.0**: Combinación óptima ✅

### **Cómo Funciona**

```python
# Ejemplo de uso
combinacion = [
    {'nombre': 'Avena', 'kcal': 150, 'cho': 27, 'pro': 5, 'fat': 3},
    {'nombre': 'Plátano', 'kcal': 90, 'cho': 23, 'pro': 1, 'fat': 0},
    {'nombre': 'Leche', 'kcal': 100, 'cho': 12, 'pro': 8, 'fat': 2}
]

score = motor.evaluar_combinacion_alimentos(
    perfil=paciente,
    combinacion=combinacion,
    contexto={'tiempo_comida': 'des', 'hora': 7}
)

# Resultado: 0.75 (combinación óptima)
```

### **Uso en el Sistema**

El Modelo 3 se usa para:
- **Optimización de planes**: Evaluar y mejorar combinaciones
- **Validación**: Verificar que las combinaciones sean adecuadas
- **Ajuste automático**: Modificar combinaciones para mejorar el score

---

## 🏆 Por qué XGBoost

### **Comparación con Otros Algoritmos**

| Algoritmo | Accuracy | AUC-ROC | F1-Score | Decisión |
|-----------|----------|---------|----------|----------|
| **XGBoost** | **0.786** ✅ | **0.861** ✅ | **0.522** ✅ | **ELEGIDO** |
| Logistic Regression | 0.261 ❌ | 0.811 | 0.289 | Rechazado |
| Random Forest | 0.329 ❌ | 0.719 | 0.310 | Rechazado |

### **Ventajas de XGBoost**

1. **Mejor Rendimiento**: AUC-ROC de 0.861 (vs 0.811 y 0.719)
2. **Bien Calibrado**: Detecta bien ambas clases (buen y mal control)
3. **Regularización Integrada**: Previene sobreajuste
4. **Manejo de Clases Desbalanceadas**: Usa `scale_pos_weight`
5. **Optimización Eficiente**: Algoritmo muy rápido y eficiente
6. **Robusto para Datos Tabulares**: Ideal para datos clínicos

### **Métricas de Evaluación**

**AUC-ROC (0.861)**: 
- Probabilidad de 86.1% de distinguir correctamente entre pacientes con buen y mal control glucémico
- **Métrica principal** para clasificación binaria

**Accuracy (0.786)**:
- 78.6% de predicciones correctas
- Mucho mejor que los otros modelos (26-33%)

**F1-Score (0.522)**:
- Buen balance entre Precision y Recall
- Mejor que los otros modelos (0.289 y 0.310)

---

## 🔄 Flujo de Integración con el Sistema

### **1. Carga de Modelos (Lazy Loading)**

Los modelos se cargan **bajo demanda** cuando se necesitan:

```python
# En motor_recomendacion.py
def _cargar_modelo_respuesta_glucemica(self):
    """Carga Modelo 1 solo cuando se necesita"""
    if self._modelo_respuesta_glucemica is None:
        # Cargar desde archivo .pkl
        modelo_path = "ApartadoInteligente/ModeloML/modelo_respuesta_glucemica.pkl"
        with open(modelo_path, 'rb') as f:
            self._modelo_respuesta_glucemica = pickle.load(f)
```

**Ventajas**:
- No carga modelos innecesarios al inicio
- Ahorra memoria
- Permite que el sistema funcione sin ML si los modelos no están disponibles

### **2. Preprocesamiento de Features**

Antes de usar los modelos, los datos se preprocesan:

```python
# 1. Preparar features del paciente
features = {
    'age': perfil.edad,
    'bmi': perfil.imc,
    'a1c': perfil.hba1c,
    # ... más features
}

# 2. Crear DataFrame
df_features = pd.DataFrame([features])

# 3. Imputar valores faltantes (si hay)
df_imputed = imputer.transform(df_features)

# 4. Escalar features (normalización)
df_scaled = scaler.transform(df_imputed)

# 5. Predecir
prediccion = modelo.predict(df_scaled)
```

### **3. Integración en el Flujo de Generación**

```
1. Nutricionista solicita generar plan
   ↓
2. Sistema obtiene perfil del paciente
   ↓
3. Sistema calcula metas nutricionales base (fórmulas clínicas)
   ↓
4. Modelo 1: Predice control glucémico → Ajusta metas
   ↓
5. Modelo 2: Selecciona alimentos más adecuados
   ↓
6. Sistema genera plan semanal con variedad
   ↓
7. Modelo 3: Evalúa y optimiza combinaciones
   ↓
8. Optimizador: Ajusta cantidades para cumplir objetivos exactos
   ↓
9. Plan final listo
```

### **4. Fallback sin ML**

Si los modelos no están disponibles, el sistema funciona con **reglas basadas en conocimiento**:

```python
# Si ML no está disponible
if not ML_AVAILABLE or modelo is None:
    # Usar reglas clínicas tradicionales
    if perfil.hba1c > 8.0:
        reducir_calorias(10%)
    if perfil.imc > 30:
        reducir_calorias(10%)
```

---

## 📊 Resumen

### **Modelos Utilizados**

1. **Modelo 1 (XGBoost Regressor)**: Predice respuesta glucémica
2. **Modelo 2 (XGBoost Classifier)**: Selecciona alimentos adecuados
3. **Modelo 3 (Ensemble)**: Evalúa combinaciones óptimas

### **Por qué XGBoost**

- ✅ Mejor rendimiento (AUC-ROC: 0.861)
- ✅ Bien calibrado para clases desbalanceadas
- ✅ Regularización integrada
- ✅ Optimización eficiente

### **Integración**

- ✅ Carga bajo demanda (lazy loading)
- ✅ Preprocesamiento automático
- ✅ Fallback a reglas clínicas si ML no está disponible
- ✅ Transparente para el usuario final

---

## 🎯 Conclusión

El sistema utiliza **Machine Learning de vanguardia** (XGBoost) para personalizar inteligentemente las recomendaciones nutricionales. Los 3 modelos trabajan en conjunto para:

1. **Predecir** cómo responderá el paciente a alimentos específicos
2. **Seleccionar** los alimentos más adecuados
3. **Optimizar** las combinaciones para mejor control glucémico

Todo esto mientras mantiene **transparencia** y **fallback** a reglas clínicas tradicionales si es necesario.

