"""
Script para preparar datos específicos para entrenar el Modelo 1: Predicción de Respuesta Glucémica.

Este script procesa los datos de CGMacros para crear un dataset donde:
- Input: Perfil del paciente + características de la comida
- Output: Respuesta glucémica postprandial (incremento, pico, tiempo hasta pico)
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

# Configuración de rutas
INPUT_FILE = r"D:\Sistema Tesis\data_para_entrenamiento\cgmacros_procesado.csv"
OUTPUT_FILE = r"D:\Sistema Tesis\data_para_entrenamiento\modelo1_respuesta_glucemica.csv"

def calcular_respuesta_glucemica(df_subject, timestamp_comida):
    """
    Calcula la respuesta glucémica postprandial después de una comida.
    
    Retorna:
    - glucose_baseline: Glucosa antes de la comida
    - glucose_peak: Pico de glucosa postprandial
    - glucose_increment: Incremento de glucosa (peak - baseline)
    - time_to_peak: Tiempo hasta el pico (minutos)
    - glucose_2h: Glucosa a las 2 horas
    """
    # Filtrar datos alrededor de la comida (30 min antes, 3 horas después)
    inicio = timestamp_comida - timedelta(minutes=30)
    fin = timestamp_comida + timedelta(hours=3)
    
    df_window = df_subject[
        (df_subject['Timestamp'] >= inicio) & 
        (df_subject['Timestamp'] <= fin)
    ].copy()
    
    if len(df_window) == 0:
        return None
    
    # Glucosa antes de la comida (promedio de 30 min antes)
    df_antes = df_window[df_window['Timestamp'] < timestamp_comida]
    if len(df_antes) > 0:
        glucose_baseline = df_antes['glucose'].mean()
    else:
        # Si no hay datos antes, usar el primer valor disponible
        glucose_baseline = df_window['glucose'].iloc[0] if pd.notna(df_window['glucose'].iloc[0]) else None
    
    if pd.isna(glucose_baseline) or glucose_baseline <= 0:
        return None
    
    # Glucosa después de la comida (hasta 3 horas)
    df_despues = df_window[df_window['Timestamp'] > timestamp_comida].copy()
    
    if len(df_despues) == 0:
        return None
    
    # Calcular tiempo desde la comida
    df_despues['minutos_desde_comida'] = (df_despues['Timestamp'] - timestamp_comida).dt.total_seconds() / 60
    
    # Filtrar solo valores válidos de glucosa
    df_despues = df_despues[df_despues['glucose'].notna() & (df_despues['glucose'] > 0) & (df_despues['glucose'] <= 400)]
    
    if len(df_despues) == 0:
        return None
    
    # Encontrar pico de glucosa
    idx_peak = df_despues['glucose'].idxmax()
    glucose_peak = df_despues.loc[idx_peak, 'glucose']
    time_to_peak = df_despues.loc[idx_peak, 'minutos_desde_comida']
    
    # Glucosa a las 2 horas (aproximada, buscar más cercana a 120 min)
    df_2h = df_despues.copy()
    df_2h['diff_2h'] = abs(df_2h['minutos_desde_comida'] - 120)
    idx_2h = df_2h['diff_2h'].idxmin()
    glucose_2h = df_despues.loc[idx_2h, 'glucose'] if df_2h.loc[idx_2h, 'diff_2h'] <= 30 else None
    
    # Incremento de glucosa
    glucose_increment = glucose_peak - glucose_baseline
    
    # Área bajo la curva (AUC) de glucosa postprandial (aproximación trapezoidal)
    df_auc = df_despues.sort_values('minutos_desde_comida')
    if len(df_auc) > 1:
        # Calcular AUC usando método trapezoidal
        tiempos = df_auc['minutos_desde_comida'].values
        glucosas = df_auc['glucose'].values
        auc = np.trapezoid(glucosas - glucose_baseline, tiempos)
    else:
        auc = None
    
    return {
        'glucose_baseline': glucose_baseline,
        'glucose_peak': glucose_peak,
        'glucose_increment': glucose_increment,
        'time_to_peak': time_to_peak,
        'glucose_2h': glucose_2h,
        'glucose_auc': auc
    }

def preparar_datos_modelo1():
    """
    Prepara datos para entrenar el modelo de predicción de respuesta glucémica.
    """
    print("=" * 70)
    print("🔧 PREPARANDO DATOS PARA MODELO 1: RESPUESTA GLUCÉMICA")
    print("=" * 70)
    print()
    
    # Cargar datos procesados
    print("📂 Cargando datos de CGMacros procesados...")
    try:
        df = pd.read_csv(INPUT_FILE, parse_dates=['Timestamp'], low_memory=False)
        print(f"  ✅ Cargadas {len(df):,} filas")
    except Exception as e:
        print(f"  ❌ Error cargando archivo: {e}")
        return
    
    print("\n🔄 Procesando datos de comidas y respuestas glucémicas...")
    
    # Filtrar solo filas con datos de comida
    df_comidas = df[
        (df['Meal Type'].notna()) & 
        (df['Meal Type'] != '') &
        (df['Calories'].notna()) & 
        (df['Calories'] > 0)
    ].copy()
    
    print(f"  ✅ Encontradas {len(df_comidas):,} comidas registradas")
    
    # Procesar cada comida para calcular respuesta glucémica
    datos_entrenamiento = []
    procesadas = 0
    
    for subject_id in df_comidas['subject_id'].unique():
        df_subject = df[df['subject_id'] == subject_id].copy()
        df_subject = df_subject.sort_values('Timestamp')
        
        # Obtener datos bioquímicos del sujeto (una sola vez)
        bio_subject = df_subject[
            df_subject['Age'].notna()
        ].iloc[0] if len(df_subject[df_subject['Age'].notna()]) > 0 else None
        
        if bio_subject is None:
            continue
        
        # Procesar cada comida del sujeto
        comidas_subject = df_comidas[df_comidas['subject_id'] == subject_id]
        
        for idx, comida in comidas_subject.iterrows():
            timestamp_comida = comida['Timestamp']
            
            # Calcular respuesta glucémica
            respuesta = calcular_respuesta_glucemica(df_subject, timestamp_comida)
            
            if respuesta is None:
                continue
            
            # Crear registro de entrenamiento
            registro = {
                # ID y contexto
                'subject_id': subject_id,
                'meal_timestamp': timestamp_comida,
                'meal_type': comida['Meal Type'],
                
                # Perfil del paciente
                'age': bio_subject['Age'] if pd.notna(bio_subject['Age']) else None,
                'gender': 1 if bio_subject['Gender'] == 'F' else 0 if bio_subject['Gender'] == 'M' else None,
                'bmi': bio_subject['BMI'] if pd.notna(bio_subject['BMI']) else None,
                'weight': bio_subject['Body weight '] if pd.notna(bio_subject['Body weight ']) else None,
                'height': bio_subject['Height '] if pd.notna(bio_subject['Height ']) else None,
                
                # Datos bioquímicos
                'a1c': bio_subject['A1c PDL (Lab)'] if pd.notna(bio_subject['A1c PDL (Lab)']) else None,
                'fasting_glucose': bio_subject['Fasting GLU - PDL (Lab)'] if pd.notna(bio_subject['Fasting GLU - PDL (Lab)']) else None,
                'insulin': bio_subject['Insulin '] if pd.notna(bio_subject['Insulin ']) else None,
                'homa_ir': bio_subject['HOMA_IR'] if pd.notna(bio_subject['HOMA_IR']) else None,
                'triglycerides': bio_subject['Triglycerides'] if pd.notna(bio_subject['Triglycerides']) else None,
                'cholesterol': bio_subject['Cholesterol'] if pd.notna(bio_subject['Cholesterol']) else None,
                'hdl': bio_subject['HDL'] if pd.notna(bio_subject['HDL']) else None,
                'ldl': bio_subject['LDL (Cal)'] if pd.notna(bio_subject['LDL (Cal)']) else None,
                'tg_hdl_ratio': bio_subject['TG_HDL_ratio'] if pd.notna(bio_subject['TG_HDL_ratio']) else None,
                
                # Características de la comida
                'calories': comida['Calories'] if pd.notna(comida['Calories']) else None,
                'carbs': comida['Carbs'] if pd.notna(comida['Carbs']) else 0,
                'protein': comida['Protein'] if pd.notna(comida['Protein']) else 0,
                'fat': comida['Fat'] if pd.notna(comida['Fat']) else 0,
                'fiber': comida['Fiber'] if pd.notna(comida['Fiber']) else 0,
                'amount_consumed': comida['Amount Consumed '] if pd.notna(comida['Amount Consumed ']) else 100,
                
                # Contexto temporal
                'hora': timestamp_comida.hour,
                'dia_semana': timestamp_comida.strftime('%A'),
                'tiempo_desde_ultima_comida': comida['tiempo_desde_comida'] if pd.notna(comida['tiempo_desde_comida']) else None,
                
                # Actividad física antes de la comida
                'hr_before': None,  # Se calculará después
                'activity_before': None,  # Se calculará después
                
                # Targets (respuesta glucémica)
                'glucose_baseline': respuesta['glucose_baseline'],
                'glucose_peak': respuesta['glucose_peak'],
                'glucose_increment': respuesta['glucose_increment'],
                'time_to_peak': respuesta['time_to_peak'],
                'glucose_2h': respuesta['glucose_2h'],
                'glucose_auc': respuesta['glucose_auc']
            }
            
            # Calcular actividad física antes de la comida (promedio de 1 hora antes)
            df_antes_1h = df_subject[
                (df_subject['Timestamp'] >= timestamp_comida - timedelta(hours=1)) &
                (df_subject['Timestamp'] < timestamp_comida)
            ]
            if len(df_antes_1h) > 0:
                registro['hr_before'] = df_antes_1h['HR'].mean() if df_antes_1h['HR'].notna().any() else None
                registro['activity_before'] = df_antes_1h['Calories (Activity)'].sum() if df_antes_1h['Calories (Activity)'].notna().any() else None
            
            datos_entrenamiento.append(registro)
            procesadas += 1
            
            if procesadas % 100 == 0:
                print(f"  ✅ Procesadas {procesadas:,} comidas...")
    
    print(f"\n  ✅ Total de comidas procesadas: {procesadas:,}")
    
    # Crear DataFrame final
    print("\n🔗 Creando dataset final...")
    df_final = pd.DataFrame(datos_entrenamiento)
    
    # Codificar día de la semana
    dias_map = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 
                'Friday': 4, 'Saturday': 5, 'Sunday': 6}
    df_final['dia_semana_encoded'] = df_final['dia_semana'].map(dias_map)
    
    # Codificar tipo de comida
    meal_type_map = {'Breakfast': 0, 'Lunch': 1, 'Dinner': 2}
    df_final['meal_type_encoded'] = df_final['meal_type'].map(meal_type_map)
    
    # Calcular características derivadas
    df_final['carbs_per_100cal'] = (df_final['carbs'] * 4 / df_final['calories'] * 100).replace([np.inf, -np.inf], np.nan)
    df_final['protein_per_100cal'] = (df_final['protein'] * 4 / df_final['calories'] * 100).replace([np.inf, -np.inf], np.nan)
    df_final['fat_per_100cal'] = (df_final['fat'] * 9 / df_final['calories'] * 100).replace([np.inf, -np.inf], np.nan)
    df_final['fiber_per_100cal'] = (df_final['fiber'] / df_final['calories'] * 100).replace([np.inf, -np.inf], np.nan)
    
    # Filtrar registros con datos completos esenciales
    columnas_esenciales = ['age', 'bmi', 'calories', 'carbs', 'glucose_baseline', 
                          'glucose_peak', 'glucose_increment']
    df_final = df_final.dropna(subset=columnas_esenciales)
    
    # Guardar
    print(f"\n💾 Guardando dataset en: {OUTPUT_FILE}")
    df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    
    # Estadísticas
    tamaño_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    
    print("\n" + "=" * 70)
    print("✅ PREPARACIÓN COMPLETA")
    print("=" * 70)
    print(f"📊 Estadísticas:")
    print(f"  - Registros finales: {len(df_final):,}")
    print(f"  - Sujetos únicos: {df_final['subject_id'].nunique()}")
    print(f"  - Columnas: {len(df_final.columns)}")
    print(f"  - Archivo: {OUTPUT_FILE}")
    print(f"  - Tamaño: {tamaño_mb:.2f} MB")
    
    print(f"\n📋 Columnas del dataset:")
    for col in df_final.columns:
        print(f"  - {col}")
    
    print(f"\n📊 Resumen estadístico de targets:")
    print(df_final[['glucose_baseline', 'glucose_peak', 'glucose_increment', 
                    'time_to_peak', 'glucose_2h']].describe())
    
    print("\n" + "=" * 70)
    print("✅ FIN DE LA PREPARACIÓN")
    print("=" * 70)

if __name__ == "__main__":
    preparar_datos_modelo1()

