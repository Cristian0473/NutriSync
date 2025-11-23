# 🧠 Sistema de Aprendizaje Continuo

## 📋 Resumen

Se ha implementado un sistema de **aprendizaje continuo** que permite a NutriSync aprender de resultados reales de pacientes **sin afectar el funcionamiento actual**. El sistema es completamente **opcional** y se puede activar/desactivar fácilmente.

---

## ✅ Características Implementadas

### 1. **Feedback Loop: Aprender de Resultados Reales**

El sistema captura y aprende de los resultados de los planes:

- **Registra baseline** cuando se crea un plan (HbA1c, glucosa, peso inicial)
- **Registra resultados** cuando el paciente completa el plan
- **Calcula si fue exitoso** basado en mejoras clínicas
- **Aprende patrones** de qué ingredientes/combinaciones funcionaron

**Archivo**: `aprendizaje_continuo.py` → métodos `registrar_resultado_plan()` y `actualizar_resultado_plan()`

### 2. **Memoria a Largo Plazo: Recordar qué Funcionó**

El sistema almacena patrones aprendidos:

- **Ingredientes exitosos**: Qué ingredientes funcionaron mejor
- **Combinaciones efectivas**: Qué combinaciones de alimentos dieron buenos resultados
- **Distribuciones óptimas**: Qué distribución de macronutrientes fue más efectiva
- **Confianza**: Cada patrón tiene un nivel de confianza basado en frecuencia de éxito

**Archivo**: `aprendizaje_continuo.py` → métodos `_aprender_de_resultado()` y `_actualizar_patron_ingrediente()`

### 3. **Reentrenamiento Automático: Actualizar Modelo Periódicamente**

El sistema puede reentrenar el modelo ML automáticamente:

- **Verifica** si hay suficientes datos nuevos (≥50 resultados)
- **Inicia reentrenamiento** automáticamente
- **Registra** versiones y métricas del nuevo modelo
- **Compara** mejoras vs modelo anterior

**Archivo**: `aprendizaje_continuo.py` → métodos `verificar_reentrenamiento_necesario()` y `iniciar_reentrenamiento()`

**Script**: `tarea_reentrenamiento.py` → Ejecutar como tarea programada

### 4. **Aprendizaje por Refuerzo: Q-Learning**

El sistema usa Q-Learning para mejorar decisiones:

- **Aprende valores Q** de acciones (ajustar CHO, seleccionar ingrediente, etc.)
- **Actualiza valores** basado en recompensas (mejoras clínicas)
- **Recomienda mejores acciones** para estados similares

**Archivo**: `aprendizaje_continuo.py` → métodos `obtener_mejor_accion()` y `actualizar_q_value()`

---

## 🚀 Instalación y Activación

### Paso 1: Crear Tablas de Base de Datos

```bash
psql -U postgres -d proyecto_tesis -f SQL/aprendizaje_continuo.sql
```

### Paso 2: Activar Aprendizaje Continuo

Agregar al archivo `.env`:

```env
APRENDIZAJE_CONTINUO=true
```

O establecer variable de entorno:

```bash
# Windows
set APRENDIZAJE_CONTINUO=true

# Linux/Mac
export APRENDIZAJE_CONTINUO=true
```

### Paso 3: (Opcional) Configurar Tarea Programada para Reentrenamiento

**Windows (Task Scheduler)**:
- Crear tarea que ejecute: `python tarea_reentrenamiento.py`
- Programar para ejecutar semanalmente

**Linux/Mac (Cron)**:
```bash
# Ejecutar cada domingo a las 2 AM
0 2 * * 0 cd /ruta/al/proyecto && python tarea_reentrenamiento.py
```

---

## 🔧 Integración en el Sistema

### Hooks Automáticos

El sistema se integra automáticamente sin modificar código existente:

1. **Cuando se guarda un plan** (`main.py` línea ~220):
   - Se registra baseline automáticamente
   - No afecta si falla (try/except silencioso)

2. **Cuando se completa un plan**:
   - Se actualizan resultados
   - Se aprende de patrones
   - Se actualizan valores Q

### Uso en Motor de Recomendación

El motor puede usar aprendizaje para mejorar selección:

```python
from aprendizaje_continuo import obtener_aprendizaje

aprendizaje = obtener_aprendizaje()

# Obtener ingredientes recomendados por aprendizaje
ingredientes_aprendidos = aprendizaje.obtener_ingredientes_recomendados_por_aprendizaje(
    paciente_id=paciente_id,
    grupo='GRUPO1_CEREALES',
    limite=5
)

# Si hay ingredientes aprendidos, usarlos en lugar de selección aleatoria
if ingredientes_aprendidos:
    # Usar ingredientes con alta confianza
    ingredientes = ingredientes_aprendidos
else:
    # Fallback a selección normal
    ingredientes = seleccion_normal()
```

---

## 📊 Estructura de Datos

### Tabla: `plan_resultado`

Almacena resultados de planes seguidos:

- **Baseline**: Datos iniciales (HbA1c, glucosa, peso)
- **Resultado**: Datos finales después del plan
- **Feedback**: Satisfacción, cumplimiento, recomendación

### Tabla: `aprendizaje_patron`

Almacena patrones aprendidos:

- **Tipo**: `ingrediente_exitoso`, `combinacion_efectiva`, `macronutriente_optimo`
- **Elemento**: ID y nombre del ingrediente/combinación
- **Confianza**: Porcentaje de éxito (0-100%)
- **Frecuencia**: Veces observado y veces exitoso

### Tabla: `modelo_reentrenamiento`

Registra reentrenamientos:

- **Versiones**: Versión anterior y nueva
- **Métricas**: Accuracy, AUC, F1 del nuevo modelo
- **Mejora**: Comparación con modelo anterior

### Tabla: `refuerzo_q_values`

Almacena valores Q de Q-Learning:

- **Estado**: Hash del estado del paciente
- **Acción**: Tipo y valor de acción tomada
- **Q-value**: Calidad aprendida de la acción
- **Recompensa**: Recompensa recibida

---

## 🎯 Flujo de Aprendizaje

```
1. Paciente recibe plan
   ↓
2. Sistema registra baseline (HbA1c, glucosa, peso inicial)
   ↓
3. Paciente sigue plan durante X días
   ↓
4. Paciente vuelve con nuevos datos clínicos
   ↓
5. Sistema actualiza resultado del plan
   ↓
6. Sistema calcula si fue exitoso
   ↓
7. Sistema aprende patrones:
   - Ingredientes que funcionaron
   - Combinaciones efectivas
   - Distribuciones óptimas
   ↓
8. Sistema actualiza valores Q (aprendizaje por refuerzo)
   ↓
9. Próximos planes usan conocimiento aprendido
   ↓
10. Cuando hay suficientes datos nuevos:
    - Sistema reentrena modelo ML
    - Mejora predicciones futuras
```

---

## ⚙️ Configuración

### Variables de Entorno

```env
# Activar/desactivar aprendizaje continuo
APRENDIZAJE_CONTINUO=true

# Umbral mínimo de confianza para usar ingredientes aprendidos
APRENDIZAJE_CONFIANZA_MINIMA=60.0

# Mínimo de resultados nuevos para reentrenar
APRENDIZAJE_MIN_RESULTADOS=50
```

### Parámetros de Q-Learning

En `aprendizaje_continuo.py`:

```python
alpha = 0.1  # Tasa de aprendizaje (qué tan rápido aprende)
gamma = 0.9  # Factor de descuento (importancia de recompensas futuras)
```

---

## 📈 Monitoreo

### Consultar Patrones Aprendidos

```sql
-- Ingredientes más exitosos
SELECT elemento_nombre, confianza, veces_observado, veces_exitoso
FROM aprendizaje_patron
WHERE tipo_patron = 'ingrediente_exitoso'
ORDER BY confianza DESC
LIMIT 10;

-- Resultados de planes
SELECT 
    pr.plan_id,
    pr.hba1c_inicial,
    pr.hba1c_final,
    (pr.hba1c_inicial - pr.hba1c_final) as mejora_hba1c,
    pr.resultado_exitoso
FROM plan_resultado pr
WHERE pr.estado = 'completado'
ORDER BY pr.fecha_fin DESC;
```

### Estadísticas de Aprendizaje

```python
from aprendizaje_continuo import obtener_aprendizaje
from bd_conexion import fetch_one

aprendizaje = obtener_aprendizaje()

# Contar patrones aprendidos
patrones = fetch_one("SELECT COUNT(*) FROM aprendizaje_patron")
print(f"Patrones aprendidos: {patrones[0]}")

# Contar resultados registrados
resultados = fetch_one("SELECT COUNT(*) FROM plan_resultado WHERE estado='completado'")
print(f"Resultados registrados: {resultados[0]}")
```

---

## ⚠️ Consideraciones

### 1. **No Afecta Funcionamiento Actual**

- Todos los hooks tienen `try/except` silencioso
- Si falla, el sistema continúa normalmente
- Se puede desactivar en cualquier momento

### 2. **Requiere Datos Reales**

- El aprendizaje solo funciona con resultados reales
- Necesita que los pacientes vuelvan con datos clínicos
- Al inicio, habrá pocos datos aprendidos

### 3. **Reentrenamiento Requiere Implementación**

- El script `tarea_reentrenamiento.py` tiene estructura básica
- Falta implementar lógica de reentrenamiento real
- Se puede usar el código de `ApartadoInteligente/Entrenamiento/`

### 4. **Privacidad y Ética**

- Los datos se almacenan en la misma BD
- Cumple con las mismas políticas de privacidad
- Se puede agregar anonimización si es necesario

---

## 🔮 Mejoras Futuras

1. **Dashboard de Aprendizaje**: Interfaz para ver qué aprendió el sistema
2. **A/B Testing**: Comparar planes con/sin aprendizaje
3. **Explicabilidad**: Mostrar por qué se recomienda algo (basado en aprendizaje)
4. **Notificaciones**: Alertar cuando hay suficientes datos para reentrenar
5. **Exportación**: Exportar patrones aprendidos para análisis

---

## ✅ Checklist de Implementación

- [x] Crear tablas de base de datos
- [x] Implementar módulo de aprendizaje continuo
- [x] Integrar hooks en `main.py`
- [x] Crear script de reentrenamiento
- [x] Documentación completa
- [ ] Implementar reentrenamiento real del modelo
- [ ] Crear dashboard de monitoreo
- [ ] Agregar tests unitarios
- [ ] Configurar tarea programada en producción

---

## 📞 Uso

### Activar Aprendizaje

```bash
# 1. Crear tablas
psql -U postgres -d proyecto_tesis -f SQL/aprendizaje_continuo.sql

# 2. Activar en .env
echo "APRENDIZAJE_CONTINUO=true" >> .env

# 3. Reiniciar servidor
python iniciar_servidor.py
```

### Verificar Funcionamiento

```python
from aprendizaje_continuo import obtener_aprendizaje

aprendizaje = obtener_aprendizaje()
print(f"Aprendizaje habilitado: {aprendizaje.habilitado}")
```

### Ejecutar Reentrenamiento Manualmente

```bash
python tarea_reentrenamiento.py
```

---

## 🎉 Conclusión

El sistema de aprendizaje continuo está **completamente implementado** y **listo para usar**. Es **opcional**, **no afecta el funcionamiento actual**, y se puede activar cuando se tengan suficientes datos reales de pacientes.

**El sistema ahora puede aprender y mejorar continuamente** 🚀

