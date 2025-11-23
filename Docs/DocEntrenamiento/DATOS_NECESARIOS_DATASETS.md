# 📋 Datos Necesarios de los Datasets para Entrenar Modelos

## 🎯 **RESUMEN EJECUTIVO**

Este documento especifica **exactamente qué datos necesitas extraer** de cada dataset para entrenar los modelos de ML que aumentarán la intervención del ML en tu sistema.

---

## 📊 **DATASET 1: CGMacros (PhysioNet)**

### **Modelo a Entrenar: Predicción de Respuesta Glucémica**

**Objetivo**: Predecir cómo responderá la glucosa a un alimento específico

---

### **Datos Necesarios (Esenciales):**

#### **1. Datos del Paciente (Perfil)**
```
- participant_id: ID del participante
- age: Edad
- sex: Sexo (M/F)
- bmi: IMC
- weight: Peso (kg)
- height: Talla (m)
- diabetes_type: Tipo de diabetes (0=sano, 1=pre-DM, 2=DM2)
```

#### **2. Datos de la Comida (Input)**
```
- meal_id: ID de la comida
- meal_timestamp: Fecha y hora de la comida
- food_item: Nombre del alimento (o ID)
- calories: Calorías (kcal)
- carbohydrates: Carbohidratos (g)
- protein: Proteína (g)
- fat: Grasa (g)
- fiber: Fibra (g)
- sugars: Azúcares (g)
- sodium: Sodio (mg)
```

#### **3. Datos de Respuesta Glucémica (Target)**
```
- cgm_timestamp: Timestamp de la medición de glucosa
- glucose_value: Valor de glucosa (mg/dL)
- time_from_meal: Tiempo desde la comida (minutos)
- glucose_peak: Pico de glucosa postprandial (mg/dL)
- glucose_increment: Incremento de glucosa (mg/dL) = peak - baseline
- glucose_baseline: Glucosa antes de la comida (mg/dL)
```

#### **4. Datos Adicionales (Si están disponibles)**
```
- meal_type: Tipo de comida (breakfast, lunch, dinner, snack)
- meal_duration: Duración de la comida (minutos)
- activity_before: Actividad física antes de la comida
- activity_after: Actividad física después de la comida
```

---

### **Estructura Final del Dataset para Entrenamiento:**

```python
# Dataset final para entrenar modelo de respuesta glucémica
dataset_cgmacros = {
    # Features (Input)
    'participant_id': [...],
    'age': [...],
    'sex': [...],  # Codificado: 0=M, 1=F
    'bmi': [...],
    'weight': [...],
    'height': [...],
    'diabetes_type': [...],  # 0=sano, 1=pre-DM, 2=DM2
    
    # Características del alimento
    'calories': [...],
    'carbohydrates': [...],
    'protein': [...],
    'fat': [...],
    'fiber': [...],
    'sugars': [...],
    'sodium': [...],
    
    # Contexto
    'meal_type': [...],  # Codificado: 0=breakfast, 1=lunch, 2=dinner, 3=snack
    'time_from_meal': [...],  # Minutos desde la comida
    
    # Target (Output)
    'glucose_increment': [...],  # Incremento de glucosa (mg/dL)
    'glucose_peak': [...]  # Pico de glucosa (mg/dL)
}
```

---

### **Procesamiento de CGM (Pasos):**

1. **Para cada comida:**
   - Identificar glucosa baseline (última medición antes de la comida)
   - Identificar pico de glucosa postprandial (máximo en las 2-3 horas siguientes)
   - Calcular incremento: `glucose_increment = peak - baseline`
   - Calcular tiempo al pico: `time_to_peak` (minutos)

2. **Crear registros:**
   - Un registro por comida
   - Features: perfil del paciente + características del alimento
   - Target: incremento de glucosa o pico de glucosa

---

### **Variables a Ignorar (Para ahorrar tiempo):**
- ❌ Fotografías de comidas (no las necesitamos)
- ❌ Datos de microbioma (irrelevante para este modelo)
- ❌ Datos de actividad física detallados (opcional)
- ❌ Todos los campos que no sean los listados arriba

---

## 📊 **DATASET 2: MyFitnessPal**

### **Modelo a Entrenar: Predicción de Adherencia**

**Objetivo**: Predecir probabilidad de que un paciente consuma un alimento específico

---

### **Datos Necesarios (Esenciales):**

#### **1. Datos del Usuario (Perfil)**
```
- user_id: ID del usuario (anónimo)
- age: Edad (si está disponible, o estimar)
- sex: Sexo (si está disponible)
- weight_goal: Objetivo de peso (kg) - si está disponible
- calorie_goal: Objetivo de calorías (kcal/día)
- macro_goals: Objetivos de macronutrientes (CHO, PRO, FAT %)
```

#### **2. Datos de la Comida Consumida**
```
- date: Fecha del registro
- meal_type: Tipo de comida (breakfast, lunch, dinner, snack)
- food_name: Nombre del alimento
- calories: Calorías (kcal)
- carbohydrates: Carbohidratos (g)
- protein: Proteína (g)
- fat: Grasa (g)
- fiber: Fibra (g) - si está disponible
- sugars: Azúcares (g) - si está disponible
```

#### **3. Datos de Cumplimiento (Si están disponibles)**
```
- calories_consumed: Calorías consumidas ese día
- calories_goal: Objetivo de calorías
- calories_ratio: Ratio consumido/objetivo (0-1)
- macros_consumed: Macros consumidos
- macros_goal: Objetivos de macros
```

---

### **Estructura Final del Dataset para Entrenamiento:**

```python
# Dataset final para entrenar modelo de adherencia
dataset_myfitnesspal = {
    # Features (Input)
    'user_id': [...],
    'calorie_goal': [...],
    'cho_goal_pct': [...],  # % objetivo de carbohidratos
    'pro_goal_pct': [...],  # % objetivo de proteínas
    'fat_goal_pct': [...],  # % objetivo de grasas
    
    # Características del alimento
    'food_name': [...],  # O categoría del alimento
    'calories': [...],
    'carbohydrates': [...],
    'protein': [...],
    'fat': [...],
    'fiber': [...],
    'sugars': [...],
    
    # Contexto
    'meal_type': [...],  # Codificado: 0=breakfast, 1=lunch, 2=dinner, 3=snack
    'day_of_week': [...],  # 0=lunes, 6=domingo
    
    # Target (Output) - Binario: ¿El usuario consumió este alimento?
    'consumed': [...]  # 1 si consumió, 0 si no (o frecuencia de consumo)
}
```

---

### **Procesamiento de MyFitnessPal (Pasos):**

1. **Parsear JSON anidado:**
   - Extraer datos de cada día
   - Extraer alimentos consumidos
   - Extraer objetivos nutricionales

2. **Crear registros:**
   - Un registro por alimento consumido por usuario por día
   - Features: perfil del usuario + características del alimento + contexto
   - Target: 1 (consumido) o frecuencia de consumo

3. **Muestreo (para MVP):**
   - Seleccionar 10,000-20,000 días aleatorios
   - O seleccionar usuarios con más días de registro
   - O seleccionar días recientes (últimos meses)

---

### **Variables a Ignorar (Para ahorrar tiempo):**
- ❌ Datos de ejercicio detallados (irrelevante)
- ❌ Notas o comentarios de usuarios
- ❌ Datos de agua (opcional, no crítico)
- ❌ Todos los campos que no sean los listados arriba

---

## 🎯 **RESUMEN: QUÉ DATOS NECESITAS**

### **De CGMacros, necesitas:**

**Archivos a procesar:**
- ✅ Datos de participantes (edad, sexo, IMC, tipo diabetes)
- ✅ Datos de comidas (alimentos, macronutrientes)
- ✅ Datos de CGM (glucosa en tiempo real)

**Columnas/Variables específicas:**
```
Participantes:
- participant_id, age, sex, bmi, weight, height, diabetes_type

Comidas:
- meal_id, meal_timestamp, food_item, calories, carbohydrates, 
  protein, fat, fiber, sugars, sodium, meal_type

CGM:
- cgm_timestamp, glucose_value, time_from_meal
```

**Target a calcular:**
- `glucose_increment` = pico_glucosa - baseline_glucosa
- `glucose_peak` = máximo valor de glucosa postprandial

---

### **De MyFitnessPal, necesitas:**

**Archivos a procesar:**
- ✅ Datos de usuarios (objetivos nutricionales)
- ✅ Datos de comidas consumidas (alimentos, nutrientes)
- ✅ Fechas y contexto

**Columnas/Variables específicas:**
```
Usuarios:
- user_id, calorie_goal, cho_goal_pct, pro_goal_pct, fat_goal_pct

Comidas:
- date, meal_type, food_name, calories, carbohydrates, 
  protein, fat, fiber, sugars

Contexto:
- day_of_week
```

**Target:**
- `consumed` = 1 si el usuario consumió ese alimento (o frecuencia)

---

## 📋 **CHECKLIST: QUÉ PREPARAR**

### **Antes de empezar, necesito que me proporciones:**

#### **CGMacros:**
- [ ] Estructura de archivos (¿qué archivos CSV/JSON contiene?)
- [ ] Ejemplo de datos de participantes (2-3 filas)
- [ ] Ejemplo de datos de comidas (2-3 filas)
- [ ] Ejemplo de datos de CGM (2-3 filas)
- [ ] Nombres exactos de las columnas

#### **MyFitnessPal:**
- [ ] Estructura del JSON (¿cómo está anidado?)
- [ ] Ejemplo de un registro completo (1-2 registros)
- [ ] Cómo están estructurados los objetivos nutricionales
- [ ] Cómo están estructurados los alimentos consumidos

---

## 🔍 **QUÉ HACER PRIMERO**

### **Paso 1: Explorar CGMacros**

1. Descargar y descomprimir
2. Abrir los archivos CSV/JSON
3. Identificar:
   - ¿Dónde están los datos de participantes?
   - ¿Dónde están los datos de comidas?
   - ¿Dónde están los datos de CGM?
   - ¿Qué columnas tiene cada archivo?

4. **Enviarme:**
   - Nombres de archivos
   - Nombres de columnas de cada archivo
   - 2-3 filas de ejemplo de cada archivo

### **Paso 2: Explorar MyFitnessPal**

1. Descargar el archivo TSV
2. Abrir y ver estructura del JSON
3. Identificar:
   - ¿Cómo está estructurado el JSON?
   - ¿Dónde están los objetivos nutricionales?
   - ¿Dónde están los alimentos consumidos?

4. **Enviarme:**
   - Estructura del JSON (ejemplo de 1 registro completo)
   - Cómo acceder a objetivos nutricionales
   - Cómo acceder a alimentos consumidos

---

## 💡 **FORMATO DE DATOS QUE ESPERO**

### **Para CGMacros:**

**Archivo de participantes:**
```csv
participant_id,age,sex,bmi,weight,height,diabetes_type
CGMacros-001,45,M,28.5,80,1.68,2
CGMacros-002,52,F,31.2,75,1.55,2
```

**Archivo de comidas:**
```csv
meal_id,participant_id,meal_timestamp,food_item,calories,carbs,protein,fat,fiber,sugars,sodium
meal_001,CGMacros-001,2024-01-15 08:00:00,Avena,150,27,5,3,4,1,5
```

**Archivo de CGM:**
```csv
cgm_id,participant_id,cgm_timestamp,glucose_value
cgm_001,CGMacros-001,2024-01-15 08:00:00,95
cgm_002,CGMacros-001,2024-01-15 08:15:00,120
cgm_003,CGMacros-001,2024-01-15 08:30:00,145
```

### **Para MyFitnessPal:**

**Estructura JSON esperada:**
```json
{
  "user_id": "12345",
  "date": "2014-09-14",
  "meals": [
    {
      "meal": "Breakfast",
      "dishes": [
        {
          "food": "Oatmeal",
          "nutritions": [
            {"name": "Calories", "value": "150"},
            {"name": "Carbs", "value": "27"},
            {"name": "Protein", "value": "5"},
            {"name": "Fat", "value": "3"}
          ]
        }
      ]
    }
  ],
  "goals": {
    "calories": "2000",
    "carbs_pct": "50",
    "protein_pct": "20",
    "fat_pct": "30"
  }
}
```

---

## ✅ **PRÓXIMOS PASOS**

1. **Descarga ambos datasets**
2. **Explora la estructura** de cada uno
3. **Envíame:**
   - Nombres de archivos y columnas de CGMacros
   - Estructura JSON de MyFitnessPal (1-2 ejemplos)
4. **Yo preparo los scripts** de procesamiento
5. **Procesamos y entrenamos** los modelos

---

## 🎯 **RESUMEN ULTRA-RÁPIDO**

### **CGMacros - Necesito:**
- Datos de participantes (edad, sexo, IMC, tipo diabetes)
- Datos de comidas (alimentos, macronutrientes)
- Datos de CGM (glucosa en tiempo real)
- **Target**: Incremento de glucosa postprandial

### **MyFitnessPal - Necesito:**
- Objetivos nutricionales de usuarios
- Alimentos consumidos (nombre, nutrientes)
- Fecha y tipo de comida
- **Target**: Si el usuario consumió ese alimento (o frecuencia)

**Una vez que me des esta información, preparo los scripts de procesamiento y entrenamiento.**

