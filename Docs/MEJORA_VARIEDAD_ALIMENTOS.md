# 🍎 Mejora de Variedad de Alimentos en Planes Nutricionales

## 📋 Problema Identificado

Los planes generados mostraban **poca variedad de alimentos**, repitiendo frecuentemente los mismos alimentos (brócoli, frijoles, pollo, etc.) en diferentes días y entre diferentes pacientes.

### Causas:
1. **No había penalización por repetición** - El algoritmo seleccionaba siempre los alimentos "óptimos" sin considerar si ya se habían usado
2. **Mismo conjunto de alimentos "permitidos"** - Para diabetes tipo 2, el conjunto de alimentos recomendados es limitado
3. **Falta de criterio de variedad** - La función objetivo solo consideraba cumplimiento nutricional, no diversidad

---

## ✅ Solución Implementada

### 1. **Sistema de Seguimiento de Alimentos Usados**

Se agregó un diccionario que rastrea qué alimentos se han usado y en qué días:

```python
alimentos_usados = {
    'Brócoli': [1, 3, 5],  # Usado en días 1, 3 y 5
    'Pollo': [2, 4],
    # ...
}
```

### 2. **Función de Filtrado por Repetición**

Nueva función `_filtrar_alimentos_por_repeticion()` que:
- **Prioriza alimentos no usados** antes que los ya usados
- **Evita alimentos usados recientemente** (menos de X días)
- **Limita repeticiones** a máximo 3 veces por semana
- **Mantiene cumplimiento nutricional** - Si no hay suficientes opciones, permite repetición controlada

### 3. **Parámetros Configurables**

- `max_repeticiones`: Máximo de veces que un alimento puede aparecer en la semana (default: 3)
- `dias_minimos_entre_repeticiones`: Días mínimos entre repeticiones del mismo alimento (default: 2)

### 4. **Integración en Todas las Funciones de Sugerencia**

Se modificaron todas las funciones que sugieren alimentos:
- `_sugerir_desayuno_variado()`
- `_sugerir_merienda_variada()`
- `_sugerir_almuerzo_variado()`
- `_sugerir_cena_variada()`

Cada una ahora filtra alimentos antes de seleccionarlos, evitando repeticiones excesivas.

---

## 🔧 Cambios Técnicos Realizados

### Archivos Modificados:

1. **Core/motor_recomendacion.py**
   - `generar_plan_semanal()`: Agregado seguimiento de alimentos usados
   - `_generar_dia_variado()`: Pasa seguimiento a funciones de sugerencia
   - `_sugerir_alimentos_tiempo_variado()`: Pasa parámetros de repetición
   - `_filtrar_alimentos_por_repeticion()`: **NUEVA** - Filtra por repetición
   - Todas las funciones `_sugerir_*_variado()`: Filtran antes de seleccionar

### Lógica de Filtrado:

```python
def _filtrar_alimentos_por_repeticion(alimentos, alimentos_usados, dia, max_repeticiones, dias_minimos_entre_repeticiones):
    """
    1. Prioriza alimentos NO usados
    2. Si se usó < max_repeticiones Y hace > dias_minimos_entre_repeticiones → OK
    3. Si se usó >= max_repeticiones → Evitar
    4. Si se usó recientemente (< dias_minimos_entre_repeticiones) → Evitar
    5. Si no hay suficientes opciones, permite algunos evitados (fallback)
    """
```

---

## 📊 Resultados Esperados

### Antes:
- Mismo alimento aparecía 5-7 veces en la semana
- Planes de diferentes pacientes muy similares
- Poca variedad visual

### Después:
- Máximo 3 repeticiones por alimento en la semana
- Mínimo 2 días entre repeticiones del mismo alimento
- Mayor variedad entre días y entre pacientes
- **Cumplimiento nutricional mantenido** (si no hay opciones, permite repetición controlada)

---

## ⚙️ Configuración

Los parámetros se pueden ajustar en `generar_plan_semanal()`:

```python
max_repeticiones_semana = 3  # Cambiar a 2 para más variedad, 4 para menos
dias_minimos_entre_repeticiones = 2  # Cambiar a 3 para más separación

# Para proteínas (reglas más estrictas):
max_repeticiones_proteinas = 2  # Máximo 2 veces por semana
dias_minimos_entre_proteinas = 3  # Mínimo 3 días entre repeticiones
```

### Reglas Especiales para Proteínas

Las proteínas tienen reglas **más estrictas** que otros alimentos:
- **Máximo 2 repeticiones por semana** (vs 3 para otros alimentos)
- **Mínimo 3 días entre repeticiones** (vs 2 para otros alimentos)
- **Prohibición absoluta de días consecutivos**: Si una proteína se usó en el día anterior, NO se puede usar en el día actual
- **Detección de días consecutivos en historial**: Si una proteína ya se usó en días consecutivos anteriormente, se prohíbe su uso

Esto asegura que no haya repeticiones como "carne de res 4 días seguidos", que no es saludable ni variado.

---

## 🎯 Beneficios

1. **Mayor adherencia**: Los pacientes no se cansan de ver siempre los mismos alimentos
2. **Mejor experiencia**: Planes más interesantes y variados
3. **Personalización visual**: Aunque los macros sean similares, los alimentos cambian
4. **Cumplimiento mantenido**: Si no hay opciones, el sistema permite repetición controlada

---

## ⚠️ Notas Importantes

1. **Cumplimiento nutricional tiene prioridad**: Si no hay suficientes alimentos alternativos, se permite repetición para mantener las metas nutricionales

2. **Grupos de alimentos limitados**: Para diabetes tipo 2, el conjunto de alimentos recomendados es naturalmente limitado (legumbres, verduras, cereales integrales, etc.)

3. **Balance entre variedad y cumplimiento**: El sistema busca el equilibrio - más variedad sin romper las metas nutricionales

---

## 🧪 Próximos Pasos (Opcional)

1. **Agregar preferencias del paciente**: Permitir que el paciente indique alimentos que no le gustan
2. **Perfiles de alimentación**: Estilos (mediterráneo, andino, vegetariano) para mayor diferenciación
3. **Variedad por grupo**: Asegurar que cada grupo de alimentos tenga rotación (no solo evitar repeticiones del mismo alimento)

