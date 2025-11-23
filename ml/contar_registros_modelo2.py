"""
Script para contar cuántos registros debe procesar el Modelo 2.
Solo lee y cuenta, no procesa ni interfiere con el procesamiento actual.
"""

import pandas as pd

# Configuración de rutas (mismas que el modelo 2)
MFP_FILE = r"D:\Sistema Tesis\data_para_entrenamiento\mfp_procesado.csv"
CGMACROS_FILE = r"D:\Sistema Tesis\data_para_entrenamiento\cgmacros_procesado.csv"

print("=" * 70)
print("📊 CONTANDO REGISTROS PARA MODELO 2")
print("=" * 70)
print()

# 1. Contar alimentos únicos en MyFitnessPal
print("📂 Cargando MyFitnessPal...")
try:
    df_mfp = pd.read_csv(MFP_FILE, usecols=['food_name'], low_memory=False)
    alimentos_unicos = df_mfp['food_name'].nunique()
    total_filas_mfp = len(df_mfp)
    print(f"  ✅ Total de filas en MyFitnessPal: {total_filas_mfp:,}")
    print(f"  ✅ Alimentos únicos: {alimentos_unicos:,}")
except Exception as e:
    print(f"  ❌ Error: {e}")
    alimentos_unicos = 0

print()

# 2. Contar perfiles de pacientes en CGMacros
print("📂 Cargando CGMacros...")
try:
    df_cgmacros = pd.read_csv(CGMACROS_FILE, usecols=['subject_id', 'Age'], low_memory=False)
    perfiles_pacientes = df_cgmacros[
        df_cgmacros['Age'].notna()
    ].groupby('subject_id').first()
    num_perfiles = len(perfiles_pacientes)
    # El script limita a 50 perfiles
    num_perfiles_limitado = min(num_perfiles, 50)
    print(f"  ✅ Total de perfiles de pacientes: {num_perfiles:,}")
    print(f"  ✅ Perfiles que se usarán (limitado a 50): {num_perfiles_limitado:,}")
except Exception as e:
    print(f"  ❌ Error: {e}")
    num_perfiles_limitado = 0

print()

# 3. Calcular total estimado
total_registros = alimentos_unicos * num_perfiles_limitado

print("=" * 70)
print("📊 RESULTADO")
print("=" * 70)
print(f"  Alimentos únicos: {alimentos_unicos:,}")
print(f"  Perfiles de pacientes (limitado): {num_perfiles_limitado:,}")
print(f"  ─────────────────────────────────────────────")
print(f"  📈 TOTAL ESTIMADO DE REGISTROS: {total_registros:,}")
print("=" * 70)

