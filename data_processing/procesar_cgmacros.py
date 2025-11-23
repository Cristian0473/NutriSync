"""
Script para procesar el dataset CGMacros y extraer datos relevantes para entrenamiento ML.
Combina datos de CGM, comidas, actividad física y datos bioquímicos.
"""

import pandas as pd
import os
import glob
from pathlib import Path
from datetime import datetime
import numpy as np

# Configuración de rutas
BASE_DIR = r"D:\Sistema Tesis\CGMacros\CGMacros_dateshifted365\CGMacros"
OUTPUT_DIR = r"D:\Sistema Tesis\data_para_entrenamiento"
BIO_FILE = os.path.join(BASE_DIR, "bio.csv")
GUT_HEALTH_FILE = os.path.join(BASE_DIR, "gut_health_test.csv")
MICROBES_FILE = os.path.join(BASE_DIR, "microbes.csv")

def procesar_cgmacros():
    """
    Procesa todos los archivos CGMacros y genera un dataset consolidado.
    """
    print("=" * 70)
    print("🔧 PROCESANDO CGMacros Dataset")
    print("=" * 70)
    print()
    
    # Crear directorio de salida si no existe
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Cargar datos bioquímicos
    print("📊 Cargando datos bioquímicos...")
    try:
        bio_df = pd.read_csv(BIO_FILE)
        print(f"  ✅ Cargados datos de {len(bio_df)} sujetos")
    except Exception as e:
        print(f"  ⚠️  Error cargando bio.csv: {e}")
        bio_df = None
    
    # 2. Encontrar todos los archivos CGMacros
    print("\n📂 Buscando archivos CGMacros...")
    cgmacros_pattern = os.path.join(BASE_DIR, "CGMacros-*", "CGMacros-*.csv")
    archivos = glob.glob(cgmacros_pattern)
    archivos.sort()
    
    print(f"  ✅ Encontrados {len(archivos)} archivos")
    print()
    
    # 3. Procesar cada archivo
    print("🔄 Procesando archivos...")
    print()
    
    todos_datos = []
    errores = 0
    
    for idx, archivo in enumerate(archivos, 1):
        try:
            # Extraer número de sujeto del nombre del archivo
            # Ejemplo: CGMacros-001.csv -> subject_id = 1
            nombre_archivo = os.path.basename(archivo)
            subject_id = int(nombre_archivo.replace("CGMacros-", "").replace(".csv", ""))
            
            # Leer archivo
            df = pd.read_csv(archivo)
            
            # Agregar subject_id
            df['subject_id'] = subject_id
            
            # Obtener datos bioquímicos del sujeto si están disponibles
            if bio_df is not None:
                bio_subject = bio_df[bio_df['subject'] == subject_id]
                if not bio_subject.empty:
                    # Agregar datos bioquímicos como columnas
                    for col in ['Age', 'Gender', 'BMI', 'Body weight ', 'Height ', 
                               'A1c PDL (Lab)', 'Fasting GLU - PDL (Lab)', 'Insulin ',
                               'Triglycerides', 'Cholesterol', 'HDL', 'LDL (Cal)']:
                        if col in bio_subject.columns:
                            df[col] = bio_subject[col].iloc[0]
            
            # Procesar timestamp
            if 'Timestamp' in df.columns:
                df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
                df['fecha'] = df['Timestamp'].dt.date
                df['hora'] = df['Timestamp'].dt.time
                df['dia_semana'] = df['Timestamp'].dt.day_name()
            
            # Limpiar y convertir valores numéricos
            columnas_numericas = ['Libre GL', 'Dexcom GL', 'HR', 'Calories (Activity)', 
                                 'METs', 'Calories', 'Carbs', 'Protein', 'Fat', 'Fiber',
                                 'Amount Consumed ']
            
            for col in columnas_numericas:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Crear columna de glucosa (preferir Dexcom, si no Libre)
            if 'Dexcom GL' in df.columns and 'Libre GL' in df.columns:
                df['glucose'] = df['Dexcom GL'].fillna(df['Libre GL'])
            elif 'Dexcom GL' in df.columns:
                df['glucose'] = df['Dexcom GL']
            elif 'Libre GL' in df.columns:
                df['glucose'] = df['Libre GL']
            
            # Mantener todas las filas con datos relevantes (glucosa o comida)
            # Filtrar filas que tengan al menos glucosa o datos de comida
            tiene_glucosa = df['glucose'].notna() & (df['glucose'] > 0) & (df['glucose'] <= 400)
            tiene_comida = df['Meal Type'].notna() & (df['Meal Type'] != '')
            
            df_relevante = df[tiene_glucosa | tiene_comida].copy()
            
            if len(df_relevante) > 0:
                todos_datos.append(df_relevante)
                print(f"  ✅ Procesado {nombre_archivo}: {len(df_relevante)} filas relevantes")
            else:
                print(f"  ⚠️  {nombre_archivo}: Sin datos relevantes")
            
        except Exception as e:
            errores += 1
            print(f"  ❌ Error procesando {archivo}: {e}")
    
    print()
    
    # 4. Consolidar todos los datos
    if not todos_datos:
        print("❌ No se encontraron datos para procesar")
        return
    
    print("🔗 Consolidando datos...")
    df_final = pd.concat(todos_datos, ignore_index=True)
    
    # Ordenar por subject_id y timestamp
    df_final = df_final.sort_values(['subject_id', 'Timestamp']).reset_index(drop=True)
    
    # Crear características adicionales útiles para ML
    print("🔧 Creando características adicionales...")
    
    # Calcular cambios en glucosa (delta)
    df_final['glucose_delta'] = df_final.groupby('subject_id')['glucose'].diff()
    
    # Tiempo desde última comida (en minutos)
    df_final['tiempo_desde_comida'] = None
    for subject_id in df_final['subject_id'].unique():
        mask_subject = df_final['subject_id'] == subject_id
        df_subject = df_final[mask_subject].copy()
        
        # Encontrar timestamps de comidas
        comidas_mask = df_subject['Meal Type'].notna() & (df_subject['Meal Type'] != '')
        if comidas_mask.any():
            timestamps_comidas = df_subject.loc[comidas_mask, 'Timestamp']
            
            # Calcular tiempo desde última comida para cada fila
            for idx in df_subject.index:
                timestamp_actual = df_subject.loc[idx, 'Timestamp']
                if pd.notna(timestamp_actual):
                    comidas_anteriores = timestamps_comidas[timestamps_comidas <= timestamp_actual]
                    if len(comidas_anteriores) > 0:
                        ultima_comida = comidas_anteriores.max()
                        tiempo_diff = (timestamp_actual - ultima_comida).total_seconds() / 60
                        df_final.loc[idx, 'tiempo_desde_comida'] = tiempo_diff
    
    # Clasificar glucosa (normal, pre-diabetes, diabetes)
    def clasificar_glucosa(glucosa):
        if pd.isna(glucosa):
            return None
        if glucosa < 100:
            return 'normal'
        elif glucosa < 126:
            return 'pre_diabetes'
        else:
            return 'diabetes'
    
    df_final['glucose_category'] = df_final['glucose'].apply(clasificar_glucosa)
    
    # Calcular HOMA-IR si tenemos insulina y glucosa en ayunas
    if 'Insulin ' in df_final.columns and 'Fasting GLU - PDL (Lab)' in df_final.columns:
        # HOMA-IR = (Glucosa en ayunas * Insulina) / 405
        df_final['HOMA_IR'] = (df_final['Fasting GLU - PDL (Lab)'] * df_final['Insulin ']) / 405
    
    # Ratio TG/HDL (marcador de resistencia a insulina)
    if 'Triglycerides' in df_final.columns and 'HDL' in df_final.columns:
        df_final['TG_HDL_ratio'] = df_final['Triglycerides'] / df_final['HDL'].replace(0, np.nan)
    
    # Seleccionar columnas relevantes para ML
    columnas_finales = [
        'subject_id', 'Timestamp', 'fecha', 'hora', 'dia_semana',
        'glucose', 'glucose_delta', 'glucose_category', 'Libre GL', 'Dexcom GL',
        'HR', 'Calories (Activity)', 'METs',
        'Meal Type', 'Calories', 'Carbs', 'Protein', 'Fat', 'Fiber', 'Amount Consumed ',
        'tiempo_desde_comida',
        'Age', 'Gender', 'BMI', 'Body weight ', 'Height ',
        'A1c PDL (Lab)', 'Fasting GLU - PDL (Lab)', 'Insulin ', 'HOMA_IR',
        'Triglycerides', 'Cholesterol', 'HDL', 'LDL (Cal)', 'TG_HDL_ratio'
    ]
    
    # Mantener solo columnas que existen
    columnas_existentes = [col for col in columnas_finales if col in df_final.columns]
    df_final = df_final[columnas_existentes]
    
    # 5. Guardar archivo final
    archivo_salida = os.path.join(OUTPUT_DIR, "cgmacros_procesado.csv")
    print(f"\n💾 Guardando archivo final: {archivo_salida}")
    df_final.to_csv(archivo_salida, index=False, encoding='utf-8')
    
    # 6. Estadísticas
    print("\n📊 Calculando estadísticas...")
    tamaño_mb = os.path.getsize(archivo_salida) / (1024 * 1024)
    
    print("\n" + "=" * 70)
    print("✅ PROCESAMIENTO COMPLETO")
    print("=" * 70)
    print(f"📊 Estadísticas:")
    print(f"  - Archivos procesados: {len(archivos)}")
    print(f"  - Errores: {errores}")
    print(f"  - Filas totales: {len(df_final):,}")
    print(f"  - Sujetos únicos: {df_final['subject_id'].nunique()}")
    print(f"  - Fechas únicas: {df_final['fecha'].nunique() if 'fecha' in df_final.columns else 'N/A'}")
    print(f"  - Archivo final: {archivo_salida}")
    print(f"  - Tamaño: {tamaño_mb:.2f} MB")
    
    # Mostrar muestra de datos
    print(f"\n📋 Resumen del dataset procesado (muestra de 10k filas):")
    print(df_final.head(10000).to_string())
    
    print(f"\n📈 Columnas: {list(df_final.columns)}")
    print(f"\n📊 Forma: ({len(df_final):,} filas, {len(df_final.columns)} columnas)")
    
    print("\n" + "=" * 70)
    print("✅ FIN DEL PROCESAMIENTO")
    print("=" * 70)

if __name__ == "__main__":
    procesar_cgmacros()

