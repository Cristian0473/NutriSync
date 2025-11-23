# Pruebas de Caja Negra - Sprint 4

## Prueba PCN01: Verificación de estructuras condicionales en OptimizadorPlan

**Requisito:**
- **Módulo / Área Funcional / Subproceso:** Optimización de planes nutricionales
- **Tipo de requisito:** Funcional
- **Código del requisito:** RF04
- **Descripción del requisito:** El sistema debe optimizar planes nutricionales para cumplir objetivos nutricionales con precisión. El optimizador debe iterar hasta máximo 20 veces o hasta que todos los días cumplan objetivos (promedio mayor o igual a 90% y todos los macronutrientes entre 83% y 100%).

**Caso de prueba:**
- **Código de prueba:** PCN01
- **Caso de prueba:** Verificación de estructuras condicionales en bucle de optimización
- **Fecha de prueba:** [Fecha a completar]
- **Descripción de la prueba:** Revisar si las estructuras condicionales dentro del bucle for de optimización están debidamente implementadas y muestren los resultados esperados. Verificar que el bucle itera correctamente hasta máximo 20 iteraciones y se detiene cuando no hay mejoras.
- **Funcionalidad / Característica a evaluar:** Bucle for con máximo de iteraciones y condicionales para verificar cumplimiento y excesos funcionan correctamente
- **Datos de entrada / Acciones de entrada:** Código fuente - Core/optimizador_plan.py, función optimizar_plan, líneas 215-313
- **Resultado esperado:** Bucle itera correctamente, condicionales verifican cumplimiento (if cumplimiento.cumple_objetivos), verifican excesos (if exceso_significativo), y se detiene cuando mejoras_en_iteracion == 0

**Requerimientos de ambiente de pruebas:**
- Equipo: Computadora con Python 3.8+ instalado
- Código fuente: Core/optimizador_plan.py
- Conexión a internet: No requerida

**Condiciones / Restricciones:**
- Contar con acceso al código fuente
- Tener Python instalado para ejecutar pruebas unitarias

**Pasos de la prueba:**
1. Abrir el archivo Core/optimizador_plan.py en editor de código
2. Ubicar la función optimizar_plan (línea 140)
3. Revisar el bucle for iteracion in range(self.max_iteraciones) (línea 215)
4. Verificar condicional if cumplimiento.cumple_objetivos (línea 227)
5. Verificar condicional if exceso_significativo (línea 240)
6. Verificar condicional if mejoras_en_iteracion == 0 (línea 312)
7. Verificar que todas las estructuras condicionales tienen bloques else o continue apropiados

**Seguimiento:**
- **Código de prueba relacionado:** PCN02, PCN03
- **Estado anterior:** Pendiente
- **Resultado obtenido:** [A completar después de ejecutar]
- **Estado actual:** [A completar]
- **Observaciones:** [A completar]

---

## Prueba PCN02: Verificación de estructuras condicionales en carga de modelos ML

**Requisito:**
- **Módulo / Área Funcional / Subproceso:** Integración de modelos ML
- **Tipo de requisito:** Funcional
- **Código del requisito:** RF05
- **Descripción del requisito:** El sistema debe cargar modelos ML bajo demanda cuando se necesita realizar predicciones. Si un modelo no está disponible, el sistema debe continuar funcionando con reglas basadas en conocimiento, registrando advertencias en logs.

**Caso de prueba:**
- **Código de prueba:** PCN02
- **Caso de prueba:** Verificación de estructuras condicionales en carga de modelos ML
- **Fecha de prueba:** [Fecha a completar]
- **Descripción de la prueba:** Revisar si las estructuras condicionales en las funciones de carga de modelos ML están debidamente implementadas. Verificar que se verifica si el modelo ya está cargado, si las dependencias están disponibles, si los archivos existen, y se manejan errores correctamente.
- **Funcionalidad / Característica a evaluar:** Estructuras condicionales para verificación de carga de modelos funcionan correctamente
- **Datos de entrada / Acciones de entrada:** Código fuente - Core/motor_recomendacion.py, funciones _cargar_modelo_respuesta_glucemica, _cargar_modelo_seleccion_alimentos, _cargar_modelo_optimizacion_combinaciones
- **Resultado esperado:** Condicionales verifican correctamente si modelo está cargado (if self._modelo_ml is not None), si dependencias están disponibles (if not ML_AVAILABLE), si archivos existen (if not modelo_path.exists()), y manejan errores con try-except

**Requerimientos de ambiente de pruebas:**
- Equipo: Computadora con Python 3.8+ instalado
- Código fuente: Core/motor_recomendacion.py
- Archivos de modelos: ApartadoInteligente/ModeloML/*.pkl (opcional para prueba)
- Conexión a internet: No requerida

**Condiciones / Restricciones:**
- Contar con acceso al código fuente
- Tener Python instalado

**Pasos de la prueba:**
1. Abrir el archivo Core/motor_recomendacion.py en editor de código
2. Ubicar la función _cargar_modelo_respuesta_glucemica (línea 196)
3. Verificar condicional if self._modelo_respuesta_glucemica is not None (línea 198)
4. Verificar condicional if not ML_AVAILABLE (línea 202)
5. Verificar condicional if not modelo_path.exists() (línea 214)
6. Verificar estructura try-except para manejo de errores (línea 208)
7. Repetir pasos 2-6 para _cargar_modelo_seleccion_alimentos y _cargar_modelo_optimizacion_combinaciones

**Seguimiento:**
- **Código de prueba relacionado:** PCN01, PCN03
- **Estado anterior:** Pendiente
- **Resultado obtenido:** [A completar después de ejecutar]
- **Estado actual:** [A completar]
- **Observaciones:** [A completar]

---

## Prueba PCN03: Verificación de estructuras condicionales anidadas en _determinar_control_glucemico

**Requisito:**
- **Módulo / Área Funcional / Subproceso:** Clasificación de control glucémico
- **Tipo de requisito:** Funcional
- **Código del requisito:** RF07
- **Descripción del requisito:** El sistema debe determinar el control glucémico del paciente basado en probabilidades ML o valores clínicos. Prioriza probabilidad_ajustada > probabilidad_ml > valores clínicos. Clasifica como BUENO, MODERADO o MALO según umbrales.

**Caso de prueba:**
- **Código de prueba:** PCN03
- **Caso de prueba:** Verificación de estructuras condicionales anidadas en determinación de control glucémico
- **Fecha de prueba:** [Fecha a completar]
- **Descripción de la prueba:** Revisar si las estructuras condicionales anidadas en la función _determinar_control_glucemico están debidamente implementadas. Verificar que se prioriza probabilidad_ajustada sobre probabilidad_ml, y valores clínicos como fallback. Verificar clasificación según umbrales (0.6 para MALO, 0.4 para MODERADO).
- **Funcionalidad / Característica a evaluar:** Estructuras condicionales anidadas para priorización y clasificación funcionan correctamente
- **Datos de entrada / Acciones de entrada:** Código fuente - main.py, función _determinar_control_glucemico, líneas 4783-4815
- **Resultado esperado:** Condicionales verifican correctamente prioridad (if prob_final is None), clasificación según umbrales (if prob_final > 0.6, elif prob_final > 0.4), y fallback a valores clínicos (if perfil.hba1c >= 7.0, if perfil.glucosa_ayunas >= 140)

**Requerimientos de ambiente de pruebas:**
- Equipo: Computadora con Python 3.8+ instalado
- Código fuente: main.py
- Conexión a internet: No requerida

**Condiciones / Restricciones:**
- Contar con acceso al código fuente
- Tener Python instalado

**Pasos de la prueba:**
1. Abrir el archivo main.py en editor de código
2. Ubicar la función _determinar_control_glucemico (línea 4783)
3. Verificar condicional de priorización: if prob_final is None (línea 4792)
4. Verificar condicionales de clasificación ML:
   - if prob_final > 0.6: return 'MALO' (línea 4797)
   - elif prob_final > 0.4: return 'MODERADO' (línea 4799)
   - else: return 'BUENO' (línea 4801)
5. Verificar condicionales de fallback clínico:
   - if perfil.hba1c and perfil.hba1c >= 7.0: return 'MALO' (línea 4806)
   - if perfil.glucosa_ayunas and perfil.glucosa_ayunas >= 140: return 'MALO' (línea 4808)
   - if perfil.hba1c and perfil.hba1c >= 6.5: return 'MODERADO' (línea 4812)
6. Verificar que todas las rutas de código retornan un valor válido

**Seguimiento:**
- **Código de prueba relacionado:** PCN01, PCN02
- **Estado anterior:** Pendiente
- **Resultado obtenido:** [A completar después de ejecutar]
- **Estado actual:** [A completar]
- **Observaciones:** [A completar]

---

## Resumen de Pruebas de Caja Negra - Sprint 4

| Código | Caso de Prueba | Módulo | Estado |
|--------|----------------|--------|--------|
| PCN01 | Estructuras condicionales en OptimizadorPlan | Optimización | Pendiente |
| PCN02 | Estructuras condicionales en carga de modelos ML | Integración ML | Pendiente |
| PCN03 | Estructuras condicionales anidadas en _determinar_control_glucemico | Clasificación | Pendiente |

**Notas:**
- Todas las pruebas requieren acceso al código fuente
- Las pruebas se realizan mediante revisión de código y verificación de estructuras de control
- Los resultados deben documentarse en la sección "Seguimiento" de cada prueba
