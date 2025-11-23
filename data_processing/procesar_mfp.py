"""
Script para procesar el dataset MyFitnessPal y extraer datos relevantes para ML
"""

import pandas as pd
import json
import os
from pathlib import Path

# Configuración
archivo_tsv = r"D:\archive\mfp-diaries.tsv"
output_dir = r"D:\Sistema Tesis\data_para_entrenamiento"
chunk_size = 10000  # Procesar en chunks de 10k filas

# Crear directorio de salida
os.makedirs(output_dir, exist_ok=True)

print("=" * 70)
print("🔧 PROCESANDO MyFitnessPal Dataset")
print("=" * 70)

def parsear_nutricion(nutritions_list):
    """Convierte lista de nutriciones a diccionario"""
    nutri_dict = {}
    for nut in nutritions_list:
        name = nut.get('name', '').lower()
        value = nut.get('value', 0)
        # Convertir strings a números
        if isinstance(value, str):
            value = value.replace(',', '').strip()
            try:
                value = float(value) if '.' in value else int(value)
            except:
                value = 0
        nutri_dict[name] = value
    return nutri_dict

def procesar_fila(row):
    """Procesa una fila del dataset y extrae información estructurada"""
    user_id = row.iloc[0]
    fecha = row.iloc[1]
    meals_json_str = row.iloc[2] if len(row) > 2 else None
    totals_json_str = row.iloc[3] if len(row) > 3 else None
    
    resultados = []
    
    # Parsear comidas
    if pd.notna(meals_json_str) and isinstance(meals_json_str, str):
        try:
            meals_data = json.loads(meals_json_str)
            if isinstance(meals_data, list):
                for meal in meals_data:
                    meal_name = meal.get('meal', 'Unknown')
                    dishes = meal.get('dishes', [])
                    
                    for dish in dishes:
                        dish_name = dish.get('name', 'Unknown')
                        nutritions = dish.get('nutritions', [])
                        nutri_dict = parsear_nutricion(nutritions)
                        
                        resultado = {
                            'user_id': user_id,
                            'fecha': fecha,
                            'meal_type': meal_name,
                            'food_name': dish_name,
                            'calories': nutri_dict.get('calories', 0),
                            'carbs': nutri_dict.get('carbs', 0),
                            'fat': nutri_dict.get('fat', 0),
                            'protein': nutri_dict.get('protein', 0),
                            'sodium': nutri_dict.get('sodium', 0),
                            'sugar': nutri_dict.get('sugar', 0),
                        }
                        resultados.append(resultado)
        except json.JSONDecodeError as e:
            pass  # Silenciar errores de JSON
    
    # Parsear totales y objetivos (una sola fila por día)
    if pd.notna(totals_json_str) and isinstance(totals_json_str, str):
        try:
            totals_data = json.loads(totals_json_str)
            
            # Totales del día
            total_nutri = {}
            if 'total' in totals_data:
                for nut in totals_data['total']:
                    name = nut.get('name', '').lower()
                    value = nut.get('value', 0)
                    if isinstance(value, str):
                        value = value.replace(',', '').strip()
                        try:
                            value = float(value) if '.' in value else int(value)
                        except:
                            value = 0
                    total_nutri[name] = value
            
            # Objetivos del día
            goal_nutri = {}
            if 'goal' in totals_data:
                for nut in totals_data['goal']:
                    name = nut.get('name', '').lower()
                    value = nut.get('value', 0)
                    if isinstance(value, str):
                        value = value.replace(',', '').strip()
                        try:
                            value = float(value) if '.' in value else int(value)
                        except:
                            value = 0
                    goal_nutri[name] = value
            
            # Agregar resumen diario (solo una vez por día)
            if len(resultados) == 0:  # Si no hay comidas, crear fila de resumen
                resultados.append({
                    'user_id': user_id,
                    'fecha': fecha,
                    'meal_type': 'DAILY_SUMMARY',
                    'food_name': 'TOTAL_DIA',
                    'calories': total_nutri.get('calories', 0),
                    'carbs': total_nutri.get('carbs', 0),
                    'fat': total_nutri.get('fat', 0),
                    'protein': total_nutri.get('protein', 0),
                    'sodium': total_nutri.get('sodium', 0),
                    'sugar': total_nutri.get('sugar', 0),
                    'goal_calories': goal_nutri.get('calories', 0),
                    'goal_carbs': goal_nutri.get('carbs', 0),
                    'goal_fat': goal_nutri.get('fat', 0),
                    'goal_protein': goal_nutri.get('protein', 0),
                })
            else:
                # Agregar objetivos a la primera fila del día
                resultados[0]['goal_calories'] = goal_nutri.get('calories', 0)
                resultados[0]['goal_carbs'] = goal_nutri.get('carbs', 0)
                resultados[0]['goal_fat'] = goal_nutri.get('fat', 0)
                resultados[0]['goal_protein'] = goal_nutri.get('protein', 0)
                
        except json.JSONDecodeError:
            pass  # Silenciar errores de JSON
    
    return resultados

def procesar_chunk(chunk_df, chunk_num, total_estimado=None):
    """Procesa un chunk del dataset"""
    if total_estimado:
        print(f"\n📦 Procesando chunk {chunk_num}/{total_estimado} ({len(chunk_df)} filas)...")
    else:
        print(f"\n📦 Procesando chunk {chunk_num} ({len(chunk_df)} filas)...")
    
    todas_filas = []
    filas_procesadas = 0
    errores = 0
    
    for idx, row in chunk_df.iterrows():
        try:
            filas_procesadas += 1
            resultados = procesar_fila(row)
            todas_filas.extend(resultados)
            
            if filas_procesadas % 1000 == 0:
                print(f"  ✅ Procesadas {filas_procesadas}/{len(chunk_df)} filas...")
                
        except Exception as e:
            errores += 1
            if errores <= 5:  # Mostrar solo primeros 5 errores
                print(f"  ⚠️  Error en fila {idx}: {e}")
    
    if todas_filas:
        df_procesado = pd.DataFrame(todas_filas)
        return df_procesado, errores
    else:
        return None, errores

# Procesar archivo por chunks
print(f"\n📂 Archivo: {archivo_tsv}")
print(f"📊 Tamaño: {os.path.getsize(archivo_tsv) / (1024*1024):.2f} MB")
print(f"🔄 Procesando en chunks de {chunk_size:,} filas...")

# Calcular total de chunks estimado
total_filas_estimado = 587186  # Del análisis anterior
total_chunks_estimado = (total_filas_estimado // chunk_size) + 1

print(f"\n📊 ESTIMACIÓN:")
print(f"  - Total de filas: ~{total_filas_estimado:,}")
print(f"  - Chunks estimados: ~{total_chunks_estimado}")
print(f"  - Tiempo estimado: 30-60 minutos")
print(f"\n⚠️  PROCESANDO TODO EL ARCHIVO")
print(f"⏱️  Esto puede tomar varios minutos...\n")

chunks_procesados = []  # Lista de rutas de archivos de chunks procesados
chunk_num = 0
total_errores = 0
total_filas_procesadas = 0

try:
    # Leer archivo sin headers (header=None)
    for chunk in pd.read_csv(archivo_tsv, sep='\t', chunksize=chunk_size, 
                             header=None, encoding='utf-8', low_memory=False):
        chunk_num += 1
        df_procesado, errores = procesar_chunk(chunk, chunk_num, total_chunks_estimado)
        
        if df_procesado is not None and len(df_procesado) > 0:
            total_filas_procesadas += len(df_procesado)
            total_errores += errores
            
            # Guardar chunk procesado inmediatamente (no mantener en memoria)
            chunk_file = os.path.join(output_dir, f"mfp_chunk_{chunk_num:04d}.csv")
            df_procesado.to_csv(chunk_file, index=False, encoding='utf-8')
            progreso_pct = (chunk_num / total_chunks_estimado) * 100
            print(f"  💾 Guardado: {os.path.basename(chunk_file)} ({len(df_procesado)} filas) - Progreso: {progreso_pct:.1f}%")
            
            # Liberar memoria - solo guardar referencia, no el DataFrame completo
            chunks_procesados.append(chunk_file)  # Guardar ruta en lugar del DataFrame
    
    # Combinar todos los chunks de forma eficiente
    if chunks_procesados:
        print(f"\n🔗 Combinando {len(chunks_procesados)} chunks...")
        archivo_final = os.path.join(output_dir, "mfp_procesado.csv")
        
        # Leer y combinar chunks de forma eficiente (sin cargar todo en memoria)
        primer_chunk = True
        for i, chunk_file in enumerate(chunks_procesados, 1):
            print(f"  📖 Leyendo chunk {i}/{len(chunks_procesados)}: {os.path.basename(chunk_file)}")
            df_chunk = pd.read_csv(chunk_file, encoding='utf-8')
            
            if primer_chunk:
                # Escribir el primer chunk con header
                df_chunk.to_csv(archivo_final, index=False, encoding='utf-8', mode='w')
                primer_chunk = False
            else:
                # Anexar los siguientes chunks sin header
                df_chunk.to_csv(archivo_final, index=False, encoding='utf-8', mode='a', header=False)
        
        # Leer archivo final para estadísticas (solo una muestra)
        print(f"\n📊 Calculando estadísticas del archivo final...")
        df_muestra = pd.read_csv(archivo_final, nrows=10000, encoding='utf-8')
        
        # Contar filas totales sin cargar todo
        total_filas_final = sum(1 for _ in open(archivo_final, 'r', encoding='utf-8')) - 1
        
        print(f"\n✅ PROCESAMIENTO COMPLETO")
        print(f"📊 Estadísticas:")
        print(f"  - Chunks procesados: {chunk_num}")
        print(f"  - Filas procesadas: {total_filas_procesadas:,}")
        print(f"  - Filas en archivo final: {total_filas_final:,}")
        print(f"  - Errores: {total_errores}")
        print(f"  - Archivo final: {archivo_final}")
        print(f"  - Tamaño final: {os.path.getsize(archivo_final) / (1024*1024):.2f} MB")
        
        # Mostrar resumen (de la muestra)
        print(f"\n📋 Resumen del dataset procesado (muestra de 10k filas):")
        print(df_muestra.head(10))
        print(f"\n📈 Columnas: {df_muestra.columns.tolist()}")
        print(f"\n📊 Forma (muestra): {df_muestra.shape}")
        print(f"\n📊 Forma (total): ({total_filas_final:,} filas, {len(df_muestra.columns)} columnas)")
        print(f"\n📊 Usuarios únicos (muestra): {df_muestra['user_id'].nunique()}")
        print(f"\n📊 Fechas únicas (muestra): {df_muestra['fecha'].nunique()}")
        print(f"\n📊 Alimentos únicos (muestra): {df_muestra['food_name'].nunique()}")
        
except Exception as e:
    print(f"\n❌ Error durante el procesamiento: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("✅ FIN DEL PROCESAMIENTO")
print("=" * 70)

