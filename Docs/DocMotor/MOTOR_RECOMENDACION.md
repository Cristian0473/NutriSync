# Motor de Recomendación Nutricional para Diabetes Tipo 2

## Descripción

El **Motor de Recomendación Nutricional** es un sistema inteligente diseñado específicamente para pacientes con diabetes tipo 2. Utiliza algoritmos personalizados que consideran múltiples factores del paciente para generar recomendaciones nutricionales precisas y seguras.

## Características Principales

### 🎯 Personalización Avanzada
- **Perfil completo del paciente**: Edad, sexo, peso, talla, IMC, nivel de actividad
- **Datos clínicos**: HbA1c, glucosa en ayunas, LDL, presión arterial
- **Preferencias personales**: Alergias, medicamentos, preferencias alimentarias
- **Historial médico**: Considera medicamentos como metformina e insulina

### 🧮 Algoritmos Especializados
- **Cálculo metabólico**: Ecuación de Mifflin-St Jeor para metabolismo basal
- **Factores de ajuste**: Específicos para diabetes tipo 2
- **Distribución de macronutrientes**: Optimizada para control glucémico
- **Control de índice glucémico**: Máximo IG de 70 para todos los alimentos

### 🍎 Recomendaciones Inteligentes
- **Distribución por comidas**: Desayuno, media mañana, almuerzo, media tarde, cena
- **Filtros de seguridad**: Excluye automáticamente alergias y alimentos no deseados
- **Cantidades precisas**: Gramos exactos de carbohidratos por comida
- **Recomendaciones especiales**: Basadas en el estado clínico del paciente

## Parámetros del Algoritmo

### Macronutrientes para Diabetes Tipo 2
- **Carbohidratos**: 45-60% del total calórico
- **Proteínas**: 15-20% del total calórico  
- **Grasas**: 25-35% del total calórico
- **Fibra**: Mínimo 25g/día (idealmente 25-35g)
- **Sodio**: Máximo 2300mg/día (1500mg si PA > 140)

### Factores de Ajuste
- **HbA1c > 8.0%**: Reduce calorías en 10%
- **HbA1c < 6.5%**: Aumenta calorías en 5%
- **Glucosa > 140 mg/dL**: Reduce calorías en 5%
- **IMC > 30**: Reduce calorías en 10% (obesidad)
- **IMC < 18.5**: Aumenta calorías en 10% (bajo peso)

### Distribución de Carbohidratos por Comida
- **Desayuno**: 20% del total de CHO
- **Media Mañana**: 10% del total de CHO
- **Almuerzo**: 35% del total de CHO
- **Media Tarde**: 10% del total de CHO
- **Cena**: 25% del total de CHO

## Uso del Sistema

### Para Administradores/Nutricionistas

1. **Acceder a la lista de pacientes**:
   - Ir a "Pacientes" en el menú lateral
   - Buscar el paciente deseado

2. **Generar recomendación**:
   - Hacer clic en el botón "Recomendación" del paciente
   - Se abrirá una vista previa de la recomendación
   - Revisar los datos y hacer clic en "Guardar Recomendación"

3. **Ver estadísticas**:
   - Ir a "Motor Recomendación" en el menú lateral
   - Ver métricas de uso y ingredientes más populares

### Para Pacientes

1. **Acceder a la recomendación**:
   - Iniciar sesión con su DNI o email
   - En la página principal, hacer clic en "Ver Mi Recomendación"

2. **Interpretar los resultados**:
   - Ver metas nutricionales diarias
   - Revisar distribución de comidas
   - Leer recomendaciones especiales

## Estructura de Datos

### Perfil del Paciente
```python
PerfilPaciente(
    paciente_id: int,
    edad: int,
    sexo: str,
    peso: float,
    talla: float,
    imc: float,
    actividad: str,
    hba1c: Optional[float],
    glucosa_ayunas: Optional[float],
    ldl: Optional[float],
    pa_sis: Optional[int],
    pa_dia: Optional[int],
    alergias: List[str],
    medicamentos: List[str],
    preferencias_excluir: List[str],
    preferencias_incluir: List[str]
)
```

### Metas Nutricionales
```python
MetaNutricional(
    calorias_diarias: int,
    carbohidratos_g: int,
    carbohidratos_porcentaje: int,
    proteinas_g: int,
    proteinas_porcentaje: int,
    grasas_g: int,
    grasas_porcentaje: int,
    fibra_g: int,
    sodio_mg: int,
    carbohidratos_por_comida: Dict[str, int]
)
```

## Endpoints de la API

### Generar Recomendación
```
POST /admin/recomendacion/<paciente_id>/generar
```
Genera y guarda una recomendación como plan nutricional.

### Vista Previa
```
GET /admin/recomendacion/<paciente_id>/preview
```
Muestra una vista previa sin guardar la recomendación.

### API JSON
```
GET /api/recomendacion/<paciente_id>
```
Devuelve la recomendación en formato JSON.

### Recomendación del Paciente
```
GET /paciente/mi-recomendacion
```
Vista para que el paciente vea su recomendación.

### Estadísticas
```
GET /admin/recomendacion/estadisticas
```
Muestra estadísticas del motor de recomendación.

## Recomendaciones Especiales

El sistema genera automáticamente recomendaciones especiales basadas en:

- **Control glucémico**: Ajustes según HbA1c y glucosa
- **Presión arterial**: Reducción de sodio si es necesario
- **Colesterol**: Preferencia por grasas insaturadas
- **Medicamentos**: Consideraciones especiales para metformina e insulina
- **Peso corporal**: Estrategias según IMC

## Seguridad y Validaciones

- ✅ **Filtros de alergias**: Excluye automáticamente ingredientes alergénicos
- ✅ **Preferencias del paciente**: Respeta exclusiones e inclusiones
- ✅ **Límites nutricionales**: Respeta rangos seguros para diabetes
- ✅ **Índice glucémico**: Solo alimentos con IG ≤ 70
- ✅ **Validación de datos**: Verifica existencia del paciente y datos completos

## Consideraciones Clínicas

### Para HbA1c Elevado (>8%)
- Reducción de carbohidratos simples
- Aumento de fibra dietética
- Enfoque en carbohidratos complejos
- Reducción calórica moderada

### Para Control Óptimo (<6.5%)
- Mantenimiento de hábitos actuales
- Ligero aumento calórico si es necesario
- Enfoque en sostenibilidad

### Para Medicamentos Específicos
- **Metformina**: Asegurar ingesta de vitamina B12
- **Insulina**: Monitoreo preciso de carbohidratos por comida
- **Otros medicamentos**: Consideraciones según interacciones

## Futuras Mejoras

- [ ] Integración con dispositivos de monitoreo continuo de glucosa
- [ ] Aprendizaje automático basado en resultados de pacientes
- [ ] Recomendaciones de ejercicio complementarias
- [ ] Alertas automáticas por cambios en parámetros clínicos
- [ ] Integración con aplicaciones móviles de seguimiento

## Soporte Técnico

Para soporte técnico o reportar problemas:
- Revisar logs del sistema
- Verificar datos del paciente en la base de datos
- Comprobar configuración de ingredientes
- Validar permisos de usuario

---

**Versión**: 1.0  
**Fecha**: Diciembre 2024  
**Desarrollado para**: Sistema NutriSync - Tesis Cristian
