# ⚙️ Funciones y Flujo de Procesamiento

## 📋 Índice

1. [Introducción](#introducción)
2. [Flujo Principal de Generación de Plan](#flujo-principal-de-generación-de-plan)
3. [Funciones Clave del Motor de Recomendación](#funciones-clave-del-motor-de-recomendación)
4. [Orden de Ejecución Detallado](#orden-de-ejecución-detallado)
5. [Integración con el Frontend](#integración-con-el-frontend)

---

## 🎯 Introducción

Este documento explica **cómo funciona el sistema internamente**, detallando las funciones principales y el orden en que se ejecutan para generar una recomendación nutricional personalizada.

### **Punto de Entrada Principal**

El flujo comienza cuando un **nutricionista o administrador** solicita generar un plan nutricional desde la interfaz web.

---

## 🔄 Flujo Principal de Generación de Plan

### **Diagrama de Flujo Completo**

```
┌─────────────────────────────────────────────────────────────┐
│  1. Usuario (Nutricionista/Admin) solicita generar plan    │
│     → Frontend: obtener_plan.js                             │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  2. POST /api/recomendacion/generar                         │
│     → main.py: api_recomendacion_generar()                 │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  3. MotorRecomendacion.generar_plan_semanal_completo()      │
│     → Core/motor_recomendacion.py                           │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  4. Cargar modelos ML (si no están cargados)               │
│     - _cargar_modelo_respuesta_glucemica()                  │
│     - _cargar_modelo_seleccion_alimentos()                  │
│     - _cargar_modelo_optimizacion_combinaciones()           │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  5. Obtener perfil del paciente                            │
│     → obtener_perfil_paciente(paciente_id)                  │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  6. Calcular metas nutricionales                            │
│     → calcular_metas_nutricionales(perfil, configuracion)   │
│     ├─ calcular_metabolismo_basal()                        │
│     ├─ calcular_factor_actividad()                          │
│     ├─ calcular_factor_diabetes()                           │
│     └─ predecir_control_glucemico_ml() [Modelo 1]          │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  7. Obtener ingredientes recomendados                       │
│     → obtener_ingredientes_recomendados(perfil, metas)     │
│     └─ calcular_score_idoneidad_alimento() [Modelo 2]       │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  8. Generar plan semanal                                    │
│     → generar_plan_semanal(perfil, metas, dias)             │
│     └─ _generar_dia_variado() (por cada día)                │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  9. Optimizar plan                                          │
│     → OptimizadorPlan.optimizar_plan()                      │
│     └─ evaluar_combinacion_alimentos() [Modelo 3]          │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  10. Convertir a formato UI                                 │
│      → _convertir_plan_semanal_a_formato_ui()               │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  11. Retornar plan al frontend                              │
│      → JSON con plan completo                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Funciones Clave del Motor de Recomendación

### **1. `generar_plan_semanal_completo()`**

**Ubicación**: `Core/motor_recomendacion.py:2282`  
**Propósito**: Función principal que orquesta todo el proceso

**Parámetros**:
- `paciente_id`: ID del paciente
- `dias`: Número de días del plan (default: 7)
- `configuracion`: Configuración personalizada (calorías, macronutrientes)
- `ingredientes`: Filtros de ingredientes (incluir/excluir)

**Flujo interno**:
```python
1. Cargar modelos ML (lazy loading)
2. Obtener perfil del paciente
3. Calcular metas nutricionales
4. Generar plan semanal
5. Optimizar plan
6. Convertir a formato UI
7. Retornar resultado
```

---

### **2. `obtener_perfil_paciente()`**

**Ubicación**: `Core/motor_recomendacion.py:853`  
**Propósito**: Obtiene y estructura todos los datos del paciente

**Datos obtenidos**:
- Datos personales (edad, sexo, fecha de nacimiento)
- Antropometría (peso, talla, IMC, circunferencia de cintura, % grasa)
- Datos clínicos (HbA1c, glucosa, lípidos, presión arterial)
- Alergias y medicamentos
- Preferencias alimentarias

**Retorna**: Objeto `PerfilPaciente` (dataclass)

---

### **3. `calcular_metas_nutricionales()`**

**Ubicación**: `Core/motor_recomendacion.py:1013`  
**Propósito**: Calcula las metas nutricionales personalizadas

**Sub-funciones llamadas**:

#### **3.1. `calcular_metabolismo_basal()`**
- Calcula TMB usando fórmula de Mifflin-St Jeor
- Considera edad, sexo, peso, talla

#### **3.2. `calcular_factor_actividad()`**
- Baja: 1.2
- Moderada: 1.55
- Alta: 1.725

#### **3.3. `calcular_factor_diabetes()`**
- Ajusta según control glucémico
- HbA1c > 7.0: factor 0.9 (reducción 10%)
- HbA1c 6.5-7.0: factor 0.95 (reducción 5%)
- HbA1c < 6.5: factor 1.0 (sin ajuste)

#### **3.4. `predecir_control_glucemico_ml()` [Modelo 1]**
- Usa Modelo 1 (XGBoost) para predecir probabilidad de mal control
- Ajusta porcentajes de macronutrientes según predicción:
  - Prob > 0.6: Reducir CHO a 35-40%, aumentar PRO
  - Prob 0.4-0.6: Ajuste ligero (CHO 43-45%)
  - Prob < 0.4: Mantener valores base

**Retorna**: Objeto `MetaNutricional` con:
- Calorías diarias
- Carbohidratos (g y %)
- Proteínas (g y %)
- Grasas (g y %)
- Fibra (g)
- Sodio (mg)
- Distribución de CHO por comida

---

### **4. `obtener_ingredientes_recomendados()`**

**Ubicación**: `Core/motor_recomendacion.py:3513`  
**Propósito**: Obtiene lista de ingredientes recomendados para el paciente

**Proceso**:
1. Consulta ingredientes activos de la BD
2. Filtra por alergias del paciente
3. Filtra por preferencias (incluir/excluir)
4. Calcula score de idoneidad usando **Modelo 2**
5. Ordena por score descendente
6. Retorna lista filtrada y ordenada

**Sub-función**: `calcular_score_idoneidad_alimento()` [Modelo 2]
- Usa Modelo 2 (XGBoost Classifier)
- Retorna score 0-1 de idoneidad

---

### **5. `generar_plan_semanal()`**

**Ubicación**: `Core/motor_recomendacion.py:1871`  
**Propósito**: Genera el plan semanal día por día

**Proceso**:
```python
Para cada día (1 a N):
    1. _generar_dia_variado()
       ├─ Para cada comida (des, mm, alm, mt, cena):
       │  ├─ _sugerir_alimentos_tiempo_variado()
       │  ├─ _priorizar_alimentos_por_variedad()
       │  └─ _calcular_cantidades_alimentos()
       └─ Actualizar seguimiento de alimentos usados
    2. Agregar día al plan_semanal
```

**Sistema de variedad**:
- Evita repetir alimentos más de 3 veces por semana
- Para proteínas: máximo 2 veces, mínimo 3 días entre repeticiones
- Prioriza alimentos no usados recientemente

---

### **6. `_generar_dia_variado()`**

**Ubicación**: `Core/motor_recomendacion.py:1939`  
**Propósito**: Genera un día completo con todas las comidas

**Distribución de calorías por comida** (ajustada por ML si está disponible):
- Desayuno: 20-25%
- Media mañana: 10-12%
- Almuerzo: 35-38%
- Media tarde: 10-12%
- Cena: 18-20%

**Para cada comida**:
1. Calcula calorías objetivo según distribución
2. Sugiere alimentos usando `_sugerir_alimentos_tiempo_variado()`
3. Calcula cantidades para cumplir objetivos nutricionales
4. Valida que se cumplan objetivos (tolerancia ±10%)

---

### **7. `_sugerir_alimentos_tiempo_variado()`**

**Ubicación**: `Core/motor_recomendacion.py`  
**Propósito**: Sugiere alimentos para un tiempo de comida específico

**Proceso**:
1. Filtra ingredientes por grupo alimentario según tiempo de comida
2. Aplica reglas de variedad (evitar repeticiones)
3. Prioriza alimentos con mejor score de idoneidad (Modelo 2)
4. Considera restricciones (alergias, preferencias)
5. Retorna lista de alimentos sugeridos con cantidades

---

### **8. `OptimizadorPlan.optimizar_plan()`**

**Ubicación**: `Core/optimizador_plan.py`  
**Propósito**: Optimiza el plan para cumplir objetivos nutricionales exactos

**Proceso**:
```python
Para cada día del plan:
    Para cada comida:
        1. Calcular cumplimiento actual
        2. Si no cumple (tolerancia < 90%):
           a. Identificar deficiencias/excesos
           b. Ajustar cantidades de alimentos
           c. Evaluar combinación con Modelo 3
           d. Aplicar ajuste si mejora el score
        3. Validar que se cumplan objetivos
```

**Sub-función**: `evaluar_combinacion_alimentos()` [Modelo 3]
- Usa Modelo 3 (Ensemble) para evaluar calidad de combinación
- Retorna score 0-1 de calidad

---

### **9. `_convertir_plan_semanal_a_formato_ui()`**

**Ubicación**: `Core/motor_recomendacion.py:2384`  
**Propósito**: Convierte el plan interno al formato esperado por el frontend

**Formato de salida**:
```json
{
  "perfil": {...},
  "metas_nutricionales": {...},
  "plan_completo": {
    "dias": {
      "2025-11-24": {
        "des": {...},
        "mm": {...},
        "alm": {...},
        "mt": {...},
        "cena": {...}
      }
    }
  },
  "validaciones": {...},
  "ingredientes_disponibles": [...]
}
```

---

## 📊 Orden de Ejecución Detallado

### **Paso 1: Inicialización**

```python
# main.py: api_recomendacion_generar()
motor = MotorRecomendacion()
```

### **Paso 2: Carga de Modelos ML (Lazy Loading)**

```python
# motor_recomendacion.py: generar_plan_semanal_completo()
self._cargar_modelo_respuesta_glucemica()      # Modelo 1
self._cargar_modelo_seleccion_alimentos()       # Modelo 2
self._cargar_modelo_optimizacion_combinaciones() # Modelo 3
```

**Nota**: Los modelos se cargan solo si no están ya cargados (singleton pattern)

### **Paso 3: Obtención de Perfil**

```python
perfil = self.obtener_perfil_paciente(paciente_id)
```

**Ejecuta**:
- Consultas SQL a BD (paciente, antropometría, clínico, alergias, medicamentos)
- Cálculo de IMC
- Cálculo de edad
- Estructuración en objeto `PerfilPaciente`

### **Paso 4: Cálculo de Metas Nutricionales**

```python
metas = self.calcular_metas_nutricionales(perfil, configuracion)
```

**Ejecuta en orden**:
1. `calcular_metabolismo_basal(perfil)` → TMB
2. `calcular_factor_actividad(perfil.actividad)` → Factor actividad
3. `calcular_factor_diabetes(perfil)` → Factor diabetes
4. Calcular calorías totales: `TMB × factor_actividad × factor_diabetes`
5. **`predecir_control_glucemico_ml(perfil)`** [Modelo 1]
   - Preparar features del paciente
   - Preprocesar (imputar, escalar)
   - Predecir probabilidad de mal control
6. Ajustar porcentajes de macronutrientes según predicción ML
7. Calcular gramos de cada macronutriente
8. Calcular distribución de CHO por comida
9. Retornar objeto `MetaNutricional`

### **Paso 5: Obtención de Ingredientes**

```python
ingredientes_recomendados = self.obtener_ingredientes_recomendados(perfil, metas)
```

**Ejecuta en orden**:
1. Consulta ingredientes activos de BD
2. Filtra por alergias
3. Filtra por preferencias
4. Para cada ingrediente:
   - **`calcular_score_idoneidad_alimento(perfil, alimento, necesidades)`** [Modelo 2]
     - Preparar features (paciente + alimento)
     - Preprocesar (escalar)
     - Predecir score de idoneidad
5. Ordenar por score descendente
6. Retornar lista filtrada y ordenada

### **Paso 6: Generación del Plan Semanal**

```python
plan_semanal = self.generar_plan_semanal(perfil, metas, dias, configuracion, ingredientes)
```

**Ejecuta para cada día (1 a N)**:

```python
for dia in range(1, dias + 1):
    dia_generado = self._generar_dia_variado(
        grupos_alimentos, dia, metas, configuracion, perfil,
        alimentos_usados=alimentos_usados,
        ...
    )
    
    # Actualizar seguimiento
    for tiempo, comida in dia_generado.items():
        for alimento in comida['alimentos']:
            actualizar_alimentos_usados(alimento, dia)
    
    plan_semanal[f'dia_{dia}'] = dia_generado
```

**Para cada día, `_generar_dia_variado()` ejecuta**:

```python
for tiempo in ['des', 'mm', 'alm', 'mt', 'cena']:
    # 1. Calcular calorías objetivo para esta comida
    calorias_objetivo = distribucion_calorias[tiempo]
    
    # 2. Sugerir alimentos
    alimentos_sugeridos = self._sugerir_alimentos_tiempo_variado(
        tiempo, grupos, dia, perfil, metas,
        alimentos_usados=alimentos_usados,
        ...
    )
    
    # 3. Calcular cantidades
    comida = self._calcular_cantidades_alimentos(
        alimentos_sugeridos, calorias_objetivo, metas, tiempo
    )
    
    # 4. Validar cumplimiento
    if not cumple_objetivos(comida, metas, tiempo):
        ajustar_cantidades(comida)
```

### **Paso 7: Optimización del Plan**

```python
optimizador = OptimizadorPlan(...)
plan_optimizado, estadisticas = optimizador.optimizar_plan(
    plan_semanal, metas_dict, grupos_alimentos, perfil, self
)
```

**Ejecuta para cada día y comida**:
1. Calcular cumplimiento actual de objetivos
2. Si cumplimiento < 90%:
   - Identificar qué falta o sobra (calorías, CHO, PRO, FAT)
   - Ajustar cantidades de alimentos
   - **`evaluar_combinacion_alimentos(perfil, combinacion)`** [Modelo 3]
     - Preparar features agregadas de la combinación
     - Preprocesar
     - Predecir score de calidad
   - Aplicar ajuste si mejora el score
3. Validar que se cumplan objetivos después del ajuste

### **Paso 8: Conversión a Formato UI**

```python
resultado = self._convertir_plan_semanal_a_formato_ui(plan_semanal, perfil, metas)
```

**Ejecuta**:
- Reestructura datos al formato esperado por frontend
- Agrega metadatos (perfil, metas, validaciones)
- Calcula resúmenes y estadísticas

### **Paso 9: Retorno al Frontend**

```python
# main.py: api_recomendacion_generar()
return jsonify(resultado)
```

---

## 🌐 Integración con el Frontend

### **Frontend: `static/js/obtener_plan.js`**

**Función principal**: `generarPlan()`

**Flujo**:
```javascript
1. Obtener datos del paciente seleccionado
2. Obtener configuración (calorías, macronutrientes)
3. Obtener filtros (ingredientes incluir/excluir)
4. POST /api/recomendacion/generar
5. Recibir plan completo
6. Renderizar plan en la interfaz
```

### **Backend: `main.py: api_recomendacion_generar()`**

**Endpoint**: `POST /api/recomendacion/generar`

**Proceso**:
```python
1. Validar datos recibidos
2. Crear instancia de MotorRecomendacion
3. Llamar a generar_plan_semanal_completo()
4. Retornar JSON con plan completo
```

---

## 📝 Resumen del Flujo

### **Orden de Ejecución**

1. ✅ **Inicialización**: Crear instancia de MotorRecomendacion
2. ✅ **Carga ML**: Cargar modelos ML (lazy loading)
3. ✅ **Perfil**: Obtener datos completos del paciente
4. ✅ **Metas**: Calcular metas nutricionales (con Modelo 1)
5. ✅ **Ingredientes**: Obtener ingredientes recomendados (con Modelo 2)
6. ✅ **Generación**: Generar plan día por día
7. ✅ **Optimización**: Optimizar plan (con Modelo 3)
8. ✅ **Conversión**: Convertir a formato UI
9. ✅ **Retorno**: Enviar plan al frontend

### **Modelos ML en el Flujo**

- **Modelo 1**: Se usa en paso 4 (cálculo de metas)
- **Modelo 2**: Se usa en paso 5 (selección de ingredientes)
- **Modelo 3**: Se usa en paso 7 (optimización de combinaciones)

---

## 🎯 Conclusión

El sistema procesa la generación de planes nutricionales en **9 pasos principales**, integrando **3 modelos de Machine Learning** en puntos estratégicos para personalizar y optimizar las recomendaciones. Cada función tiene un propósito específico y se ejecuta en un orden determinado para garantizar la calidad y personalización del plan final.

