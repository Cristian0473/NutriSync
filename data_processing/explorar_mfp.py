"""
Script para explorar rápidamente el archivo MyFitnessPal TSV
"""

import pandas as pd
import json
import os

# Ruta del archivo
archivo_tsv = r"D:\archive\mfp-diaries.tsv"

print("=" * 70)
print("🔍 EXPLORANDO MyFitnessPal (TSV)")
print("=" * 70)

if not os.path.exists(archivo_tsv):
    print(f"❌ Archivo no encontrado: {archivo_tsv}")
    print("\n💡 Verifica que la ruta sea correcta")
    exit(1)

try:
    # Leer primeras 20 filas para análisis
    print(f"\n📂 Leyendo archivo: {archivo_tsv}")
    print("⏳ Esto puede tomar unos segundos...")
    
    df = pd.read_csv(archivo_tsv, sep='\t', nrows=20, encoding='utf-8', low_memory=False)
    
    print(f"\n✅ Archivo leído correctamente")
    print(f"📏 Dimensiones (primeras 20 filas): {len(df)} filas × {len(df.columns)} columnas")
    
    print(f"\n📋 Columnas encontradas ({len(df.columns)}):")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")
    
    print(f"\n📊 Primeras 3 filas completas:")
    print("-" * 70)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 100)
    print(df.head(3).to_string())
    
    print(f"\n📈 Tipos de datos y valores nulos:")
    for col in df.columns:
        dtype = df[col].dtype
        null_count = df[col].isna().sum()
        non_null = len(df) - null_count
        print(f"  {col:30s} | {str(dtype):15s} | Nulos: {null_count:2d}/{len(df):2d} | No nulos: {non_null:2d}")
    
    # Intentar detectar JSON en columnas
    print(f"\n🔍 Buscando columnas con JSON anidado:")
    json_columns = []
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                # Buscar en las primeras filas no nulas
                for idx in range(len(df)):
                    sample = df[col].iloc[idx]
                    if pd.notna(sample) and isinstance(sample, str):
                        sample_clean = sample.strip()
                        # Intentar parsear como JSON
                        if (sample_clean.startswith('{') or 
                            sample_clean.startswith('[')):
                            try:
                                parsed = json.loads(sample)
                                print(f"\n  ✅ Columna '{col}' contiene JSON:")
                                print(f"     Tipo: {type(parsed).__name__}")
                                if isinstance(parsed, dict):
                                    print(f"     Claves principales: {list(parsed.keys())[:15]}")
                                    # Mostrar estructura de una clave
                                    if len(parsed) > 0:
                                        first_key = list(parsed.keys())[0]
                                        first_value = parsed[first_key]
                                        print(f"     Ejemplo - Clave '{first_key}': {type(first_value).__name__}")
                                        if isinstance(first_value, list) and len(first_value) > 0:
                                            print(f"       Primer elemento: {type(first_value[0]).__name__}")
                                            if isinstance(first_value[0], dict):
                                                print(f"       Claves del elemento: {list(first_value[0].keys())[:10]}")
                                elif isinstance(parsed, list):
                                    print(f"     Lista con {len(parsed)} elementos")
                                    if len(parsed) > 0:
                                        print(f"     Tipo del primer elemento: {type(parsed[0]).__name__}")
                                        if isinstance(parsed[0], dict):
                                            print(f"     Claves del primer elemento: {list(parsed[0].keys())[:10]}")
                                
                                # Mostrar ejemplo completo (limitado)
                                print(f"\n     Ejemplo completo (primeros 500 caracteres):")
                                ejemplo_json = json.dumps(parsed, indent=2, ensure_ascii=False)
                                print(f"     {ejemplo_json[:500]}...")
                                
                                json_columns.append(col)
                                break  # Solo mostrar una vez por columna
                            except json.JSONDecodeError:
                                continue
            except (AttributeError, IndexError, TypeError) as e:
                pass
    
    if not json_columns:
        print("  ℹ️  No se encontraron columnas con JSON anidado")
    
    # Contar total de filas (sin leer todo)
    print(f"\n📊 Contando total de filas en el archivo...")
    try:
        total_rows = sum(1 for _ in open(archivo_tsv, 'r', encoding='utf-8')) - 1  # -1 por header
        print(f"  Total de filas: {total_rows:,}")
        
        # Calcular tamaño aproximado
        file_size_mb = os.path.getsize(archivo_tsv) / (1024 * 1024)
        print(f"  Tamaño del archivo: {file_size_mb:.2f} MB")
        print(f"  Tamaño promedio por fila: {(file_size_mb * 1024 * 1024 / total_rows):.0f} bytes")
    except Exception as e:
        print(f"  ⚠️  No se pudo contar filas: {e}")
    
    # Análisis de valores únicos en columnas clave
    print(f"\n📊 Análisis de valores únicos (primeras 20 filas):")
    for col in df.columns:
        if df[col].dtype == 'object':
            unique_count = df[col].nunique()
            total_count = len(df)
            print(f"  {col:30s} | Valores únicos: {unique_count:2d}/{total_count:2d}")
            if unique_count <= 5 and unique_count > 0:
                print(f"    Valores: {df[col].unique().tolist()}")
    
    print("\n" + "=" * 70)
    print("✅ EXPLORACIÓN COMPLETA")
    print("=" * 70)
    print("\n💡 Información lista para procesamiento")
    
except Exception as e:
    print(f"❌ Error al leer archivo: {e}")
    import traceback
    traceback.print_exc()

