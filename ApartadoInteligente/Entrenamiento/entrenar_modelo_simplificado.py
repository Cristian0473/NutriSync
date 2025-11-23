"""
Script para entrenar un modelo XGBoost SIMPLIFICADO usando solo las variables
disponibles en la base de datos del sistema.

Variables disponibles:
- Antropometría: peso, talla, imc, cc (circunferencia de cintura)
- Clínicas: ldl, trigliceridos, pa_sis, pa_dia
- Demográficas: edad, sexo, actividad

Variables NO disponibles (excluidas):
- hdl, colesterol_total, insulina_ayunas
- Variables derivadas: no_hdl, homa_ir, tg_hdl_ratio, ldl_hdl_ratio, aip
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pickle
from datetime import datetime
import warnings

# Scikit-learn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix
)

# XGBoost
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    print("❌ XGBoost no está instalado. Instalar con: pip install xgboost")
    exit(1)

# SMOTE para manejo de clases desbalanceadas
try:
    from imblearn.over_sampling import SMOTE
    SMOTE_AVAILABLE = True
except ImportError:
    print("⚠️  imbalanced-learn no está instalado. Instalar con: pip install imbalanced-learn")
    SMOTE_AVAILABLE = False

warnings.filterwarnings('ignore')

# Configuración
BASE_DIR = Path(__file__).parent
DATASETS_DIR = BASE_DIR / "Datasets"
MODELOS_DIR = BASE_DIR / "ModeloEntrenamiento"
MODELOS_DIR.mkdir(exist_ok=True)

# Semilla para reproducibilidad
RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

# Variables disponibles en la BD del sistema
FEATURES_DISPONIBLES = [
    # Antropometría
    'edad', 'peso', 'talla', 'imc', 'cc',
    # Clínicas
    'ldl', 'trigliceridos', 'pa_sis', 'pa_dia',
    # Categóricas
    'sexo', 'actividad'
]

TARGET = 'control_glucemico'  # Binario: 1 si HbA1c ≥ 7.0


def cargar_datos():
    """Carga el dataset procesado."""
    print("="*60)
    print("CARGANDO DATOS")
    print("="*60)
    
    archivo = DATASETS_DIR / "nhanes_procesado.csv"
    if not archivo.exists():
        raise FileNotFoundError(f"Dataset no encontrado: {archivo}")
    
    df = pd.read_csv(archivo)
    print(f"✅ Dataset cargado: {len(df):,} filas, {len(df.columns)} columnas")
    
    return df


def preparar_features_simplificadas(df: pd.DataFrame):
    """
    Prepara las features usando SOLO las variables disponibles en la BD.
    """
    print("\n" + "="*60)
    print("PREPARANDO FEATURES SIMPLIFICADAS")
    print("="*60)
    print("📋 Variables disponibles en la BD del sistema:")
    print("   - Antropometría: edad, peso, talla, imc, cc")
    print("   - Clínicas: ldl, trigliceridos, pa_sis, pa_dia")
    print("   - Categóricas: sexo, actividad")
    
    # Seleccionar solo las features disponibles
    features_num = [f for f in FEATURES_DISPONIBLES if f in df.columns and f not in ['sexo', 'actividad']]
    features_cat = [f for f in FEATURES_DISPONIBLES if f in df.columns and f in ['sexo', 'actividad']]
    
    print(f"\n📊 Features numéricas seleccionadas: {len(features_num)}")
    for f in features_num:
        completos = df[f].notna().sum()
        print(f"   - {f:20s}: {completos:4d} valores ({completos/len(df)*100:5.1f}%)")
    
    print(f"\n📋 Features categóricas seleccionadas: {len(features_cat)}")
    for f in features_cat:
        completos = df[f].notna().sum()
        print(f"   - {f:20s}: {completos:4d} valores ({completos/len(df)*100:5.1f}%)")
    
    # Crear DataFrame de features
    X = df[features_num + features_cat].copy()
    
    # Codificar variables categóricas
    le_sexo = LabelEncoder()
    le_actividad = LabelEncoder()
    
    if 'sexo' in X.columns:
        X['sexo'] = X['sexo'].fillna('M')
        X['sexo_encoded'] = le_sexo.fit_transform(X['sexo'])
        X = X.drop(columns=['sexo'])
    
    if 'actividad' in X.columns:
        X['actividad'] = X['actividad'].fillna('moderada')
        X['actividad_encoded'] = le_actividad.fit_transform(X['actividad'])
        X = X.drop(columns=['actividad'])
    
    # Preparar target
    y = None
    if TARGET in df.columns:
        y = df[TARGET].copy()
        completos = y.notna().sum()
        print(f"\n🎯 Target ({TARGET}): {completos} valores")
        if completos > 0:
            balance = y.value_counts()
            print(f"   - Clase 0 (control bueno): {balance.get(0, 0)} ({balance.get(0, 0)/completos*100:.1f}%)")
            print(f"   - Clase 1 (control malo): {balance.get(1, 0)} ({balance.get(1, 0)/completos*100:.1f}%)")
    
    # Guardar encoders
    encoders = {}
    if 'sexo' in features_cat:
        encoders['sexo'] = le_sexo
    if 'actividad' in features_cat:
        encoders['actividad'] = le_actividad
    
    return X, y, encoders


def dividir_datos(X, y, test_size=0.15, val_size=0.15):
    """Divide los datos en train, validation y test."""
    print("\n" + "="*60)
    print("DIVIDIENDO DATOS")
    print("="*60)
    
    # Primero separar test
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=test_size, random_state=RANDOM_STATE, stratify=y
    )
    
    # Luego separar train y validation
    val_size_ajustado = val_size / (1 - test_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=val_size_ajustado, random_state=RANDOM_STATE, stratify=y_temp
    )
    
    print(f"📊 División de datos:")
    print(f"   - Train: {len(X_train):,} ({len(X_train)/len(X)*100:.1f}%)")
    print(f"   - Validation: {len(X_val):,} ({len(X_val)/len(X)*100:.1f}%)")
    print(f"   - Test: {len(X_test):,} ({len(X_test)/len(X)*100:.1f}%)")
    
    return X_train, X_val, X_test, y_train, y_val, y_test


def imputar_y_escalar(X_train, X_val, X_test):
    """Imputa valores faltantes y escala las features."""
    print("\n" + "="*60)
    print("PREPROCESAMIENTO")
    print("="*60)
    
    # Imputar valores faltantes
    imputer = SimpleImputer(strategy='median')
    X_train_imputed = pd.DataFrame(
        imputer.fit_transform(X_train),
        columns=X_train.columns,
        index=X_train.index
    )
    X_val_imputed = pd.DataFrame(
        imputer.transform(X_val),
        columns=X_val.columns,
        index=X_val.index
    )
    X_test_imputed = pd.DataFrame(
        imputer.transform(X_test),
        columns=X_test.columns,
        index=X_test.index
    )
    
    print("✅ Valores faltantes imputados (estrategia: median)")
    
    # Escalar features
    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(
        scaler.fit_transform(X_train_imputed),
        columns=X_train_imputed.columns,
        index=X_train_imputed.index
    )
    X_val_scaled = pd.DataFrame(
        scaler.transform(X_val_imputed),
        columns=X_val_imputed.columns,
        index=X_val_imputed.index
    )
    X_test_scaled = pd.DataFrame(
        scaler.transform(X_test_imputed),
        columns=X_test_imputed.columns,
        index=X_test_imputed.index
    )
    
    print("✅ Features escaladas (StandardScaler)")
    
    return X_train_scaled, X_val_scaled, X_test_scaled, imputer, scaler


def balancear_clases(X_train, y_train):
    """Balancea las clases usando SMOTE."""
    print("\n" + "="*60)
    print("BALANCEANDO CLASES")
    print("="*60)
    
    balance_antes = y_train.value_counts()
    print(f"📊 Balance ANTES:")
    print(f"   - Clase 0: {balance_antes.get(0, 0)} ({balance_antes.get(0, 0)/len(y_train)*100:.1f}%)")
    print(f"   - Clase 1: {balance_antes.get(1, 0)} ({balance_antes.get(1, 0)/len(y_train)*100:.1f}%)")
    
    if SMOTE_AVAILABLE:
        smote = SMOTE(random_state=RANDOM_STATE, k_neighbors=5)
        X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)
        
        balance_despues = pd.Series(y_train_balanced).value_counts()
        print(f"\n📊 Balance DESPUÉS (SMOTE):")
        print(f"   - Clase 0: {balance_despues.get(0, 0)} ({balance_despues.get(0, 0)/len(y_train_balanced)*100:.1f}%)")
        print(f"   - Clase 1: {balance_despues.get(1, 0)} ({balance_despues.get(1, 0)/len(y_train_balanced)*100:.1f}%)")
        
        # Calcular scale_pos_weight para XGBoost
        clases, conteos = np.unique(y_train_balanced, return_counts=True)
        if len(clases) == 2:
            scale_pos_weight = conteos[0] / conteos[1]
        else:
            scale_pos_weight = None
        
        return X_train_balanced, y_train_balanced, scale_pos_weight
    else:
        print("⚠️  SMOTE no disponible, usando datos sin balancear")
        clases, conteos = np.unique(y_train, return_counts=True)
        if len(clases) == 2:
            scale_pos_weight = conteos[0] / conteos[1]
        else:
            scale_pos_weight = None
        return X_train, y_train, scale_pos_weight


def entrenar_xgboost_simplificado(X_train, y_train, X_val, y_val, X_test, y_test, scale_pos_weight=None):
    """Entrena un modelo XGBoost simplificado."""
    print("\n" + "="*60)
    print("ENTRENANDO XGBOOST SIMPLIFICADO")
    print("="*60)
    
    # Modelo optimizado para dataset con menos features
    modelo = xgb.XGBClassifier(
        n_estimators=150,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.5,
        reg_lambda=0.5,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        eval_metric='logloss',
        scale_pos_weight=scale_pos_weight
    )
    
    print("🔧 Hiperparámetros:")
    print(f"   - n_estimators: {modelo.n_estimators}")
    print(f"   - max_depth: {modelo.max_depth}")
    print(f"   - learning_rate: {modelo.learning_rate}")
    print(f"   - scale_pos_weight: {scale_pos_weight:.2f}" if scale_pos_weight else "   - scale_pos_weight: None")
    
    # Entrenar
    print("\n📚 Entrenando modelo...")
    modelo.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )
    
    # Predicciones
    y_train_pred = modelo.predict(X_train)
    y_val_pred = modelo.predict(X_val)
    y_test_pred = modelo.predict(X_test)
    
    y_train_proba = modelo.predict_proba(X_train)[:, 1]
    y_val_proba = modelo.predict_proba(X_val)[:, 1]
    y_test_proba = modelo.predict_proba(X_test)[:, 1]
    
    # Métricas
    metricas = {
        'modelo': 'XGBoost_Simplificado',
        'features': list(X_train.columns),
        'n_features': len(X_train.columns),
        'train': {
            'accuracy': accuracy_score(y_train, y_train_pred),
            'precision': precision_score(y_train, y_train_pred, zero_division=0),
            'recall': recall_score(y_train, y_train_pred, zero_division=0),
            'f1': f1_score(y_train, y_train_pred, zero_division=0),
            'auc_roc': roc_auc_score(y_train, y_train_proba)
        },
        'val': {
            'accuracy': accuracy_score(y_val, y_val_pred),
            'precision': precision_score(y_val, y_val_pred, zero_division=0),
            'recall': recall_score(y_val, y_val_pred, zero_division=0),
            'f1': f1_score(y_val, y_val_pred, zero_division=0),
            'auc_roc': roc_auc_score(y_val, y_val_proba)
        },
        'test': {
            'accuracy': accuracy_score(y_test, y_test_pred),
            'precision': precision_score(y_test, y_test_pred, zero_division=0),
            'recall': recall_score(y_test, y_test_pred, zero_division=0),
            'f1': f1_score(y_test, y_test_pred, zero_division=0),
            'auc_roc': roc_auc_score(y_test, y_test_proba)
        }
    }
    
    # Mostrar métricas
    print("\n📊 MÉTRICAS DEL MODELO:")
    print(f"\n   TRAIN:")
    print(f"   - Accuracy:  {metricas['train']['accuracy']:.4f}")
    print(f"   - Precision: {metricas['train']['precision']:.4f}")
    print(f"   - Recall:    {metricas['train']['recall']:.4f}")
    print(f"   - F1-Score:  {metricas['train']['f1']:.4f}")
    print(f"   - AUC-ROC:   {metricas['train']['auc_roc']:.4f}")
    
    print(f"\n   VALIDATION:")
    print(f"   - Accuracy:  {metricas['val']['accuracy']:.4f}")
    print(f"   - Precision: {metricas['val']['precision']:.4f}")
    print(f"   - Recall:    {metricas['val']['recall']:.4f}")
    print(f"   - F1-Score:  {metricas['val']['f1']:.4f}")
    print(f"   - AUC-ROC:   {metricas['val']['auc_roc']:.4f}")
    
    print(f"\n   TEST:")
    print(f"   - Accuracy:  {metricas['test']['accuracy']:.4f}")
    print(f"   - Precision: {metricas['test']['precision']:.4f}")
    print(f"   - Recall:    {metricas['test']['recall']:.4f}")
    print(f"   - F1-Score:  {metricas['test']['f1']:.4f}")
    print(f"   - AUC-ROC:   {metricas['test']['auc_roc']:.4f}")
    
    # Matriz de confusión
    cm_test = confusion_matrix(y_test, y_test_pred)
    print(f"\n📋 Matriz de confusión (TEST):")
    print(f"   {'':>15} Predicción")
    print(f"   {'':>15}  0     1")
    print(f"   Real  0  {cm_test[0,0]:4d}  {cm_test[0,1]:4d}")
    print(f"         1  {cm_test[1,0]:4d}  {cm_test[1,1]:4d}")
    
    return modelo, metricas


def guardar_modelo_simplificado(modelo, metricas, imputer, scaler, encoders):
    """Guarda el modelo simplificado y preprocesadores."""
    print("\n" + "="*60)
    print("GUARDANDO MODELO")
    print("="*60)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Guardar modelo
    modelo_path = MODELOS_DIR / f"modelo_xgboost_simplificado_{timestamp}.pkl"
    with open(modelo_path, 'wb') as f:
        pickle.dump(modelo, f)
    print(f"✅ Modelo guardado: {modelo_path.name}")
    
    # Guardar preprocesadores
    preprocesadores = {
        'imputer': imputer,
        'scaler': scaler,
        'encoders': encoders
    }
    preprocesadores_path = MODELOS_DIR / f"preprocesadores_simplificado_{timestamp}.pkl"
    with open(preprocesadores_path, 'wb') as f:
        pickle.dump(preprocesadores, f)
    print(f"✅ Preprocesadores guardados: {preprocesadores_path.name}")
    
    # Guardar métricas
    metricas_path = MODELOS_DIR / f"metricas_simplificado_{timestamp}.json"
    import json
    with open(metricas_path, 'w') as f:
        json.dump(metricas, f, indent=2)
    print(f"✅ Métricas guardadas: {metricas_path.name}")
    
    print(f"\n📁 Archivos guardados en: {MODELOS_DIR}")
    print(f"\n⚠️  IMPORTANTE: Actualiza motor_recomendacion.py para usar este modelo simplificado")
    print(f"   Busca: modelo_xgboost_*.pkl")
    print(f"   Cambia a: modelo_xgboost_simplificado_*.pkl")


def main():
    """Función principal."""
    print("="*60)
    print("ENTRENAMIENTO DE MODELO XGBOOST SIMPLIFICADO")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📋 Este modelo usa SOLO las variables disponibles en tu BD:")
    print("   - Antropometría: edad, peso, talla, imc, cc")
    print("   - Clínicas: ldl, trigliceridos, pa_sis, pa_dia")
    print("   - Categóricas: sexo, actividad")
    
    try:
        # 1. Cargar datos
        df = cargar_datos()
        
        # 2. Preparar features simplificadas
        X, y, encoders = preparar_features_simplificadas(df)
        
        if y is None:
            print("\n❌ ERROR: No se encontró target")
            return
        
        # 3. Dividir datos
        X_train, X_val, X_test, y_train, y_val, y_test = dividir_datos(X, y)
        
        # 4. Imputar y escalar
        X_train_scaled, X_val_scaled, X_test_scaled, imputer, scaler = imputar_y_escalar(
            X_train, X_val, X_test
        )
        
        # 5. Balancear clases
        X_train_balanced, y_train_balanced, scale_pos_weight = balancear_clases(
            X_train_scaled, y_train
        )
        
        # 6. Entrenar modelo
        modelo, metricas = entrenar_xgboost_simplificado(
            X_train_balanced, y_train_balanced, X_val_scaled, y_val, X_test_scaled, y_test,
            scale_pos_weight=scale_pos_weight
        )
        
        # 7. Guardar modelo
        guardar_modelo_simplificado(modelo, metricas, imputer, scaler, encoders)
        
        print("\n" + "="*60)
        print("✅ ENTRENAMIENTO COMPLETADO")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


