"""
Script para entrenar el Modelo 3: Optimización de Combinaciones de Alimentos.

Algoritmo: Ensemble (XGBoost + Random Forest)
Target: score_calidad (regresión) o clasificación binaria (buena/mala combinación)
"""

import pandas as pd
import numpy as np
import os
import pickle
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

# Configuración de rutas
INPUT_FILE = r"D:\Sistema Tesis\data_para_entrenamiento\modelo3_combinaciones.csv"
OUTPUT_DIR = r"D:\Sistema Tesis\ApartadoInteligente\ModeloML"
MODEL_FILE = os.path.join(OUTPUT_DIR, "modelo_optimizacion_combinaciones.pkl")
SCALER_FILE = os.path.join(OUTPUT_DIR, "scaler_combinaciones.pkl")

def entrenar_modelo3():
    """
    Entrena el modelo de optimización de combinaciones usando ensemble.
    """
    print("=" * 70)
    print("🤖 ENTRENANDO MODELO 3: OPTIMIZACIÓN DE COMBINACIONES")
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
        # Características de la combinación
        'n_comidas_combinadas', 'total_calories', 'total_carbs', 'total_protein', 
        'total_fat', 'total_fiber',
        'carbs_percent', 'protein_percent', 'fat_percent',
        'tipos_comida',
        # Contexto temporal
        'hora_primera_comida', 'duracion_combinacion'
    ]
    
    # Filtrar solo columnas que existen
    feature_columns = [col for col in feature_columns if col in df.columns]
    
    # Target: score_calidad (0-1)
    target_column = 'score_calidad'
    
    # Preparar datos
    X = df[feature_columns].copy()
    y = df[target_column].copy()
    
    # Eliminar filas con valores faltantes
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
        X, y, test_size=0.2, random_state=42
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
    
    # 5. Entrenar modelos (Ensemble)
    print("\n🤖 Entrenando modelos ensemble...")
    
    # Modelo 1: XGBoost
    print("\n  📈 Entrenando XGBoost Regressor...")
    modelo_xgb = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbosity=0
    )
    modelo_xgb.fit(X_train_scaled, y_train)
    
    y_pred_xgb_train = modelo_xgb.predict(X_train_scaled)
    y_pred_xgb_test = modelo_xgb.predict(X_test_scaled)
    
    mae_xgb_test = mean_absolute_error(y_test, y_pred_xgb_test)
    rmse_xgb_test = np.sqrt(mean_squared_error(y_test, y_pred_xgb_test))
    r2_xgb_test = r2_score(y_test, y_pred_xgb_test)
    
    print(f"    ✅ XGBoost - MAE: {mae_xgb_test:.3f}, RMSE: {rmse_xgb_test:.3f}, R²: {r2_xgb_test:.3f}")
    
    # Modelo 2: Random Forest
    print("\n  📈 Entrenando Random Forest Regressor...")
    modelo_rf = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    modelo_rf.fit(X_train_scaled, y_train)
    
    y_pred_rf_train = modelo_rf.predict(X_train_scaled)
    y_pred_rf_test = modelo_rf.predict(X_test_scaled)
    
    mae_rf_test = mean_absolute_error(y_test, y_pred_rf_test)
    rmse_rf_test = np.sqrt(mean_squared_error(y_test, y_pred_rf_test))
    r2_rf_test = r2_score(y_test, y_pred_rf_test)
    
    print(f"    ✅ Random Forest - MAE: {mae_rf_test:.3f}, RMSE: {rmse_rf_test:.3f}, R²: {r2_rf_test:.3f}")
    
    # Ensemble: Promedio de predicciones
    print("\n  📈 Creando ensemble (promedio de predicciones)...")
    y_pred_ensemble_test = (y_pred_xgb_test + y_pred_rf_test) / 2
    
    mae_ensemble_test = mean_absolute_error(y_test, y_pred_ensemble_test)
    rmse_ensemble_test = np.sqrt(mean_squared_error(y_test, y_pred_ensemble_test))
    r2_ensemble_test = r2_score(y_test, y_pred_ensemble_test)
    
    print(f"    ✅ Ensemble - MAE: {mae_ensemble_test:.3f}, RMSE: {rmse_ensemble_test:.3f}, R²: {r2_ensemble_test:.3f}")
    
    # Usar el mejor modelo (ensemble)
    modelo_final = {
        'xgb': modelo_xgb,
        'rf': modelo_rf,
        'tipo': 'ensemble'
    }
    
    # 6. Guardar modelos y scaler
    print("\n💾 Guardando modelos y scaler...")
    
    modelo_completo = {
        'modelos': modelo_final,
        'feature_columns': feature_columns,
        'target_column': target_column,
        'scaler': scaler,
        'metricas': {
            'xgb': {'mae': mae_xgb_test, 'rmse': rmse_xgb_test, 'r2': r2_xgb_test},
            'rf': {'mae': mae_rf_test, 'rmse': rmse_rf_test, 'r2': r2_rf_test},
            'ensemble': {'mae': mae_ensemble_test, 'rmse': rmse_ensemble_test, 'r2': r2_ensemble_test}
        }
    }
    
    with open(MODEL_FILE, 'wb') as f:
        pickle.dump(modelo_completo, f)
    
    print(f"  ✅ Modelo guardado en: {MODEL_FILE}")
    
    # 7. Resumen final
    print("\n" + "=" * 70)
    print("✅ ENTRENAMIENTO COMPLETO")
    print("=" * 70)
    print(f"\n📊 RESULTADOS FINALES (Test):")
    print(f"\n  🎯 XGBoost:")
    print(f"     MAE: {mae_xgb_test:.3f}")
    print(f"     RMSE: {rmse_xgb_test:.3f}")
    print(f"     R²: {r2_xgb_test:.3f}")
    
    print(f"\n  🎯 Random Forest:")
    print(f"     MAE: {mae_rf_test:.3f}")
    print(f"     RMSE: {rmse_rf_test:.3f}")
    print(f"     R²: {r2_rf_test:.3f}")
    
    print(f"\n  🎯 Ensemble (FINAL):")
    print(f"     MAE: {mae_ensemble_test:.3f}")
    print(f"     RMSE: {rmse_ensemble_test:.3f}")
    print(f"     R²: {r2_ensemble_test:.3f}")
    
    print("\n" + "=" * 70)
    print("✅ FIN DEL ENTRENAMIENTO")
    print("=" * 70)

if __name__ == "__main__":
    entrenar_modelo3()

