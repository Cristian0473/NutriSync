# 🏥 Sistema Inteligente de Recomendación Nutricional Personalizado para Pacientes con Diabetes Tipo 2

## 📋 Índice

1. [Visión General del Sistema](#visión-general-del-sistema)
2. [Arquitectura y Componentes Principales](#arquitectura-y-componentes-principales)
3. [Archivos Clave del Sistema](#archivos-clave-del-sistema)
4. [Por qué cumple con el título de la tesis](#por-qué-cumple-con-el-título-de-la-tesis)
5. [Flujo de Funcionamiento General](#flujo-de-funcionamiento-general)

---

## 🎯 Visión General del Sistema

**NutriSync** es un sistema web inteligente diseñado específicamente para generar planes nutricionales personalizados para pacientes con diabetes tipo 2. El sistema combina:

- **Reglas clínicas basadas en evidencia** para el manejo de diabetes tipo 2
- **Machine Learning (XGBoost)** para personalización inteligente
- **Optimización automática** de combinaciones de alimentos
- **Interfaz web moderna** para nutricionistas y pacientes

### Características Principales

✅ **Personalización Inteligente**: Usa 3 modelos de Machine Learning para ajustar recomendaciones según el perfil metabólico del paciente

✅ **Gestión Completa**: Administración de pacientes, datos clínicos, antropometría, planes nutricionales

✅ **Control de Acceso**: Sistema de roles (Administrador, Nutricionista, Paciente) con permisos diferenciados

✅ **Historial Clínico**: Seguimiento histórico de datos clínicos y antropométricos para evaluar evolución

✅ **Optimización Automática**: Ajusta automáticamente las combinaciones de alimentos para cumplir objetivos nutricionales

---

## 🏗️ Arquitectura y Componentes Principales

### Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Admin UI    │  │ Nutricionista│  │  Paciente UI │      │
│  │  (Templates) │  │   (Templates)│  │  (Templates) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE LÓGICA                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           main.py (Flask Application)                │   │
│  │  - Rutas y endpoints                                  │   │
│  │  - Autenticación y autorización                       │   │
│  │  - Gestión de sesiones                                │   │
│  └──────────────────────────────────────────────────────┘   │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │      Core/motor_recomendacion.py                      │   │
│  │  - Motor principal de recomendaciones                 │   │
│  │  - Integración con modelos ML                         │   │
│  │  - Generación de planes nutricionales                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │      Core/optimizador_plan.py                         │   │
│  │  - Optimización de combinaciones de alimentos          │   │
│  │  - Validación de objetivos nutricionales              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE DATOS                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │      Core/bd_conexion.py                              │   │
│  │  - Pool de conexiones PostgreSQL                     │   │
│  │  - Funciones de acceso a datos                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           PostgreSQL Database                         │   │
│  │  - Usuarios, roles, pacientes                         │   │
│  │  - Datos clínicos y antropométricos                   │   │
│  │  - Planes nutricionales                               │   │
│  │  - Ingredientes y alimentos                           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              CAPA DE MACHINE LEARNING                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ApartadoInteligente/ModeloML/                       │   │
│  │  - modelo_respuesta_glucemica.pkl                    │   │
│  │  - modelo_seleccion_alimentos.pkl                    │   │
│  │  - modelo_optimizacion_combinaciones.pkl             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Archivos Clave del Sistema

### 1. **main.py** (6,288 líneas)
**Ubicación**: Raíz del proyecto  
**Propósito**: Aplicación principal Flask que orquesta todo el sistema

**Funcionalidades principales**:
- **Rutas y Endpoints**: Define todas las rutas HTTP (GET, POST) del sistema
- **Autenticación y Autorización**: Maneja login, sesiones, y control de acceso por roles
- **Gestión de Usuarios**: CRUD de usuarios, roles, nutricionistas
- **Gestión de Pacientes**: Registro, edición, visualización de pacientes
- **Gestión de Planes**: Creación, edición, publicación de planes nutricionales
- **APIs REST**: Endpoints para comunicación frontend-backend
- **Integración con Motor**: Llama al motor de recomendación para generar planes

**Decoradores importantes**:
- `@login_required`: Requiere autenticación
- `@admin_required`: Solo administradores y nutricionistas
- `@admin_only_required`: Solo administradores
- `@nutricionista_required`: Nutricionistas y administradores

### 2. **Core/motor_recomendacion.py** (4,009 líneas)
**Ubicación**: `Core/motor_recomendacion.py`  
**Propósito**: Motor principal de recomendaciones nutricionales inteligentes

**Funcionalidades principales**:
- **Cálculo de Metas Nutricionales**: Calcula calorías, macronutrientes según perfil del paciente
- **Integración con ML**: Carga y usa 3 modelos de Machine Learning
- **Generación de Planes**: Crea planes semanales personalizados
- **Selección de Alimentos**: Selecciona alimentos según perfil y preferencias
- **Optimización**: Integra con optimizador para ajustar combinaciones

**Clases principales**:
- `MotorRecomendacion`: Clase principal del motor
- `PerfilPaciente`: Dataclass con datos del paciente
- `MetaNutricional`: Dataclass con objetivos nutricionales

**Modelos ML integrados**:
1. **Modelo 1**: Predicción de respuesta glucémica (XGBoost Regressor)
2. **Modelo 2**: Selección personalizada de alimentos (XGBoost Classifier)
3. **Modelo 3**: Optimización de combinaciones (Ensemble XGBoost + Random Forest)

### 3. **Core/bd_conexion.py** (129 líneas)
**Ubicación**: `Core/bd_conexion.py`  
**Propósito**: Gestión de conexiones a la base de datos PostgreSQL

**Funcionalidades principales**:
- **Pool de Conexiones**: Maneja pool de conexiones para eficiencia
- **Reintentos Automáticos**: Maneja errores SSL y reconexiones
- **Funciones Helper**: `fetch_one()`, `fetch_all()`, `execute()`

**Características**:
- Detección automática de entorno (local vs Render)
- Configuración SSL automática para producción
- Reintentos con backoff exponencial en caso de errores

### 4. **Core/optimizador_plan.py**
**Ubicación**: `Core/optimizador_plan.py`  
**Propósito**: Optimización automática de planes nutricionales

**Funcionalidades principales**:
- **Validación de Objetivos**: Verifica cumplimiento de metas nutricionales
- **Ajuste Automático**: Modifica cantidades de alimentos para cumplir objetivos
- **Integración con Modelo 3**: Usa ML para evaluar combinaciones

### 5. **Templates/** (Carpeta)
**Ubicación**: `templates/`  
**Propósito**: Interfaces de usuario (HTML con Jinja2)

**Estructura**:
- `admin/`: Templates para administradores (19 archivos)
- `nutricionista/`: Templates para nutricionistas (15 archivos)
- `paciente/`: Templates para pacientes (6 archivos)
- `login.html`, `activar.html`: Autenticación

**Templates clave**:
- `admin/dashboard.html`: Dashboard del administrador
- `nutricionista/dashboard.html`: Dashboard del nutricionista
- `admin/obtener_plan.html`: Interfaz para generar planes
- `paciente/mi_plan.html`: Visualización del plan para pacientes

### 6. **static/** (Carpeta)
**Ubicación**: `static/`  
**Propósito**: Archivos estáticos (CSS, JavaScript, imágenes)

**Archivos importantes**:
- `static/js/obtener_plan.js`: Lógica frontend para generación de planes
- `static/css/`: Estilos CSS personalizados

### 7. **SQL/** (Carpeta)
**Ubicación**: `SQL/`  
**Propósito**: Scripts de base de datos

**Archivos importantes**:
- `bd_inicial.sql`: Esquema completo de la base de datos
- Scripts de migración y actualización

### 8. **ApartadoInteligente/ModeloML/** (Carpeta)
**Ubicación**: `ApartadoInteligente/ModeloML/`  
**Propósito**: Modelos de Machine Learning entrenados

**Modelos**:
- `modelo_respuesta_glucemica.pkl`: Modelo 1 (XGBoost Regressor)
- `scaler_respuesta_glucemica.pkl`: Scaler para Modelo 1
- `modelo_seleccion_alimentos.pkl`: Modelo 2 (XGBoost Classifier)
- `modelo_optimizacion_combinaciones.pkl`: Modelo 3 (Ensemble)

---

## ✅ Por qué cumple con el título de la tesis

### **"Sistema Inteligente"**

✅ **Machine Learning Integrado**: El sistema usa 3 modelos de ML entrenados con datos reales:
- Predicción de respuesta glucémica
- Selección personalizada de alimentos
- Optimización de combinaciones

✅ **Aprendizaje de Patrones**: Los modelos aprenden de patrones complejos en datos de pacientes reales (NHANES dataset con 12,054 pacientes)

✅ **Personalización Automática**: El sistema ajusta automáticamente las recomendaciones según el perfil metabólico del paciente, no solo reglas fijas

### **"Recomendación Nutricional"**

✅ **Planes Nutricionales Completos**: Genera planes semanales con:
- Distribución de comidas (desayuno, media mañana, almuerzo, media tarde, cena)
- Cantidades precisas de alimentos
- Metas nutricionales diarias (calorías, macronutrientes, fibra, sodio)

✅ **Selección Inteligente de Alimentos**: Usa Modelo 2 para seleccionar alimentos más adecuados según el perfil del paciente

✅ **Optimización Automática**: Ajusta automáticamente las combinaciones para cumplir objetivos nutricionales

### **"Personalizado"**

✅ **Perfil Individual**: Cada plan se genera basado en:
- Datos antropométricos (peso, talla, IMC, circunferencia de cintura)
- Datos clínicos (HbA1c, glucosa, lípidos, presión arterial)
- Edad, sexo, nivel de actividad
- Alergias y preferencias alimentarias
- Medicamentos actuales

✅ **Ajuste por ML**: El Modelo 1 predice el control glucémico y ajusta las metas nutricionales específicamente para ese paciente

✅ **Variedad y Preferencias**: Respeta preferencias de inclusión/exclusión y genera variedad en los alimentos

### **"Para Pacientes con Diabetes Tipo 2"**

✅ **Parámetros Específicos**: El sistema está configurado específicamente para diabetes tipo 2:
- Distribución de carbohidratos: 45-60% (recomendado para diabetes)
- Índice glucémico máximo: 70
- Fibra mínima: 25g/día
- Consideración de HbA1c y glucosa en ayunas

✅ **Control Glucémico**: El Modelo 1 predice y ajusta según el riesgo de mal control glucémico

✅ **Evidencia Clínica**: Las reglas base están basadas en guías clínicas para diabetes tipo 2 (ADA, AACE)

---

## 🔄 Flujo de Funcionamiento General

### 1. **Registro y Autenticación**

```
Usuario → Login → Verificación de credenciales → Asignación de rol → Redirección según rol
```

- **Administrador**: Acceso completo al sistema
- **Nutricionista**: Acceso a pacientes y generación de planes
- **Paciente**: Acceso a su plan y datos personales

### 2. **Registro de Paciente**

```
Nutricionista/Admin → Registro de datos → Almacenamiento en BD
```

- Datos personales (DNI, nombre, fecha de nacimiento)
- Antropometría (peso, talla, IMC, etc.)
- Datos clínicos (HbA1c, glucosa, lípidos, etc.)
- Medicamentos y alergias

### 3. **Generación de Plan Nutricional**

```
Nutricionista → Selecciona paciente → Configura parámetros → 
Sistema genera plan → Optimización automática → Plan listo
```

**Proceso detallado**:
1. Nutricionista selecciona paciente y configura parámetros (días, calorías, distribución de macronutrientes)
2. Sistema obtiene perfil completo del paciente
3. Sistema calcula metas nutricionales base (usando fórmulas clínicas)
4. **Modelo 1 (ML)**: Predice control glucémico y ajusta metas
5. **Modelo 2 (ML)**: Selecciona alimentos más adecuados
6. Sistema genera plan semanal con variedad
7. **Modelo 3 (ML)**: Optimiza combinaciones de alimentos
8. **Optimizador**: Ajusta cantidades para cumplir objetivos exactos
9. Plan se guarda en BD y se muestra al nutricionista

### 4. **Visualización y Seguimiento**

```
Paciente → Login → Dashboard → Ver plan → Ver progreso
```

- Paciente puede ver su plan nutricional activo
- Puede ver su evolución (antropometría y datos clínicos)
- Puede ver información del nutricionista que generó su plan

---

## 🎯 Resumen

**NutriSync** es un sistema completo que:

1. ✅ **Es Inteligente**: Usa 3 modelos de Machine Learning para personalización
2. ✅ **Genera Recomendaciones Nutricionales**: Crea planes completos y optimizados
3. ✅ **Es Personalizado**: Ajusta según perfil individual de cada paciente
4. ✅ **Está Especializado**: Diseñado específicamente para diabetes tipo 2

El sistema combina **reglas clínicas basadas en evidencia** con **aprendizaje automático** para ofrecer la mejor experiencia tanto para nutricionistas como para pacientes.

