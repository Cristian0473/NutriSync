# Pruebas de Caja Blanca - Sprint 4

## Prueba PCB01: Generación de plan nutricional con exclusión de grupos alimentarios

**Requisito:**
- **Módulo / Área Funcional / Subproceso:** Generación de planes nutricionales
- **Tipo de requisito:** Funcional
- **Código del requisito:** RF09
- **Descripción del requisito:** El sistema debe permitir excluir grupos alimentarios completos durante la generación del plan. Los alimentos del grupo excluido no deben aparecer en el plan generado.

**Caso de prueba:**
- **Código de prueba:** PCB01
- **Caso de prueba:** Verificación de exclusión de grupos alimentarios mediante petición HTTP
- **Fecha de prueba:** [Fecha a completar]
- **Descripción de la prueba:** Verificar mediante Postman o DevTools del navegador que al enviar una petición POST a /api/recomendacion/generar con grupos_excluidos en el body, el sistema retorna un plan sin alimentos del grupo excluido. Verificar en la respuesta JSON que ningún alimento tiene grupo igual al excluido.
- **Funcionalidad / Característica a evaluar:** Endpoint de generación de planes respeta exclusiones de grupos alimentarios
- **Datos de entrada / Acciones de entrada:** 
  - Petición POST a /api/recomendacion/generar
  - Body JSON: { "paciente_id": 1, "configuracion": { "dias_plan": 7, "kcal_obj": 2000 }, "ingredientes": { "grupos_excluidos": ["GRUPO6_AZUCARES"] } }
  - Headers: Content-Type: application/json, Cookie con sesión activa
- **Resultado esperado:** 
  - Status code 200 OK
  - Respuesta JSON con plan_completo
  - Ningún alimento en el plan tiene grupo igual a "GRUPO6_AZUCARES"
  - El plan contiene alimentos de otros grupos (GRUPO1_CEREALES, GRUPO2_VERDURAS, etc.)

**Requerimientos de ambiente de pruebas:**
- Equipo: Computadora con navegador web (Chrome, Firefox, Edge) o Postman
- Sistema: Aplicación web ejecutándose en localhost o servidor
- Usuario: Sesión activa de nutricionista o administrador
- Base de datos: Paciente de prueba con datos clínicos y antropométricos registrados
- Conexión a internet: No requerida (si el sistema está en localhost)

**Condiciones / Restricciones:**
- Tener sesión de usuario activa (obtener cookie de sesión mediante login)
- Tener al menos un paciente registrado con ID conocido
- El sistema debe estar funcionando correctamente

**Pasos de la prueba:**
1. Abrir Postman o DevTools del navegador (F12)
2. Realizar login en la aplicación para obtener cookie de sesión
3. En Postman: Crear nueva petición POST
   - URL: http://localhost:5000/api/recomendacion/generar
   - Método: POST
   - Headers: Content-Type: application/json, Cookie: [cookie de sesión]
   - Body (raw JSON):
     ```json
     {
       "paciente_id": 1,
       "configuracion": {
         "dias_plan": 7,
         "kcal_obj": 2000,
         "cho_pct": 50,
         "pro_pct": 18,
         "fat_pct": 32,
         "ig_max": 70
       },
       "ingredientes": {
         "grupos_excluidos": ["GRUPO6_AZUCARES"]
       }
     }
     ```
4. Enviar la petición
5. Verificar respuesta:
   - Status code debe ser 200
   - Response body debe contener plan_completo
6. Inspeccionar el JSON de respuesta y buscar todos los alimentos
7. Verificar que ningún alimento tiene grupo igual a "GRUPO6_AZUCARES"

**Evidencia requerida (capturas de pantalla):**
1. **Captura 1:** Postman o DevTools mostrando la petición POST con:
   - URL completa
   - Headers (Content-Type, Cookie)
   - Body JSON con grupos_excluidos: ["GRUPO6_AZUCARES"]
2. **Captura 2:** Postman o DevTools mostrando la respuesta con:
   - Status code 200
   - Response body JSON (puede ser parcial si es muy largo)
3. **Captura 3:** Detalle del JSON de respuesta mostrando un día del plan (ej: dia_1) con alimentos, verificando que ningún alimento tiene grupo "GRUPO6_AZUCARES"
4. **Captura 4 (opcional):** Búsqueda en el JSON de respuesta de la palabra "GRUPO6_AZUCARES" mostrando que no aparece (0 resultados)

**Seguimiento:**
- **Código de prueba relacionado:** PCB02, PCB03
- **Estado anterior:** Pendiente
- **Resultado obtenido:** [A completar después de ejecutar]
- **Estado actual:** [A completar]
- **Observaciones:** [A completar]

---

## Prueba PCB02: Configuración inteligente con ajuste ML según control glucémico

**Requisito:**
- **Módulo / Área Funcional / Subproceso:** Configuración de planes nutricionales
- **Tipo de requisito:** Funcional
- **Código del requisito:** RF10
- **Descripción del requisito:** El sistema debe proporcionar configuración recomendada con ajuste ML mediante endpoint /api/recomendacion/configuracion/<paciente_id>. Debe ajustar IG máximo y repeticiones máximas según probabilidad de mal control: > 0.6 (IG 55, rep 2), 0.4-0.6 (IG 65, rep 3), < 0.4 (IG 70, rep 3). Debe mostrar clasificación de control glucémico (BUENO, MODERADO, MALO).

**Caso de prueba:**
- **Código de prueba:** PCB02
- **Caso de prueba:** Verificación de configuración inteligente mediante petición HTTP GET
- **Fecha de prueba:** [Fecha a completar]
- **Descripción de la prueba:** Verificar mediante Postman o DevTools que al realizar petición GET a /api/recomendacion/configuracion/<paciente_id>, el sistema retorna configuración base, configuración final ajustada por ML, y clasificación de control glucémico. Verificar que los valores de IG máximo y repeticiones máximas se ajustan según la clasificación.
- **Funcionalidad / Característica a evaluar:** Endpoint de configuración retorna valores ajustados por ML según control glucémico
- **Datos de entrada / Acciones de entrada:**
  - Petición GET a /api/recomendacion/configuracion/1 (paciente con control MALO)
  - Petición GET a /api/recomendacion/configuracion/2 (paciente con control MODERADO)
  - Petición GET a /api/recomendacion/configuracion/3 (paciente con control BUENO)
  - Headers: Cookie con sesión activa
- **Resultado esperado:**
  - Status code 200 OK para cada petición
  - Respuesta JSON con estructura:
    - configuracion_base: { kcal_obj, cho_pct, pro_pct, fat_pct, ig_max, repeticiones_max }
    - configuracion_final: { kcal_obj, cho_pct, pro_pct, fat_pct, ig_max, repeticiones_max }
    - ml: { probabilidad_mal_control, probabilidad_ajustada, control_glucemico }
  - Para paciente con control MALO: configuracion_final.ig_max = 55, repeticiones_max = 2
  - Para paciente con control MODERADO: configuracion_final.ig_max = 65, repeticiones_max = 3
  - Para paciente con control BUENO: configuracion_final.ig_max = 70, repeticiones_max = 3

**Requerimientos de ambiente de pruebas:**
- Equipo: Computadora con navegador web (Chrome, Firefox, Edge) o Postman
- Sistema: Aplicación web ejecutándose en localhost o servidor
- Usuario: Sesión activa de nutricionista o administrador
- Base de datos: 
  - Paciente 1: Con HbA1c >= 7.0 o glucosa >= 140 (control MALO)
  - Paciente 2: Con HbA1c entre 6.5 y 6.9 o glucosa entre 126 y 139 (control MODERADO)
  - Paciente 3: Con HbA1c < 6.5 y glucosa < 126 (control BUENO)
- Conexión a internet: No requerida (si el sistema está en localhost)

**Condiciones / Restricciones:**
- Tener sesión de usuario activa (obtener cookie de sesión mediante login)
- Tener al menos 3 pacientes registrados con diferentes niveles de control glucémico
- Conocer los IDs de los pacientes de prueba

**Pasos de la prueba:**
1. Abrir Postman o DevTools del navegador (F12)
2. Realizar login en la aplicación para obtener cookie de sesión
3. En Postman: Crear nueva petición GET
   - URL: http://localhost:5000/api/recomendacion/configuracion/1
   - Método: GET
   - Headers: Cookie: [cookie de sesión]
4. Enviar la petición para Paciente 1 (control MALO)
5. Verificar respuesta:
   - Status code debe ser 200
   - Response body debe contener configuracion_base, configuracion_final y ml
   - Verificar que ml.control_glucemico = "MALO"
   - Verificar que configuracion_final.ig_max = 55
   - Verificar que configuracion_final.repeticiones_max = 2
6. Repetir pasos 3-5 para Paciente 2 (control MODERADO) cambiando URL a /configuracion/2
7. Repetir pasos 3-5 para Paciente 3 (control BUENO) cambiando URL a /configuracion/3

**Evidencia requerida (capturas de pantalla):**
1. **Captura 1:** Postman o DevTools mostrando petición GET a /api/recomendacion/configuracion/1 con:
   - URL completa
   - Headers (Cookie)
   - Response status 200
2. **Captura 2:** Response body JSON para Paciente 1 mostrando:
   - configuracion_base.ig_max (valor base)
   - configuracion_final.ig_max = 55
   - configuracion_final.repeticiones_max = 2
   - ml.control_glucemico = "MALO"
3. **Captura 3:** Response body JSON para Paciente 2 mostrando:
   - configuracion_final.ig_max = 65
   - configuracion_final.repeticiones_max = 3
   - ml.control_glucemico = "MODERADO"
4. **Captura 4:** Response body JSON para Paciente 3 mostrando:
   - configuracion_final.ig_max = 70
   - configuracion_final.repeticiones_max = 3
   - ml.control_glucemico = "BUENO"

**Seguimiento:**
- **Código de prueba relacionado:** PCB01, PCB03
- **Estado anterior:** Pendiente
- **Resultado obtenido:** [A completar después de ejecutar]
- **Estado actual:** [A completar]
- **Observaciones:** [A completar]

---

## Prueba PCB03: Guardado de plan nutricional en base de datos

**Requisito:**
- **Módulo / Área Funcional / Subproceso:** Persistencia de planes nutricionales
- **Tipo de requisito:** Funcional
- **Código del requisito:** RF11
- **Descripción del requisito:** El sistema debe permitir guardar planes nutricionales generados en la base de datos mediante endpoint /api/planes con método POST. El plan debe guardarse con estado "borrador" o "publicado" y debe retornar el ID del plan guardado y URL de detalle.

**Caso de prueba:**
- **Código de prueba:** PCB03
- **Caso de prueba:** Verificación de guardado de plan mediante petición HTTP POST
- **Fecha de prueba:** [Fecha a completar]
- **Descripción de la prueba:** Verificar mediante Postman o DevTools que al enviar una petición POST a /api/planes con un plan completo en el body, el sistema guarda el plan en la base de datos y retorna ID del plan y URL de detalle. Verificar que el plan se puede recuperar mediante GET /planes/<plan_id>.
- **Funcionalidad / Característica a evaluar:** Endpoint de guardado de planes funciona correctamente y persiste datos en base de datos
- **Datos de entrada / Acciones de entrada:**
  - Petición POST a /api/planes
  - Body JSON: { "paciente_id": 1, "estado": "borrador", "plan": { estructura completa del plan }, "configuracion": { parámetros de configuración }, "ingredientes": { filtros aplicados } }
  - Headers: Content-Type: application/json, Cookie con sesión activa
- **Resultado esperado:**
  - Status code 200 OK
  - Respuesta JSON: { "ok": true, "id": plan_id, "detalle_url": "/planes/<plan_id>" }
  - El plan se guarda en la base de datos
  - Se puede recuperar el plan mediante GET /planes/<plan_id>

**Requerimientos de ambiente de pruebas:**
- Equipo: Computadora con navegador web (Chrome, Firefox, Edge) o Postman
- Sistema: Aplicación web ejecutándose en localhost o servidor
- Usuario: Sesión activa de nutricionista o administrador
- Base de datos: PostgreSQL con tablas plan, plan_detalle, plan_alimento
- Conexión a internet: No requerida (si el sistema está en localhost)

**Condiciones / Restricciones:**
- Tener sesión de usuario activa (obtener cookie de sesión mediante login)
- Tener un plan nutricional generado (puede generarse previamente o incluirse en el body)
- El paciente_id debe existir en la base de datos

**Pasos de la prueba:**
1. Abrir Postman o DevTools del navegador (F12)
2. Realizar login en la aplicación para obtener cookie de sesión
3. Generar un plan nutricional previamente (o preparar estructura de plan en JSON)
4. En Postman: Crear nueva petición POST
   - URL: http://localhost:5000/api/planes
   - Método: POST
   - Headers: Content-Type: application/json, Cookie: [cookie de sesión]
   - Body (raw JSON) con estructura completa del plan:
     ```json
     {
       "paciente_id": 1,
       "estado": "borrador",
       "plan": {
         "dias": 7,
         "dia_1": { ... },
         "dia_2": { ... },
         ...
       },
       "configuracion": {
         "fecha_inicio": "2025-11-23",
         "fecha_fin": "2025-11-29",
         "kcal_obj": 2000
       },
       "ingredientes": {
         "grupos_excluidos": []
       }
     }
     ```
5. Enviar la petición
6. Verificar respuesta:
   - Status code debe ser 200
   - Response body debe contener ok: true, id: [número], detalle_url: "/planes/[id]"
7. Realizar petición GET a la URL retornada en detalle_url
8. Verificar que el plan se recupera correctamente con status 200

**Evidencia requerida (capturas de pantalla):**
1. **Captura 1:** Postman o DevTools mostrando la petición POST a /api/planes con:
   - URL completa
   - Headers (Content-Type, Cookie)
   - Body JSON (puede ser parcial si es muy largo, mostrar estructura principal)
2. **Captura 2:** Response de POST /api/planes mostrando:
   - Status code 200
   - Response body: { "ok": true, "id": [número], "detalle_url": "/planes/[id]" }
3. **Captura 3:** Petición GET a /planes/[id] mostrando:
   - URL completa
   - Status code 200
   - Response HTML o JSON con datos del plan guardado
4. **Captura 4 (opcional):** Verificación en base de datos (si se tiene acceso) mostrando registro en tabla plan con el id retornado

**Seguimiento:**
- **Código de prueba relacionado:** PCB01, PCB02
- **Estado anterior:** Pendiente
- **Resultado obtenido:** [A completar después de ejecutar]
- **Estado actual:** [A completar]
- **Observaciones:** [A completar]

---

## Resumen de Pruebas de Caja Blanca - Sprint 4

| Código | Caso de Prueba | Módulo | Estado | Herramienta |
|--------|----------------|--------|--------|-------------|
| PCB01 | Generación de plan con exclusión de grupos | Generación | Pendiente | Postman/DevTools |
| PCB02 | Configuración inteligente con ajuste ML | Configuración | Pendiente | Postman/DevTools |
| PCB03 | Guardado de plan en base de datos | Persistencia | Pendiente | Postman/DevTools |

**Notas importantes:**
- Todas las pruebas se realizan mediante peticiones HTTP usando Postman o DevTools del navegador
- Las capturas deben mostrar claramente la petición (Request) y la respuesta (Response)
- Se requiere sesión activa (cookie de sesión) para todas las peticiones
- Los resultados deben documentarse en la sección "Seguimiento" de cada prueba
- Las pruebas validan el comportamiento externo del sistema sin conocer la implementación interna
