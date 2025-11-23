# Estado Actual de Algoritmos en el Sistema

## 📊 Resumen Ejecutivo

**Estado actual**: El sistema usa **100% algoritmos basados en reglas (rule-based)**, sin Machine Learning integrado.

**Modelos ML entrenados**: Se entrenaron 3 modelos ML pero **NO están integrados** en el motor de recomendación.

---

## 🔧 Algoritmos Actualmente en Uso (Motor de Recomendación)

### 1. **Cálculo de Metabolismo Basal (TMB)**
- **Algoritmo**: Ecuación de **Mifflin-St Jeor**
- **Tipo**: Fórmula matemática basada en reglas
- **Implementación**: `calcular_metabolismo_basal()`
- **Fórmula**:
  - Hombres: `TMB = (10 × peso) + (6.25 × talla) - (5 × edad) + 5`
  - Mujeres: `TMB = (10 × peso) + (6.25 × talla) - (5 × edad) - 161`

### 2. **Factor de Actividad Física**
- **Algoritmo**: Multiplicadores estándar
- **Tipo**: Reglas condicionales
- **Implementación**: `calcular_factor_actividad()`
- **Valores**:
  - Sedentario: 1.2
  - Moderado: 1.4
  - Alto: 1.6

### 3. **Factor de Ajuste para Diabetes**
- **Algoritmo**: Reglas condicionales basadas en umbrales clínicos
- **Tipo**: Sistema experto (if-then rules)
- **Implementación**: `calcular_factor_diabetes()`
- **Reglas**:
  - Si HbA1c > 8.0: reducir calorías 10%
  - Si HbA1c < 6.5: aumentar calorías 5%
  - Si glucosa > 140: reducir calorías 5%
  - Si IMC > 30: reducir calorías 10%
  - Si IMC < 18.5: aumentar calorías 10%

### 4. **Distribución de Macronutrientes**
- **Algoritmo**: Porcentajes fijos para diabetes tipo 2
- **Tipo**: Reglas basadas en guías clínicas
- **Implementación**: `calcular_metas_nutricionales()`
- **Valores**:
  - Carbohidratos: 45-60% (por defecto 45%)
  - Proteínas: 15-20% (por defecto 15%)
  - Grasas: 25-35% (por defecto 40%)

### 5. **Distribución Calórica por Comida**
- **Algoritmo**: Porcentajes fijos
- **Tipo**: Reglas predefinidas
- **Implementación**: `_generar_dia_completo()`
- **Valores**:
  - Desayuno: 25%
  - Media mañana: 10%
  - Almuerzo: 35%
  - Media tarde: 10%
  - Cena: 20%

### 6. **Algoritmo de Variedad Semanal**
- **Algoritmo**: Rotación cíclica basada en módulo matemático
- **Tipo**: Algoritmo determinístico
- **Implementación**: `_sugerir_*_variado()`
- **Método**:
  - Factor de variedad: `(edad % 7) + (peso % 5) + (día % 3)`
  - Selección de ingredientes: `índice = factor_variedad % len(grupo)`
  - Rotación por día para evitar repeticiones

### 7. **Filtrado de Ingredientes**
- **Algoritmo**: Consultas SQL con condiciones múltiples
- **Tipo**: Filtrado basado en reglas
- **Implementación**: `obtener_ingredientes_recomendados()`
- **Filtros**:
  - Índice glucémico ≤ umbral
  - Exclusión de alergias
  - Exclusión de preferencias
  - Exclusión de grupos alimentarios

### 8. **Agrupación de Ingredientes**
- **Algoritmo**: Clasificación por categorías predefinidas
- **Tipo**: Reglas de categorización
- **Implementación**: `_agrupar_ingredientes()`
- **Grupos**: 7 categorías (CEREALES, VERDURAS, FRUTAS, LACTEOS, CARNES, AZUCARES, GRASAS)

---

## 🤖 Modelos de Machine Learning Entrenados (NO en Uso)

### 1. **Logistic Regression**
- **Estado**: ✅ Entrenado y guardado
- **Ubicación**: `ApartadoInteligente/Entrenamiento/ModeloEntrenamiento/`
- **Métricas**:
  - AUC-ROC: 0.744
  - F1-Score: 0.263
  - Accuracy: 0.224
- **Uso**: ❌ NO integrado en el motor

### 2. **Random Forest**
- **Estado**: ✅ Entrenado y guardado
- **Ubicación**: `ApartadoInteligente/Entrenamiento/ModeloEntrenamiento/`
- **Métricas**:
  - AUC-ROC: 0.687
  - F1-Score: 0.303
  - Accuracy: 0.381
- **Uso**: ❌ NO integrado en el motor

### 3. **XGBoost** (Mejor modelo)
- **Estado**: ✅ Entrenado y guardado
- **Ubicación**: `ApartadoInteligente/Entrenamiento/ModeloEntrenamiento/`
- **Métricas**:
  - AUC-ROC: 0.817 ✅
  - F1-Score: 0.456
  - Accuracy: 0.768
  - Recall: 0.662 ✅
- **Uso**: ❌ NO integrado en el motor

---

## 📋 Comparación: Sistema Actual vs Sistema con ML

| Aspecto | Sistema Actual (Rule-Based) | Sistema con ML (Planeado) |
|---------|----------------------------|---------------------------|
| **Tipo de algoritmo** | Reglas y fórmulas matemáticas | Modelos ML entrenados con datos reales |
| **Personalización** | Basada en umbrales fijos | Basada en patrones aprendidos |
| **Adaptabilidad** | Estática (no aprende) | Dinámica (aprende de datos) |
| **Precisión** | Buena para casos estándar | Mejor para casos complejos |
| **Interpretabilidad** | Alta (reglas claras) | Media (requiere SHAP/LIME) |
| **Datos necesarios** | Datos clínicos básicos | Dataset de entrenamiento |
| **Estado** | ✅ Implementado y funcionando | ⚠️ Modelos entrenados pero no integrados |

---

## 🎯 Próximos Pasos para Integración de ML

### 1. **Cargar Modelo XGBoost**
- Cargar modelo entrenado desde `.pkl`
- Cargar preprocesadores (imputer, scaler, encoder)

### 2. **Integrar Predicción en Motor**
- Agregar función `predecir_control_glucemico()` en `MotorRecomendacion`
- Usar predicción para ajustar metas nutricionales

### 3. **Ajustar Metas según Predicción**
- Si `control_glucemico = 1` (mal control): reducir CHO, aumentar fibra
- Si `control_glucemico = 0` (buen control): mantener o ajustar ligeramente

### 4. **Validar con Datos Reales**
- Probar con pacientes del hospital
- Comparar resultados con sistema actual
- Ajustar según feedback

---

## 📊 Conclusión

**Estado actual**:
- ✅ Sistema funcional con algoritmos basados en reglas
- ✅ Modelos ML entrenados y guardados
- ❌ Modelos ML NO integrados en el motor

**Recomendación**:
- Integrar modelo XGBoost para mejorar personalización
- Mantener sistema rule-based como fallback
- Implementar sistema híbrido (reglas + ML)

