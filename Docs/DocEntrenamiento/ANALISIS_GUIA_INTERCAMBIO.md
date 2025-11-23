# Análisis: Implementación de Guía de Intercambio de Alimentos Adaptada para Diabetes Tipo 2

## 📋 Resumen Ejecutivo

La **Guía de Intercambio de Alimentos** está diseñada para personas **sanas con actividad física moderada**. Para implementarla en un sistema de recomendación para **diabetes tipo 2**, necesitamos adaptarla considerando:

1. **Control glucémico** (HbA1c, glucosa)
2. **IMC** (obesidad, bajo peso)
3. **Actividad física personalizada** (baja, moderada, alta)
4. **Metas calóricas personalizadas** (calculadas por TMB, no valores fijos de la guía)
5. **Distribución de macronutrientes específica para diabetes**

---

## 🔄 Adaptaciones Necesarias de la Guía

### 1. **Porciones por Grupo según Perfil del Paciente**

**Guía Original (personas sanas, actividad moderada):**
- Usa rangos fijos por edad (ej: 18-59 años = 6-7 porciones de cereales)
- Asume actividad física moderada
- No considera condiciones médicas

**Adaptación para Diabetes:**
- **Calcular porciones basándose en calorías personalizadas** (no solo edad)
- **Ajustar por actividad física real** del paciente (baja/moderada/alta)
- **Ajustar por control glucémico** (reducir cereales si HbA1c alto)
- **Ajustar por IMC** (reducir porciones si obesidad, aumentar si bajo peso)

### 2. **Valores Nutricionales Estándar de la Guía**

La guía define valores **promedio** por porción de intercambio:

| Grupo | Kcal | CHO (g) | PRO (g) | FAT (g) |
|-------|------|---------|---------|---------|
| GRUPO1 (Cereales) | 135 | 25 | 5 | 1 |
| GRUPO2 (Verduras) | 25 | 5 | 1 | 0 |
| GRUPO3 (Frutas) | 55 | 13 | 1 | 1 |
| GRUPO4 (Lácteos altos grasa) | 130 | 10 | 7 | 7 |
| GRUPO4 (Lácteos bajos grasa) | 65 | 10 | 5 | 1 |
| GRUPO5 (Carnes altas grasa) | 130 | 0 | 12 | 9 |
| GRUPO5 (Carnes bajas grasa) | 55 | 0 | 11 | 1 |
| GRUPO6 (Azúcares) | 20 | 6 | 0 | 0 |
| GRUPO7 (Aceites) | 90 | 0 | 0 | 10 |
| GRUPO7 (Oleaginosas) | 110 | 4 | 4 | 10 |

**Adaptación:**
- Usar estos valores como **base de cálculo**
- Mapear cada ingrediente de la BD a su equivalente en porciones
- Calcular cantidades reales basándose en estos valores estándar

---

## 🗄️ Cambios Necesarios en la Base de Datos

### 1. **Nueva Tabla: `guia_intercambio_estandar`**

Almacenar los valores nutricionales estándar de la guía:

```sql
CREATE TABLE guia_intercambio_estandar (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  grupo VARCHAR(20) NOT NULL,
  subgrupo VARCHAR(50),  -- NULL o valores como 'altos_grasa', 'bajos_grasa', 'aceites', 'oleaginosas'
  kcal_por_porcion DECIMAL(8,2) NOT NULL,
  cho_por_porcion DECIMAL(8,2) NOT NULL,
  pro_por_porcion DECIMAL(8,2) NOT NULL,
  fat_por_porcion DECIMAL(8,2) NOT NULL,
  descripcion TEXT,
  activo BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT uk_grupo_subgrupo UNIQUE (grupo, subgrupo)
);
```

**Datos a insertar:**
- GRUPO1_CEREALES: 135 kcal, 25g CHO, 5g PRO, 1g FAT
- GRUPO2_VERDURAS: 25 kcal, 5g CHO, 1g PRO, 0g FAT
- GRUPO3_FRUTAS: 55 kcal, 13g CHO, 1g PRO, 1g FAT
- GRUPO4_LACTEOS (altos_grasa): 130 kcal, 10g CHO, 7g PRO, 7g FAT
- GRUPO4_LACTEOS (bajos_grasa): 65 kcal, 10g CHO, 5g PRO, 1g FAT
- GRUPO5_CARNES (altas_grasa): 130 kcal, 0g CHO, 12g PRO, 9g FAT
- GRUPO5_CARNES (bajas_grasa): 55 kcal, 0g CHO, 11g PRO, 1g FAT
- GRUPO6_AZUCARES: 20 kcal, 6g CHO, 0g PRO, 0g FAT
- GRUPO7_GRASAS (aceites): 90 kcal, 0g CHO, 0g PRO, 10g FAT
- GRUPO7_GRASAS (oleaginosas): 110 kcal, 4g CHO, 4g PRO, 10g FAT

### 2. **Modificar Tabla: `ingrediente`**

Agregar campos para mapear a la guía de intercambio:

```sql
ALTER TABLE ingrediente ADD COLUMN porciones_intercambio DECIMAL(8,4);
-- Ejemplo: si 100g de arroz = 1 porción de intercambio, entonces porciones_intercambio = 1.0
-- Si 50g de arroz = 1 porción, entonces porciones_intercambio = 2.0 (2 porciones por 100g)

ALTER TABLE ingrediente ADD COLUMN subgrupo_intercambio VARCHAR(50);
-- Para GRUPO4 y GRUPO5: 'altos_grasa' o 'bajos_grasa'
-- Para GRUPO7: 'aceites' o 'oleaginosas'
-- Para otros grupos: NULL
```

**Lógica de cálculo:**
- `porciones_intercambio` = (valores nutricionales del ingrediente) / (valores estándar de la guía)
- Ejemplo: Si un ingrediente tiene 270 kcal por 100g y la guía dice 135 kcal por porción → `porciones_intercambio = 2.0`

### 3. **Nueva Tabla: `porciones_recomendadas_por_edad` (Opcional - Referencial)**

Almacenar las recomendaciones de la guía original por edad (solo como referencia):

```sql
CREATE TABLE porciones_recomendadas_por_edad (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  grupo_edad VARCHAR(20) NOT NULL,  -- '2-5', '6-8', '9-11', '12-14', '15-17', '18-59', '60+'
  calorias_referenciales INT NOT NULL,
  grupo_alimento VARCHAR(20) NOT NULL,
  porciones_min INT NOT NULL,
  porciones_max INT NOT NULL,
  CONSTRAINT uk_grupo_edad_grupo_alimento UNIQUE (grupo_edad, grupo_alimento)
);
```

**Nota:** Esta tabla es solo referencial. El sistema calculará porciones basándose en las calorías personalizadas del paciente, no en rangos de edad fijos.

---

## 💻 Cambios Necesarios en el Sistema (motor_recomendacion.py)

### 1. **Nuevo Método: `calcular_porciones_por_grupo()`**

Calcular cuántas porciones de cada grupo necesita el paciente basándose en:
- Calorías totales personalizadas (calculadas por TMB)
- Distribución de macronutrientes (ajustada por control glucémico)
- Actividad física
- IMC

**Lógica:**
```python
def calcular_porciones_por_grupo(self, perfil: PerfilPaciente, metas: MetaNutricional) -> Dict:
    """
    Calcula porciones de intercambio por grupo basándose en:
    - Calorías totales personalizadas
    - Distribución de macronutrientes
    - Control glucémico
    - IMC
    """
    # 1. Obtener valores estándar de la guía
    # 2. Calcular porciones necesarias para cumplir metas de CHO, PRO, FAT
    # 3. Ajustar por control glucémico (reducir cereales si HbA1c alto)
    # 4. Ajustar por IMC (reducir si obesidad)
    # 5. Ajustar por actividad (aumentar si alta actividad)
```

### 2. **Modificar Método: `_sugerir_alimentos_tiempo_variado()`**

En lugar de sugerir cantidades fijas (ej: 30g de cereal), sugerir **porciones de intercambio**:

**Antes:**
```python
sugerencias.append({
    'ingrediente': cereal,
    'cantidad_sugerida': 30,  # gramos fijos
    'unidad': 'g',
})
```

**Después:**
```python
# Calcular cuántas porciones de intercambio necesita esta comida
porciones_necesarias = self._calcular_porciones_para_comida(tiempo, metas, perfil)

# Convertir porciones a gramos del ingrediente específico
gramos = self._convertir_porciones_a_gramos(ingrediente, porciones_necesarias)

sugerencias.append({
    'ingrediente': cereal,
    'cantidad_sugerida': gramos,
    'porciones_intercambio': porciones_necesarias,  # Nuevo campo
    'unidad': 'g',
})
```

### 3. **Nuevo Método: `_convertir_porciones_a_gramos()`**

Convertir porciones de intercambio a gramos reales del ingrediente:

```python
def _convertir_porciones_a_gramos(self, ingrediente: Dict, porciones: float) -> float:
    """
    Convierte porciones de intercambio a gramos del ingrediente.
    
    Si ingrediente.porciones_intercambio = 2.0 (2 porciones por 100g)
    y necesitamos 1 porción → 50g
    """
    if ingrediente.get('porciones_intercambio'):
        return (100.0 / ingrediente['porciones_intercambio']) * porciones
    else:
        # Fallback: calcular basándose en valores nutricionales
        return self._calcular_gramos_por_valores_nutricionales(ingrediente, porciones)
```

### 4. **Modificar Método: `calcular_metas_nutricionales()`**

Agregar cálculo de porciones por grupo además de gramos de macronutrientes:

```python
# Después de calcular carbohidratos_g, proteinas_g, grasas_g
porciones_por_grupo = self.calcular_porciones_por_grupo(perfil, metas)

# Agregar a MetaNutricional
return MetaNutricional(
    # ... campos existentes ...
    porciones_por_grupo=porciones_por_grupo  # Nuevo campo
)
```

### 5. **Nuevo Método: `_calcular_porciones_para_comida()`**

Calcular cuántas porciones de cada grupo necesita una comida específica:

```python
def _calcular_porciones_para_comida(self, tiempo: str, metas: MetaNutricional, perfil: PerfilPaciente) -> Dict:
    """
    Calcula porciones de intercambio por grupo para una comida específica.
    
    Ejemplo para desayuno:
    - 1 porción de cereales (25g CHO)
    - 0.5 porción de carnes (5.5g PRO)
    - 1 porción de frutas (13g CHO)
    """
    # Distribuir porciones según distribución calórica por comida
    # Ajustar según control glucémico
```

---

## 📊 Ejemplo de Adaptación

### Paciente de Ejemplo:
- **Edad:** 45 años
- **Sexo:** Femenino
- **Peso:** 75 kg
- **Talla:** 1.65 m
- **IMC:** 27.5 (sobrepeso)
- **Actividad:** Baja
- **HbA1c:** 8.2% (mal control)
- **Glucosa:** 180 mg/dL

### Cálculo de Calorías:
- TMB: ~1400 kcal
- Factor actividad (baja): 1.2
- Factor diabetes (HbA1c alto): 0.9
- **Calorías totales:** ~1512 kcal

### Porciones Adaptadas (vs. Guía Original):

| Grupo | Guía Original (18-59 años, actividad moderada) | Adaptación para este paciente |
|-------|-----------------------------------------------|------------------------------|
| GRUPO1 (Cereales) | 6-7 porciones | **4-5 porciones** (reducido por mal control + baja actividad) |
| GRUPO2 (Verduras) | 3 porciones | **3 porciones** (mantener, importante para fibra) |
| GRUPO3 (Frutas) | 4 porciones | **3 porciones** (reducido por mal control) |
| GRUPO4 (Lácteos) | 2-3 porciones | **2 porciones bajos grasa** (reducido por sobrepeso) |
| GRUPO5 (Carnes) | 3-4 porciones | **3 porciones bajas grasa** (reducido por sobrepeso) |
| GRUPO6 (Azúcares) | 6 porciones | **2-3 porciones** (reducido drásticamente por diabetes) |
| GRUPO7 (Grasas) | 4-5 porciones | **3 porciones** (reducido por sobrepeso) |

---

## ✅ Resumen de Cambios

### Base de Datos:
1. ✅ Crear tabla `guia_intercambio_estandar`
2. ✅ Modificar tabla `ingrediente` (agregar `porciones_intercambio`, `subgrupo_intercambio`)
3. ⚠️ Opcional: Crear tabla `porciones_recomendadas_por_edad` (solo referencial)

### Sistema (motor_recomendacion.py):
1. ✅ Crear método `calcular_porciones_por_grupo()`
2. ✅ Modificar método `_sugerir_alimentos_tiempo_variado()`
3. ✅ Crear método `_convertir_porciones_a_gramos()`
4. ✅ Modificar método `calcular_metas_nutricionales()`
5. ✅ Crear método `_calcular_porciones_para_comida()`
6. ✅ Modificar dataclass `MetaNutricional` (agregar campo `porciones_por_grupo`)

### Scripts SQL:
1. ✅ Script para poblar `guia_intercambio_estandar`
2. ✅ Script para calcular y actualizar `porciones_intercambio` en `ingrediente`
3. ✅ Script para clasificar `subgrupo_intercambio` (altos_grasa/bajos_grasa, etc.)

---

## 🎯 Ventajas de esta Implementación

1. **Base científica:** Respeta la guía de intercambio como fundamento
2. **Personalización:** Adapta porciones según perfil del paciente
3. **Flexibilidad:** Mantiene ajustes por control glucémico, IMC, actividad
4. **Compatibilidad:** Puede coexistir con el sistema actual (migración gradual)
5. **Educación:** Facilita educación nutricional al paciente (concepto de porciones)

---

## ⚠️ Consideraciones

1. **Migración de datos:** Necesitamos calcular `porciones_intercambio` para todos los ingredientes existentes
2. **Validación:** Verificar que las porciones calculadas cumplan con las metas nutricionales
3. **Testing:** Probar con diferentes perfiles de pacientes
4. **Documentación:** Actualizar documentación del sistema

---

## 📝 Próximos Pasos

1. ✅ **Análisis completado** (este documento)
2. ⏳ **Aprobación del análisis**
3. ⏳ **Implementación de cambios en BD**
4. ⏳ **Implementación de cambios en sistema**
5. ⏳ **Testing y validación**
6. ⏳ **Migración de datos existentes**

