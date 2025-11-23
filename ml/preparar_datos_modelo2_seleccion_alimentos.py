"""
Script para preparar datos específicos para entrenar el Modelo 2: Selección Personalizada de Alimentos.

Este script combina datos de MyFitnessPal y CGMacros para crear un dataset donde:
- Input: Perfil del paciente + alimento + contexto
- Output: Score de idoneidad del alimento (basado en respuesta glucémica y preferencias)
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

# Configuración de rutas
MFP_FILE = r"D:\Sistema Tesis\data_para_entrenamiento\mfp_procesado.csv"
CGMACROS_FILE = r"D:\Sistema Tesis\data_para_entrenamiento\cgmacros_procesado.csv"
OUTPUT_FILE = r"D:\Sistema Tesis\data_para_entrenamiento\modelo2_seleccion_alimentos.csv"

def calcular_score_idoneidad_alimento(respuesta_glucemica, frecuencia_consumo, preferencia=None):
    """
    Calcula un score de idoneidad (0-1) para un alimento basado en:
    - Respuesta glucémica (menor incremento = mejor)
    - Frecuencia de consumo (más consumo = mejor, indica preferencia)
    - Preferencia explícita (si está disponible)
    """
    score = 0.0
    
    # Factor 1: Respuesta glucémica (50% del score)
    if respuesta_glucemica is not None:
        incremento = respuesta_glucemica.get('glucose_increment', 100)
        # Normalizar: incremento < 20 mg/dL = score alto, > 60 mg/dL = score bajo
        if incremento < 20:
            score_glucosa = 1.0
        elif incremento < 40:
            score_glucosa = 0.8
        elif incremento < 60:
            score_glucosa = 0.5
        else:
            score_glucosa = 0.2
        score += score_glucosa * 0.5
    else:
        score += 0.5  # Si no hay datos, score neutro
    
    # Factor 2: Frecuencia de consumo (30% del score)
    if frecuencia_consumo > 0:
        # Normalizar frecuencia (máximo 1.0)
        freq_normalizada = min(frecuencia_consumo / 100, 1.0)  # Asumiendo 100 como máximo razonable
        score += freq_normalizada * 0.3
    else:
        score += 0.15  # Score neutro si no hay frecuencia
    
    # Factor 3: Preferencia explícita (20% del score)
    if preferencia is not None:
        score += preferencia * 0.2
    else:
        score += 0.1  # Score neutro
    
    return min(score, 1.0)

def preparar_datos_modelo2():
    """
    Prepara datos para entrenar el modelo de selección personalizada de alimentos.
    """
    print("=" * 70)
    print("🔧 PREPARANDO DATOS PARA MODELO 2: SELECCIÓN DE ALIMENTOS")
    print("=" * 70)
    print()
    
    # 1. Cargar datos de MyFitnessPal
    print("📂 Cargando datos de MyFitnessPal...")
    try:
        df_mfp = pd.read_csv(MFP_FILE, parse_dates=['fecha'], low_memory=False)
        print(f"  ✅ Cargadas {len(df_mfp):,} filas de MyFitnessPal")
    except Exception as e:
        print(f"  ❌ Error cargando MyFitnessPal: {e}")
        return
    
    # 2. Cargar datos de CGMacros
    print("\n📂 Cargando datos de CGMacros...")
    try:
        df_cgmacros = pd.read_csv(CGMACROS_FILE, parse_dates=['Timestamp'], low_memory=False)
        print(f"  ✅ Cargadas {len(df_cgmacros):,} filas de CGMacros")
    except Exception as e:
        print(f"  ❌ Error cargando CGMacros: {e}")
        return
    
    print("\n🔄 Procesando y combinando datos...")
    
    # 3. Extraer alimentos únicos de MyFitnessPal con sus valores nutricionales promedio
    print("\n📊 Analizando alimentos de MyFitnessPal...")
    alimentos_mfp = df_mfp.groupby('food_name').agg({
        'calories': 'mean',
        'carbs': 'mean',
        'fat': 'mean',
        'protein': 'mean',
        'sodium': 'mean',
        'sugar': 'mean',
        'user_id': 'count'  # Frecuencia de consumo
    }).reset_index()
    alimentos_mfp.columns = ['food_name', 'avg_calories', 'avg_carbs', 'avg_fat', 
                            'avg_protein', 'avg_sodium', 'avg_sugar', 'frecuencia_consumo']
    
    print(f"  ✅ Encontrados {len(alimentos_mfp):,} alimentos únicos")
    
    # OPTIMIZACIÓN: Filtrar alimentos más relevantes
    print("\n🔍 Filtrando alimentos más relevantes...")
    
    # 1. Filtrar por frecuencia mínima (al menos 10 consumos)
    alimentos_mfp = alimentos_mfp[alimentos_mfp['frecuencia_consumo'] >= 10]
    print(f"  ✅ Después de filtrar por frecuencia mínima (≥10): {len(alimentos_mfp):,} alimentos")
    
    # 2. Filtrar alimentos con valores nutricionales válidos
    alimentos_mfp = alimentos_mfp[
        (alimentos_mfp['avg_calories'] > 0) &
        (alimentos_mfp['avg_calories'] < 2000) &  # Filtrar valores anómalos
        (alimentos_mfp['avg_carbs'].notna()) &
        (alimentos_mfp['avg_protein'].notna()) &
        (alimentos_mfp['avg_fat'].notna())
    ]
    print(f"  ✅ Después de filtrar valores válidos: {len(alimentos_mfp):,} alimentos")
    
    # 3. Limitar a los top 10,000 más frecuentes
    alimentos_mfp = alimentos_mfp.nlargest(10000, 'frecuencia_consumo')
    print(f"  ✅ Top 10,000 alimentos más frecuentes seleccionados: {len(alimentos_mfp):,} alimentos")
    
    # Calcular estimación de registros finales
    perfiles_pacientes = df_cgmacros[
        df_cgmacros['Age'].notna()
    ].groupby('subject_id').first()
    num_perfiles = min(len(perfiles_pacientes), 50)
    estimacion_registros = len(alimentos_mfp) * num_perfiles
    print(f"\n  📊 ESTIMACIÓN: Se procesarán aproximadamente {estimacion_registros:,} registros")
    print(f"     ({len(alimentos_mfp):,} alimentos × {num_perfiles} perfiles)")
    
    # 4. Para cada alimento, buscar respuestas glucémicas en CGMacros
    print("\n🔄 Calculando scores de idoneidad para cada alimento...")
    
    datos_entrenamiento = []
    procesados = 0
    
    # Agrupar CGMacros por alimento (usando macronutrientes como proxy)
    # Ya que CGMacros no tiene nombres de alimentos, usaremos combinaciones de macronutrientes
    df_cgmacros_comidas = df_cgmacros[
        (df_cgmacros['Meal Type'].notna()) &
        (df_cgmacros['Calories'].notna()) &
        (df_cgmacros['Calories'] > 0)
    ].copy()
    
    # Crear "perfiles nutricionales" de CGMacros (agrupar por rangos de macronutrientes)
    df_cgmacros_comidas['carbs_range'] = pd.cut(df_cgmacros_comidas['Carbs'], 
                                                bins=[0, 20, 40, 60, 100, 200], 
                                                labels=['bajo', 'medio-bajo', 'medio', 'medio-alto', 'alto'])
    df_cgmacros_comidas['protein_range'] = pd.cut(df_cgmacros_comidas['Protein'], 
                                                   bins=[0, 10, 20, 30, 50, 200], 
                                                   labels=['bajo', 'medio-bajo', 'medio', 'medio-alto', 'alto'])
    df_cgmacros_comidas['fat_range'] = pd.cut(df_cgmacros_comidas['Fat'], 
                                              bins=[0, 5, 10, 20, 30, 100], 
                                              labels=['bajo', 'medio-bajo', 'medio', 'medio-alto', 'alto'])
    
    # Para cada alimento de MyFitnessPal, buscar perfiles similares en CGMacros
    for idx, alimento in alimentos_mfp.iterrows():
        # Determinar rango nutricional del alimento
        carbs_r = 'medio'
        if alimento['avg_carbs'] < 20:
            carbs_r = 'bajo'
        elif alimento['avg_carbs'] < 40:
            carbs_r = 'medio-bajo'
        elif alimento['avg_carbs'] < 60:
            carbs_r = 'medio'
        elif alimento['avg_carbs'] < 100:
            carbs_r = 'medio-alto'
        else:
            carbs_r = 'alto'
        
        protein_r = 'medio'
        if alimento['avg_protein'] < 10:
            protein_r = 'bajo'
        elif alimento['avg_protein'] < 20:
            protein_r = 'medio-bajo'
        elif alimento['avg_protein'] < 30:
            protein_r = 'medio'
        elif alimento['avg_protein'] < 50:
            protein_r = 'medio-alto'
        else:
            protein_r = 'alto'
        
        fat_r = 'medio'
        if alimento['avg_fat'] < 5:
            fat_r = 'bajo'
        elif alimento['avg_fat'] < 10:
            fat_r = 'medio-bajo'
        elif alimento['avg_fat'] < 20:
            fat_r = 'medio'
        elif alimento['avg_fat'] < 30:
            fat_r = 'medio-alto'
        else:
            fat_r = 'alto'
        
        # Buscar comidas similares en CGMacros
        comidas_similares = df_cgmacros_comidas[
            (df_cgmacros_comidas['carbs_range'] == carbs_r) &
            (df_cgmacros_comidas['protein_range'] == protein_r) &
            (df_cgmacros_comidas['fat_range'] == fat_r)
        ]
        
        # Calcular respuesta glucémica promedio para este perfil nutricional
        respuesta_promedio = None
        if len(comidas_similares) > 0:
            # Calcular incremento promedio de glucosa (simplificado)
            # En un caso real, calcularíamos la respuesta real postprandial
            incrementos = []
            for _, comida in comidas_similares.head(100).iterrows():  # Limitar para rendimiento
                subject_id = comida['subject_id']
                timestamp = comida['Timestamp']
                
                # Buscar glucosa antes y después
                df_subject = df_cgmacros[df_cgmacros['subject_id'] == subject_id].sort_values('Timestamp')
                df_antes = df_subject[
                    (df_subject['Timestamp'] >= timestamp - timedelta(minutes=30)) &
                    (df_subject['Timestamp'] < timestamp)
                ]
                df_despues = df_subject[
                    (df_subject['Timestamp'] > timestamp) &
                    (df_subject['Timestamp'] <= timestamp + timedelta(hours=2))
                ]
                
                if len(df_antes) > 0 and len(df_despues) > 0:
                    baseline = df_antes['glucose'].mean()
                    peak = df_despues['glucose'].max()
                    if pd.notna(baseline) and pd.notna(peak) and baseline > 0:
                        incremento = peak - baseline
                        if 0 < incremento < 150:  # Filtrar valores anómalos
                            incrementos.append(incremento)
            
            if len(incrementos) > 0:
                respuesta_promedio = {
                    'glucose_increment': np.mean(incrementos),
                    'n_muestras': len(incrementos)
                }
        
        # Calcular score de idoneidad
        score = calcular_score_idoneidad_alimento(
            respuesta_promedio,
            alimento['frecuencia_consumo']
        )
        
        # Crear registro para cada combinación alimento-perfil de paciente
        # Usar perfiles representativos de CGMacros
        perfiles_pacientes = df_cgmacros[
            df_cgmacros['Age'].notna()
        ].groupby('subject_id').first().reset_index()
        
        for _, perfil in perfiles_pacientes.head(50).iterrows():  # Limitar para rendimiento
            registro = {
                # Identificación
                'food_name': alimento['food_name'],
                'subject_id': perfil['subject_id'],
                
                # Perfil del paciente
                'age': perfil['Age'] if pd.notna(perfil['Age']) else None,
                'gender': 1 if perfil['Gender'] == 'F' else 0 if perfil['Gender'] == 'M' else None,
                'bmi': perfil['BMI'] if pd.notna(perfil['BMI']) else None,
                'a1c': perfil['A1c PDL (Lab)'] if pd.notna(perfil['A1c PDL (Lab)']) else None,
                'fasting_glucose': perfil['Fasting GLU - PDL (Lab)'] if pd.notna(perfil['Fasting GLU - PDL (Lab)']) else None,
                'homa_ir': perfil['HOMA_IR'] if pd.notna(perfil['HOMA_IR']) else None,
                
                # Características del alimento
                'calories': alimento['avg_calories'],
                'carbs': alimento['avg_carbs'],
                'protein': alimento['avg_protein'],
                'fat': alimento['avg_fat'],
                'sodium': alimento['avg_sodium'],
                'sugar': alimento['avg_sugar'],
                
                # Características derivadas
                'carbs_per_100cal': (alimento['avg_carbs'] * 4 / alimento['avg_calories'] * 100) if alimento['avg_calories'] > 0 else 0,
                'protein_per_100cal': (alimento['avg_protein'] * 4 / alimento['avg_calories'] * 100) if alimento['avg_calories'] > 0 else 0,
                'fat_per_100cal': (alimento['avg_fat'] * 9 / alimento['avg_calories'] * 100) if alimento['avg_calories'] > 0 else 0,
                
                # Contexto
                'frecuencia_consumo': alimento['frecuencia_consumo'],
                
                # Target
                'score_idoneidad': score
            }
            
            datos_entrenamiento.append(registro)
            procesados += 1
            
            if procesados % 1000 == 0:
                print(f"  ✅ Procesados {procesados:,} registros...")
    
    print(f"\n  ✅ Total de registros procesados: {procesados:,}")
    
    # Crear DataFrame final
    print("\n🔗 Creando dataset final...")
    df_final = pd.DataFrame(datos_entrenamiento)
    
    # Filtrar registros con datos completos esenciales
    columnas_esenciales = ['age', 'bmi', 'calories', 'carbs', 'score_idoneidad']
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
    print(f"  - Alimentos únicos: {df_final['food_name'].nunique()}")
    print(f"  - Sujetos únicos: {df_final['subject_id'].nunique()}")
    print(f"  - Archivo: {OUTPUT_FILE}")
    print(f"  - Tamaño: {tamaño_mb:.2f} MB")
    
    print(f"\n📊 Distribución de scores de idoneidad:")
    print(df_final['score_idoneidad'].describe())
    
    print("\n" + "=" * 70)
    print("✅ FIN DE LA PREPARACIÓN")
    print("=" * 70)

if __name__ == "__main__":
    preparar_datos_modelo2()

