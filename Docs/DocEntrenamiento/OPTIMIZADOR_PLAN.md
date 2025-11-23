# 🔧 Optimizador de Planes Nutricionales

## 📋 Resumen

Se ha implementado un **optimizador automático** que mejora las recomendaciones nutricionales para cumplir con los objetivos planteados. El optimizador se ejecuta **automáticamente durante la generación del plan**, mientras se muestra la pantalla de carga.

---

## 🎯 ¿Qué hace el optimizador?

### 1. **Analiza el cumplimiento de objetivos**
- Calcula porcentajes de cumplimiento para cada macronutriente (kcal, CHO, PRO, FAT)
- Identifica qué nutrientes están por debajo del objetivo (90% mínimo)

### 2. **Ajusta iterativamente el plan**
- **Aumenta cantidades** de alimentos existentes que aportan el nutriente faltante
- **Agrega nuevos alimentos** del grupo apropiado si es necesario
- **Prioriza ajustes**: Grasas → Proteínas → Carbohidratos → Calorías

### 3. **Optimiza hasta cumplir objetivos**
- Realiza hasta 10 iteraciones de optimización
- Se detiene cuando:
  - Todos los objetivos se cumplen (≥90%)
  - No hay más mejoras posibles
  - Se alcanza el máximo de iteraciones

---

## 🔄 Flujo de Optimización

```
1. Generar plan inicial
   ↓
2. Calcular cumplimiento de objetivos
   ↓
3. ¿Cumple objetivos? (≥90%)
   ├─ SÍ → Terminar ✅
   └─ NO → Continuar
       ↓
4. Identificar déficits (grasas, proteínas, carbohidratos)
   ↓
5. Ajustar comidas principales (almuerzo, cena, desayuno)
   ├─ Aumentar cantidades de alimentos existentes
   └─ Agregar nuevos alimentos si es necesario
   ↓
6. Recalcular cumplimiento
   ↓
7. Repetir hasta cumplir o máximo iteraciones
```

---

## 📊 Ejemplo de Optimización

### Antes de optimizar:
- **Kcal**: 1,609 (89%) ❌
- **CHO**: 212g (94%) ✅
- **PRO**: 91g (112%) ✅
- **FAT**: 49g (77%) ❌ ← **Problema principal**

### Después de optimizar:
- **Kcal**: 1,750 (97%) ✅
- **CHO**: 220g (97%) ✅
- **PRO**: 95g (117%) ✅
- **FAT**: 62g (97%) ✅ ← **Corregido**

---

## ⚙️ Configuración

El optimizador tiene parámetros configurables:

```python
optimizador = OptimizadorPlan(
    umbral_cumplimiento=0.90,  # 90% mínimo de cumplimiento
    max_iteraciones=10          # Máximo 10 iteraciones
)
```

---

## 🔌 Integración

El optimizador está **integrado automáticamente** en el flujo de generación:

1. **Frontend**: Usuario presiona "Generar Plan"
2. **Pantalla de carga**: Muestra "Generando plan nutricional..." → "Optimizando plan..."
3. **Backend**: 
   - Genera plan inicial
   - **Ejecuta optimizador automáticamente**
   - Retorna plan optimizado
4. **Resultado**: Plan que cumple objetivos nutricionales

---

## 📈 Estadísticas de Optimización

El optimizador retorna estadísticas que incluyen:

```python
{
    'iteraciones': 5,              # Iteraciones realizadas
    'dias_optimizados': 7,         # Días que fueron optimizados
    'mejoras_aplicadas': [...],    # Lista de mejoras por día
    'cumplimiento_inicial': {...}, # Cumplimiento antes de optimizar
    'cumplimiento_final': {...}    # Cumplimiento después de optimizar
}
```

---

## ✅ Ventajas

1. **Automático**: No requiere intervención del nutricionista
2. **Inteligente**: Prioriza ajustes según importancia (grasas primero)
3. **Conservador**: Aumenta cantidades máximo 50% para mantener realismo
4. **Eficiente**: Se detiene cuando cumple objetivos
5. **Transparente**: Muestra estadísticas de optimización

---

## ⚠️ Limitaciones

1. **No puede crear alimentos**: Solo ajusta cantidades o agrega de la base de datos
2. **No considera preferencias**: No verifica alergias/preferencias al agregar alimentos
3. **Ajustes lineales**: Aumenta proporcionalmente, no optimiza combinaciones complejas
4. **Máximo 10 iteraciones**: Puede no optimizar completamente planes muy complejos

---

## 🚀 Próximas Mejoras

1. **Validación de preferencias**: Verificar alergias antes de agregar alimentos
2. **Optimización de combinaciones**: Considerar sinergias entre alimentos
3. **Ajustes más inteligentes**: Reducir algunos alimentos si otros aumentan
4. **Optimización multiobjetivo**: Balancear cumplimiento, variedad y adherencia

---

## 📝 Notas Técnicas

- El optimizador maneja correctamente el formato de cantidad como string ("100g")
- Recalcula valores nutricionales proporcionalmente al aumentar cantidades
- Actualiza totales de comidas después de cada ajuste
- Funciona con la estructura de datos existente sin modificaciones mayores

