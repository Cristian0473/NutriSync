# 🔧 Guía de Procesamiento de Datasets

## 📊 **MyFitnessPal - Archivo TSV**

### **✅ NO necesitas convertir TSV a CSV**

**Razones:**
1. **TSV (Tab-Separated Values)** es muy similar a CSV, solo usa tabs (`\t`) en lugar de comas
2. **Python puede leer TSV directamente** con pandas usando `sep='\t'`
3. **Más eficiente**: No necesitas convertir, trabajamos directamente con TSV

---

## 🔍 **Cómo Leer TSV en Python**

### **Opción 1: Con pandas (Recomendado)**
```python
import pandas as pd

# Leer TSV directamente
df = pd.read_csv('myfitnesspal.tsv', sep='\t', encoding='utf-8')

# Si el archivo es muy grande, leer por chunks
chunk_size = 10000
for chunk in pd.read_csv('myfitnesspal.tsv', sep='\t', chunksize=chunk_size):
    # Procesar cada chunk
    process_chunk(chunk)
```

### **Opción 2: Si tiene JSON anidado**
```python
import pandas as pd
import json

# Leer TSV
df = pd.read_csv('myfitnesspal.tsv', sep='\t', encoding='utf-8')

# Si una columna contiene JSON, parsearlo
df['meals_json'] = df['meals'].apply(json.loads)
```

---

## 📋 **Estructura Esperada del TSV**

El archivo TSV de MyFitnessPal probablemente tiene esta estructura:

### **Opción A: Una columna con JSON**
```tsv
user_id	date	meals_json	goals_json
12345	2014-09-14	{"Breakfast":[...]}	{"calories":2000}
12345	2014-09-15	{"Lunch":[...]}	{"calories":2000}
```

### **Opción B: Columnas separadas**
```tsv
user_id	date	meal_type	food_name	calories	carbs	protein	fat
12345	2014-09-14	Breakfast	Oatmeal	150	27	5	3
12345	2014-09-14	Lunch	Chicken	200	0	30	8
```

---

## 🎯 **Próximos Pasos**

### **1. CGMacros (Ya está descargando)**
- ✅ Esperar a que termine de descargar
- ✅ Descomprimir si está comprimido
- ✅ Explorar estructura de archivos
- ✅ Enviarme nombres de archivos y columnas

### **2. MyFitnessPal (Archivo TSV)**
- ✅ **NO convertir a CSV** (trabajamos directamente con TSV)
- ✅ Abrir el archivo TSV (puedes usar Excel, Notepad++, o Python)
- ✅ Ver las primeras 5-10 filas
- ✅ Identificar:
  - ¿Qué columnas tiene?
  - ¿Tiene JSON anidado?
  - ¿Cómo está estructurado?
- ✅ Enviarme:
  - Nombres de columnas
  - 2-3 filas de ejemplo
  - Estructura del JSON (si hay)

---

## 💡 **Cómo Explorar el TSV Rápidamente**

### **Opción 1: Con Python (Recomendado)**
```python
import pandas as pd

# Leer solo las primeras 5 filas para explorar
df = pd.read_csv('myfitnesspal.tsv', sep='\t', nrows=5)

# Ver columnas
print("Columnas:", df.columns.tolist())

# Ver primeras filas
print(df.head())

# Ver tipos de datos
print(df.dtypes)
```

### **Opción 2: Con Excel**
1. Abrir Excel
2. Archivo → Abrir
3. Seleccionar el archivo `.tsv`
4. En "Delimitadores", seleccionar "Tab"
5. Ver las primeras filas

### **Opción 3: Con Notepad++**
1. Abrir el archivo `.tsv` en Notepad++
2. Ver las primeras 10-20 líneas
3. Identificar columnas separadas por tabs

---

## 🔧 **Script de Exploración Rápida**

Te preparo un script para explorar ambos datasets:

```python
# explorar_datasets.py
import pandas as pd
import json

print("=" * 50)
print("EXPLORANDO MyFitnessPal TSV")
print("=" * 50)

# Leer primeras 5 filas
df = pd.read_csv('myfitnesspal.tsv', sep='\t', nrows=5)

print("\n📋 Columnas encontradas:")
print(df.columns.tolist())

print("\n📊 Primeras filas:")
print(df.head())

print("\n📈 Tipos de datos:")
print(df.dtypes)

print("\n📏 Forma del dataset (primeras 5 filas):")
print(f"Filas: {len(df)}, Columnas: {len(df.columns)}")

# Si hay columnas con JSON, intentar parsearlas
for col in df.columns:
    if 'json' in col.lower() or df[col].dtype == 'object':
        try:
            # Intentar parsear como JSON
            sample = df[col].iloc[0]
            if isinstance(sample, str) and (sample.startswith('{') or sample.startswith('[')):
                parsed = json.loads(sample)
                print(f"\n🔍 Columna '{col}' contiene JSON:")
                print(json.dumps(parsed, indent=2)[:500])  # Primeros 500 caracteres
        except:
            pass
```

---

## ✅ **Resumen**

1. ✅ **NO convertir TSV a CSV** - Trabajamos directamente con TSV
2. ✅ **CGMacros**: Esperar descarga, explorar estructura
3. ✅ **MyFitnessPal**: Abrir TSV, ver columnas y estructura
4. ✅ **Enviarme**: Nombres de archivos, columnas, ejemplos

**Una vez que tengas la estructura de ambos, preparo los scripts de procesamiento completo.**

