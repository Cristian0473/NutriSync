"""
Script para explorar rápidamente la estructura de los datasets
CGMacros y MyFitnessPal antes de procesarlos.
"""

import pandas as pd
import json
import os
from pathlib import Path

def explorar_myfitnesspal(archivo_tsv, nrows=10):
    """Explora la estructura del archivo TSV de MyFitnessPal"""
    print("=" * 70)
    print("🔍 EXPLORANDO MyFitnessPal (TSV)")
    print("=" * 70)
    
    if not os.path.exists(archivo_tsv):
        print(f"❌ Archivo no encontrado: {archivo_tsv}")
        return None
    
    try:
        # Leer primeras filas
        print(f"\n📂 Leyendo archivo: {archivo_tsv}")
        df = pd.read_csv(archivo_tsv, sep='\t', nrows=nrows, encoding='utf-8')
        
        print(f"\n✅ Archivo leído correctamente")
        print(f"📏 Dimensiones (primeras {nrows} filas): {len(df)} filas × {len(df.columns)} columnas")
        
        print(f"\n📋 Columnas encontradas ({len(df.columns)}):")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i}. {col}")
        
        print(f"\n📊 Primeras {min(3, len(df))} filas:")
        print(df.head(3).to_string())
        
        print(f"\n📈 Tipos de datos:")
        for col in df.columns:
            dtype = df[col].dtype
            null_count = df[col].isna().sum()
            print(f"  {col}: {dtype} (nulos: {null_count}/{len(df)})")
        
        # Intentar detectar JSON en columnas
        print(f"\n🔍 Buscando columnas con JSON anidado:")
        for col in df.columns:
            if df[col].dtype == 'object':
                try:
                    sample = df[col].iloc[0]
                    if isinstance(sample, str):
                        # Intentar parsear como JSON
                        if (sample.strip().startswith('{') or 
                            sample.strip().startswith('[')):
                            parsed = json.loads(sample)
                            print(f"\n  ✅ Columna '{col}' contiene JSON:")
                            print(f"     Tipo: {type(parsed).__name__}")
                            if isinstance(parsed, dict):
                                print(f"     Claves: {list(parsed.keys())[:10]}")
                            print(f"     Ejemplo (primeros 300 caracteres):")
                            print(f"     {json.dumps(parsed, indent=2)[:300]}...")
                except (json.JSONDecodeError, AttributeError, IndexError):
                    pass
        
        # Contar total de filas (sin leer todo)
        print(f"\n📊 Contando total de filas...")
        total_rows = sum(1 for _ in open(archivo_tsv, 'r', encoding='utf-8')) - 1  # -1 por header
        print(f"  Total de filas en archivo: {total_rows:,}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error al leer archivo: {e}")
        import traceback
        traceback.print_exc()
        return None


def explorar_cgmacros(directorio):
    """Explora la estructura del directorio de CGMacros"""
    print("\n" + "=" * 70)
    print("🔍 EXPLORANDO CGMacros")
    print("=" * 70)
    
    if not os.path.exists(directorio):
        print(f"❌ Directorio no encontrado: {directorio}")
        return None
    
    print(f"\n📂 Directorio: {directorio}")
    
    # Buscar archivos CSV, JSON, TXT
    archivos = []
    for ext in ['*.csv', '*.json', '*.txt', '*.tsv']:
        archivos.extend(Path(directorio).rglob(ext))
    
    if not archivos:
        print("❌ No se encontraron archivos CSV/JSON/TXT en el directorio")
        return None
    
    print(f"\n📋 Archivos encontrados ({len(archivos)}):")
    for i, archivo in enumerate(archivos[:20], 1):  # Mostrar primeros 20
        size_mb = archivo.stat().st_size / (1024 * 1024)
        print(f"  {i}. {archivo.name} ({size_mb:.2f} MB)")
        print(f"     Ruta: {archivo}")
    
    if len(archivos) > 20:
        print(f"  ... y {len(archivos) - 20} archivos más")
    
    # Explorar cada archivo
    resultados = {}
    for archivo in archivos[:10]:  # Explorar primeros 10 archivos
        print(f"\n{'=' * 70}")
        print(f"📄 Explorando: {archivo.name}")
        print(f"{'=' * 70}")
        
        try:
            if archivo.suffix == '.csv' or archivo.suffix == '.tsv':
                sep = '\t' if archivo.suffix == '.tsv' else ','
                df = pd.read_csv(archivo, sep=sep, nrows=5, encoding='utf-8')
                
                print(f"✅ Archivo leído correctamente")
                print(f"📏 Dimensiones (primeras 5 filas): {len(df)} filas × {len(df.columns)} columnas")
                
                print(f"\n📋 Columnas ({len(df.columns)}):")
                for i, col in enumerate(df.columns, 1):
                    print(f"  {i}. {col}")
                
                print(f"\n📊 Primeras 3 filas:")
                print(df.head(3).to_string())
                
                resultados[archivo.name] = {
                    'tipo': 'CSV/TSV',
                    'columnas': df.columns.tolist(),
                    'muestra': df.head(3).to_dict()
                }
                
            elif archivo.suffix == '.json':
                with open(archivo, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                print(f"✅ Archivo JSON leído correctamente")
                print(f"📊 Tipo de estructura: {type(data).__name__}")
                
                if isinstance(data, dict):
                    print(f"📋 Claves principales:")
                    for key in list(data.keys())[:10]:
                        print(f"  - {key}")
                elif isinstance(data, list):
                    print(f"📊 Lista con {len(data)} elementos")
                    if len(data) > 0:
                        print(f"📋 Claves del primer elemento:")
                        if isinstance(data[0], dict):
                            for key in list(data[0].keys())[:10]:
                                print(f"  - {key}")
                
                resultados[archivo.name] = {
                    'tipo': 'JSON',
                    'estructura': type(data).__name__
                }
                
        except Exception as e:
            print(f"❌ Error al leer archivo: {e}")
            resultados[archivo.name] = {'error': str(e)}
    
    return resultados


def main():
    """Función principal"""
    print("\n" + "=" * 70)
    print("🚀 EXPLORACIÓN DE DATASETS")
    print("=" * 70)
    
    # Configuración
    archivo_myfitnesspal = input("\n📂 Ruta del archivo MyFitnessPal TSV (o Enter para omitir): ").strip()
    directorio_cgmacros = input("📂 Ruta del directorio CGMacros (o Enter para omitir): ").strip()
    
    # Explorar MyFitnessPal
    if archivo_myfitnesspal:
        explorar_myfitnesspal(archivo_myfitnesspal)
    
    # Explorar CGMacros
    if directorio_cgmacros:
        explorar_cgmacros(directorio_cgmacros)
    
    print("\n" + "=" * 70)
    print("✅ EXPLORACIÓN COMPLETA")
    print("=" * 70)
    print("\n💡 Siguiente paso: Enviar esta información para preparar scripts de procesamiento")


if __name__ == "__main__":
    main()

