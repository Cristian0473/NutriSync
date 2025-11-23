"""
Script para entrenar modelos de Machine Learning con el dataset NHANES procesado.

Modelos a entrenar:
1. Logistic Regression (baseline)
2. Random Forest (con regularización)
3. XGBoost (con regularización)

Targets:
- control_glucemico: 1 si HbA1c ≥ 7.0, 0 si no
- riesgo_metabolico: score continuo (0-1)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import json
from datetime import datetime
import warnings

# Scikit-learn
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, confusion_matrix,
    mean_absolute_error, mean_squared_error, r2_score
)

# XGBoost
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    print("⚠️  XGBoost no está instalado. Instalar con: pip install xgboost")
    XGBOOST_AVAILABLE = False

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

# Variables a usar como features
# NOTA: No incluir 'hba1c' ni 'glucosa_ayunas' cuando se predice 'control_glucemico'
# porque el target se calcula directamente de estas variables (data leakage)
FEATURES_NUMERICAS = [
    'edad', 'peso', 'talla', 'imc', 'cc',
    'ldl', 'hdl', 'trigliceridos', 'colesterol_total',
    'pa_sis', 'pa_dia', 'insulina_ayunas',
    'no_hdl', 'homa_ir', 'tg_hdl_ratio', 'ldl_hdl_ratio', 'aip'
]

# Features que causan data leakage si se usan para predecir control_glucemico
FEATURES_LEAKAGE = ['hba1c', 'glucosa_ayunas']

FEATURES_CATEGORICAS = ['sexo', 'actividad']

# Targets
TARGET_CLASIFICACION = 'control_glucemico'  # Binario: 1 si HbA1c ≥ 7.0
TARGET_REGRESION = 'riesgo_metabolico'      # Continuo: 0-1


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


def preparar_features(df: pd.DataFrame, excluir_leakage: bool = True):
    """
    Prepara las features para el entrenamiento.
    
    Args:
        df: DataFrame con todos los datos
        excluir_leakage: Si True, excluye features que causan data leakage
        
    Returns:
        X: DataFrame con features
        y_clasificacion: Series con target de clasificación
        y_regresion: Series con target de regresión
    """
    print("\n" + "="*60)
    print("PREPARANDO FEATURES")
    print("="*60)
    
    if excluir_leakage:
        print("⚠️  EXCLUYENDO features que causan data leakage:")
        print("   - hba1c (el target se calcula de esta variable)")
        print("   - glucosa_ayunas (también usada en el cálculo del target)")
    
    # Seleccionar features numéricas disponibles (excluyendo leakage si es necesario)
    features_num = [f for f in FEATURES_NUMERICAS if f in df.columns]
    if excluir_leakage:
        features_num = [f for f in features_num if f not in FEATURES_LEAKAGE]
    
    print(f"\n📊 Features numéricas: {len(features_num)}")
    for f in features_num:
        completos = df[f].notna().sum()
        print(f"   - {f:20s}: {completos:4d} valores ({completos/len(df)*100:5.1f}%)")
    
    # Seleccionar features categóricas disponibles
    features_cat = [f for f in FEATURES_CATEGORICAS if f in df.columns]
    print(f"\n📋 Features categóricas: {len(features_cat)}")
    for f in features_cat:
        completos = df[f].notna().sum()
        print(f"   - {f:20s}: {completos:4d} valores ({completos/len(df)*100:5.1f}%)")
    
    # Crear DataFrame de features
    X = df[features_num + features_cat].copy()
    
    # Codificar variables categóricas
    le_sexo = LabelEncoder()
    le_actividad = LabelEncoder()
    
    if 'sexo' in X.columns:
        X['sexo'] = X['sexo'].fillna('M')  # Valor por defecto
        X['sexo_encoded'] = le_sexo.fit_transform(X['sexo'])
        X = X.drop(columns=['sexo'])
    
    if 'actividad' in X.columns:
        X['actividad'] = X['actividad'].fillna('moderada')  # Valor por defecto
        X['actividad_encoded'] = le_actividad.fit_transform(X['actividad'])
        X = X.drop(columns=['actividad'])
    
    # Preparar targets
    y_clasificacion = None
    y_regresion = None
    
    if TARGET_CLASIFICACION in df.columns:
        y_clasificacion = df[TARGET_CLASIFICACION].copy()
        completos = y_clasificacion.notna().sum()
        print(f"\n🎯 Target clasificación ({TARGET_CLASIFICACION}): {completos} valores")
        if completos > 0:
            balance = y_clasificacion.value_counts()
            print(f"   - Clase 0 (control bueno): {balance.get(0, 0)} ({balance.get(0, 0)/completos*100:.1f}%)")
            print(f"   - Clase 1 (control malo): {balance.get(1, 0)} ({balance.get(1, 0)/completos*100:.1f}%)")
    
    if TARGET_REGRESION in df.columns:
        y_regresion = df[TARGET_REGRESION].copy()
        completos = y_regresion.notna().sum()
        print(f"\n🎯 Target regresión ({TARGET_REGRESION}): {completos} valores")
        if completos > 0:
            print(f"   - Media: {y_regresion.mean():.3f}")
            print(f"   - Desv. std: {y_regresion.std():.3f}")
            print(f"   - Min: {y_regresion.min():.3f}, Max: {y_regresion.max():.3f}")
    
    # Guardar encoders para uso futuro
    encoders = {
        'sexo': le_sexo,
        'actividad': le_actividad
    }
    
    return X, y_clasificacion, y_regresion, encoders


def dividir_datos(X, y, test_size=0.15, val_size=0.15, random_state=RANDOM_STATE):
    """
    Divide los datos en train, validation y test.
    
    Args:
        X: Features
        y: Target
        test_size: Porcentaje para test
        val_size: Porcentaje para validation (del train restante)
        random_state: Semilla aleatoria
        
    Returns:
        X_train, X_val, X_test, y_train, y_val, y_test
    """
    print("\n" + "="*60)
    print("DIVIDIENDO DATOS")
    print("="*60)
    
    # Eliminar filas con target faltante
    mask = y.notna()
    X_clean = X[mask].copy()
    y_clean = y[mask].copy()
    
    print(f"📊 Datos válidos: {len(X_clean):,} filas")
    
    # Primera división: train+val / test
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X_clean, y_clean, test_size=test_size, random_state=random_state, stratify=y_clean if y_clean.dtype == 'int64' else None
    )
    
    # Segunda división: train / val
    val_size_adjusted = val_size / (1 - test_size)  # Ajustar para que val sea 15% del total
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=val_size_adjusted, random_state=random_state, stratify=y_train_val if y_train_val.dtype == 'int64' else None
    )
    
    print(f"✅ Train: {len(X_train):,} filas ({len(X_train)/len(X_clean)*100:.1f}%)")
    print(f"✅ Validation: {len(X_val):,} filas ({len(X_val)/len(X_clean)*100:.1f}%)")
    print(f"✅ Test: {len(X_test):,} filas ({len(X_test)/len(X_clean)*100:.1f}%)")
    
    return X_train, X_val, X_test, y_train, y_val, y_test


def imputar_valores_faltantes(X_train, X_val, X_test):
    """
    Imputa valores faltantes usando la mediana (numéricas) o moda (categóricas).
    
    Args:
        X_train, X_val, X_test: DataFrames de features
        
    Returns:
        X_train_imputed, X_val_imputed, X_test_imputed, imputer
    """
    print("\n" + "="*60)
    print("IMPUTANDO VALORES FALTANTES")
    print("="*60)
    
    # Usar mediana para imputación (más robusta que la media)
    imputer = SimpleImputer(strategy='median')
    
    # Ajustar con train y transformar todos
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
    
    print(f"✅ Valores faltantes imputados")
    print(f"   - Train: {X_train_imputed.isna().sum().sum()} faltantes restantes")
    print(f"   - Val: {X_val_imputed.isna().sum().sum()} faltantes restantes")
    print(f"   - Test: {X_test_imputed.isna().sum().sum()} faltantes restantes")
    
    return X_train_imputed, X_val_imputed, X_test_imputed, imputer


def escalar_features(X_train, X_val, X_test):
    """
    Escala las features usando StandardScaler.
    
    Args:
        X_train, X_val, X_test: DataFrames de features
        
    Returns:
        X_train_scaled, X_val_scaled, X_test_scaled, scaler
    """
    print("\n" + "="*60)
    print("ESCALANDO FEATURES")
    print("="*60)
    
    scaler = StandardScaler()
    
    X_train_scaled = pd.DataFrame(
        scaler.fit_transform(X_train),
        columns=X_train.columns,
        index=X_train.index
    )
    
    X_val_scaled = pd.DataFrame(
        scaler.transform(X_val),
        columns=X_val.columns,
        index=X_val.index
    )
    
    X_test_scaled = pd.DataFrame(
        scaler.transform(X_test),
        columns=X_test.columns,
        index=X_test.index
    )
    
    print("✅ Features escaladas (StandardScaler)")
    
    return X_train_scaled, X_val_scaled, X_test_scaled, scaler


def balancear_clases(X_train, y_train, usar_smote: bool = True):
    """
    Balancea las clases usando SMOTE o class weights.
    
    Args:
        X_train: Features de entrenamiento
        y_train: Target de entrenamiento
        usar_smote: Si True, usa SMOTE; si False, solo calcula class weights
        
    Returns:
        X_train_balanced, y_train_balanced, class_weights
    """
    print("\n" + "="*60)
    print("BALANCEANDO CLASES")
    print("="*60)
    
    # Calcular distribución de clases
    clases, conteos = np.unique(y_train, return_counts=True)
    print(f"📊 Distribución de clases original:")
    for clase, conteo in zip(clases, conteos):
        porcentaje = (conteo / len(y_train)) * 100
        print(f"   - Clase {clase}: {conteo} ({porcentaje:.1f}%)")
    
    # Calcular class weights
    from sklearn.utils.class_weight import compute_class_weight
    class_weights = compute_class_weight('balanced', classes=clases, y=y_train)
    class_weight_dict = dict(zip(clases, class_weights))
    print(f"\n⚖️  Class weights calculados: {class_weight_dict}")
    
    # Aplicar SMOTE si está disponible y se solicita
    if usar_smote and SMOTE_AVAILABLE:
        print("\n🔄 Aplicando SMOTE para balancear clases...")
        smote = SMOTE(random_state=RANDOM_STATE, k_neighbors=3)
        X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)
        
        clases_balanced, conteos_balanced = np.unique(y_train_balanced, return_counts=True)
        print(f"✅ Clases balanceadas con SMOTE:")
        for clase, conteo in zip(clases_balanced, conteos_balanced):
            porcentaje = (conteo / len(y_train_balanced)) * 100
            print(f"   - Clase {clase}: {conteo} ({porcentaje:.1f}%)")
        
        return X_train_balanced, y_train_balanced, class_weight_dict
    else:
        if usar_smote and not SMOTE_AVAILABLE:
            print("⚠️  SMOTE no disponible. Usando solo class weights.")
        return X_train, y_train, class_weight_dict


def entrenar_logistic_regression(X_train, y_train, X_val, y_val, X_test, y_test, class_weight=None):
    """
    Entrena un modelo de Logistic Regression.
    
    Returns:
        modelo, metricas
    """
    print("\n" + "="*60)
    print("ENTRENANDO LOGISTIC REGRESSION")
    print("="*60)
    
    # Modelo con regularización fuerte
    modelo = LogisticRegression(
        max_iter=1000,
        C=0.1,  # Regularización fuerte (C pequeño = más regularización)
        penalty='l2',
        random_state=RANDOM_STATE,
        solver='lbfgs',
        class_weight=class_weight  # Balancear clases
    )
    
    print("🔧 Hiperparámetros:")
    print(f"   - C: {modelo.C} (regularización)")
    print(f"   - Penalty: {modelo.penalty}")
    print(f"   - Max iterations: {modelo.max_iter}")
    
    # Entrenar
    print("\n📚 Entrenando modelo...")
    modelo.fit(X_train, y_train)
    
    # Predicciones
    y_train_pred = modelo.predict(X_train)
    y_val_pred = modelo.predict(X_val)
    y_test_pred = modelo.predict(X_test)
    
    y_train_proba = modelo.predict_proba(X_train)[:, 1]
    y_val_proba = modelo.predict_proba(X_val)[:, 1]
    y_test_proba = modelo.predict_proba(X_test)[:, 1]
    
    # Métricas
    metricas = {
        'modelo': 'Logistic Regression',
        'train': {
            'accuracy': accuracy_score(y_train, y_train_pred),
            'precision': precision_score(y_train, y_train_pred, zero_division=0),
            'recall': recall_score(y_train, y_train_pred, zero_division=0),
            'f1': f1_score(y_train, y_train_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_train, y_train_proba) if len(np.unique(y_train)) > 1 else 0
        },
        'val': {
            'accuracy': accuracy_score(y_val, y_val_pred),
            'precision': precision_score(y_val, y_val_pred, zero_division=0),
            'recall': recall_score(y_val, y_val_pred, zero_division=0),
            'f1': f1_score(y_val, y_val_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_val, y_val_proba) if len(np.unique(y_val)) > 1 else 0
        },
        'test': {
            'accuracy': accuracy_score(y_test, y_test_pred),
            'precision': precision_score(y_test, y_test_pred, zero_division=0),
            'recall': recall_score(y_test, y_test_pred, zero_division=0),
            'f1': f1_score(y_test, y_test_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_test, y_test_proba) if len(np.unique(y_test)) > 1 else 0
        }
    }
    
    print("\n📊 Métricas:")
    print(f"   Train - Accuracy: {metricas['train']['accuracy']:.3f}, F1: {metricas['train']['f1']:.3f}, AUC: {metricas['train']['roc_auc']:.3f}")
    print(f"   Val   - Accuracy: {metricas['val']['accuracy']:.3f}, F1: {metricas['val']['f1']:.3f}, AUC: {metricas['val']['roc_auc']:.3f}")
    print(f"   Test  - Accuracy: {metricas['test']['accuracy']:.3f}, F1: {metricas['test']['f1']:.3f}, AUC: {metricas['test']['roc_auc']:.3f}")
    
    return modelo, metricas


def entrenar_random_forest(X_train, y_train, X_val, y_val, X_test, y_test, class_weight=None):
    """
    Entrena un modelo de Random Forest con regularización fuerte.
    
    Returns:
        modelo, metricas
    """
    print("\n" + "="*60)
    print("ENTRENANDO RANDOM FOREST")
    print("="*60)
    
    # Modelo con regularización fuerte para dataset pequeño
    modelo = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,  # Profundidad limitada
        min_samples_split=20,  # Más muestras por split
        min_samples_leaf=10,  # Más muestras por hoja
        max_features='sqrt',  # Menos features por split
        random_state=RANDOM_STATE,
        n_jobs=-1,
        class_weight=class_weight  # Balancear clases
    )
    
    print("🔧 Hiperparámetros:")
    print(f"   - n_estimators: {modelo.n_estimators}")
    print(f"   - max_depth: {modelo.max_depth}")
    print(f"   - min_samples_split: {modelo.min_samples_split}")
    print(f"   - min_samples_leaf: {modelo.min_samples_leaf}")
    print(f"   - max_features: {modelo.max_features}")
    
    # Entrenar
    print("\n📚 Entrenando modelo...")
    modelo.fit(X_train, y_train)
    
    # Predicciones
    y_train_pred = modelo.predict(X_train)
    y_val_pred = modelo.predict(X_val)
    y_test_pred = modelo.predict(X_test)
    
    y_train_proba = modelo.predict_proba(X_train)[:, 1]
    y_val_proba = modelo.predict_proba(X_val)[:, 1]
    y_test_proba = modelo.predict_proba(X_test)[:, 1]
    
    # Métricas
    metricas = {
        'modelo': 'Random Forest',
        'train': {
            'accuracy': accuracy_score(y_train, y_train_pred),
            'precision': precision_score(y_train, y_train_pred, zero_division=0),
            'recall': recall_score(y_train, y_train_pred, zero_division=0),
            'f1': f1_score(y_train, y_train_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_train, y_train_proba) if len(np.unique(y_train)) > 1 else 0
        },
        'val': {
            'accuracy': accuracy_score(y_val, y_val_pred),
            'precision': precision_score(y_val, y_val_pred, zero_division=0),
            'recall': recall_score(y_val, y_val_pred, zero_division=0),
            'f1': f1_score(y_val, y_val_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_val, y_val_proba) if len(np.unique(y_val)) > 1 else 0
        },
        'test': {
            'accuracy': accuracy_score(y_test, y_test_pred),
            'precision': precision_score(y_test, y_test_pred, zero_division=0),
            'recall': recall_score(y_test, y_test_pred, zero_division=0),
            'f1': f1_score(y_test, y_test_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_test, y_test_proba) if len(np.unique(y_test)) > 1 else 0
        },
        'feature_importance': dict(zip(X_train.columns, modelo.feature_importances_))
    }
    
    print("\n📊 Métricas:")
    print(f"   Train - Accuracy: {metricas['train']['accuracy']:.3f}, F1: {metricas['train']['f1']:.3f}, AUC: {metricas['train']['roc_auc']:.3f}")
    print(f"   Val   - Accuracy: {metricas['val']['accuracy']:.3f}, F1: {metricas['val']['f1']:.3f}, AUC: {metricas['val']['roc_auc']:.3f}")
    print(f"   Test  - Accuracy: {metricas['test']['accuracy']:.3f}, F1: {metricas['test']['f1']:.3f}, AUC: {metricas['test']['roc_auc']:.3f}")
    
    # Top 10 features más importantes
    if 'feature_importance' in metricas:
        top_features = sorted(metricas['feature_importance'].items(), key=lambda x: x[1], reverse=True)[:10]
        print("\n🔝 Top 10 Features más importantes:")
        for i, (feature, importance) in enumerate(top_features, 1):
            print(f"   {i:2d}. {feature:20s}: {importance:.4f}")
    
    return modelo, metricas


def entrenar_xgboost(X_train, y_train, X_val, y_val, X_test, y_test, scale_pos_weight=None):
    """
    Entrena un modelo de XGBoost con regularización fuerte.
    
    Returns:
        modelo, metricas
    """
    if not XGBOOST_AVAILABLE:
        print("⚠️  XGBoost no está disponible. Omitiendo entrenamiento.")
        return None, None
    
    print("\n" + "="*60)
    print("ENTRENANDO XGBOOST")
    print("="*60)
    
    # Modelo con regularización fuerte para dataset pequeño
    modelo = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=3,  # Profundidad limitada
        learning_rate=0.1,  # Learning rate conservador
        subsample=0.8,  # Submuestreo
        colsample_bytree=0.8,  # Submuestreo de features
        reg_alpha=1.0,  # Regularización L1
        reg_lambda=1.0,  # Regularización L2
        random_state=RANDOM_STATE,
        n_jobs=-1,
        eval_metric='logloss',
        scale_pos_weight=scale_pos_weight  # Balancear clases (ratio clase negativa/positiva)
    )
    
    print("🔧 Hiperparámetros:")
    print(f"   - n_estimators: {modelo.n_estimators}")
    print(f"   - max_depth: {modelo.max_depth}")
    print(f"   - learning_rate: {modelo.learning_rate}")
    print(f"   - subsample: {modelo.subsample}")
    print(f"   - colsample_bytree: {modelo.colsample_bytree}")
    print(f"   - reg_alpha: {modelo.reg_alpha}")
    print(f"   - reg_lambda: {modelo.reg_lambda}")
    
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
        'modelo': 'XGBoost',
        'train': {
            'accuracy': accuracy_score(y_train, y_train_pred),
            'precision': precision_score(y_train, y_train_pred, zero_division=0),
            'recall': recall_score(y_train, y_train_pred, zero_division=0),
            'f1': f1_score(y_train, y_train_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_train, y_train_proba) if len(np.unique(y_train)) > 1 else 0
        },
        'val': {
            'accuracy': accuracy_score(y_val, y_val_pred),
            'precision': precision_score(y_val, y_val_pred, zero_division=0),
            'recall': recall_score(y_val, y_val_pred, zero_division=0),
            'f1': f1_score(y_val, y_val_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_val, y_val_proba) if len(np.unique(y_val)) > 1 else 0
        },
        'test': {
            'accuracy': accuracy_score(y_test, y_test_pred),
            'precision': precision_score(y_test, y_test_pred, zero_division=0),
            'recall': recall_score(y_test, y_test_pred, zero_division=0),
            'f1': f1_score(y_test, y_test_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_test, y_test_proba) if len(np.unique(y_test)) > 1 else 0
        },
        'feature_importance': dict(zip(X_train.columns, modelo.feature_importances_))
    }
    
    print("\n📊 Métricas:")
    print(f"   Train - Accuracy: {metricas['train']['accuracy']:.3f}, F1: {metricas['train']['f1']:.3f}, AUC: {metricas['train']['roc_auc']:.3f}")
    print(f"   Val   - Accuracy: {metricas['val']['accuracy']:.3f}, F1: {metricas['val']['f1']:.3f}, AUC: {metricas['val']['roc_auc']:.3f}")
    print(f"   Test  - Accuracy: {metricas['test']['accuracy']:.3f}, F1: {metricas['test']['f1']:.3f}, AUC: {metricas['test']['roc_auc']:.3f}")
    
    # Top 10 features más importantes
    if 'feature_importance' in metricas:
        top_features = sorted(metricas['feature_importance'].items(), key=lambda x: x[1], reverse=True)[:10]
        print("\n🔝 Top 10 Features más importantes:")
        for i, (feature, importance) in enumerate(top_features, 1):
            print(f"   {i:2d}. {feature:20s}: {importance:.4f}")
    
    return modelo, metricas


def comparar_modelos(resultados):
    """
    Compara los resultados de todos los modelos entrenados.
    
    Args:
        resultados: Lista de diccionarios con métricas de cada modelo
    """
    print("\n" + "="*60)
    print("COMPARACIÓN DE MODELOS")
    print("="*60)
    
    # Crear DataFrame comparativo
    comparacion = []
    for res in resultados:
        if res is None:
            continue
        comparacion.append({
            'Modelo': res['modelo'],
            'Test Accuracy': res['test']['accuracy'],
            'Test Precision': res['test']['precision'],
            'Test Recall': res['test']['recall'],
            'Test F1': res['test']['f1'],
            'Test AUC-ROC': res['test']['roc_auc']
        })
    
    if not comparacion:
        print("⚠️  No hay modelos para comparar")
        return None
    
    df_comparacion = pd.DataFrame(comparacion)
    df_comparacion = df_comparacion.sort_values('Test AUC-ROC', ascending=False)
    
    print("\n📊 Comparación de modelos (ordenados por AUC-ROC):")
    print(df_comparacion.to_string(index=False))
    
    # Mejor modelo
    mejor = df_comparacion.iloc[0]
    print(f"\n🏆 MEJOR MODELO: {mejor['Modelo']}")
    print(f"   - AUC-ROC: {mejor['Test AUC-ROC']:.3f}")
    print(f"   - F1-Score: {mejor['Test F1']:.3f}")
    print(f"   - Accuracy: {mejor['Test Accuracy']:.3f}")
    
    return df_comparacion


def guardar_modelos(modelos, metricas, imputer, scaler, encoders, comparacion):
    """
    Guarda los modelos entrenados y sus métricas.
    
    Args:
        modelos: Diccionario con modelos entrenados
        metricas: Diccionario con métricas de cada modelo
        imputer: Imputer usado
        scaler: Scaler usado
        encoders: Encoders usados
        comparacion: DataFrame con comparación de modelos
    """
    print("\n" + "="*60)
    print("GUARDANDO MODELOS Y MÉTRICAS")
    print("="*60)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Guardar cada modelo
    for nombre, modelo in modelos.items():
        if modelo is None:
            continue
        
        archivo_modelo = MODELOS_DIR / f"modelo_{nombre.lower().replace(' ', '_')}_{timestamp}.pkl"
        with open(archivo_modelo, 'wb') as f:
            pickle.dump(modelo, f)
        print(f"✅ Modelo guardado: {archivo_modelo.name}")
    
    # Guardar preprocesadores
    preprocesadores = {
        'imputer': imputer,
        'scaler': scaler,
        'encoders': encoders
    }
    
    archivo_prepro = MODELOS_DIR / f"preprocesadores_{timestamp}.pkl"
    with open(archivo_prepro, 'wb') as f:
        pickle.dump(preprocesadores, f)
    print(f"✅ Preprocesadores guardados: {archivo_prepro.name}")
    
    # Guardar métricas
    archivo_metricas = MODELOS_DIR / f"metricas_{timestamp}.json"
    with open(archivo_metricas, 'w', encoding='utf-8') as f:
        json.dump(metricas, f, indent=2, ensure_ascii=False, default=str)
    print(f"✅ Métricas guardadas: {archivo_metricas.name}")
    
    # Guardar comparación
    if comparacion is not None:
        archivo_comparacion = MODELOS_DIR / f"comparacion_modelos_{timestamp}.csv"
        comparacion.to_csv(archivo_comparacion, index=False)
        print(f"✅ Comparación guardada: {archivo_comparacion.name}")
    
    print(f"\n📁 Todos los archivos guardados en: {MODELOS_DIR}")


def main():
    """
    Función principal que ejecuta todo el pipeline de entrenamiento.
    """
    print("="*60)
    print("ENTRENAMIENTO DE MODELOS DE MACHINE LEARNING")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. Cargar datos
        df = cargar_datos()
        
        # 2. Preparar features y targets (excluyendo features que causan data leakage)
        X, y_clasificacion, y_regresion, encoders = preparar_features(df, excluir_leakage=True)
        
        # Usar clasificación como target principal
        if y_clasificacion is None:
            print("\n❌ ERROR: No se encontró target de clasificación")
            return
        
        # 3. Dividir datos
        X_train, X_val, X_test, y_train, y_val, y_test = dividir_datos(
            X, y_clasificacion, test_size=0.15, val_size=0.15
        )
        
        # 4. Imputar valores faltantes
        X_train, X_val, X_test, imputer = imputar_valores_faltantes(X_train, X_val, X_test)
        
        # 5. Escalar features
        X_train, X_val, X_test, scaler = escalar_features(X_train, X_val, X_test)
        
        # 6. Balancear clases (SMOTE + class weights)
        X_train_balanced, y_train_balanced, class_weights = balancear_clases(X_train, y_train, usar_smote=True)
        
        # Calcular scale_pos_weight para XGBoost (ratio clase negativa/positiva)
        clases, conteos = np.unique(y_train_balanced, return_counts=True)
        if len(clases) == 2:
            scale_pos_weight = conteos[0] / conteos[1]  # negativa / positiva
        else:
            scale_pos_weight = None
        
        # 7. Entrenar modelos
        modelos = {}
        metricas = {}
        resultados = []
        
        # Logistic Regression
        modelo_lr, metricas_lr = entrenar_logistic_regression(
            X_train_balanced, y_train_balanced, X_val, y_val, X_test, y_test,
            class_weight=class_weights
        )
        if modelo_lr is not None:
            modelos['Logistic Regression'] = modelo_lr
            metricas['Logistic Regression'] = metricas_lr
            resultados.append(metricas_lr)
        
        # Random Forest
        modelo_rf, metricas_rf = entrenar_random_forest(
            X_train_balanced, y_train_balanced, X_val, y_val, X_test, y_test,
            class_weight=class_weights
        )
        if modelo_rf is not None:
            modelos['Random Forest'] = modelo_rf
            metricas['Random Forest'] = metricas_rf
            resultados.append(metricas_rf)
        
        # XGBoost
        modelo_xgb, metricas_xgb = entrenar_xgboost(
            X_train_balanced, y_train_balanced, X_val, y_val, X_test, y_test,
            scale_pos_weight=scale_pos_weight
        )
        if modelo_xgb is not None:
            modelos['XGBoost'] = modelo_xgb
            metricas['XGBoost'] = metricas_xgb
            resultados.append(metricas_xgb)
        
        # 7. Comparar modelos
        comparacion = comparar_modelos(resultados)
        
        # 8. Guardar modelos y métricas
        guardar_modelos(modelos, metricas, imputer, scaler, encoders, comparacion)
        
        print("\n" + "="*60)
        print("✅ ENTRENAMIENTO COMPLETADO EXITOSAMENTE")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()

