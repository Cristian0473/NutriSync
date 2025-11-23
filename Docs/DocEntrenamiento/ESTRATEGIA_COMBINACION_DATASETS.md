# 🎯 Estrategia: Combinación y Uso de Datasets para ML

## 📊 **¿DEBEMOS COMBINARLOS?**

### **Respuesta: SÍ, pero de forma estratégica**

**NO los combinaremos en un solo archivo plano**, sino que los usaremos para entrenar **modelos ML específicos** que aumentarán la intervención del ML en tu sistema.

---

## 🔍 **¿QUÉ BUSCAMOS LOGRAR?**

### **Objetivo Principal:**
Aumentar la **intervención del Machine Learning** en la generación de recomendaciones nutricionales del **15-25% actual** al **60-70%**, como requiere tu asesor.

### **Problema Actual:**
El sistema actual usa ML principalmente para:
- Predecir probabilidad de mal control glucémico (XGBoost)
- Ajustar distribución de macronutrientes
- Filtrar alimentos por índice glucémico

**Limitaciones:**
- ❌ No predice respuesta glucémica a alimentos específicos
- ❌ No selecciona alimentos personalizados
- ❌ No optimiza combinaciones de alimentos
- ❌ No predice cantidades ideales por paciente

---

## 🎯 **QUÉ HACEREMOS CON LOS DATASETS**

### **ESTRATEGIA: 3 Modelos ML Especializados**

En lugar de combinar todo en un archivo, entrenaremos **3 modelos ML diferentes** que trabajarán juntos:

---

### **MODELO 1: Predicción de Respuesta Glucémica Postprandial** 
**Dataset principal: CGMacros**

#### **¿Qué hace?**
Predice cómo responderá la glucosa de un paciente específico después de consumir una comida con ciertos macronutrientes.

#### **Input (Features):**
```
- Perfil del paciente: edad, sexo, BMI, HbA1c, insulina, HOMA-IR
- Características de la comida: calorías, carbohidratos, proteína, grasa, fibra
- Contexto: tipo de comida (desayuno/almuerzo/cena), hora del día
- Estado previo: glucosa antes de la comida, tiempo desde última comida
```

#### **Output (Target):**
```
- Incremento de glucosa esperado (mg/dL)
- Pico de glucosa postprandial (mg/dL)
- Tiempo hasta el pico (minutos)
```

#### **Algoritmo:**
- **XGBoost Regressor** o **Random Forest Regressor**
- Métricas: MAE, RMSE, R²

#### **Datos necesarios de CGMacros:**
- ✅ Glucosa continua (Libre GL / Dexcom GL)
- ✅ Datos de comidas (tipo, macronutrientes)
- ✅ Datos bioquímicos del paciente
- ✅ Timestamps para calcular respuestas postprandiales

---

### **MODELO 2: Selección Personalizada de Alimentos**
**Dataset principal: MyFitnessPal + CGMacros**

#### **¿Qué hace?**
Para un paciente y contexto dado, predice qué alimentos específicos son más adecuados y en qué cantidades.

#### **Input (Features):**
```
- Perfil del paciente: edad, sexo, BMI, HbA1c, preferencias
- Necesidades nutricionales: calorías objetivo, macronutrientes objetivo
- Contexto: tipo de comida, hora del día
- Historial: alimentos que funcionaron bien anteriormente
```

#### **Output (Target):**
```
- Score de idoneidad (0-1) para cada alimento
- Cantidad recomendada (gramos/porciones)
```

#### **Algoritmo:**
- **XGBoost Classifier** o **Neural Network**
- Métricas: Precision, Recall, F1-Score

#### **Datos necesarios:**
- ✅ De MyFitnessPal: alimentos consumidos, valores nutricionales, preferencias
- ✅ De CGMacros: qué alimentos causaron mejor respuesta glucémica
- ✅ Combinación: alimentos que funcionaron bien para perfiles similares

---

### **MODELO 3: Optimización de Combinaciones de Alimentos**
**Dataset principal: CGMacros**

#### **¿Qué hace?**
Predice si una combinación específica de alimentos (ej: arroz + pollo + ensalada) resultará en mejor control glucémico que otra combinación.

#### **Input (Features):**
```
- Perfil del paciente
- Combinación de alimentos: lista de alimentos con cantidades
- Orden de consumo (si aplica)
- Contexto temporal
```

#### **Output (Target):**
```
- Score de calidad de la combinación (0-1)
- Predicción de respuesta glucémica esperada
```

#### **Algoritmo:**
- **Ensemble (XGBoost + Random Forest)**
- Métricas: Accuracy, AUC-ROC

---

## 🔧 **CÓMO LO IMPLEMENTAREMOS EN EL SISTEMA**

### **Arquitectura Propuesta:**

```
┌─────────────────────────────────────────────────────────┐
│         MOTOR DE RECOMENDACIÓN (motor_recomendacion.py) │
└─────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Modelo 1:   │ │  Modelo 2:   │ │  Modelo 3:   │
│ Respuesta    │ │ Selección     │ │ Optimización │
│ Glucémica    │ │ Alimentos     │ │ Combinaciones│
└──────────────┘ └──────────────┘ └──────────────┘
        │               │               │
        └───────────────┼───────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │  PLAN NUTRICIONAL    │
            │  PERSONALIZADO        │
            └──────────────────────┘
```

### **Flujo de Generación de Recomendación:**

#### **Paso 1: Análisis del Paciente (Actual - se mantiene)**
```python
# Usa el modelo actual XGBoost para predecir riesgo
probabilidad_mal_control = modelo_actual.predecir(perfil_paciente)
```

#### **Paso 2: Predicción de Respuesta Glucémica (NUEVO - Modelo 1)**
```python
# Para cada alimento candidato, predice respuesta glucémica
for alimento in alimentos_candidatos:
    respuesta_esperada = modelo_respuesta_glucemica.predecir(
        paciente=perfil_paciente,
        alimento=alimento,
        contexto=contexto_comida
    )
    # Filtrar alimentos que causarían picos altos
    if respuesta_esperada['pico_glucosa'] > umbral_seguro:
        excluir_alimento(alimento)
```

#### **Paso 3: Selección Personalizada (NUEVO - Modelo 2)**
```python
# Para cada alimento restante, calcula score de idoneidad
scores_alimentos = {}
for alimento in alimentos_filtrados:
    score = modelo_seleccion_alimentos.predecir(
        paciente=perfil_paciente,
        alimento=alimento,
        necesidades=necesidades_nutricionales
    )
    scores_alimentos[alimento] = score

# Ordenar por score y seleccionar mejores
alimentos_seleccionados = ordenar_por_score(scores_alimentos)
```

#### **Paso 4: Optimización de Combinaciones (NUEVO - Modelo 3)**
```python
# Generar combinaciones de alimentos seleccionados
combinaciones = generar_combinaciones(alimentos_seleccionados)

# Evaluar cada combinación
mejor_combinacion = None
mejor_score = 0
for combo in combinaciones:
    score = modelo_optimizacion_combinaciones.predecir(
        paciente=perfil_paciente,
        combinacion=combo
    )
    if score > mejor_score:
        mejor_score = score
        mejor_combinacion = combo

# Usar mejor combinación en el plan
plan_nutricional = crear_plan_desde_combinacion(mejor_combinacion)
```

#### **Paso 5: Ajuste Final (Actual - se mantiene)**
```python
# Ajustes finales según guía de intercambio
plan_final = ajustar_segun_guia_intercambio(plan_nutricional)
```

---

## 📈 **IMPACTO EN LA INTERVENCIÓN DEL ML**

### **Intervención Actual:**
- **15-25%**: Solo ajusta distribución de macronutrientes y filtra por IG

### **Intervención con Nuevos Modelos:**
- **60-70%**: 
  - ✅ Predice respuesta glucémica específica (Modelo 1): **20%**
  - ✅ Selecciona alimentos personalizados (Modelo 2): **25%**
  - ✅ Optimiza combinaciones (Modelo 3): **15%**
  - ✅ Ajusta distribución (Actual): **10%**

---

## 🗂️ **ESTRUCTURA DE DATOS PARA ENTRENAMIENTO**

### **NO combinaremos en un solo CSV**, sino que crearemos:

1. **`cgmacros_para_respuesta_glucemica.csv`**
   - Datos de CGMacros procesados para entrenar Modelo 1
   - Estructura: paciente + comida + respuesta glucémica

2. **`mfp_para_seleccion_alimentos.csv`**
   - Datos de MyFitnessPal procesados para entrenar Modelo 2
   - Estructura: paciente + alimento + score de idoneidad

3. **`cgmacros_para_combinaciones.csv`**
   - Datos de CGMacros procesados para entrenar Modelo 3
   - Estructura: paciente + combinación de alimentos + resultado

---

## ⚙️ **IMPLEMENTACIÓN TÉCNICA**

### **Archivos a Crear/Modificar:**

1. **`entrenar_modelo_respuesta_glucemica.py`**
   - Script para entrenar Modelo 1
   - Usa datos de CGMacros

2. **`entrenar_modelo_seleccion_alimentos.py`**
   - Script para entrenar Modelo 2
   - Usa datos combinados de MyFitnessPal + CGMacros

3. **`entrenar_modelo_optimizacion_combinaciones.py`**
   - Script para entrenar Modelo 3
   - Usa datos de CGMacros

4. **`motor_recomendacion.py` (MODIFICAR)**
   - Integrar los 3 nuevos modelos
   - Modificar flujo de generación de recomendaciones

5. **`modelos_ml/` (NUEVA CARPETA)**
   - `modelo_respuesta_glucemica.pkl`
   - `modelo_seleccion_alimentos.pkl`
   - `modelo_optimizacion_combinaciones.pkl`

---

## ✅ **VENTAJAS DE ESTA ESTRATEGIA**

1. **✅ Aumenta intervención ML**: De 15-25% a 60-70%
2. **✅ Modelos especializados**: Cada modelo hace una tarea específica
3. **✅ Mejor precisión**: Modelos entrenados con datos relevantes
4. **✅ Mantenibilidad**: Fácil actualizar modelos individuales
5. **✅ Escalabilidad**: Puedes agregar más modelos después
6. **✅ Explicabilidad**: Cada modelo tiene un propósito claro

---

## ⚠️ **CONSIDERACIONES**

1. **Tiempo de entrenamiento**: Cada modelo requiere tiempo (1-2 horas cada uno)
2. **Validación**: Necesitas validar cada modelo con datos de prueba
3. **Integración**: Requiere modificar `motor_recomendacion.py`
4. **Rendimiento**: 3 modelos pueden ser más lentos que 1 (pero más preciso)

---

## 🎯 **PRÓXIMOS PASOS**

1. ✅ **Procesar datasets** (YA HECHO)
2. ⏳ **Preparar datos específicos para cada modelo**
3. ⏳ **Entrenar Modelo 1 (Respuesta Glucémica)**
4. ⏳ **Entrenar Modelo 2 (Selección de Alimentos)**
5. ⏳ **Entrenar Modelo 3 (Optimización de Combinaciones)**
6. ⏳ **Integrar modelos en motor_recomendacion.py**
7. ⏳ **Probar y validar**

---

## 📝 **RESUMEN**

**NO combinamos los datasets en un solo archivo**, sino que:
- Usamos **CGMacros** principalmente para entrenar modelos de **respuesta glucémica**
- Usamos **MyFitnessPal** principalmente para entrenar modelos de **selección de alimentos**
- Entrenamos **3 modelos ML especializados** que trabajan juntos
- Integramos los modelos en el sistema para aumentar la intervención del ML al **60-70%**

¿Te parece bien esta estrategia? ¿Quieres que empecemos a preparar los datos específicos para cada modelo?

