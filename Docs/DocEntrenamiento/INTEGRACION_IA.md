# 🤖 Guía de Integración de IA para Mejorar Recomendaciones

## 📋 Resumen

Este documento explica cómo integrar APIs de IA (especialmente OpenAI GPT) para mejorar las recomendaciones nutricionales del sistema.

---

## 🎯 ¿Qué puede hacer la IA?

### 1. **Análisis de Preferencias en Texto Libre**
- El paciente escribe: "No me gusta el pescado, prefiero pollo. Soy vegetariano los lunes"
- La IA extrae: alergias, preferencias, restricciones dietéticas

### 2. **Explicaciones Personalizadas**
- Genera explicaciones claras y motivadoras del plan nutricional
- Adaptadas al perfil específico del paciente

### 3. **Sugerencias de Mejora**
- Analiza el cumplimiento de objetivos
- Sugiere mejoras específicas y accionables

### 4. **Optimización de Selección de Alimentos**
- Prioriza alimentos según el perfil del paciente
- Considera múltiples factores simultáneamente

---

## 🚀 Instalación

### Paso 1: Instalar OpenAI

```bash
pip install openai
```

### Paso 2: Obtener API Key

1. Ve a https://platform.openai.com/api-keys
2. Crea una cuenta (si no tienes)
3. Genera una nueva API key
4. **IMPORTANTE**: Guarda la key de forma segura

### Paso 3: Configurar API Key

**Opción A: Variable de entorno (Recomendado)**
```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY="tu-api-key-aqui"

# Windows (CMD)
set OPENAI_API_KEY=tu-api-key-aqui

# Linux/Mac
export OPENAI_API_KEY="tu-api-key-aqui"
```

**Opción B: En el código**
```python
from motor_ia_recomendaciones import MotorIARecomendaciones

motor_ia = MotorIARecomendaciones(api_key="tu-api-key-aqui")
```

---

## 💰 Costos

### Modelos Disponibles:

1. **GPT-4o-mini** (Recomendado para este uso)
   - Costo: ~$0.15 por 1M tokens de entrada, ~$0.60 por 1M tokens de salida
   - Uso estimado: ~$0.001-0.005 por recomendación
   - **Ventaja**: Económico y suficiente para este caso

2. **GPT-4**
   - Costo: ~$2.50 por 1M tokens de entrada, ~$10 por 1M tokens de salida
   - Uso estimado: ~$0.01-0.05 por recomendación
   - **Ventaja**: Mejor calidad, más caro

### Estimación de Costos Mensuales:

- **100 pacientes/mes**: ~$0.10 - $0.50 (con GPT-4o-mini)
- **1,000 pacientes/mes**: ~$1 - $5 (con GPT-4o-mini)
- **10,000 pacientes/mes**: ~$10 - $50 (con GPT-4o-mini)

**Conclusión**: Muy económico para la mayoría de casos de uso.

---

## 🔧 Integración en el Sistema

### Paso 1: Importar el Motor de IA

```python
from motor_ia_recomendaciones import MotorIARecomendaciones

# Inicializar (busca OPENAI_API_KEY en variables de entorno)
motor_ia = MotorIARecomendaciones()
```

### Paso 2: Usar en `motor_recomendacion.py`

#### A. Analizar Preferencias del Paciente

```python
# En obtener_perfil_paciente() o donde se procesen preferencias
if motor_ia.client:
    texto_preferencias = paciente.get('preferencias_texto', '')
    if texto_preferencias:
        preferencias_ia = motor_ia.analizar_preferencias_texto(
            texto_preferencias, 
            {
                'edad': edad,
                'sexo': sexo,
                'imc': imc,
                'hba1c': hba1c,
                'actividad': actividad
            }
        )
        # Combinar con preferencias existentes
        alergias.extend(preferencias_ia.get('alergias', []))
        preferencias_excluir.extend(preferencias_ia.get('preferencias_excluir', []))
```

#### B. Generar Explicación del Plan

```python
# Después de generar el plan
if motor_ia.client:
    explicacion = motor_ia.generar_explicacion_plan(
        plan_nutricional=plan_semanal,
        perfil_paciente={
            'edad': perfil.edad,
            'sexo': perfil.sexo,
            'imc': perfil.imc,
            'hba1c': perfil.hba1c,
            'actividad': perfil.actividad
        },
        metas={
            'calorias_diarias': metas.calorias_diarias,
            'carbohidratos_g': metas.carbohidratos_g,
            'carbohidratos_porcentaje': metas.carbohidratos_porcentaje,
            'proteinas_g': metas.proteinas_g,
            'proteinas_porcentaje': metas.proteinas_porcentaje,
            'grasas_g': metas.grasas_g,
            'grasas_porcentaje': metas.grasas_porcentaje,
            'fibra_g': metas.fibra_g
        }
    )
    # Agregar explicación al plan
    plan_semanal['explicacion_ia'] = explicacion
```

#### C. Sugerir Mejoras

```python
# Después de calcular cumplimiento de objetivos
if motor_ia.client:
    sugerencias = motor_ia.sugerir_mejoras_plan(
        plan_nutricional=plan_semanal,
        perfil_paciente={
            'edad': perfil.edad,
            'imc': perfil.imc,
            'hba1c': perfil.hba1c
        },
        cumplimiento_objetivos={
            'kcal': porcentaje_kcal,
            'cho': porcentaje_cho,
            'pro': porcentaje_pro,
            'fat': porcentaje_fat
        }
    )
    # Agregar sugerencias al plan
    plan_semanal['sugerencias_mejora'] = sugerencias
```

#### D. Optimizar Selección de Alimentos

```python
# En _sugerir_desayuno_variado() o funciones similares
if motor_ia.client and grupos.get('GRUPO1_CEREALES'):
    alimentos_candidatos = [
        {
            'nombre': c.get('nombre'),
            'kcal': c.get('kcal', 0),
            'cho': c.get('cho', 0),
            'pro': c.get('pro', 0),
            'fat': c.get('fat', 0),
            'ig': c.get('ig', 100)
        }
        for c in grupos['GRUPO1_CEREALES']
    ]
    
    alimentos_optimizados = motor_ia.optimizar_seleccion_alimentos(
        alimentos_candidatos=alimentos_candidatos,
        perfil_paciente={
            'edad': perfil.edad,
            'imc': perfil.imc,
            'hba1c': perfil.hba1c,
            'actividad': perfil.actividad
        },
        objetivos={
            'calorias': calorias_comida,
            'carbohidratos': cho_comida,
            'proteinas': pro_comida,
            'grasas': fat_comida
        }
    )
    
    # Usar alimentos optimizados en lugar de selección aleatoria
    for alimento_opt in alimentos_optimizados:
        # ... agregar a sugerencias
```

---

## 📊 Otras APIs Disponibles

### 1. **Google Cloud Natural Language API**
- **Uso**: Análisis de sentimientos, extracción de entidades
- **Costo**: Primeros 5,000 unidades/mes gratis, luego $1 por 1,000 unidades
- **Ventaja**: Especializado en análisis de texto

### 2. **AWS Personalize**
- **Uso**: Recomendaciones personalizadas basadas en comportamiento
- **Costo**: ~$0.024 por hora de entrenamiento + almacenamiento
- **Ventaja**: Especializado en sistemas de recomendación

### 3. **Azure Cognitive Services**
- **Uso**: Análisis de texto, recomendaciones
- **Costo**: Variado según servicio
- **Ventaja**: Integración con ecosistema Microsoft

---

## ⚠️ Consideraciones Importantes

### 1. **Privacidad y Seguridad**
- ✅ No envíes información médica sensible sin consentimiento
- ✅ Usa HTTPS para todas las comunicaciones
- ✅ Considera encriptar datos antes de enviar a la API

### 2. **Validación Médica**
- ⚠️ **IMPORTANTE**: La IA genera sugerencias, pero un nutricionista debe validarlas
- ⚠️ No reemplaza el juicio clínico profesional
- ⚠️ Siempre revisa las recomendaciones antes de darlas al paciente

### 3. **Límites de Rate**
- OpenAI tiene límites de requests por minuto
- Implementa retry logic y manejo de errores
- Considera cachear resultados cuando sea posible

### 4. **Fallback**
- Siempre ten un fallback si la IA no está disponible
- El sistema debe funcionar sin IA (modo degradado)

---

## 🧪 Pruebas

### Probar el Motor de IA

```python
from motor_ia_recomendaciones import MotorIARecomendaciones

# Inicializar
motor_ia = MotorIARecomendaciones()

# Probar análisis de preferencias
texto = "No me gusta el pescado, prefiero pollo. Tengo alergia a los frutos secos."
perfil = {"edad": 50, "sexo": "M", "imc": 28.5, "hba1c": 7.2, "actividad": "moderada"}

if motor_ia.client:
    resultado = motor_ia.analizar_preferencias_texto(texto, perfil)
    print("Resultado:", resultado)
else:
    print("⚠️  Configura OPENAI_API_KEY")
```

---

## 📈 Mejoras Futuras

1. **Fine-tuning del modelo**: Entrenar GPT con datos específicos de nutrición
2. **Caché inteligente**: Guardar respuestas comunes para reducir costos
3. **Validación automática**: Verificar que las recomendaciones sean seguras
4. **Aprendizaje continuo**: Mejorar prompts basándose en feedback

---

## ✅ Checklist de Integración

- [ ] Instalar OpenAI: `pip install openai`
- [ ] Obtener API key de OpenAI
- [ ] Configurar variable de entorno `OPENAI_API_KEY`
- [ ] Probar `motor_ia_recomendaciones.py`
- [ ] Integrar en `motor_recomendacion.py`
- [ ] Agregar manejo de errores y fallback
- [ ] Probar con datos reales
- [ ] Validar recomendaciones con nutricionista
- [ ] Monitorear costos y uso

---

## 📞 Soporte

Si tienes problemas:
1. Verifica que `OPENAI_API_KEY` esté configurada
2. Revisa los logs de errores
3. Verifica que tengas créditos en tu cuenta de OpenAI
4. Revisa la documentación de OpenAI: https://platform.openai.com/docs

