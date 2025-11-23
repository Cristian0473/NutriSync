"""
Script para analizar el dataset procesado y evaluar si es suficiente para entrenar modelos.
"""
import pandas as pd
import json
from pathlib import Path

DATASETS_DIR = Path(__file__).parent / "Datasets"

# Cargar dataset
df = pd.read_csv(DATASETS_DIR / "nhanes_procesado.csv")

print("="*60)
print("ANÁLISIS DEL DATASET PROCESADO")
print("="*60)
print(f"\nTotal de filas: {len(df):,}")

# Análisis de completitud
print("\n📊 COMPLETITUD DE VARIABLES CLAVE:")
variables_clave = ['hba1c', 'glucosa_ayunas', 'peso', 'talla', 'imc', 'ldl', 'hdl', 'trigliceridos']
for var in variables_clave:
    if var in df.columns:
        completos = df[var].notna().sum()
        porcentaje = (completos / len(df)) * 100
        print(f"  - {var:20s}: {completos:4d} valores ({porcentaje:5.1f}%)")

# Análisis de criterios DM2
print("\n🔍 ANÁLISIS DE CRITERIOS DM2:")
if 'hba1c' in df.columns:
    hba1c_dm2 = (df['hba1c'] >= 6.5).sum()
    hba1c_prediabetes = ((df['hba1c'] >= 5.7) & (df['hba1c'] < 6.5)).sum()
    print(f"  - HbA1c ≥ 6.5 (DM2): {hba1c_dm2} pacientes")
    print(f"  - HbA1c 5.7-6.4 (Prediabetes): {hba1c_prediabetes} pacientes")

if 'glucosa_ayunas' in df.columns:
    glu_dm2 = (df['glucosa_ayunas'] >= 126).sum()
    glu_prediabetes = ((df['glucosa_ayunas'] >= 100) & (df['glucosa_ayunas'] < 126)).sum()
    print(f"  - Glucosa ≥ 126 (DM2): {glu_dm2} pacientes")
    print(f"  - Glucosa 100-125 (Prediabetes): {glu_prediabetes} pacientes")

# Evaluación de tamaño para ML
print("\n📈 EVALUACIÓN PARA MACHINE LEARNING:")
print(f"  - Dataset actual: {len(df):,} filas")
print(f"  - Recomendado mínimo para Random Forest: 1,000-5,000 filas")
print(f"  - Recomendado mínimo para XGBoost: 1,000-10,000 filas")
print(f"  - Recomendado para modelos complejos: 5,000+ filas")

# Análisis de balance de clases
print("\n⚖️  BALANCE DE CLASES (Targets para ML):")
if 'control_glucemico' in df.columns:
    control_bien = (df['control_glucemico'] == 0).sum()
    control_mal = (df['control_glucemico'] == 1).sum()
    total_control = control_bien + control_mal
    if total_control > 0:
        print(f"  - Control glucémico BUENO (HbA1c < 7.0): {control_bien} ({control_bien/total_control*100:.1f}%)")
        print(f"  - Control glucémico MALO (HbA1c ≥ 7.0): {control_mal} ({control_mal/total_control*100:.1f}%)")
        ratio = min(control_bien, control_mal) / max(control_bien, control_mal) if max(control_bien, control_mal) > 0 else 0
        if ratio > 0.7:
            print(f"  ✅ Clases balanceadas (ratio: {ratio:.2f})")
        elif ratio > 0.5:
            print(f"  ⚠️  Clases ligeramente desbalanceadas (ratio: {ratio:.2f})")
        else:
            print(f"  ❌ Clases muy desbalanceadas (ratio: {ratio:.2f}) - considerar SMOTE")

if 'riesgo_metabolico' in df.columns:
    riesgo_bajo = (df['riesgo_metabolico'] < 0.3).sum()
    riesgo_medio = ((df['riesgo_metabolico'] >= 0.3) & (df['riesgo_metabolico'] < 0.7)).sum()
    riesgo_alto = (df['riesgo_metabolico'] >= 0.7).sum()
    total_riesgo = riesgo_bajo + riesgo_medio + riesgo_alto
    if total_riesgo > 0:
        print(f"\n  - Riesgo metabólico BAJO (<0.3): {riesgo_bajo} ({riesgo_bajo/total_riesgo*100:.1f}%)")
        print(f"  - Riesgo metabólico MEDIO (0.3-0.7): {riesgo_medio} ({riesgo_medio/total_riesgo*100:.1f}%)")
        print(f"  - Riesgo metabólico ALTO (≥0.7): {riesgo_alto} ({riesgo_alto/total_riesgo*100:.1f}%)")

# Evaluación de tamaño para ML
print("\n📈 EVALUACIÓN PARA MACHINE LEARNING:")
print(f"  - Dataset actual: {len(df):,} filas")
print(f"  - Recomendado mínimo para Random Forest: 1,000-5,000 filas")
print(f"  - Recomendado mínimo para XGBoost: 1,000-10,000 filas")
print(f"  - Recomendado para modelos complejos: 5,000+ filas")

if len(df) >= 1000 and len(df) < 5000:
    print("\n✅ DATASET ADECUADO para entrenar modelos:")
    print("   - Random Forest: ✅ Óptimo")
    print("   - XGBoost: ✅ Aceptable (con regularización)")
    print("   - Logistic Regression: ✅ Excelente")
    print("\n📋 PRÓXIMOS PASOS:")
    print("   1. Preparar features y targets")
    print("   2. Dividir en train/validation/test (70/15/15)")
    print("   3. Entrenar Logistic Regression (baseline)")
    print("   4. Entrenar Random Forest (con regularización)")
    print("   5. Entrenar XGBoost (si Random Forest funciona bien)")
    print("   6. Comparar modelos y seleccionar el mejor")
elif len(df) < 1000:
    print("\n⚠️  ADVERTENCIA: Dataset pequeño para modelos complejos")
    print("   Recomendaciones:")
    print("   1. Incluir prediabetes (HbA1c 5.7-6.4 o GLU 100-125)")
    print("   2. Relajar umbral de faltantes (de 30% a 50%)")
    print("   3. Usar técnicas para datasets pequeños:")
    print("      - Validación cruzada estratificada")
    print("      - Regularización fuerte")
    print("      - Modelos más simples (Logistic Regression primero)")
    print("      - Data augmentation sintética")
else:
    print("\n✅ DATASET EXCELENTE para entrenar modelos complejos")
    print("   - Todos los modelos son viables")
    print("   - Puedes usar técnicas avanzadas sin restricciones")

