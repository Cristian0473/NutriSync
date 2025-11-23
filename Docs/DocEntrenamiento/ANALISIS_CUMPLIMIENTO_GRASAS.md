# Análisis de Cumplimiento de Metas Nutricionales - Plan #42

## 📋 Resumen Ejecutivo

Este documento analiza el cumplimiento de las metas nutricionales del Plan #42 generado para la paciente **María Delgado Torres**, con especial énfasis en el problema identificado: **las grasas están consistentemente por debajo del objetivo**.

---

## 🎯 Metas Nutricionales Objetivo

### Configuración del Sistema

- **Calorías diarias objetivo:** 1,811 kcal
- **Carbohidratos:** 226g (50% = 904 kcal)
- **Proteínas:** 81g (18% = 324 kcal)
- **Grasas:** 64g (32% = 576 kcal)
- **Fibra:** 27g

**Verificación de calorías:**
- CHO: 226g × 4 kcal/g = 904 kcal
- PRO: 81g × 4 kcal/g = 324 kcal
- FAT: 64g × 9 kcal/g = 576 kcal
- **Total:** 904 + 324 + 576 = **1,804 kcal** ✓ (diferencia de 7 kcal por redondeo)

---

## 📊 Análisis del Cumplimiento Real

### Día 1 (2025-11-21)

**Metas:**
- Kcal: 1,811 | CHO: 226g | PRO: 81g | FAT: 64g

**Resultado:**
- Kcal: 1,609 (89%) | CHO: 212g (94%) | PRO: 91g (100%) | FAT: 49g (77%)

**Análisis de Grasas:**
- **Objetivo:** 64g
- **Obtenido:** 49g
- **Déficit:** 15g (23% por debajo del objetivo)
- **Porcentaje de cumplimiento:** 77%

**Alimentos del Día 1 según el log:**
1. Amaranto - 80.8g
2. Leche entera - 109.4g
3. Pera - 104.0g
4. Aceitunas negras - 27.3g
5. Queso fresco - 83.3g
6. Carne de res - 69.2g
7. Centeno - 102.0g
8. Zanahoria - 155.0g
9. Pistachos - 17.8g
10. Queso fresco - 83.3g
11. Muslo de pollo - 46.2g
12. Brócoli - 157.1g
13. Macadamias - 7.9g
14. Quinoa - 39.1g

**Cálculo de Grasas del Día 1:**

Usando los valores nutricionales de la base de datos (por 100g):

| Alimento | Cantidad (g) | Grasas por 100g | Grasas Totales |
|----------|--------------|-----------------|----------------|
| Amaranto | 80.8 | 7 | 5.66 |
| Leche entera | 109.4 | 3.2 | 3.50 |
| Pera | 104.0 | 0.1 | 0.10 |
| Aceitunas negras | 27.3 | 11 | 3.00 |
| Queso fresco | 83.3 | 1.2 | 1.00 |
| Carne de res | 69.2 | 15 | 10.38 |
| Centeno | 102.0 | 2 | 2.04 |
| Zanahoria | 155.0 | 0.2 | 0.31 |
| Pistachos | 17.8 | 45 | 8.01 |
| Queso fresco | 83.3 | 1.2 | 1.00 |
| Muslo de pollo | 46.2 | 12 | 5.54 |
| Brócoli | 157.1 | 0.4 | 0.63 |
| Macadamias | 7.9 | 76 | 6.00 |
| Quinoa | 39.1 | 6 | 2.35 |

**Total de grasas calculado:** 5.66 + 3.50 + 0.10 + 3.00 + 1.00 + 10.38 + 2.04 + 0.31 + 8.01 + 1.00 + 5.54 + 0.63 + 6.00 + 2.35 = **49.52g**

**Conclusión Día 1:**
- ✅ El cálculo es correcto: 49g de grasas
- ❌ **Falta 15g de grasas** para cumplir el objetivo de 64g
- **Problema:** Solo se están asignando ~77% de las grasas necesarias

---

## 🔍 Análisis del Problema: Por qué las Grasas Están Bajas

### 1. Cálculo de Porciones Diarias de Grasas

El sistema calcula las porciones diarias de grasas en `calcular_porciones_por_grupo()`:

```python
# Línea 804-820 de motor_recomendacion.py
# GRUPO7_GRASAS: basado en FAT
fat_cereales = porciones.get('GRUPO1_CEREALES', 0) * estandares_dict.get('GRUPO1_CEREALES', {}).get('fat', 1)
fat_frutas = porciones.get('GRUPO3_FRUTAS', 0) * estandares_dict.get('GRUPO3_FRUTAS', {}).get('fat', 1)
fat_lacteos = porciones.get('GRUPO4_LACTEOS', 0) * estandares_dict.get('GRUPO4_LACTEOS_bajos_grasa', {}).get('fat', 1)
fat_carnes = porciones.get('GRUPO5_CARNES', 0) * estandares_dict.get('GRUPO5_CARNES_bajas_grasa', {}).get('fat', 1)
fat_asignado = fat_cereales + fat_frutas + fat_lacteos + fat_carnes
fat_restante = max(0, grasas_g - fat_asignado)
porciones_grasas = fat_restante / est['fat'] if est['fat'] > 0 else 0
porciones_grasas *= 1.5  # Factor de compensación
porciones['GRUPO7_GRASAS'] = max(4.0, min(7.0, round(porciones_grasas, 1)))
```

**Problema identificado:**
- El cálculo asume que las carnes y lácteos son "bajas en grasa" (1g de grasa por porción)
- Pero en el plan real se usan carnes con más grasa (carne de res: 15g/100g, muslo de pollo: 12g/100g)
- Esto hace que `fat_asignado` se subestime, y por tanto `fat_restante` se sobrestime
- Sin embargo, el límite máximo de 7.0 porciones puede estar cortando las porciones necesarias

### 2. Distribución de Grasas por Comida

El sistema distribuye las grasas usando `_calcular_porciones_para_comida()`:

```python
# Línea 944-970 de motor_recomendacion.py
distribucion_grupos_por_comida = {
    'des': {
        'GRUPO7_GRASAS': 0.15  # 15% de las calorías del desayuno
    },
    'alm': {
        'GRUPO7_GRASAS': 0.25  # 25% de las calorías del almuerzo
    },
    'cena': {
        'GRUPO7_GRASAS': 0.25  # 25% de las calorías de la cena
    }
}
```

**Cálculo para Día 1:**

**Desayuno (25% de 1,811 = 453 kcal objetivo):**
- Grasas objetivo: 453 × 0.15 = 68 kcal de grasas = 7.6g de grasas
- Con aceites (90 kcal/porción, 10g grasa/porción): 7.6g / 10g = 0.76 porciones
- **Pero el código usa valor por defecto:** 0.3 porciones (línea 1800)
- **Grasas obtenidas:** 0.3 × 10g = 3g (solo 39% de lo necesario)

**Almuerzo (35% de 1,811 = 634 kcal objetivo):**
- Grasas objetivo: 634 × 0.25 = 158 kcal de grasas = 17.6g de grasas
- Con aceites: 17.6g / 10g = 1.76 porciones
- **Valor por defecto usado:** 0.8 porciones (línea 1957)
- **Grasas obtenidas:** 0.8 × 10g = 8g (solo 45% de lo necesario)

**Cena (20% de 1,811 = 362 kcal objetivo):**
- Grasas objetivo: 362 × 0.25 = 90 kcal de grasas = 10g de grasas
- Con aceites: 10g / 10g = 1.0 porción
- **Valor por defecto usado:** 0.6 porciones (línea 2036)
- **Grasas obtenidas:** 0.6 × 10g = 6g (solo 60% de lo necesario)

**Total de grasas del GRUPO7_GRASAS:** 3 + 8 + 6 = 17g

**Grasas de otros grupos (estimado):**
- Carnes: ~15g (carne de res + muslo de pollo)
- Lácteos: ~4g (leche entera + queso fresco)
- Cereales: ~2g (centeno, quinoa, amaranto)
- Frutas: ~0.1g (pera)
- Oleaginosas: ~14g (pistachos + macadamias)

**Total estimado:** 17 + 15 + 4 + 2 + 0.1 + 14 = **52.1g** ✓ (cercano a los 49g reportados)

---

## 🐛 Problema Raíz Identificado

### Problema 1: Valores por Defecto Insuficientes

Las funciones `_sugerir_desayuno_variado()`, `_sugerir_almuerzo_variado()` y `_sugerir_cena_variada()` usan valores por defecto para las porciones de grasas:

- **Desayuno:** 0.3 porciones (línea 1800) → 3g de grasas
- **Almuerzo:** 0.8 porciones (línea 1957) → 8g de grasas  
- **Cena:** 0.6 porciones (línea 2036) → 6g de grasas

**Total:** 17g de grasas del GRUPO7_GRASAS

Estos valores **NO** están usando las porciones calculadas por `_calcular_porciones_para_comida()`, que sí calcula correctamente las necesidades.

### Problema 2: Límite Máximo de Porciones

El límite máximo de 7.0 porciones diarias (línea 820) puede ser insuficiente para algunos casos:

- Si se necesitan 6.4 porciones diarias (64g / 10g por porción)
- Y se distribuyen en 3 comidas: desayuno (1.5) + almuerzo (2.5) + cena (2.4) = 6.4 porciones
- Pero con los valores por defecto: 0.3 + 0.8 + 0.6 = 1.7 porciones (solo 27% de lo necesario)

### Problema 3: No se Usan las Porciones Calculadas

El código calcula correctamente las porciones en `_calcular_porciones_para_comida()`, pero luego las funciones de sugerencia usan valores por defecto en lugar de usar `porciones_comida.get('GRUPO7_GRASAS', valor_por_defecto)`.

---

## ✅ Solución Propuesta

### 1. Usar las Porciones Calculadas

Modificar las funciones de sugerencia para usar las porciones calculadas:

```python
# En lugar de:
porciones_grasa = porciones_comida.get('GRUPO7_GRASAS', 0.3)

# Debería ser:
porciones_grasa = porciones_comida.get('GRUPO7_GRASAS', 0)
if porciones_grasa == 0:
    # Solo usar valor por defecto si no se calculó nada
    porciones_grasa = 0.3
```

### 2. Aumentar los Valores por Defecto

Si no se pueden usar las porciones calculadas, aumentar los valores por defecto:

- **Desayuno:** 0.3 → 0.8 porciones (8g)
- **Almuerzo:** 0.8 → 1.5 porciones (15g)
- **Cena:** 0.6 → 1.2 porciones (12g)

**Total:** 35g de grasas del GRUPO7_GRASAS (vs 17g actual)

### 3. Aumentar el Límite Máximo

Aumentar el límite máximo de 7.0 a 10.0 porciones diarias para permitir más flexibilidad.

---

## 📈 Demostración: Cálculo Correcto para Día 1

### Metas del Día 1:
- **Grasas objetivo:** 64g
- **Grasas de otros grupos (estimado):** 35g
- **Grasas necesarias del GRUPO7_GRASAS:** 64 - 35 = 29g
- **Porciones necesarias (aceites):** 29g / 10g = 2.9 porciones

### Distribución Ideal:
- **Desayuno:** 0.8 porciones (8g) = 25% de 2.9
- **Almuerzo:** 1.5 porciones (15g) = 52% de 2.9
- **Cena:** 0.6 porciones (6g) = 21% de 2.9

**Total:** 2.9 porciones = 29g ✓

### Con los Valores Actuales:
- **Desayuno:** 0.3 porciones (3g)
- **Almuerzo:** 0.8 porciones (8g)
- **Cena:** 0.6 porciones (6g)

**Total:** 1.7 porciones = 17g ❌ (falta 12g)

---

## 🎯 Conclusión

El sistema **NO está cumpliendo** las metas de grasas porque:

1. ❌ Usa valores por defecto insuficientes en lugar de las porciones calculadas
2. ❌ Los valores por defecto suman solo 17g cuando se necesitan ~29g del GRUPO7_GRASAS
3. ❌ El límite máximo de 7.0 porciones puede ser restrictivo en algunos casos

**Recomendación:** Modificar el código para usar las porciones calculadas por `_calcular_porciones_para_comida()` en lugar de valores por defecto, o aumentar significativamente los valores por defecto.

---

## 📝 Notas Técnicas

- Los cálculos de conversión de porciones a gramos están correctos
- Los valores nutricionales de los ingredientes parecen correctos
- El problema está en la **distribución** de las porciones de grasas, no en los cálculos base
- Las grasas de otros grupos (carnes, lácteos) se están contabilizando correctamente

---

---

## 🔬 Análisis Detallado: Por qué los Valores por Defecto son Insuficientes

### Cálculo Teórico de Porciones de Grasas para Día 1

**Metas diarias:**
- Calorías: 1,811 kcal
- Grasas: 64g

**Distribución de calorías por comida:**
- Desayuno: 1,811 × 0.25 = 453 kcal
- Almuerzo: 1,811 × 0.35 = 634 kcal
- Cena: 1,811 × 0.20 = 362 kcal

**Distribución de grasas por comida (según código línea 944-970):**
- Desayuno: 15% de las calorías = 453 × 0.15 = 68 kcal = 7.6g de grasas
- Almuerzo: 25% de las calorías = 634 × 0.25 = 158 kcal = 17.6g de grasas
- Cena: 25% de las calorías = 362 × 0.25 = 90 kcal = 10.0g de grasas

**Porciones necesarias (usando aceites: 10g grasa/porción):**
- Desayuno: 7.6g / 10g = **0.76 porciones**
- Almuerzo: 17.6g / 10g = **1.76 porciones**
- Cena: 10.0g / 10g = **1.00 porción**

**Total:** 0.76 + 1.76 + 1.00 = **3.52 porciones** del GRUPO7_GRASAS

**Pero el código usa valores por defecto:**
- Desayuno: 0.3 porciones (39% de lo necesario)
- Almuerzo: 0.8 porciones (45% de lo necesario)
- Cena: 0.6 porciones (60% de lo necesario)

**Total:** 0.3 + 0.8 + 0.6 = **1.7 porciones** (solo 48% de lo necesario)

**Grasas obtenidas del GRUPO7_GRASAS:** 1.7 × 10g = **17g**

**Grasas de otros grupos (estimado):**
- Carnes: ~15g
- Lácteos: ~4g
- Cereales: ~2g
- Frutas: ~0.1g
- Oleaginosas (incluidas en GRUPO7): ~14g

**Total estimado:** 17 + 15 + 4 + 2 + 0.1 = **38.1g** (sin contar oleaginosas que ya están en GRUPO7)

**Problema:** Las oleaginosas (pistachos, macadamias) están en GRUPO7_GRASAS, pero se están usando como si fueran aceites puros. Las oleaginosas tienen 10g de grasa por porción, pero también aportan CHO y PRO.

---

## 💡 Solución Propuesta: Aumentar Valores por Defecto

### Opción 1: Aumentar Valores por Defecto (Solución Rápida)

Modificar los valores por defecto en las funciones de sugerencia:

```python
# Desayuno (línea 1800)
porciones_grasa = porciones_comida.get('GRUPO7_GRASAS', 0.8)  # Aumentar de 0.3 a 0.8

# Almuerzo (línea 1957)
porciones_grasa = porciones_comida.get('GRUPO7_GRASAS', 1.5)  # Aumentar de 0.8 a 1.5

# Cena (línea 2036)
porciones_grasa = porciones_comida.get('GRUPO7_GRASAS', 1.2)  # Aumentar de 0.6 a 1.2
```

**Total:** 0.8 + 1.5 + 1.2 = **3.5 porciones** = 35g de grasas del GRUPO7_GRASAS

Con grasas de otros grupos (~21g), el total sería: **56g** (87% del objetivo)

### Opción 2: Usar Solo las Porciones Calculadas (Solución Ideal)

Modificar para que siempre use las porciones calculadas, sin valores por defecto:

```python
# En lugar de:
porciones_grasa = porciones_comida.get('GRUPO7_GRASAS', 0.3)

# Usar:
porciones_grasa = porciones_comida.get('GRUPO7_GRASAS', 0)
if porciones_grasa == 0 and metas:
    # Recalcular si no se obtuvo valor
    porciones_comida = self._calcular_porciones_para_comida(tiempo, metas, perfil)
    porciones_grasa = porciones_comida.get('GRUPO7_GRASAS', 0)
```

---

## 📊 Verificación: Cálculo Real vs. Objetivo

### Día 1 - Desglose Completo

**Alimentos con grasas del Día 1:**

| Alimento | Cantidad | Grasas/100g | Grasas Totales |
|----------|----------|-------------|----------------|
| **GRUPO7_GRASAS (Aceites/Oleaginosas):** |
| Aceitunas negras | 27.3g | 11 | 3.00 |
| Pistachos | 17.8g | 45 | 8.01 |
| Macadamias | 7.9g | 76 | 6.00 |
| **Subtotal GRUPO7:** | | | **17.01g** |
| **GRUPO5_CARNES:** |
| Carne de res | 69.2g | 15 | 10.38 |
| Muslo de pollo | 46.2g | 12 | 5.54 |
| **Subtotal CARNES:** | | | **15.92g** |
| **GRUPO4_LACTEOS:** |
| Leche entera | 109.4g | 3.2 | 3.50 |
| Queso fresco | 166.6g (83.3×2) | 1.2 | 2.00 |
| **Subtotal LACTEOS:** | | | **5.50g** |
| **GRUPO1_CEREALES:** |
| Amaranto | 80.8g | 7 | 5.66 |
| Centeno | 102.0g | 2 | 2.04 |
| Quinoa | 39.1g | 6 | 2.35 |
| **Subtotal CEREALES:** | | | **10.05g** |
| **GRUPO3_FRUTAS:** |
| Pera | 104.0g | 0.1 | 0.10 |
| **Subtotal FRUTAS:** | | | **0.10g** |
| **GRUPO2_VERDURAS:** |
| Zanahoria | 155.0g | 0.2 | 0.31 |
| Brócoli | 157.1g | 0.4 | 0.63 |
| **Subtotal VERDURAS:** | | | **0.94g** |
| **TOTAL GRASAS:** | | | **49.52g** |

**Conclusión:**
- ✅ El cálculo es correcto: **49.52g ≈ 49g** reportado
- ❌ **Falta 15g** para cumplir el objetivo de 64g
- **Problema:** El GRUPO7_GRASAS solo aporta 17g cuando debería aportar ~29g

---

## 🎯 Recomendación Final

**Problema identificado:** Los valores por defecto para las porciones de grasas son insuficientes.

**Solución inmediata:** Aumentar los valores por defecto:
- Desayuno: 0.3 → **0.8 porciones** (8g)
- Almuerzo: 0.8 → **1.5 porciones** (15g)
- Cena: 0.6 → **1.2 porciones** (12g)

**Solución ideal:** Modificar el código para que siempre use las porciones calculadas por `_calcular_porciones_para_comida()`, que sí calcula correctamente las necesidades.

---

**Fecha de análisis:** 2025-11-20  
**Plan analizado:** Plan #42 - María Delgado Torres  
**Período:** 2025-11-21 a 2025-12-04  
**Versión del código analizado:** motor_recomendacion.py (líneas 1715-2045)

