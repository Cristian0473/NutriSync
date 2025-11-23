# Estructura de Organización de Archivos

## 📁 Estructura Propuesta

```
Sistema Tesis/
│
├── 📄 main.py                          [MANTENER EN RAÍZ - Aplicación principal Flask]
├── 📄 requirements.txt                 [MANTENER EN RAÍZ - Dependencias]
├── 📄 readme.md                        [MANTENER EN RAÍZ - README principal]
│
├── 📁 core/                            [NUEVA - Código principal del sistema]
│   ├── motor_recomendacion.py
│   ├── motor_recomendacion_basico.py   [✅ SE USA - Mantener]
│   ├── motor_ia_recomendaciones.py    [⚠️ NO SE USA - Opcional eliminar]
│   ├── optimizador_plan.py
│   ├── bd_conexion.py
│   └── user.py
│
├── 📁 ml/                              [NUEVA - Machine Learning]
│   ├── preparar_datos_modelo1_respuesta_glucemica.py
│   ├── preparar_datos_modelo2_seleccion_alimentos.py
│   ├── preparar_datos_modelo3_combinaciones.py
│   ├── entrenar_modelo1_respuesta_glucemica.py
│   ├── entrenar_modelo2_seleccion_alimentos.py
│   ├── entrenar_modelo3_combinaciones.py
│   ├── pipeline_completo_ml.py
│   └── contar_registros_modelo2.py
│
├── 📁 data_processing/                 [NUEVA - Procesamiento de datos]
│   ├── explorar_datasets.py
│   ├── explorar_mfp.py
│   ├── procesar_mfp.py
│   └── procesar_cgmacros.py
│
├── 📁 aprendizaje/                     [NUEVA - Aprendizaje continuo]
│   ├── aprendizaje_continuo.py
│   ├── integracion_aprendizaje.py
│   ├── diagnostico_aprendizaje.py
│   ├── verificar_aprendizaje.py
│   └── tarea_reentrenamiento.py
│
├── 📁 utils/                           [NUEVA - Utilidades]
│   ├── capturar_logs.py
│   ├── capturar_logs_flask.py
│   ├── envio_email.py
│   └── iniciar_servidor.py
│
├── 📁 scripts/                         [YA EXISTE - Scripts]
│   └── ejecutar_pipeline.bat           [MOVER aquí]
│
├── 📁 docs/                            [NUEVA - Documentación]
│   ├── analisis/                       [Análisis y estudios]
│   │   ├── ANALISIS_PLANES_GENERADOS.md
│   │   ├── ANALISIS_CUMPLIMIENTO_GRASAS.md
│   │   ├── ANALISIS_DATASETS_CHAT.md
│   │   ├── ANALISIS_DATASETS_ENCONTRADOS.md
│   │   ├── ANALISIS_GUIA_INTERCAMBIO.md
│   │   ├── ANALISIS_INTERVENCION_ML.md
│   │   ├── ANALISIS_MEJORAS_MODELOS_ML.md
│   │   ├── ANALISIS_SEGUIMIENTO_HISTORICO.md
│   │   └── ANALISIS_VALORES_NUTRICIONALES.md
│   │
│   ├── estrategias/                    [Estrategias y planes]
│   │   ├── ESTRATEGIA_COMBINACION_DATASETS.md
│   │   ├── PROCESAMIENTO_DATASETS.md
│   │   ├── DATOS_NECESARIOS_DATASETS.md
│   │   ├── COMPARACION_3_DATASETS.md
│   │   ├── VIABILIDAD_REALISTA_36HORAS.md
│   │   └── VIABILIDAD_TIEMPO_ESTRATEGIA3.md
│   │
│   ├── resumenes/                      [Resúmenes ejecutivos]
│   │   ├── RESUMEN_ASEROR_ML.md
│   │   └── RESUMEN_CAMBIOS_SEGUIMIENTO.md
│   │
│   ├── guias/                          [Guías y tutoriales]
│   │   ├── EXPLICACION_MODELOS_ML.md
│   │   ├── FUNCIONAMIENTO_SISTEMA.md
│   │   ├── GUIA_API_OPENAI.md
│   │   ├── INTEGRACION_IA.md
│   │   ├── INTERVENCION_ML_DECISIONES_CRITICAS.md
│   │   ├── OPTIMIZADOR_PLAN.md
│   │   ├── APRENDIZAJE_CONTINUO.md
│   │   ├── LEER_LOGS.md
│   │   ├── CONFIGURAR_EMAIL.md
│   │   ├── CONFIGURAR_EMAIL_PASO_A_PASO.md
│   │   └── SOLUCIONAR_ERROR_EMAIL.md
│   │
│   └── logs/                           [Logs del sistema]
│       └── logs_sistema.md
│
├── 📁 templates/                       [YA EXISTE - Plantillas HTML]
├── 📁 static/                          [YA EXISTE - Archivos estáticos]
├── 📁 SQL/                             [YA EXISTE - Scripts SQL]
├── 📁 Docs/                            [YA EXISTE - Documentación técnica]
├── 📁 ApartadoInteligente/             [YA EXISTE - Modelos ML]
├── 📁 planes_guardados/                [YA EXISTE - Planes JSON]
└── 📁 ejemploRecomend/                 [YA EXISTE - Ejemplos]
```

---

## 🗑️ Archivos que PODRÍAS ELIMINAR (verificar primero)

### ✅ Verificación realizada:

1. **`motor_recomendacion_basico.py`**
   - **Estado:** ✅ **SE USA** - Importado en `main.py` y `iniciar_servidor.py`
   - **Acción:** **NO ELIMINAR** - Mantener en `core/`

2. **`motor_ia_recomendaciones.py`**
   - **Estado:** ⚠️ **NO SE USA** en código activo (no importado en `main.py`)
   - **Razón:** Parece ser código obsoleto de cuando se usaba ChatGPT
   - **Acción:** **PUEDES ELIMINAR** si estás seguro de que no lo necesitas, o moverlo a `docs/legacy/` por si acaso

3. **Archivos en `ejemploRecomend/`**
   - **Razón:** Son ejemplos de planes guardados
   - **Acción:** Si son solo ejemplos de prueba, puedes eliminarlos

4. **Algunos planes antiguos en `planes_guardados/`**
   - **Razón:** Planes de prueba antiguos
   - **Acción:** Conservar solo los más recientes o importantes

---

## 📋 Resumen de Movimientos

### Archivos que SE QUEDAN en la raíz:
- `main.py` (aplicación principal)
- `requirements.txt` (dependencias)
- `readme.md` (README)

### Archivos a mover a `core/`:
- `motor_recomendacion.py`
- `motor_recomendacion_basico.py` (✅ se usa en main.py)
- `motor_ia_recomendaciones.py` (⚠️ no se usa - opcional eliminar)
- `optimizador_plan.py`
- `bd_conexion.py`
- `user.py`

### Archivos a mover a `ml/`:
- `preparar_datos_modelo1_respuesta_glucemica.py`
- `preparar_datos_modelo2_seleccion_alimentos.py`
- `preparar_datos_modelo3_combinaciones.py`
- `entrenar_modelo1_respuesta_glucemica.py`
- `entrenar_modelo2_seleccion_alimentos.py`
- `entrenar_modelo3_combinaciones.py`
- `pipeline_completo_ml.py`
- `contar_registros_modelo2.py`

### Archivos a mover a `data_processing/`:
- `explorar_datasets.py`
- `explorar_mfp.py`
- `procesar_mfp.py`
- `procesar_cgmacros.py`

### Archivos a mover a `aprendizaje/`:
- `aprendizaje_continuo.py`
- `integracion_aprendizaje.py`
- `diagnostico_aprendizaje.py`
- `verificar_aprendizaje.py`
- `tarea_reentrenamiento.py`

### Archivos a mover a `utils/`:
- `capturar_logs.py`
- `capturar_logs_flask.py`
- `envio_email.py`
- `iniciar_servidor.py`

### Archivos a mover a `scripts/`:
- `ejecutar_pipeline.bat`

### Archivos a mover a `docs/analisis/`:
- `ANALISIS_PLANES_GENERADOS.md`
- `ANALISIS_CUMPLIMIENTO_GRASAS.md`
- `ANALISIS_DATASETS_CHAT.md`
- `ANALISIS_DATASETS_ENCONTRADOS.md`
- `ANALISIS_GUIA_INTERCAMBIO.md`
- `ANALISIS_INTERVENCION_ML.md`
- `ANALISIS_MEJORAS_MODELOS_ML.md`
- `ANALISIS_SEGUIMIENTO_HISTORICO.md`
- `ANALISIS_VALORES_NUTRICIONALES.md`

### Archivos a mover a `docs/estrategias/`:
- `ESTRATEGIA_COMBINACION_DATASETS.md`
- `PROCESAMIENTO_DATASETS.md`
- `DATOS_NECESARIOS_DATASETS.md`
- `COMPARACION_3_DATASETS.md`
- `VIABILIDAD_REALISTA_36HORAS.md`
- `VIABILIDAD_TIEMPO_ESTRATEGIA3.md`

### Archivos a mover a `docs/resumenes/`:
- `RESUMEN_ASEROR_ML.md`
- `RESUMEN_CAMBIOS_SEGUIMIENTO.md`

### Archivos a mover a `docs/guias/`:
- `EXPLICACION_MODELOS_ML.md`
- `FUNCIONAMIENTO_SISTEMA.md`
- `GUIA_API_OPENAI.md`
- `INTEGRACION_IA.md`
- `INTERVENCION_ML_DECISIONES_CRITICAS.md`
- `OPTIMIZADOR_PLAN.md`
- `APRENDIZAJE_CONTINUO.md`
- `LEER_LOGS.md`
- `CONFIGURAR_EMAIL.md`
- `CONFIGURAR_EMAIL_PASO_A_PASO.md`
- `SOLUCIONAR_ERROR_EMAIL.md`

### Archivos a mover a `docs/logs/`:
- `logs_sistema.md`

---

## ⚠️ IMPORTANTE: Después de mover archivos

### 1. Actualizar imports en Python:
Después de mover los archivos, necesitarás actualizar los imports en:
- `main.py` (importar desde `core.motor_recomendacion`, etc.)
- Otros archivos que importen estos módulos

### 2. Actualizar rutas en scripts:
- `ejecutar_pipeline.bat` (si tiene rutas relativas)

### 3. Verificar archivos antes de eliminar:
```bash
# Buscar uso de motor_recomendacion_basico
grep -r "motor_recomendacion_basico" .

# Buscar uso de motor_ia_recomendaciones
grep -r "motor_ia_recomendaciones" .
```

---

## ✅ Ventajas de esta organización:

1. **Código principal separado** (`core/`) - Fácil de encontrar
2. **ML separado** (`ml/`) - Todo lo relacionado con modelos
3. **Documentación organizada** (`docs/`) - Por categorías
4. **Utilidades separadas** (`utils/`) - Scripts auxiliares
5. **Raíz limpia** - Solo archivos esenciales

