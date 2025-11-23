# 📊 Información del Dataset de Entrenamiento

## 📁 **Dataset Usado**

### **Archivo:**
- **Nombre**: `nhanes_procesado.csv`
- **Ubicación**: `ApartadoInteligente/Entrenamiento/Datasets/nhanes_procesado.csv`
- **Formato**: ✅ **CSV** (Comma-Separated Values)

---

## 📊 **Estadísticas del Dataset**

### **Tamaño:**
- **Filas (pacientes)**: **12,057** pacientes con diabetes tipo 2 y prediabetes
- **Columnas (variables)**: **26** variables clínicas, antropométricas y derivadas

### **Años Incluidos:**
- **2013-2014**: Datos del ciclo 2013-2014
- **2015-2016**: Datos del ciclo 2015-2016
- **2017-2018**: Datos del ciclo 2017-2018
- **2021-2023**: Datos del ciclo 2021-2023

**Total**: 4 años de datos NHANES combinados

---

## 📋 **Variables del Dataset (26 columnas)**

### **Variables Clínicas:**
1. `hba1c` - Hemoglobina glicosilada (%)
2. `glucosa_ayunas` - Glucosa en ayunas (mg/dL)
3. `insulina_ayunas` - Insulina en ayunas (μU/mL)
4. `hdl` - Colesterol HDL (mg/dL)
5. `trigliceridos` - Triglicéridos (mg/dL)
6. `colesterol_total` - Colesterol total (mg/dL)
7. `ldl` - Colesterol LDL (mg/dL)
8. `pa_sis` - Presión arterial sistólica (mmHg)
9. `pa_dia` - Presión arterial diastólica (mmHg)

### **Variables Antropométricas:**
10. `peso` - Peso (kg)
11. `talla` - Talla (m)
12. `imc` - Índice de masa corporal (kg/m²)
13. `cc` - Circunferencia de cintura (cm)

### **Variables Derivadas:**
14. `no_hdl` - Colesterol no-HDL (mg/dL)
15. `homa_ir` - Índice HOMA-IR (resistencia a la insulina)
16. `tg_hdl_ratio` - Ratio Triglicéridos/HDL
17. `ldl_hdl_ratio` - Ratio LDL/HDL
18. `aip` - Índice aterogénico (AIP)
19. `hipertension` - Hipertensión (0/1)
20. `control_glucemico` - Control glucémico (0/1) ← **TARGET**
21. `riesgo_metabolico` - Riesgo metabólico (0-1) ← **TARGET**

### **Variables de Identificación:**
22. `seqn` - Identificador único del paciente
23. `anio_nhanes` - Año del ciclo NHANES
24. `metodo_bp` - Método de medición de presión arterial
25. `actividad` - Nivel de actividad física
26. `imc_nhanes` - IMC calculado por NHANES

---

## 🎯 **Targets (Variables Objetivo)**

### **1. `control_glucemico`** (Clasificación Binaria)
- **0**: Control glucémico bueno (HbA1c < 7.0%)
- **1**: Control glucémico malo (HbA1c ≥ 7.0%)
- **Distribución**:
  - Clase 0: ~85.3% (10,290 pacientes)
  - Clase 1: ~14.7% (1,767 pacientes)

### **2. `riesgo_metabolico`** (Regresión Continua)
- **Rango**: 0.0 - 1.0
- **Media**: 0.21
- **Desviación estándar**: 0.15
- **Interpretación**: Score de riesgo metabólico (0 = bajo riesgo, 1 = alto riesgo)

---

## 📊 **Completitud de Datos**

### **Variables con Mayor Completitud:**
- `seqn`: 100% (12,057 valores)
- `control_glucemico`: 100% (12,057 valores)
- `riesgo_metabolico`: 100% (12,057 valores)
- `hipertension`: 100% (12,057 valores)
- `peso`: 99.9% (12,039 valores)
- `talla`: 99.9% (12,044 valores)
- `hdl`: 97.7% (11,778 valores)

### **Variables con Menor Completitud:**
- `ldl`: 17.1% (2,064 valores) - Calculado solo cuando hay triglicéridos
- `trigliceridos`: 17.4% (2,092 valores)
- `glucosa_ayunas`: 62.8% (7,568 valores)
- `insulina_ayunas`: 60.8% (7,335 valores)

**Nota**: El modelo usa imputación (mediana) para llenar valores faltantes.

---

## 🔄 **Proceso de Creación del Dataset**

### **1. Datos Originales:**
- Archivos `.XPT` (formato SAS) de NHANES
- 4 años de datos (2013-2014, 2015-2016, 2017-2018, 2021-2023)
- Múltiples archivos por año (BMX, BPX, GHB, GLU, HDL, INS, TCHOL, TRIGLY)

### **2. Procesamiento:**
- **Script**: `procesar_nhanes_multi_anio.py`
- **Pasos**:
  1. Cargar archivos `.XPT` de cada año
  2. Unificar variables (ej: BPX/BPXO para presión arterial)
  3. Mapear variables NHANES a formato del sistema
  4. Crear variables derivadas (IMC, LDL, HOMA-IR, ratios, etc.)
  5. Filtrar pacientes con DM2 y prediabetes
  6. Validar rangos clínicos
  7. Limpiar datos (valores faltantes, outliers)
  8. Guardar en CSV

### **3. Resultado:**
- **Archivo final**: `nhanes_procesado.csv`
- **12,057 filas** (pacientes)
- **26 columnas** (variables)
- **Listo para entrenar modelos ML**

---

## 📈 **Uso del Dataset**

### **En el Entrenamiento:**
```python
# El script entrenar_modelos.py carga el dataset:
df = pd.read_csv('Datasets/nhanes_procesado.csv')
# Resultado: 12,057 filas, 26 columnas
```

### **División de Datos:**
- **Train**: 70% (~8,440 pacientes) - Para entrenar el modelo
- **Validation**: 15% (~1,809 pacientes) - Para ajustar hiperparámetros
- **Test**: 15% (~1,809 pacientes) - Para evaluar el modelo final

---

## ✅ **Resumen**

| Aspecto | Valor |
|---------|-------|
| **Archivo** | `nhanes_procesado.csv` |
| **Formato** | ✅ CSV |
| **Filas (pacientes)** | **12,057** |
| **Columnas (variables)** | **26** |
| **Años incluidos** | 4 (2013-2014, 2015-2016, 2017-2018, 2021-2023) |
| **Target principal** | `control_glucemico` (clasificación binaria) |
| **Target secundario** | `riesgo_metabolico` (regresión continua) |
| **Fuente** | NHANES (National Health and Nutrition Examination Survey) |
| **Procesamiento** | `procesar_nhanes_multi_anio.py` |

---

## 🎯 **Conclusión**

El dataset **`nhanes_procesado.csv`** contiene **12,057 pacientes** con diabetes tipo 2 y prediabetes, con **26 variables** clínicas, antropométricas y derivadas, procesadas de **4 años de datos NHANES** (2013-2023). Este dataset se usa para entrenar el modelo XGBoost que predice el control glucémico y ajusta las recomendaciones nutricionales.

