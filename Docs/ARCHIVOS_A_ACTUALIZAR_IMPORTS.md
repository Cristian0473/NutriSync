# Archivos que Necesitan Actualización de Imports

## 📊 Resumen

**Total de archivos a actualizar: 8 archivos Python**

No es tanto como parece. La mayoría de los imports están concentrados en pocos archivos.

---

## 📝 Lista de Archivos a Actualizar

### 1. **main.py** (4 imports + 2 dentro de funciones)
```python
# Línea 21-24 (al inicio del archivo)
from bd_conexion import fetch_one, fetch_all, execute
from motor_recomendacion import MotorRecomendacion
from motor_recomendacion_basico import MotorRecomendacionBasico
from envio_email import enviar_token_activacion

# Línea 232 (dentro de función)
from integracion_aprendizaje import hook_plan_guardado

# Línea 1239 (dentro de función)
from motor_recomendacion import MotorRecomendacion

# Línea 4948 (dentro de función)
from motor_recomendacion import MotorRecomendacion
```

**Cambios necesarios:**
```python
# Cambiar a:
from core.bd_conexion import fetch_one, fetch_all, execute
from core.motor_recomendacion import MotorRecomendacion
from core.motor_recomendacion_basico import MotorRecomendacionBasico
from utils.envio_email import enviar_token_activacion
from aprendizaje.integracion_aprendizaje import hook_plan_guardado
```

---

### 2. **motor_recomendacion.py** (1 import + 1 dentro de función)
```python
# Línea 26 (al inicio)
from bd_conexion import fetch_one, fetch_all, execute

# Línea 2199 (dentro de función)
from optimizador_plan import OptimizadorPlan
```

**Cambios necesarios:**
```python
# Cambiar a:
from core.bd_conexion import fetch_one, fetch_all, execute
from core.optimizador_plan import OptimizadorPlan
```

---

### 3. **iniciar_servidor.py** (2 imports)
```python
# Línea 28-29
from motor_recomendacion_basico import MotorRecomendacionBasico
from bd_conexion import fetch_one
```

**Cambios necesarios:**
```python
# Cambiar a:
from core.motor_recomendacion_basico import MotorRecomendacionBasico
from core.bd_conexion import fetch_one
```

---

### 4. **aprendizaje_continuo.py** (1 import)
```python
# Línea 13
from bd_conexion import fetch_one, fetch_all, execute
```

**Cambios necesarios:**
```python
# Cambiar a:
from core.bd_conexion import fetch_one, fetch_all, execute
```

---

### 5. **integracion_aprendizaje.py** (2 imports)
```python
# Línea 5-7
from aprendizaje_continuo import obtener_aprendizaje
from bd_conexion import fetch_one
```

**Cambios necesarios:**
```python
# Cambiar a:
from aprendizaje.aprendizaje_continuo import obtener_aprendizaje
from core.bd_conexion import fetch_one
```

---

### 6. **verificar_aprendizaje.py** (2 imports)
```python
# Línea 11-12
from bd_conexion import fetch_one, fetch_all
from aprendizaje_continuo import obtener_aprendizaje
```

**Cambios necesarios:**
```python
# Cambiar a:
from core.bd_conexion import fetch_one, fetch_all
from aprendizaje.aprendizaje_continuo import obtener_aprendizaje
```

---

### 7. **tarea_reentrenamiento.py** (2 imports)
```python
# Línea 14-15
from aprendizaje_continuo import obtener_aprendizaje
from bd_conexion import fetch_one, fetch_all, execute
```

**Cambios necesarios:**
```python
# Cambiar a:
from aprendizaje.aprendizaje_continuo import obtener_aprendizaje
from core.bd_conexion import fetch_one, fetch_all, execute
```

---

### 8. **user.py** (1 import)
```python
# Línea 2
from bd_conexion import execute, fetch_one
```

**Cambios necesarios:**
```python
# Cambiar a:
from core.bd_conexion import execute, fetch_one
```

---

## 📋 Mapa de Cambios por Módulo

### Módulos que se mueven a `core/`:
- `bd_conexion` → `core.bd_conexion` (usado en 7 archivos)
- `motor_recomendacion` → `core.motor_recomendacion` (usado en 2 archivos)
- `motor_recomendacion_basico` → `core.motor_recomendacion_basico` (usado en 2 archivos)
- `optimizador_plan` → `core.optimizador_plan` (usado en 1 archivo)
- `user` → `core.user` (no tiene imports de otros módulos locales)

### Módulos que se mueven a `utils/`:
- `envio_email` → `utils.envio_email` (usado en 1 archivo)

### Módulos que se mueven a `aprendizaje/`:
- `aprendizaje_continuo` → `aprendizaje.aprendizaje_continuo` (usado en 3 archivos)
- `integracion_aprendizaje` → `aprendizaje.integracion_aprendizaje` (usado en 1 archivo)

---

## ⚠️ Consideraciones Importantes

### 1. **Imports dentro de funciones**
Algunos imports están dentro de funciones (como en `main.py` líneas 1239 y 4948). Estos también deben actualizarse.

### 2. **Archivos que NO necesitan cambios**
Los archivos de ML (`entrenar_modelo*.py`, `preparar_datos*.py`) y procesamiento de datos (`procesar_*.py`, `explorar_*.py`) **NO importan** estos módulos, así que no necesitan cambios.

### 3. **Archivos de templates y static**
Los archivos HTML, CSS y JS **NO necesitan cambios** porque no tienen imports de Python.

---

## ✅ Estrategia Recomendada

1. **Mover los archivos primero** a sus nuevas carpetas
2. **Actualizar imports uno por uno** empezando por los más simples
3. **Probar después de cada cambio** para asegurar que funciona
4. **Usar búsqueda y reemplazo** para cambios masivos (como `bd_conexion`)

---

## 🔧 Script de Búsqueda y Reemplazo (Opcional)

Si quieres automatizar algunos cambios, puedes usar estos patrones:

```python
# En tu editor, buscar y reemplazar:
"from bd_conexion import" → "from core.bd_conexion import"
"from motor_recomendacion import" → "from core.motor_recomendacion import"
"from motor_recomendacion_basico import" → "from core.motor_recomendacion_basico import"
"from optimizador_plan import" → "from core.optimizador_plan import"
"from envio_email import" → "from utils.envio_email import"
"from aprendizaje_continuo import" → "from aprendizaje.aprendizaje_continuo import"
"from integracion_aprendizaje import" → "from aprendizaje.integracion_aprendizaje import"
```

**⚠️ CUIDADO:** Revisa cada cambio manualmente, especialmente los que están dentro de funciones o tienen imports condicionales.

---

## 📊 Resumen Final

- **Total archivos a actualizar:** 8
- **Total imports a cambiar:** ~12-15 (algunos están duplicados)
- **Complejidad:** Media (la mayoría son cambios simples)
- **Tiempo estimado:** 15-30 minutos

**No es tan complicado como parece.** La mayoría son cambios directos de `from X import` a `from carpeta.X import`.

