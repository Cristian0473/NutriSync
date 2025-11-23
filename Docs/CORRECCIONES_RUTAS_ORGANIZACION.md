# 🔧 Correcciones de Rutas Después de Organizar Archivos

## 📋 Problema Identificado

Al mover archivos a carpetas (`Core/`, `aprendizaje/`, `ml/`, `utils/`, `data_processing/`), las rutas relativas se rompieron porque `Path(__file__).parent` ahora apunta a la carpeta en lugar de la raíz del proyecto.

---

## ✅ Archivos Corregidos

### 1. **Core/motor_recomendacion.py** ✅

**Problema:** Buscaba modelos ML en `Core/ApartadoInteligente/` en lugar de `ApartadoInteligente/`

**Correcciones:**
- `_cargar_modelo_ml()` - Línea 126: `Path(__file__).parent` → `Path(__file__).parent.parent`
- `_cargar_modelo_respuesta_glucemica()` - Línea 215: `Path(__file__).parent` → `Path(__file__).parent.parent`
- `_cargar_modelo_seleccion_alimentos()` - Línea 254: `Path(__file__).parent` → `Path(__file__).parent.parent`
- `_cargar_modelo_optimizacion_combinaciones()` - Línea 298: `Path(__file__).parent` → `Path(__file__).parent.parent`

**Impacto:** El modelo ML no se cargaba, causando que siempre mostrara "BUENO" en lugar de "MALO"/"MODERADO"

---

### 2. **aprendizaje/diagnostico_aprendizaje.py** ✅

**Problema:** Buscaba `.env` en `aprendizaje/` en lugar de la raíz

**Corrección:**
- Línea 19: `Path(".env")` → `base_dir / ".env"` donde `base_dir = Path(__file__).parent.parent`

**Impacto:** No podía verificar la configuración de aprendizaje continuo

---

### 3. **utils/capturar_logs_flask.py** ✅

**Problema:** Buscaba `logs_sistema.md` en `utils/` y ejecutaba `main.py` desde `utils/`

**Correcciones:**
- Línea 14: `Path("logs_sistema.md")` → `base_dir / "logs_sistema.md"`
- Línea 49: `"main.py"` → `str(base_dir / "main.py")`

**Impacto:** No podía capturar logs ni ejecutar Flask correctamente

---

### 4. **utils/capturar_logs.py** ✅

**Problema:** Buscaba `logs_sistema.md` en `utils/` cuando se usa sin ruta absoluta

**Corrección:**
- Línea 12-13: Si la ruta es relativa, buscar en la raíz del proyecto

**Impacto:** No podía guardar logs en la ubicación correcta

---

### 5. **ml/pipeline_completo_ml.py** ✅

**Problema:** Buscaba scripts en el directorio actual en lugar de `ml/`

**Corrección:**
- Líneas 60-70: Usar `ml_dir = Path(__file__).parent` y construir rutas completas
- Cambiar tuplas de strings a objetos `Path`

**Impacto:** No podía ejecutar el pipeline completo de ML

---

## 📊 Resumen de Cambios

| Archivo | Líneas Afectadas | Tipo de Corrección |
|---------|------------------|-------------------|
| `Core/motor_recomendacion.py` | 4 funciones | `Path(__file__).parent` → `Path(__file__).parent.parent` |
| `aprendizaje/diagnostico_aprendizaje.py` | 1 línea | Ruta relativa → Ruta desde raíz |
| `utils/capturar_logs_flask.py` | 2 líneas | Rutas relativas → Rutas desde raíz |
| `utils/capturar_logs.py` | 3 líneas | Lógica condicional para rutas |
| `ml/pipeline_completo_ml.py` | 10+ líneas | Strings → Objetos Path con rutas correctas |

---

## ⚠️ Archivos que NO Necesitaron Cambios

### **data_processing/** ✅
- Los archivos usan rutas absolutas (`r"D:\Sistema Tesis\..."`) o rutas relativas que funcionan desde cualquier ubicación
- No requieren corrección

### **ml/entrenar_modelo*.py** ✅
- Usan rutas absolutas para guardar modelos
- No requieren corrección

### **ml/preparar_datos*.py** ✅
- Usan rutas absolutas o relativas que funcionan correctamente
- No requieren corrección

---

## 🎯 Patrón de Corrección Aplicado

Para archivos que necesitan acceder a recursos en la raíz del proyecto:

```python
# ANTES (cuando estaba en la raíz):
base_dir = Path(__file__).parent
archivo = base_dir / "archivo.txt"

# DESPUÉS (cuando está en una subcarpeta):
base_dir = Path(__file__).parent.parent  # Subir un nivel
archivo = base_dir / "archivo.txt"
```

Para archivos que necesitan acceder a recursos en su misma carpeta:

```python
# CORRECTO (funciona desde cualquier ubicación):
carpeta_actual = Path(__file__).parent
archivo = carpeta_actual / "archivo.txt"
```

---

## ✅ Estado Final

**Todos los archivos con rutas relativas han sido corregidos.**

El sistema debería funcionar correctamente con la nueva estructura de carpetas.

---

## 🧪 Verificación Recomendada

1. **Probar carga de modelos ML:**
   - Verificar que los modelos se cargan correctamente
   - Revisar logs para confirmar que encuentra los archivos `.pkl`

2. **Probar scripts de aprendizaje:**
   - Ejecutar `aprendizaje/diagnostico_aprendizaje.py`
   - Verificar que encuentra `.env` en la raíz

3. **Probar captura de logs:**
   - Ejecutar `utils/capturar_logs_flask.py`
   - Verificar que crea `logs_sistema.md` en la raíz

4. **Probar pipeline ML:**
   - Ejecutar `ml/pipeline_completo_ml.py`
   - Verificar que encuentra todos los scripts en `ml/`

