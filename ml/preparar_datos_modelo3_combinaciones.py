"""
Script para preparar datos específicos para entrenar el Modelo 3: Optimización de Combinaciones.

Este script procesa datos de CGMacros para crear un dataset donde:
- Input: Perfil del paciente + combinación de alimentos (lista de alimentos con cantidades)
- Output: Score de calidad de la combinación (basado en respuesta glucémica total)
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from itertools import combinations

# Configuración de rutas
CGMACROS_FILE = r"D:\Sistema Tesis\data_para_entrenamiento\cgmacros_procesado.csv"
OUTPUT_FILE = r"D:\Sistema Tesis\data_para_entrenamiento\modelo3_combinaciones.csv"

def calcular_respuesta_combinacion(df_subject, timestamps_comidas, ventana_horas=3):
    """
    Calcula la respuesta glucémica total de una combinación de comidas consumidas
    en un período corto (ej: desayuno completo con varios platos).
    
    Retorna métricas agregadas de la respuesta glucémica.
    """
    if len(timestamps_comidas) == 0:
        return None
    
    # Definir ventana de análisis (desde primera comida hasta ventana_horas después de la última)
    primera_comida = min(timestamps_comidas)
    ultima_comida = max(timestamps_comidas)
    inicio = primera_comida - timedelta(minutes=30)
    fin = ultima_comida + timedelta(hours=ventana_horas)
    
    # Filtrar datos en la ventana
    df_window = df_subject[
        (df_subject['Timestamp'] >= inicio) & 
        (df_subject['Timestamp'] <= fin)
    ].copy()
    
    if len(df_window) == 0:
        return None
    
    # Glucosa baseline (antes de la primera comida)
    df_antes = df_window[df_window['Timestamp'] < primera_comida]
    if len(df_antes) > 0:
        glucose_baseline = df_antes['glucose'].mean()
    else:
        glucose_baseline = df_window['glucose'].iloc[0] if len(df_window) > 0 and pd.notna(df_window['glucose'].iloc[0]) else None
    
    if pd.isna(glucose_baseline) or glucose_baseline <= 0:
        return None
    
    # Glucosa después de las comidas
    df_despues = df_window[df_window['Timestamp'] > primera_comida].copy()
    df_despues = df_despues[df_despues['glucose'].notna() & (df_despues['glucose'] > 0) & (df_despues['glucose'] <= 400)]
    
    if len(df_despues) == 0:
        return None
    
    # Calcular métricas
    glucose_peak = df_despues['glucose'].max()
    glucose_increment = glucose_peak - glucose_baseline
    
    # Calcular tiempo hasta el pico
    idx_peak = df_despues['glucose'].idxmax()
    time_to_peak = (df_despues.loc[idx_peak, 'Timestamp'] - primera_comida).total_seconds() / 60
    
    # Glucosa promedio postprandial
    glucose_avg_post = df_despues['glucose'].mean()
    
    # Área bajo la curva (AUC)
    df_despues = df_despues.sort_values('Timestamp')
    df_despues['minutos_desde_primera'] = (df_despues['Timestamp'] - primera_comida).dt.total_seconds() / 60
    tiempos = df_despues['minutos_desde_primera'].values
    glucosas = df_despues['glucose'].values
    auc = np.trapz(glucosas - glucose_baseline, tiempos) if len(tiempos) > 1 else None
    
    # Variabilidad de glucosa (desviación estándar)
    glucose_std = df_despues['glucose'].std()
    
    # Calcular score de calidad (0-1): menor incremento y variabilidad = mejor
    if glucose_increment < 20:
        score_incremento = 1.0
    elif glucose_increment < 40:
        score_incremento = 0.8
    elif glucose_increment < 60:
        score_incremento = 0.6
    elif glucose_increment < 80:
        score_incremento = 0.4
    else:
        score_incremento = 0.2
    
    if glucose_std < 10:
        score_variabilidad = 1.0
    elif glucose_std < 20:
        score_variabilidad = 0.8
    elif glucose_std < 30:
        score_variabilidad = 0.6
    else:
        score_variabilidad = 0.4
    
    score_calidad = (score_incremento * 0.7 + score_variabilidad * 0.3)
    
    return {
        'glucose_baseline': glucose_baseline,
        'glucose_peak': glucose_peak,
        'glucose_increment': glucose_increment,
        'glucose_avg_post': glucose_avg_post,
        'glucose_std': glucose_std,
        'time_to_peak': time_to_peak,
        'glucose_auc': auc,
        'score_calidad': score_calidad
    }

def preparar_datos_modelo3():
    """
    Prepara datos para entrenar el modelo de optimización de combinaciones.
    """
    print("=" * 70)
    print("🔧 PREPARANDO DATOS PARA MODELO 3: OPTIMIZACIÓN DE COMBINACIONES")
    print("=" * 70)
    print()
    
    # Cargar datos de CGMacros
    print("📂 Cargando datos de CGMacros...")
    try:
        df = pd.read_csv(CGMACROS_FILE, parse_dates=['Timestamp'], low_memory=False)
        print(f"  ✅ Cargadas {len(df):,} filas")
    except Exception as e:
        print(f"  ❌ Error cargando archivo: {e}")
        return
    
    print("\n🔄 Procesando combinaciones de comidas...")
    
    # Filtrar comidas con datos completos
    df_comidas = df[
        (df['Meal Type'].notna()) &
        (df['Meal Type'] != '') &
        (df['Calories'].notna()) &
        (df['Calories'] > 0) &
        (df['Carbs'].notna()) &
        (df['Protein'].notna()) &
        (df['Fat'].notna())
    ].copy()
    
    print(f"  ✅ Encontradas {len(df_comidas):,} comidas con datos completos")
    
    datos_entrenamiento = []
    procesadas = 0
    
    # Para cada sujeto, agrupar comidas por día y crear combinaciones
    for subject_id in df_comidas['subject_id'].unique():
        df_subject = df[df['subject_id'] == subject_id].copy()
        df_subject = df_subject.sort_values('Timestamp')
        
        # Obtener perfil del paciente
        bio_subject = df_subject[df_subject['Age'].notna()].iloc[0] if len(df_subject[df_subject['Age'].notna()]) > 0 else None
        if bio_subject is None:
            continue
        
        # Obtener comidas del sujeto
        comidas_subject = df_comidas[df_comidas['subject_id'] == subject_id].copy()
        comidas_subject['fecha'] = comidas_subject['Timestamp'].dt.date
        
        # Agrupar comidas por día y tipo de comida
        for fecha in comidas_subject['fecha'].unique():
            comidas_dia = comidas_subject[comidas_subject['fecha'] == fecha].copy()
            
            # Agrupar comidas del mismo tipo que estén cerca en el tiempo (dentro de 1 hora)
            # Esto representa una "comida completa" con varios platos
            comidas_dia = comidas_dia.sort_values('Timestamp')
            
            # Crear grupos de comidas cercanas (combinaciones)
            grupos = []
            grupo_actual = []
            timestamp_anterior = None
            
            for idx, comida in comidas_dia.iterrows():
                timestamp = comida['Timestamp']
                
                if timestamp_anterior is None:
                    grupo_actual = [comida]
                elif (timestamp - timestamp_anterior).total_seconds() / 60 <= 60:  # Dentro de 1 hora
                    grupo_actual.append(comida)
                else:
                    if len(grupo_actual) > 0:
                        grupos.append(grupo_actual)
                    grupo_actual = [comida]
                
                timestamp_anterior = timestamp
            
            if len(grupo_actual) > 0:
                grupos.append(grupo_actual)
            
            # Procesar cada grupo (combinación de comidas)
            for grupo in grupos:
                if len(grupo) < 1:  # Necesitamos al menos 1 comida
                    continue
                
                # Calcular características agregadas de la combinación
                timestamps_comidas = [c['Timestamp'] for c in grupo]
                
                # Sumar macronutrientes de todas las comidas del grupo
                total_calories = sum(c['Calories'] for c in grupo if pd.notna(c['Calories']))
                total_carbs = sum(c['Carbs'] for c in grupo if pd.notna(c['Carbs']))
                total_protein = sum(c['Protein'] for c in grupo if pd.notna(c['Protein']))
                total_fat = sum(c['Fat'] for c in grupo if pd.notna(c['Fat']))
                total_fiber = sum(c['Fiber'] for c in grupo if pd.notna(c['Fiber']))
                
                # Calcular respuesta glucémica de la combinación
                respuesta = calcular_respuesta_combinacion(df_subject, timestamps_comidas)
                
                if respuesta is None:
                    continue
                
                # Crear registro
                registro = {
                    # Identificación
                    'subject_id': subject_id,
                    'fecha': fecha,
                    'n_comidas_combinadas': len(grupo),
                    
                    # Perfil del paciente
                    'age': bio_subject['Age'] if pd.notna(bio_subject['Age']) else None,
                    'gender': 1 if bio_subject['Gender'] == 'F' else 0 if bio_subject['Gender'] == 'M' else None,
                    'bmi': bio_subject['BMI'] if pd.notna(bio_subject['BMI']) else None,
                    'a1c': bio_subject['A1c PDL (Lab)'] if pd.notna(bio_subject['A1c PDL (Lab)']) else None,
                    'fasting_glucose': bio_subject['Fasting GLU - PDL (Lab)'] if pd.notna(bio_subject['Fasting GLU - PDL (Lab)']) else None,
                    'homa_ir': bio_subject['HOMA_IR'] if pd.notna(bio_subject['HOMA_IR']) else None,
                    
                    # Características de la combinación (agregadas)
                    'total_calories': total_calories,
                    'total_carbs': total_carbs,
                    'total_protein': total_protein,
                    'total_fat': total_fat,
                    'total_fiber': total_fiber,
                    
                    # Proporciones
                    'carbs_percent': (total_carbs * 4 / total_calories * 100) if total_calories > 0 else 0,
                    'protein_percent': (total_protein * 4 / total_calories * 100) if total_calories > 0 else 0,
                    'fat_percent': (total_fat * 9 / total_calories * 100) if total_calories > 0 else 0,
                    
                    # Diversidad nutricional (número de tipos de comida diferentes)
                    'tipos_comida': len(set(c['Meal Type'] for c in grupo if pd.notna(c['Meal Type']))),
                    
                    # Contexto temporal
                    'hora_primera_comida': timestamps_comidas[0].hour,
                    'duracion_combinacion': (max(timestamps_comidas) - min(timestamps_comidas)).total_seconds() / 60,
                    
                    # Targets (respuesta glucémica de la combinación)
                    'glucose_baseline': respuesta['glucose_baseline'],
                    'glucose_peak': respuesta['glucose_peak'],
                    'glucose_increment': respuesta['glucose_increment'],
                    'glucose_avg_post': respuesta['glucose_avg_post'],
                    'glucose_std': respuesta['glucose_std'],
                    'time_to_peak': respuesta['time_to_peak'],
                    'glucose_auc': respuesta['glucose_auc'],
                    'score_calidad': respuesta['score_calidad']
                }
                
                datos_entrenamiento.append(registro)
                procesadas += 1
                
                if procesadas % 100 == 0:
                    print(f"  ✅ Procesadas {procesadas:,} combinaciones...")
    
    print(f"\n  ✅ Total de combinaciones procesadas: {procesadas:,}")
    
    # Crear DataFrame final
    print("\n🔗 Creando dataset final...")
    df_final = pd.DataFrame(datos_entrenamiento)
    
    # Filtrar registros con datos completos esenciales
    columnas_esenciales = ['age', 'bmi', 'total_calories', 'total_carbs', 
                          'glucose_baseline', 'glucose_peak', 'score_calidad']
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
    
    print(f"\n📊 Resumen estadístico de scores de calidad:")
    print(df_final['score_calidad'].describe())
    
    print("\n" + "=" * 70)
    print("✅ FIN DE LA PREPARACIÓN")
    print("=" * 70)

if __name__ == "__main__":
    preparar_datos_modelo3()

