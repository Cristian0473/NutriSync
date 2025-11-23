"""
Script para entrenar el Modelo 1: Predicción de Respuesta Glucémica Postprandial.

Algoritmo: XGBoost Regressor
Targets: glucose_increment, glucose_peak, time_to_peak
"""

import pandas as pd
import numpy as np
import os
import pickle
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

# Configuración de rutas
INPUT_FILE = r"D:\Sistema Tesis\data_para_entrenamiento\modelo1_respuesta_glucemica.csv"
OUTPUT_DIR = r"D:\Sistema Tesis\ApartadoInteligente\ModeloML"
MODEL_FILE = os.path.join(OUTPUT_DIR, "modelo_respuesta_glucemica.pkl")
SCALER_FILE = os.path.join(OUTPUT_DIR, "scaler_respuesta_glucemica.pkl")

def entrenar_modelo1():
    """
    Entrena el modelo de predicción de respuesta glucémica.
    """
    print("=" * 70)
    print("🤖 ENTRENANDO MODELO 1: PREDICCIÓN DE RESPUESTA GLUCÉMICA")
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
    
    # 2. Preparar features y targets
    print("\n🔧 Preparando features y targets...")
    
    # Features (input)
    feature_columns = [
        # Perfil del paciente
        'age', 'gender', 'bmi', 'weight', 'height',
        # Datos bioquímicos
        'a1c', 'fasting_glucose', 'insulin', 'homa_ir',
        'triglycerides', 'cholesterol', 'hdl', 'ldl', 'tg_hdl_ratio',
        # Características de la comida
        'calories', 'carbs', 'protein', 'fat', 'fiber', 'amount_consumed',
        'carbs_per_100cal', 'protein_per_100cal', 'fat_per_100cal', 'fiber_per_100cal',
        # Contexto
        'hora', 'dia_semana_encoded', 'meal_type_encoded', 'tiempo_desde_ultima_comida',
        'hr_before', 'activity_before'
    ]
    
    # Filtrar solo columnas que existen
    feature_columns = [col for col in feature_columns if col in df.columns]
    
    # Targets (output) - múltiples targets
    target_columns = ['glucose_increment', 'glucose_peak', 'time_to_peak']
    
    # Preparar datos
    X = df[feature_columns].copy()
    y = df[target_columns].copy()
    
    # Eliminar filas con valores faltantes en features esenciales
    print(f"  📊 Filas antes de limpieza: {len(X):,}")
    X = X.dropna()
    y = y.loc[X.index]
    print(f"  📊 Filas después de limpieza: {len(X):,}")
    
    if len(X) == 0:
        print("  ❌ No hay datos suficientes después de la limpieza")
        return
    
    # 3. Dividir en entrenamiento y prueba
    print("\n📊 Dividiendo datos (80% entrenamiento, 20% prueba)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=None
    )
    
    print(f"  ✅ Entrenamiento: {len(X_train):,} muestras")
    print(f"  ✅ Prueba: {len(X_test):,} muestras")
    
    # 4. Escalar features
    print("\n🔧 Escalando features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Convertir a DataFrame para mantener nombres de columnas
    X_train_scaled = pd.DataFrame(X_train_scaled, columns=feature_columns, index=X_train.index)
    X_test_scaled = pd.DataFrame(X_test_scaled, columns=feature_columns, index=X_test.index)
    
    # 5. Entrenar modelos para cada target
    print("\n🤖 Entrenando modelos XGBoost...")
    
    modelos = {}
    resultados = {}
    
    for target in target_columns:
        print(f"\n  📈 Entrenando modelo para: {target}")
        
        y_train_target = y_train[target].values
        y_test_target = y_test[target].values
        
        # Filtrar valores válidos
        mask_train = ~np.isnan(y_train_target) & np.isfinite(y_train_target)
        mask_test = ~np.isnan(y_test_target) & np.isfinite(y_test_target)
        
        X_train_clean = X_train_scaled[mask_train]
        y_train_clean = y_train_target[mask_train]
        X_test_clean = X_test_scaled[mask_test]
        y_test_clean = y_test_target[mask_test]
        
        if len(X_train_clean) == 0:
            print(f"    ⚠️  No hay datos válidos para {target}, saltando...")
            continue
        
        # Configurar modelo XGBoost
        modelo = xgb.XGBRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbosity=0
        )
        
        # Entrenar
        modelo.fit(X_train_clean, y_train_clean)
        
        # Predecir
        y_pred_train = modelo.predict(X_train_clean)
        y_pred_test = modelo.predict(X_test_clean)
        
        # Calcular métricas
        mae_train = mean_absolute_error(y_train_clean, y_pred_train)
        mae_test = mean_absolute_error(y_test_clean, y_pred_test)
        rmse_train = np.sqrt(mean_squared_error(y_train_clean, y_pred_train))
        rmse_test = np.sqrt(mean_squared_error(y_test_clean, y_pred_test))
        r2_train = r2_score(y_train_clean, y_pred_train)
        r2_test = r2_score(y_test_clean, y_pred_test)
        
        modelos[target] = modelo
        resultados[target] = {
            'mae_train': mae_train,
            'mae_test': mae_test,
            'rmse_train': rmse_train,
            'rmse_test': rmse_test,
            'r2_train': r2_train,
            'r2_test': r2_test
        }
        
        print(f"    ✅ Entrenamiento completado")
        print(f"       MAE (train/test): {mae_train:.2f} / {mae_test:.2f}")
        print(f"       RMSE (train/test): {rmse_train:.2f} / {rmse_test:.2f}")
        print(f"       R² (train/test): {r2_train:.3f} / {r2_test:.3f}")
    
    # 6. Guardar modelos y scaler
    print("\n💾 Guardando modelos y scaler...")
    
    modelo_completo = {
        'modelos': modelos,
        'feature_columns': feature_columns,
        'target_columns': target_columns,
        'scaler': scaler
    }
    
    with open(MODEL_FILE, 'wb') as f:
        pickle.dump(modelo_completo, f)
    
    with open(SCALER_FILE, 'wb') as f:
        pickle.dump(scaler, f)
    
    print(f"  ✅ Modelo guardado en: {MODEL_FILE}")
    print(f"  ✅ Scaler guardado en: {SCALER_FILE}")
    
    # 7. Resumen final
    print("\n" + "=" * 70)
    print("✅ ENTRENAMIENTO COMPLETO")
    print("=" * 70)
    print("\n📊 RESUMEN DE RESULTADOS:")
    print()
    
    for target, metrics in resultados.items():
        print(f"🎯 {target.upper()}:")
        print(f"   MAE (test): {metrics['mae_test']:.2f}")
        print(f"   RMSE (test): {metrics['rmse_test']:.2f}")
        print(f"   R² (test): {metrics['r2_test']:.3f}")
        print()
    
    print("=" * 70)
    print("✅ FIN DEL ENTRENAMIENTO")
    print("=" * 70)

if __name__ == "__main__":
    entrenar_modelo1()

