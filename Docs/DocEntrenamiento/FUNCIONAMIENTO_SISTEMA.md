# 📚 Funcionamiento del Sistema NutriSync

## 🎯 Visión General

NutriSync es un **sistema inteligente** de recomendaciones nutricionales personalizadas para pacientes con diabetes tipo 2. El sistema utiliza **Machine Learning (ML)** y **Inteligencia Artificial (IA)** como componentes centrales para generar planes alimentarios adaptados a cada paciente, complementados con optimización automática y cálculos nutricionales basados en evidencia científica.

---

## 🏗️ Arquitectura del Sistema

El sistema está construido con:
- **Backend**: Flask (Python) - Framework web
- **Base de Datos**: PostgreSQL - Almacenamiento de datos
- **Motor de Recomendación**: Lógica de negocio personalizada
- **Machine Learning**: Modelo XGBoost entrenado con datos NHANES
- **IA Externa**: OpenAI GPT (opcional) - Mejora de recomendaciones
- **Optimizador**: Algoritmo iterativo para cumplir objetivos nutricionales

---

## 📂 Estructura de Archivos Principales

### Archivos Core del Sistema

1. **`main.py`** - Aplicación Flask principal
   - Define todas las rutas (endpoints) del sistema
   - Maneja autenticación y autorización
   - Coordina las llamadas a los diferentes módulos

2. **`bd_conexion.py`** - Conexión a base de datos
   - Gestiona el pool de conexiones PostgreSQL
   - Proporciona funciones helper: `fetch_one()`, `fetch_all()`, `execute()`

3. **`motor_recomendacion.py`** - Motor principal de recomendaciones
   - Calcula metas nutricionales
   - Genera planes semanales
   - Integra ML para ajustar recomendaciones
   - Coordina con el optimizador

4. **`motor_ia_recomendaciones.py`** - Motor de IA (opcional)
   - Usa OpenAI GPT para mejorar recomendaciones
   - Analiza preferencias en texto libre
   - Genera explicaciones personalizadas

5. **`optimizador_plan.py`** - Optimizador de planes
   - Ajusta planes para cumplir objetivos nutricionales
   - Realiza iteraciones hasta alcanzar ≥90% de cumplimiento
   - Prioriza ajustes: grasas → proteínas → carbohidratos → calorías

---

## 🔄 Flujo Completo del Sistema

### 1. Inicio del Sistema

**Archivo**: `iniciar_servidor.py` → `main.py`

El sistema inicia cuando se ejecuta `iniciar_servidor.py`:
1. Verifica importaciones de módulos
2. Verifica conexión a PostgreSQL
3. Cuenta pacientes e ingredientes disponibles
4. Inicia el servidor Flask en `http://127.0.0.1:5000`

**Archivo**: `main.py` (líneas 26-28)
- Crea la aplicación Flask
- Configura la clave secreta desde variables de entorno
- Establece tiempo de sesión (5 minutos)

---

### 2. Autenticación y Autorización

**Archivo**: `main.py` (líneas 34-81)

Cuando un usuario intenta acceder:

1. **Login** (`/login`):
   - El usuario ingresa DNI o email + contraseña
   - El sistema busca en la tabla `usuario`
   - Si es DNI, busca en `paciente` → `usuario`
   - Verifica contraseña con `check_password_hash()`
   - Crea sesión con `user_id` y `user_email`

2. **Verificación de Roles**:
   - `get_user_roles(user_id)`: Consulta `usuario_rol` → `rol`
   - Retorna lista de roles: `['admin']`, `['paciente']`, `['nutricionista']`, etc.

3. **Decoradores de Protección**:
   - `@login_required`: Verifica que haya sesión activa
   - `@admin_required`: Verifica rol "admin"
   - `@paciente_required`: Verifica rol "paciente"

---

### 3. Pre-registro y Activación de Pacientes

**Archivo**: `main.py` (líneas 2406-2533)

**Flujo de Pre-registro**:

1. **Admin crea pre-registro** (`/admin/pre-registro`):
   - Ingresa DNI, nombres, apellidos, teléfono, email
   - Se guarda en tabla `pre_registro` con estado "pendiente"

2. **Generación de Token** (`/admin/pre-registro/<dni>/token`):
   - Genera UUID único como token
   - Calcula fecha de vencimiento (48 horas)
   - Guarda en `activacion_token`
   - **Envía email automático** (si está configurado SMTP) con:
     - Token de activación
     - Enlace directo para activar cuenta

3. **Activación de Cuenta** (`/activar`):
   - Paciente ingresa DNI, token y nueva contraseña
   - Valida token (no usado, no expirado)
   - Crea/actualiza usuario en `usuario` con contraseña hasheada
   - **Asigna rol "paciente"** automáticamente
   - Crea registro en `paciente` asociado al usuario
   - Marca token como usado y pre-registro como "activado"

**Archivo**: `envio_email.py`
- Maneja envío de emails vía SMTP (Gmail u otros)
- Formatea email HTML con token y enlace de activación

---

### 4. Generación de Plan Nutricional

**Archivo**: `main.py` (línea 4667) → `motor_recomendacion.py`

#### 4.1. Solicitud desde Frontend

**Archivo**: `static/js/obtener_plan.js` (función `generarPlan()`)

El usuario (admin/nutricionista) solicita generar un plan:
1. Selecciona paciente
2. Configura parámetros (días, calorías, distribución de macronutrientes)
3. Aplica filtros (grupos excluidos, ingredientes preferidos)
4. Hace clic en "Generar Plan"
5. Frontend envía POST a `/api/recomendacion/generar`

#### 4.2. Endpoint de Generación

**Archivo**: `main.py` (líneas 4667-4704)

```python
@app.route("/api/recomendacion/generar", methods=["POST"])
def api_recomendacion_generar():
    # 1. Recibe datos del frontend
    paciente_id = data.get('paciente_id')
    configuracion = data.get('configuracion', {})
    ingredientes = data.get('ingredientes', {})
    
    # 2. Crea instancia del motor
    motor = MotorRecomendacion()
    
    # 3. Genera plan completo
    resultado = motor.generar_plan_semanal_completo(
        paciente_id=paciente_id,
        dias=configuracion.get('dias_plan', 7),
        configuracion=configuracion,
        ingredientes=ingredientes
    )
    
    # 4. Retorna plan al frontend
    return resultado
```

#### 4.3. Motor de Recomendación - Obtener Perfil

**Archivo**: `motor_recomendacion.py` (método `obtener_perfil_paciente()`)

El motor consulta la base de datos para obtener:

1. **Datos Antropométricos** (tabla `antropometria`):
   - Peso, talla, IMC
   - Último registro disponible

2. **Datos Clínicos** (tabla `clinico`):
   - HbA1c (hemoglobina glicosilada)
   - Glucosa en ayunas
   - LDL, triglicéridos
   - Presión arterial

3. **Datos del Paciente** (tabla `paciente`):
   - Edad, sexo, actividad física

4. **Preferencias y Restricciones**:
   - Alergias (tabla `paciente_alergia`)
   - Medicamentos (tabla `paciente_medicamento`)
   - Preferencias de inclusión/exclusión (tabla `paciente_preferencia`)

5. **Crea objeto `PerfilPaciente`**:
   - Dataclass con toda la información consolidada

#### 4.4. Cálculo de Metas Nutricionales

**Archivo**: `motor_recomendacion.py` (método `calcular_metas_nutricionales()`)

El motor calcula las necesidades nutricionales:

1. **Cálculo de Calorías Basales**:
   - Usa fórmula de Harris-Benedict o Mifflin-St Jeor
   - Ajusta según actividad física (sedentario, ligera, moderada, intensa)
   - Aplica factor de corrección según IMC y control glucémico

2. **Distribución de Macronutrientes**:
   - **Carbohidratos**: 45-60% (ajustado según control glucémico)
   - **Proteínas**: 15-20%
   - **Grasas**: 25-35%

3. **Ajuste por Machine Learning** (si está disponible):
   - Carga modelo XGBoost entrenado
   - Predice probabilidad de mal control glucémico
   - Si probabilidad > 0.6 (mal control):
     - Reduce carbohidratos a 45-50%
     - Prioriza alimentos con IG bajo
   - Si probabilidad < 0.4 (buen control):
     - Permite carbohidratos hasta 60%
     - Más flexibilidad en selección

4. **Distribución por Comidas**:
   - Desayuno: 20% de CHO
   - Media mañana: 10% de CHO
   - Almuerzo: 35% de CHO
   - Media tarde: 10% de CHO
   - Cena: 25% de CHO

5. **Retorna objeto `MetaNutricional`**:
   - Calorías diarias, gramos de CHO/PRO/FAT
   - Porcentajes de cada macronutriente
   - Distribución por comidas

#### 4.5. Selección de Ingredientes Recomendados

**Archivo**: `motor_recomendacion.py` (método `obtener_ingredientes_recomendados()`)

El motor selecciona alimentos apropiados:

1. **Consulta Base de Datos**:
   - Obtiene ingredientes activos de tabla `ingrediente`
   - Filtra por grupo de alimentos (GRUPO1_CEREALES, GRUPO2_VERDURAS, etc.)

2. **Aplicación de Filtros**:
   - **Alergias**: Excluye ingredientes con alergias del paciente
   - **Preferencias**: Prioriza ingredientes marcados como "incluir"
   - **Índice Glucémico**: Si mal control, prioriza IG < 55
   - **Grupos Excluidos**: Si el usuario excluyó grupos, los omite

3. **Priorización**:
   - Alimentos con IG bajo tienen mayor prioridad
   - Si hay mal control glucémico, penaliza alimentos con IG alto
   - Considera variedad (evita repetir demasiado)

4. **Retorna Lista de Ingredientes**:
   - Cada ingrediente con: id, nombre, kcal, CHO, PRO, FAT, IG, grupo

#### 4.6. Generación del Plan Semanal

**Archivo**: `motor_recomendacion.py` (método `generar_plan_semanal()`)

El motor genera el plan día por día:

1. **Para cada día** (1 a 7 días):
   - Crea estructura con fecha
   - Genera comidas según tiempos configurados

2. **Para cada comida** (desayuno, almuerzo, cena, etc.):
   - Calcula necesidades nutricionales de esa comida
   - Selecciona ingredientes del grupo apropiado
   - Usa método `_sugerir_desayuno_variado()`, `_sugerir_almuerzo_variado()`, etc.
   - Aplica variedad (cambia ingredientes según el día)
   - Calcula cantidades para cumplir objetivos de la comida

3. **Cálculo de Cantidades**:
   - Usa porciones de intercambio según guía de alimentos
   - Ajusta gramos según necesidades nutricionales
   - Considera densidad calórica del alimento

4. **Estructura del Plan**:
   ```python
   {
     'plan_semanal': {
       '2025-01-15': {
         'des': {
           'alimentos': [
             {'id': 1, 'nombre': 'Avena', 'cantidad': 50, 'unidad': 'g', 'kcal': 195, ...}
           ]
         },
         'alm': {...},
         'cena': {...}
       },
       '2025-01-16': {...}
     }
   }
   ```

#### 4.7. Optimización del Plan

**Archivo**: `motor_recomendacion.py` (líneas 1786-1845) → `optimizador_plan.py`

Después de generar el plan inicial, se optimiza:

1. **Análisis de Cumplimiento**:
   - Calcula totales nutricionales de cada día
   - Compara con metas nutricionales
   - Calcula porcentajes de cumplimiento (kcal, CHO, PRO, FAT, fibra)

2. **Identificación de Déficits**:
   - Si algún nutriente está < 90% del objetivo, marca como déficit
   - Prioriza: grasas → proteínas → carbohidratos → calorías

3. **Iteraciones de Optimización** (hasta 20 iteraciones):
   - **Aumentar cantidades**: Si falta un nutriente, aumenta cantidad de alimentos que lo aportan
   - **Agregar alimentos**: Si no es suficiente, agrega nuevos alimentos del grupo apropiado
   - **Ajustar comidas principales**: Prioriza almuerzo y cena (mayor aporte nutricional)

4. **Validación con IA** (opcional):
   - Si `MotorIARecomendaciones` está disponible:
     - Valida que las combinaciones de alimentos sean apropiadas
     - Sugiere mejoras en la selección

5. **Criterios de Parada**:
   - Todos los objetivos cumplen ≥90% → ✅ Termina
   - No hay más mejoras posibles → ⚠️ Termina con advertencia
   - Máximo de iteraciones alcanzado → ⚠️ Termina con advertencia

6. **Estadísticas de Optimización**:
   - Número de iteraciones realizadas
   - Días optimizados
   - Mejoras aplicadas (lista de cambios)

#### 4.8. Conversión a Formato UI

**Archivo**: `motor_recomendacion.py` (método `_convertir_plan_semanal_a_formato_ui()`)

El plan se convierte al formato esperado por el frontend:

```python
{
  'perfil': {...},  # Datos del paciente
  'metas_nutricionales': {...},  # Objetivos calculados
  'debug_ml': {
    'probabilidad_mal_control': 0.65,  # Probabilidad ML
    'ml_disponible': True
  },
  'configuracion_original': {...},  # Config antes de ajuste ML
  'comidas': {...},  # Estructura de comidas (primer día)
  'plan_semanal': {...},  # Plan completo (todos los días)
  'resumen_semanal': {...},  # Totales y promedios
  'recomendaciones_especiales': [...]  # Sugerencias personalizadas
}
```

#### 4.9. Respuesta al Frontend

**Archivo**: `main.py` (línea 4699)

El endpoint retorna el plan completo al frontend:
- Frontend recibe JSON con el plan
- Muestra plan en la interfaz
- Permite editar, guardar o regenerar

---

## 🤖 Integración de Machine Learning

### Modelo XGBoost

**Ubicación**: `ApartadoInteligente/ModeloML/`

El sistema incluye un modelo de ML entrenado con datos NHANES:

1. **Entrenamiento**:
   - Dataset: NHANES (National Health and Nutrition Examination Survey)
   - Modelo: XGBoost (Gradient Boosting)
   - Objetivo: Predecir probabilidad de mal control glucémico
   - Features: Edad, sexo, IMC, HbA1c, glucosa, presión arterial, etc.

2. **Carga del Modelo**:
   - **Archivo**: `motor_recomendacion.py` (método `_cargar_modelo_ml()`)
   - Carga modelo `.pkl` y preprocesadores
   - Se carga bajo demanda (lazy loading)

3. **Uso en Recomendaciones**:
   - Cuando se calculan metas nutricionales:
     - Prepara datos del paciente (features)
     - Preprocesa con scalers guardados
     - Predice probabilidad de mal control (0.0 a 1.0)
   - Si probabilidad > 0.6:
     - Ajusta distribución de carbohidratos (reduce a 45-50%)
     - Prioriza alimentos con IG bajo
   - Si probabilidad < 0.4:
     - Permite más flexibilidad (hasta 60% CHO)
     - Menos restricciones en selección

4. **Almacenamiento de Probabilidad**:
   - Se guarda en `_ultima_probabilidad_ml`
   - Se incluye en la respuesta al frontend
   - Permite mostrar explicación al usuario

---

## 🧠 Integración de IA Externa (OpenAI)

**Archivo**: `motor_ia_recomendaciones.py`

El sistema puede usar OpenAI GPT para mejorar recomendaciones (opcional):

1. **Inicialización**:
   - Busca `OPENAI_API_KEY` en variables de entorno
   - Crea cliente OpenAI
   - Si no está disponible, sistema funciona sin IA

2. **Funcionalidades**:

   a. **Análisis de Preferencias en Texto Libre**:
      - Paciente escribe: "No me gusta el pescado, prefiero pollo"
      - IA extrae: alergias, preferencias, restricciones
      - Retorna estructura JSON con preferencias procesadas

   b. **Explicación Personalizada del Plan**:
      - Genera explicación clara y motivadora
      - Adaptada al perfil específico del paciente
      - Incluye razones de cada recomendación

   c. **Sugerencias de Mejora**:
      - Analiza cumplimiento de objetivos
      - Sugiere mejoras específicas y accionables
      - Prioriza según importancia

   d. **Optimización de Selección de Alimentos**:
      - Dada una lista de candidatos, prioriza los más apropiados
      - Considera múltiples factores simultáneamente
      - Retorna ranking de alimentos

3. **Uso en Optimizador**:
   - El optimizador puede usar IA para validar combinaciones
   - Verifica que las combinaciones sean nutricionalmente apropiadas
   - Sugiere alternativas si es necesario

---

## 🔧 Optimizador de Planes

**Archivo**: `optimizador_plan.py`

El optimizador ajusta planes para cumplir objetivos:

### Proceso de Optimización

1. **Análisis Inicial**:
   - Calcula cumplimiento de cada día
   - Identifica nutrientes por debajo del 90%

2. **Estrategia de Ajuste**:
   - **Prioridad 1 - Grasas**: Si faltan grasas, aumenta/agrega alimentos grasos
   - **Prioridad 2 - Proteínas**: Si faltan proteínas, aumenta/agrega carnes, lácteos
   - **Prioridad 3 - Carbohidratos**: Si faltan CHO, aumenta/agrega cereales, frutas
   - **Prioridad 4 - Calorías**: Si faltan calorías, aumenta porciones generales

3. **Algoritmo Iterativo**:
   ```
   Para cada día:
     Calcular cumplimiento
     Si no cumple (≥90%):
       Identificar déficit principal
       Ajustar comidas principales (almuerzo, cena)
       Recalcular cumplimiento
       Repetir hasta cumplir o máximo iteraciones
   ```

4. **Ajustes Específicos**:
   - **Aumentar cantidad**: Multiplica cantidad de alimento existente
   - **Agregar alimento**: Inserta nuevo alimento del grupo apropiado
   - **Reemplazar**: Si un alimento no aporta lo necesario, lo reemplaza

5. **Validación**:
   - Verifica que no se excedan límites superiores
   - Asegura variedad (no repite demasiado)
   - Valida con IA si está disponible

---

## 💾 Base de Datos

**Archivo**: `bd_conexion.py`

### Estructura Principal

1. **Tablas de Usuarios y Roles**:
   - `usuario`: Email, contraseña, estado
   - `rol`: admin, paciente, nutricionista
   - `usuario_rol`: Asignación de roles

2. **Tablas de Pacientes**:
   - `paciente`: DNI, usuario_id, datos básicos
   - `pre_registro`: Pre-registros pendientes
   - `activacion_token`: Tokens de activación

3. **Tablas Clínicas**:
   - `antropometria`: Peso, talla, IMC (histórico)
   - `clinico`: HbA1c, glucosa, lípidos, presión (histórico)

4. **Tablas Nutricionales**:
   - `ingrediente`: Alimentos con valores nutricionales
   - `plan`: Planes guardados
   - `plan_detalle`: Detalle de comidas del plan
   - `plan_alimento`: Alimentos específicos en cada comida

5. **Tablas de Preferencias**:
   - `paciente_preferencia`: Alimentos a incluir/excluir
   - `paciente_alergia`: Alergias del paciente
   - `paciente_medicamento`: Medicamentos que toma

### Conexión

- Usa `psycopg_pool` para pool de conexiones
- Configuración desde variables de entorno o `.env`
- Funciones helper: `fetch_one()`, `fetch_all()`, `execute()`

---

## 🎨 Frontend

### Estructura

1. **Templates HTML** (`templates/`):
   - `admin/`: Interfaz de administración
   - `paciente/`: Interfaz del paciente
   - `login.html`, `activar.html`: Autenticación

2. **JavaScript** (`static/js/`):
   - `obtener_plan.js`: Lógica de generación de planes
   - Maneja formularios, validaciones, llamadas AJAX

3. **CSS** (`static/css/`):
   - Estilos para admin, paciente, login

### Flujo Frontend → Backend

1. Usuario interactúa con formulario
2. JavaScript recopila datos
3. Envía POST a endpoint Flask
4. Muestra loading mientras procesa
5. Recibe respuesta JSON
6. Renderiza plan en la interfaz
7. Permite editar, guardar, exportar

---

## 🔐 Seguridad

1. **Autenticación**:
   - Contraseñas hasheadas con `werkzeug.security`
   - Sesiones con Flask (tiempo limitado)
   - Tokens de activación con expiración

2. **Autorización**:
   - Decoradores verifican roles antes de permitir acceso
   - Pacientes solo ven sus propios datos
   - Admins y nutricionistas ven todos los pacientes

3. **Validación**:
   - Validación de datos en backend (nunca confiar en frontend)
   - Sanitización de inputs
   - Protección contra SQL injection (usando parámetros)

---

## 📊 Flujo de Datos Completo

```
1. Usuario inicia sesión
   ↓
2. Admin/Nutricionista selecciona paciente
   ↓
3. Configura parámetros del plan
   ↓
4. Frontend envía POST a /api/recomendacion/generar
   ↓
5. Backend (main.py) recibe solicitud
   ↓
6. Crea MotorRecomendacion()
   ↓
7. Motor obtiene perfil del paciente (BD)
   ↓
8. Motor calcula metas nutricionales
   ↓
9. Motor carga modelo ML (si disponible)
   ↓
10. ML predice probabilidad de mal control
    ↓
11. Motor ajusta metas según ML
    ↓
12. Motor selecciona ingredientes recomendados
    ↓
13. Motor genera plan semanal día por día
    ↓
14. Optimizador analiza cumplimiento
    ↓
15. Optimizador ajusta iterativamente
    ↓
16. (Opcional) IA valida combinaciones
    ↓
17. Motor convierte a formato UI
    ↓
18. Backend retorna JSON al frontend
    ↓
19. Frontend renderiza plan
    ↓
20. Usuario puede editar/guardar plan
```

---

## 🎯 Resumen de Componentes

| Componente | Archivo | Función Principal |
|------------|---------|-------------------|
| **Aplicación Web** | `main.py` | Rutas, autenticación, coordinación |
| **Conexión BD** | `bd_conexion.py` | Pool de conexiones PostgreSQL |
| **Motor Principal** | `motor_recomendacion.py` | Cálculo de metas, generación de planes |
| **Motor ML** | `motor_recomendacion.py` | Integración modelo XGBoost |
| **Motor IA** | `motor_ia_recomendaciones.py` | Mejora con OpenAI GPT |
| **Optimizador** | `optimizador_plan.py` | Ajuste para cumplir objetivos |
| **Envío Email** | `envio_email.py` | Envío de tokens de activación |

---

## 🔄 Interacción entre Componentes

1. **Motor de Recomendación** es el núcleo:
   - Coordina todo el proceso
   - Llama a ML para ajustar metas
   - Llama a Optimizador para mejorar plan
   - Opcionalmente usa IA para validar

2. **Machine Learning** ajusta parámetros:
   - No genera el plan directamente
   - Ajusta distribución de macronutrientes
   - Prioriza alimentos según control glucémico

3. **Optimizador** mejora el plan:
   - Recibe plan inicial del Motor
   - Ajusta cantidades y alimentos
   - Usa IA opcionalmente para validar

4. **IA Externa** mejora calidad:
   - Analiza preferencias
   - Valida combinaciones
   - Genera explicaciones

---

## ✅ Conclusión

El sistema NutriSync es un **sistema inteligente** que integra múltiples tecnologías de IA y ML para generar planes nutricionales personalizados:

- **Machine Learning (XGBoost)** como componente central para predecir riesgo de mal control glucémico y ajustar recomendaciones
- **Inteligencia Artificial (OpenAI GPT)** para analizar preferencias, validar combinaciones y generar explicaciones personalizadas
- **Optimización automática** con algoritmos iterativos para cumplir objetivos nutricionales
- **Cálculos basados en evidencia científica** para fundamentar las recomendaciones

Todo coordinado por el Motor de Recomendación, que actúa como orquestador principal del proceso, haciendo que el sistema sea **inteligente y adaptativo** según el perfil específico de cada paciente.

