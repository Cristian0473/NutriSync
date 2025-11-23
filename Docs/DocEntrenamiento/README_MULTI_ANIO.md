# Procesamiento de NHANES Multi-Año

## 📋 Descripción

Este script procesa automáticamente archivos NHANES de **múltiples años** y los combina en un solo dataset unificado para entrenamiento de modelos ML.

### Características principales:

1. ✅ **Detección automática** de carpetas de años
2. ✅ **Unificación de BPX/BPXO**: Maneja automáticamente las diferencias entre:
   - **BPX** (auscultatorio) - años antiguos (2013-2014, 2015-2016)
   - **BPXO** (oscilométrico) - años recientes (2017-2018, 2021-2023)
3. ✅ **Promedio de mediciones**: Usa el promedio de las 3 mediciones de presión arterial
4. ✅ **Combinación automática**: Une todos los años en un solo dataset

---

## 📁 Estructura de Carpetas

El script espera esta estructura:

```
Datasets/
├── 2013-2014/
│   ├── BMX_H.xpt
│   ├── BPX_H.xpt      # Auscultatorio
│   ├── GHB_H.xpt
│   ├── GLU_H.xpt
│   ├── HDL_H.xpt
│   ├── INS_H.xpt
│   ├── TCHOL_H.xpt
│   └── TRIGLY_H.xpt
├── 2015-2016/         # Nota: Si la carpeta se llama "2015-1016", el script la detectará igual
│   ├── BMX_I.xpt
│   ├── BPX_I.xpt      # Auscultatorio
│   └── ...
├── 2017-2018/
│   ├── BMX_J.xpt
│   ├── BPXO_J.xpt     # Oscilométrico
│   └── ...
└── 2021-2023/
    ├── BMX_L.xpt
    ├── BPXO_L.xpt     # Oscilométrico
    └── ...
```

---

## 🚀 Uso

### Ejecutar el script:

```bash
cd "ApartadoInteligente/Entrenamiento"
python procesar_nhanes_multi_anio.py
```

### Parámetros opcionales:

Puedes modificar la función `main()` para cambiar:

```python
main(
    incluir_prediabetes=True,    # Incluir prediabetes (aumenta dataset)
    umbral_faltantes=0.5         # Umbral de valores faltantes (50%)
)
```

---

## 🔄 Cómo Funciona la Unificación de BPX/BPXO

### Problema:
- **Años antiguos (2013-2014, 2015-2016)**: Usan `BPX_*.xpt` con variables `BPXSY1`, `BPXDI1` (método auscultatorio)
- **Años recientes (2017-2018, 2021-2023)**: Usan `BPXO_*.xpt` con variables `BPXOSY1`, `BPXODI1` (método oscilométrico)

### Solución:
El script detecta automáticamente el tipo de archivo y unifica las variables:

1. **Detecta el tipo**: Busca `BPXOSY1` (oscilométrico) o `BPXSY1` (auscultatorio)
2. **Promedia mediciones**: Usa el promedio de las 3 mediciones disponibles
3. **Unifica variables**: Crea `pa_sis` y `pa_dia` independientemente del método
4. **Marca el método**: Agrega columna `metodo_bp` ('auscultatorio' o 'oscilometrico')

### Resultado:
```python
SEQN | pa_sis | pa_dia | metodo_bp | ...
-----|--------|--------|-----------|----
1234 | 130.5  | 85.2   | auscultatorio
5678 | 125.3  | 80.1   | oscilometrico
```

---

## 📊 Output

El script genera:

1. **`nhanes_procesado.csv`**: Dataset completo combinado
2. **`nhanes_procesado.json`**: Muestra (primeras 1000 filas)
3. **`nhanes_metadatos.json`**: Metadatos del dataset

### Metadatos incluyen:
- Total de filas y columnas
- Años incluidos
- Distribución de métodos de presión arterial
- Estadísticas de valores faltantes
- Variables clínicas, antropométricas y derivadas

---

## ⚠️ Notas Importantes

### 1. Typo en carpeta "2015-1016"
Si tu carpeta se llama **"2015-1016"** en lugar de **"2015-2016"**, el script la detectará automáticamente. No es necesario renombrarla.

### 2. Compatibilidad Clínica
Ambos métodos (auscultatorio y oscilométrico) son **clínicamente equivalentes** para ML. Las diferencias son mínimas y no afectan el patrón metabólico general.

### 3. Promedio de Mediciones
El script usa el **promedio de las 3 mediciones** de presión arterial cuando están disponibles, lo que reduce el ruido y mejora la calidad de los datos.

### 4. Años Incluidos
El script procesa automáticamente **todos los años** que encuentre en carpetas dentro de `Datasets/`. No necesitas especificar qué años procesar.

---

## 🔍 Verificación

Después de ejecutar el script, verifica:

1. **Total de filas**: Debería ser mayor que con un solo año
2. **Años incluidos**: Deberían aparecer todos los años procesados
3. **Método BP**: Debería haber ambos métodos ('auscultatorio' y 'oscilometrico')
4. **Valores faltantes**: Revisa que no sean excesivos

---

## 📈 Resultados Esperados

Con 4 años de datos (2013-2014, 2015-2016, 2017-2018, 2021-2023):

- **Dataset esperado**: ~10,000-15,000 filas (antes: 3,215)
- **Mejora en entrenamiento**: +10-15% en AUC-ROC esperado
- **Mejor generalización**: Modelo entrenado con más diversidad temporal

---

## 🐛 Troubleshooting

### Error: "No se encontraron archivos"
- Verifica que las carpetas estén dentro de `Datasets/`
- Verifica que los archivos tengan extensión `.xpt`

### Error: "Archivo BPX desconocido"
- Verifica que el archivo tenga variables `BPXSY1` o `BPXOSY1`
- Revisa que el archivo no esté corrupto

### Dataset muy pequeño después de filtrar
- Aumenta `incluir_prediabetes=True`
- Aumenta `umbral_faltantes=0.6` o `0.7`

---

## ✅ Próximos Pasos

Después de procesar los datos:

1. **Entrenar modelos**: Ejecutar `entrenar_modelos.py`
2. **Analizar dataset**: Ejecutar `analizar_dataset.py`
3. **Integrar modelo**: Integrar XGBoost en el motor de recomendación

