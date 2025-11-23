"""
Script para entrenar el Modelo 2: Selección Personalizada de Alimentos.

Algoritmo: XGBoost Classifier (clasifica alimentos como adecuados/no adecuados)
Target: score_idoneidad (binarizado: >0.6 = adecuado, <=0.6 = no adecuado)
"""

import pandas as pd
import numpy as np
import os
import pickle
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, classification_report
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

# Configuración de rutas
INPUT_FILE = r"D:\Sistema Tesis\data_para_entrenamiento\modelo2_seleccion_alimentos.csv"
OUTPUT_DIR = r"D:\Sistema Tesis\ApartadoInteligente\ModeloML"
MODEL_FILE = os.path.join(OUTPUT_DIR, "modelo_seleccion_alimentos.pkl")
SCALER_FILE = os.path.join(OUTPUT_DIR, "scaler_seleccion_alimentos.pkl")
LABEL_ENCODER_FILE = os.path.join(OUTPUT_DIR, "label_encoder_alimentos.pkl")

def entrenar_modelo2():
    """
    Entrena el modelo de selección personalizada de alimentos.
    """
    print("=" * 70)
    print("🤖 ENTRENANDO MODELO 2: SELECCIÓN DE ALIMENTOS")
    print("=" * 70)
    print()
    
    # Crear directorio de salida
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Cargar datos
    print("📂 Cargando datos de entrenamiento...")
    try:
        df = pd.read_csv(INPUT_FILE, low_memory=False)
        print(f"  ✅ Cargadas {len(df):,} muestras")
    except Exception as e:
        print(f"  ❌ Error cargando archivo: {e}")
        return
    
    # 2. Preparar features y target
    print("\n🔧 Preparando features y target...")
    
    # Features (input)
    feature_columns = [
        # Perfil del paciente
        'age', 'gender', 'bmi', 'a1c', 'fasting_glucose', 'homa_ir',
        # Características del alimento
        'calories', 'carbs', 'protein', 'fat', 'sodium', 'sugar',
        'carbs_per_100cal', 'protein_per_100cal', 'fat_per_100cal',
        # Contexto
        'frecuencia_consumo'
    ]
    
    # Filtrar solo columnas que existen
    feature_columns = [col for col in feature_columns if col in df.columns]
    
    # Codificar nombres de alimentos (si queremos incluir el alimento como feature)
    # Por ahora no lo incluimos directamente, pero podemos usar embeddings después
    
    # Target: binarizar score_idoneidad
    # > 0.6 = adecuado (1), <= 0.6 = no adecuado (0)
    df['target'] = (df['score_idoneidad'] > 0.6).astype(int)
    
    print(f"  📊 Distribución de target:")
    print(f"     Adecuado (1): {df['target'].sum():,} ({df['target'].mean()*100:.1f}%)")
    print(f"     No adecuado (0): {(df['target']==0).sum():,} ({(1-df['target'].mean())*100:.1f}%)")
    
    # Preparar datos
    X = df[feature_columns].copy()
    y = df['target'].copy()
    
    # Eliminar filas con valores faltantes
    print(f"\n  📊 Filas antes de limpieza: {len(X):,}")
    X = X.dropna()
    y = y.loc[X.index]
    print(f"  📊 Filas después de limpieza: {len(X):,}")
    
    if len(X) == 0:
        print("  ❌ No hay datos suficientes después de la limpieza")
        return
    
    # 3. Dividir en entrenamiento y prueba
    print("\n📊 Dividiendo datos (80% entrenamiento, 20% prueba)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"  ✅ Entrenamiento: {len(X_train):,} muestras")
    print(f"  ✅ Prueba: {len(X_test):,} muestras")
    
    # 4. Escalar features
    print("\n🔧 Escalando features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Convertir a DataFrame
    X_train_scaled = pd.DataFrame(X_train_scaled, columns=feature_columns, index=X_train.index)
    X_test_scaled = pd.DataFrame(X_test_scaled, columns=feature_columns, index=X_test.index)
    
    # 5. Entrenar modelo XGBoost Classifier
    print("\n🤖 Entrenando modelo XGBoost Classifier...")
    
    modelo = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbosity=0,
        eval_metric='logloss'
    )
    
    modelo.fit(X_train_scaled, y_train)
    
    # 6. Predecir
    print("\n📊 Evaluando modelo...")
    y_pred_train = modelo.predict(X_train_scaled)
    y_pred_test = modelo.predict(X_test_scaled)
    y_pred_proba_train = modelo.predict_proba(X_train_scaled)[:, 1]
    y_pred_proba_test = modelo.predict_proba(X_test_scaled)[:, 1]
    
    # 7. Calcular métricas
    accuracy_train = accuracy_score(y_train, y_pred_train)
    accuracy_test = accuracy_score(y_test, y_pred_test)
    precision_train = precision_score(y_train, y_pred_train, zero_division=0)
    precision_test = precision_score(y_test, y_pred_test, zero_division=0)
    recall_train = recall_score(y_train, y_pred_train, zero_division=0)
    recall_test = recall_score(y_test, y_pred_test, zero_division=0)
    f1_train = f1_score(y_train, y_pred_train, zero_division=0)
    f1_test = f1_score(y_test, y_pred_test, zero_division=0)
    
    try:
        auc_train = roc_auc_score(y_train, y_pred_proba_train)
        auc_test = roc_auc_score(y_test, y_pred_proba_test)
    except:
        auc_train = None
        auc_test = None
    
    print(f"\n  ✅ Métricas de Entrenamiento:")
    print(f"     Accuracy: {accuracy_train:.3f}")
    print(f"     Precision: {precision_train:.3f}")
    print(f"     Recall: {recall_train:.3f}")
    print(f"     F1-Score: {f1_train:.3f}")
    if auc_train:
        print(f"     AUC-ROC: {auc_train:.3f}")
    
    print(f"\n  ✅ Métricas de Prueba:")
    print(f"     Accuracy: {accuracy_test:.3f}")
    print(f"     Precision: {precision_test:.3f}")
    print(f"     Recall: {recall_test:.3f}")
    print(f"     F1-Score: {f1_test:.3f}")
    if auc_test:
        print(f"     AUC-ROC: {auc_test:.3f}")
    
    print(f"\n  📋 Reporte de Clasificación (Test):")
    print(classification_report(y_test, y_pred_test, target_names=['No Adecuado', 'Adecuado']))
    
    # 8. Guardar modelo, scaler y metadata
    print("\n💾 Guardando modelo, scaler y metadata...")
    
    modelo_completo = {
        'modelo': modelo,
        'feature_columns': feature_columns,
        'scaler': scaler,
        'umbral_score': 0.6  # Umbral usado para binarizar
    }
    
    with open(MODEL_FILE, 'wb') as f:
        pickle.dump(modelo_completo, f)
    
    print(f"  ✅ Modelo guardado en: {MODEL_FILE}")
    
    # 9. Resumen final
    print("\n" + "=" * 70)
    print("✅ ENTRENAMIENTO COMPLETO")
    print("=" * 70)
    print(f"\n📊 RESULTADOS FINALES:")
    print(f"   Accuracy (test): {accuracy_test:.3f}")
    print(f"   Precision (test): {precision_test:.3f}")
    print(f"   Recall (test): {recall_test:.3f}")
    print(f"   F1-Score (test): {f1_test:.3f}")
    if auc_test:
        print(f"   AUC-ROC (test): {auc_test:.3f}")
    
    print("\n" + "=" * 70)
    print("✅ FIN DEL ENTRENAMIENTO")
    print("=" * 70)

if __name__ == "__main__":
    entrenar_modelo2()

