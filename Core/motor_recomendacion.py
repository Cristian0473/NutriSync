# motor_recomendacion.py
# Motor de recomendación nutricional personalizado para diabetes tipo 2

import math
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
import os
import sys
from pathlib import Path
import pickle

# Verificar que las dependencias ML estén disponibles
try:
    import numpy as np
    import pandas as pd
    ML_AVAILABLE = True
except ImportError as e:
    print(f"[WARN]  Advertencia: Dependencias ML no disponibles: {e}")
    ML_AVAILABLE = False
    np = None
    pd = None

from Core.bd_conexion import fetch_one, fetch_all, execute

@dataclass
class PerfilPaciente:
    """Perfil completo del paciente para recomendaciones"""
    paciente_id: int
    edad: int
    sexo: str
    peso: float
    talla: float
    imc: float
    actividad: str
    hba1c: Optional[float]
    glucosa_ayunas: Optional[float]
    ldl: Optional[float]
    trigliceridos: Optional[float]
    pa_sis: Optional[int]
    pa_dia: Optional[int]
    alergias: List[str]
    medicamentos: List[str]
    preferencias_excluir: List[str]
    preferencias_incluir: List[str]

@dataclass
class MetaNutricional:
    """Metas nutricionales calculadas"""
    calorias_diarias: int
    carbohidratos_g: int
    carbohidratos_porcentaje: int
    proteinas_g: int
    proteinas_porcentaje: int
    grasas_g: int
    grasas_porcentaje: int
    fibra_g: int
    sodio_mg: int
    carbohidratos_por_comida: Dict[str, int]
    porciones_por_grupo: Optional[Dict[str, float]] = None  # Porciones de intercambio por grupo

class MotorRecomendacion:
    """Motor principal para generar recomendaciones nutricionales"""
    
    def __init__(self):
        # Parámetros específicos para diabetes tipo 2
        self.PARAMETROS_DIABETES = {
            'carbohidratos_min': 45,  # % mínimo
            'carbohidratos_max': 60,  # % máximo
            'proteinas_min': 15,     # % mínimo
            'proteinas_max': 20,     # % máximo
            'grasas_min': 25,        # % mínimo
            'grasas_max': 35,        # % máximo
            'fibra_min': 25,         # g/día mínimo
            'sodio_max': 2300,       # mg/día máximo
            'ig_max': 70,            # Índice glucémico máximo recomendado
        }
        
        # Distribución de carbohidratos por comida
        self.DISTRIBUCION_CHO = {
            'des': 0.20,    # desayuno
            'mm': 0.10,     # media mañana
            'alm': 0.35,    # almuerzo
            'mt': 0.10,     # media tarde
            'cena': 0.25    # cena
        }
        
        # Modelo ML original (cargado bajo demanda)
        self._modelo_ml = None
        self._preprocesadores_ml = None
        self._usar_ml = True
        self._ultima_probabilidad_ajustada = None  # Flag para habilitar/deshabilitar ML
        
        # Nuevos modelos ML (cargados bajo demanda)
        self._modelo_respuesta_glucemica = None
        self._modelo_seleccion_alimentos = None
        self._modelo_optimizacion_combinaciones = None
        self._scaler_respuesta_glucemica = None
        self._scaler_seleccion_alimentos = None
        self._scaler_combinaciones = None

    def _cargar_modelo_ml(self):
        """Carga el modelo XGBoost y preprocesadores más recientes"""
        if self._modelo_ml is not None and self._preprocesadores_ml is not None:
            return  # Ya está cargado
        
        # Verificar que las dependencias ML estén disponibles
        if not ML_AVAILABLE:
            print("[WARN]  Dependencias ML (numpy, pandas) no disponibles, usando sistema rule-based")
            self._usar_ml = False
            return
        
        try:
            # Intentar importar xgboost
            try:
                import xgboost
            except ImportError:
                print("[WARN]  XGBoost no está instalado en este entorno Python")
                print(f"   Python usado: {sys.executable}")
                print("   Instalar con: pip install xgboost")
                self._usar_ml = False
                return
            # Buscar el directorio de modelos (desde la raíz del proyecto)
            base_dir = Path(__file__).parent.parent  # Subir un nivel desde Core/ a la raíz
            modelos_dir = base_dir / "ApartadoInteligente" / "Entrenamiento" / "ModeloEntrenamiento"
            
            if not modelos_dir.exists():
                print("[WARN]  Directorio de modelos no encontrado, usando sistema rule-based")
                self._usar_ml = False
                return
            
            # Buscar el modelo más reciente
            # Buscar primero modelos simplificados (prioridad)
            modelos_simplificados = list(modelos_dir.glob("modelo_xgboost_simplificado_*.pkl"))
            if modelos_simplificados:
                # Ordenar por fecha (más reciente primero)
                modelos_simplificados.sort(reverse=True)
                modelo_path = modelos_simplificados[0]
                print(f"[OK] Usando modelo simplificado: {modelo_path.name}")
            else:
                # Si no hay simplificados, buscar modelos normales
                modelos_xgboost = list(modelos_dir.glob("modelo_xgboost_*.pkl"))
                if not modelos_xgboost:
                    print("[WARN]  No se encontraron modelos XGBoost, usando sistema rule-based")
                    self._usar_ml = False
                    return
                # Ordenar por fecha (más reciente primero)
                modelos_xgboost.sort(reverse=True)
                modelo_path = modelos_xgboost[0]
                print(f"[OK] Usando modelo estándar: {modelo_path.name}")
            
            # Buscar preprocesadores correspondientes (mismo timestamp)
            # El timestamp tiene formato: YYYYMMDD_HHMMSS (ej: 20251107_185913)
            # Extraer las últimas dos partes del nombre (fecha y hora)
            partes = modelo_path.stem.split('_')
            if len(partes) >= 3:
                # Tomar las últimas dos partes: fecha y hora
                timestamp = '_'.join(partes[-2:])
            else:
                # Fallback: tomar solo la última parte
                timestamp = partes[-1]
            
            # Determinar si es modelo simplificado o estándar
            es_simplificado = 'simplificado' in modelo_path.stem
            if es_simplificado:
                prepro_path = modelos_dir / f"preprocesadores_simplificado_{timestamp}.pkl"
            else:
                prepro_path = modelos_dir / f"preprocesadores_{timestamp}.pkl"
            
            # Debug: mostrar qué está buscando
            print(f"[DEBUG] Buscando preprocesadores: {prepro_path.name}")
            print(f"[DEBUG] Ruta completa: {prepro_path}")
            
            if not prepro_path.exists():
                print(f"[WARN]  Preprocesadores no encontrados para {timestamp}, usando sistema rule-based")
                self._usar_ml = False
                return
            
            # Cargar modelo y preprocesadores
            with open(modelo_path, 'rb') as f:
                self._modelo_ml = pickle.load(f)
            
            with open(prepro_path, 'rb') as f:
                self._preprocesadores_ml = pickle.load(f)
            
            print(f"[OK] Modelo ML cargado: {modelo_path.name}")
            
        except Exception as e:
            print(f"[WARN]  Error al cargar modelo ML: {e}, usando sistema rule-based")
            self._usar_ml = False
            self._modelo_ml = None
            self._preprocesadores_ml = None
    
    def _cargar_modelo_respuesta_glucemica(self):
        """Carga el Modelo 1: Predicción de Respuesta Glucémica"""
        if self._modelo_respuesta_glucemica is not None:
            # Modelo ya cargado, no imprimir para evitar spam en logs
            return
        
        if not ML_AVAILABLE:
            print("[WARN]  ML_AVAILABLE = False, no se puede cargar Modelo 1")
            return
        
        print("[DEBUG] Intentando cargar Modelo 1: Respuesta Glucémica...")
        
        try:
            # Usar ruta relativa desde la raíz del proyecto
            base_dir = Path(__file__).parent.parent  # Subir un nivel desde Core/ a la raíz
            modelo_path = base_dir / "ApartadoInteligente" / "ModeloML" / "modelo_respuesta_glucemica.pkl"
            scaler_path = base_dir / "ApartadoInteligente" / "ModeloML" / "scaler_respuesta_glucemica.pkl"
            
            if not modelo_path.exists() or not scaler_path.exists():
                print(f"[WARN]  Modelo de respuesta glucémica no encontrado en: {modelo_path}")
                return
            
            with open(modelo_path, 'rb') as f:
                self._modelo_respuesta_glucemica = pickle.load(f)
            
            with open(scaler_path, 'rb') as f:
                self._scaler_respuesta_glucemica = pickle.load(f)
            
            print("[OK] Modelo de respuesta glucémica cargado")
        except Exception as e:
            print(f"[WARN]  Error al cargar modelo de respuesta glucémica: {e}")
    
    def _cargar_modelo_seleccion_alimentos(self):
        """Carga el Modelo 2: Selección Personalizada de Alimentos"""
        if self._modelo_seleccion_alimentos is not None:
            # Modelo ya cargado, no imprimir para evitar spam en logs
            return
        
        if not ML_AVAILABLE:
            print("[WARN]  ML_AVAILABLE = False, no se puede cargar Modelo 2")
            return
        
        print("[DEBUG] Intentando cargar Modelo 2: Selección de Alimentos...")
        
        try:
            # Usar ruta relativa desde la raíz del proyecto
            base_dir = Path(__file__).parent.parent  # Subir un nivel desde Core/ a la raíz
            modelo_path = base_dir / "ApartadoInteligente" / "ModeloML" / "modelo_seleccion_alimentos.pkl"
            
            if not modelo_path.exists():
                print(f"[WARN]  Modelo de selección de alimentos no encontrado en: {modelo_path}")
                return
            
            with open(modelo_path, 'rb') as f:
                modelo_completo = pickle.load(f)
            
            # El scaler está dentro del modelo_completo
            self._modelo_seleccion_alimentos = modelo_completo
            self._scaler_seleccion_alimentos = modelo_completo.get('scaler')
            
            if self._scaler_seleccion_alimentos is None:
                print("[WARN]  Scaler no encontrado dentro del modelo de selección de alimentos")
                return
            
            print("[OK] Modelo de selección de alimentos cargado")
        except Exception as e:
            print(f"[WARN]  Error al cargar modelo de selección de alimentos: {e}")
            import traceback
            traceback.print_exc()
    
    def _cargar_modelo_optimizacion_combinaciones(self):
        """Carga el Modelo 3: Optimización de Combinaciones"""
        if self._modelo_optimizacion_combinaciones is not None:
            # Modelo ya cargado, no imprimir para evitar spam en logs
            return
        
        if not ML_AVAILABLE:
            print("[WARN]  ML_AVAILABLE = False, no se puede cargar Modelo 3")
            return
        
        print("[DEBUG] Intentando cargar Modelo 3: Optimización de Combinaciones...")
        
        try:
            # Usar ruta relativa desde la raíz del proyecto
            base_dir = Path(__file__).parent.parent  # Subir un nivel desde Core/ a la raíz
            modelo_path = base_dir / "ApartadoInteligente" / "ModeloML" / "modelo_optimizacion_combinaciones.pkl"
            
            if not modelo_path.exists():
                print(f"[WARN]  Modelo de optimización de combinaciones no encontrado en: {modelo_path}")
                return
            
            with open(modelo_path, 'rb') as f:
                modelo_completo = pickle.load(f)
            
            # El scaler está dentro del modelo_completo
            self._modelo_optimizacion_combinaciones = modelo_completo
            self._scaler_combinaciones = modelo_completo.get('scaler')
            
            if self._scaler_combinaciones is None:
                print("[WARN]  Scaler no encontrado dentro del modelo de optimización de combinaciones")
                return
            
            print("[OK] Modelo de optimización de combinaciones cargado")
        except Exception as e:
            print(f"[WARN]  Error al cargar modelo de optimización de combinaciones: {e}")
            import traceback
            traceback.print_exc()

    def _preparar_features_ml(self, perfil: PerfilPaciente, feature_names_esperadas: List[str] = None) -> pd.DataFrame:
        """
        Prepara las features del paciente para la predicción ML.
        Calcula variables derivadas y maneja valores faltantes.
        
        Args:
            perfil: Perfil del paciente
            feature_names_esperadas: Lista de nombres de features que el modelo espera (opcional)
        """
        # Features numéricas posibles (sin hba1c ni glucosa_ayunas por data leakage)
        # Nota: El modelo puede no usar todas estas features
        features_num_posibles = [
            'edad', 'peso', 'talla', 'imc', 'cc',
            'ldl', 'hdl', 'trigliceridos', 'colesterol_total',
            'pa_sis', 'pa_dia', 'insulina_ayunas',
            'no_hdl', 'homa_ir', 'tg_hdl_ratio', 'ldl_hdl_ratio', 'aip'
        ]
        
        # Si se proporcionan las features esperadas, usar solo esas
        if feature_names_esperadas:
            # Filtrar solo las features numéricas que el modelo espera
            features_num = [f for f in features_num_posibles if f in feature_names_esperadas]
        else:
            # Usar todas las features numéricas posibles
            features_num = features_num_posibles
        
        # Inicializar diccionario de features
        features = {}
        
        # Features básicas disponibles (solo si el modelo las espera)
        if not feature_names_esperadas or 'edad' in feature_names_esperadas:
            features['edad'] = perfil.edad
        if not feature_names_esperadas or 'peso' in feature_names_esperadas:
            features['peso'] = perfil.peso
        if not feature_names_esperadas or 'talla' in feature_names_esperadas:
            features['talla'] = perfil.talla
        if not feature_names_esperadas or 'imc' in feature_names_esperadas:
            features['imc'] = perfil.imc
        if not feature_names_esperadas or 'ldl' in feature_names_esperadas:
            features['ldl'] = perfil.ldl if perfil.ldl else np.nan
        if not feature_names_esperadas or 'pa_sis' in feature_names_esperadas:
            features['pa_sis'] = perfil.pa_sis if perfil.pa_sis else np.nan
        if not feature_names_esperadas or 'pa_dia' in feature_names_esperadas:
            features['pa_dia'] = perfil.pa_dia if perfil.pa_dia else np.nan
        
        # Features no disponibles en la BD (usar NaN, el imputer las manejará)
        # Solo agregar si el modelo las espera
        if not feature_names_esperadas or 'cc' in feature_names_esperadas:
            features['cc'] = np.nan  # Circunferencia de cintura
        if not feature_names_esperadas or 'hdl' in feature_names_esperadas:
            features['hdl'] = np.nan  # Colesterol HDL
        if not feature_names_esperadas or 'trigliceridos' in feature_names_esperadas:
            features['trigliceridos'] = perfil.trigliceridos if perfil.trigliceridos is not None else np.nan
        if not feature_names_esperadas or 'colesterol_total' in feature_names_esperadas:
            features['colesterol_total'] = np.nan  # Colesterol total
        if not feature_names_esperadas or 'insulina_ayunas' in feature_names_esperadas:
            features['insulina_ayunas'] = np.nan  # Insulina en ayunas
        
        # Calcular variables derivadas si tenemos los datos necesarios (solo si el modelo las espera)
        # No-HDL = Colesterol total - HDL
        if (not feature_names_esperadas or 'no_hdl' in feature_names_esperadas):
            if 'colesterol_total' in features and 'hdl' in features:
                if not np.isnan(features['colesterol_total']) and not np.isnan(features['hdl']):
                    features['no_hdl'] = features['colesterol_total'] - features['hdl']
                else:
                    features['no_hdl'] = np.nan
            else:
                features['no_hdl'] = np.nan
        
        # HOMA-IR = (glucosa * insulina) / 405
        if (not feature_names_esperadas or 'homa_ir' in feature_names_esperadas):
            if 'insulina_ayunas' in features and perfil.glucosa_ayunas:
                if not np.isnan(features['insulina_ayunas']):
                    features['homa_ir'] = (perfil.glucosa_ayunas * features['insulina_ayunas']) / 405
                else:
                    features['homa_ir'] = np.nan
            else:
                features['homa_ir'] = np.nan
        
        # Ratios
        if (not feature_names_esperadas or 'tg_hdl_ratio' in feature_names_esperadas):
            if 'trigliceridos' in features and 'hdl' in features:
                if not np.isnan(features['trigliceridos']) and not np.isnan(features['hdl']):
                    features['tg_hdl_ratio'] = features['trigliceridos'] / features['hdl']
                else:
                    features['tg_hdl_ratio'] = np.nan
            else:
                features['tg_hdl_ratio'] = np.nan
        
        if (not feature_names_esperadas or 'ldl_hdl_ratio' in feature_names_esperadas):
            if 'ldl' in features and 'hdl' in features:
                if not np.isnan(features['ldl']) and not np.isnan(features['hdl']):
                    features['ldl_hdl_ratio'] = features['ldl'] / features['hdl']
                else:
                    features['ldl_hdl_ratio'] = np.nan
            else:
                features['ldl_hdl_ratio'] = np.nan
        
        # AIP = log10(TG/HDL)
        if (not feature_names_esperadas or 'aip' in feature_names_esperadas):
            if 'tg_hdl_ratio' in features:
                if not np.isnan(features['tg_hdl_ratio']) and features['tg_hdl_ratio'] > 0:
                    features['aip'] = np.log10(features['tg_hdl_ratio'])
                else:
                    features['aip'] = np.nan
            else:
                features['aip'] = np.nan
        
        # Crear DataFrame con las features en el orden correcto
        # Orden: features numéricas primero, luego categóricas codificadas
        orden_columnas = features_num.copy()
        
        # Codificar variables categóricas (solo si el modelo las espera)
        if self._preprocesadores_ml and 'encoders' in self._preprocesadores_ml:
            encoders = self._preprocesadores_ml['encoders']
            
            # Sexo (solo si el modelo lo espera)
            if 'sexo' in encoders and (not feature_names_esperadas or 'sexo_encoded' in feature_names_esperadas):
                sexo_val = perfil.sexo if perfil.sexo else 'M'
                try:
                    features['sexo_encoded'] = encoders['sexo'].transform([sexo_val])[0]
                except (ValueError, KeyError):
                    # Si el valor no está en el encoder, usar el primer valor
                    features['sexo_encoded'] = 0
                if 'sexo_encoded' not in orden_columnas:
                    orden_columnas.append('sexo_encoded')
            
            # Actividad (solo si el modelo lo espera)
            if 'actividad' in encoders and (not feature_names_esperadas or 'actividad_encoded' in feature_names_esperadas):
                actividad_val = perfil.actividad if perfil.actividad else 'moderada'
                try:
                    features['actividad_encoded'] = encoders['actividad'].transform([actividad_val])[0]
                except (ValueError, KeyError):
                    # Si el valor no está en el encoder, usar 'moderada'
                    features['actividad_encoded'] = 0
                if 'actividad_encoded' not in orden_columnas:
                    orden_columnas.append('actividad_encoded')
        
        # Crear DataFrame con el orden correcto de columnas
        df_features = pd.DataFrame([features], columns=orden_columnas)
        
        return df_features

    def predecir_control_glucemico_ml(self, perfil: PerfilPaciente) -> Optional[float]:
        """
        Predice el control glucémico usando el modelo ML.
        Retorna la probabilidad de mal control (0-1) o None si no se puede predecir.
        """
        print(f"[DEBUG] predecir_control_glucemico_ml() llamado")
        print(f"   _usar_ml: {self._usar_ml}")
        
        if not self._usar_ml:
            print("[WARN]  ML deshabilitado, retornando None")
            return None
        
        try:
            # Cargar modelo si no está cargado
            if self._modelo_ml is None:
                print("[DEBUG] Cargando modelo ML...")
                self._cargar_modelo_ml()
            
            if self._modelo_ml is None or self._preprocesadores_ml is None:
                print("[WARN]  Modelo ML no disponible después de intentar cargar")
                return None
            
            print(f"[OK] Modelo ML disponible, procediendo con predicción...")
            
            # Obtener los nombres de features que el modelo espera PRIMERO
            if not hasattr(self._modelo_ml, 'feature_names_in_'):
                print("[WARN]  El modelo no tiene feature_names_in_, no se puede validar features")
                return None
            
            feature_names_esperadas = list(self._modelo_ml.feature_names_in_)
            print(f"[DEBUG] Features que el modelo espera ({len(feature_names_esperadas)}): {feature_names_esperadas}")
            
            # Preparar features (pasando las features esperadas para que solo prepare las necesarias)
            df_features = self._preparar_features_ml(perfil, feature_names_esperadas)
            print(f"[DEBUG] Features que tenemos después de preparar ({len(df_features.columns)}): {list(df_features.columns)}")
            
            # Verificar que todas las features esperadas estén presentes ANTES de preprocesar
            features_faltantes = set(feature_names_esperadas) - set(df_features.columns)
            if features_faltantes:
                print(f"[WARN]  Features faltantes: {features_faltantes}")
                # Agregar las features faltantes con valores NaN
                for feat in features_faltantes:
                    df_features[feat] = np.nan
            
            # Reordenar el DataFrame ANTES de preprocesar para que coincida con el orden esperado
            df_features = df_features[feature_names_esperadas]
            print(f"[OK] DataFrame reordenado con {len(df_features.columns)} features en el orden correcto")
            
            # Aplicar preprocesadores
            imputer = self._preprocesadores_ml.get('imputer')
            scaler = self._preprocesadores_ml.get('scaler')
            
            if imputer is None or scaler is None:
                return None
            
            # Imputar valores faltantes
            df_imputed = pd.DataFrame(
                imputer.transform(df_features),
                columns=df_features.columns,
                index=df_features.index
            )
            
            # Escalar features
            df_scaled = pd.DataFrame(
                scaler.transform(df_imputed),
                columns=df_imputed.columns,
                index=df_imputed.index
            )
            
            # Predecir probabilidad de mal control (ahora con las features en el orden correcto)
            probabilidad = self._modelo_ml.predict_proba(df_scaled)[0][1]
            
            print(f"[OK] Predicción ML completada: probabilidad_mal_control = {probabilidad:.4f}")
            
            return float(probabilidad)
            
        except Exception as e:
            print(f"[WARN]  Error al predecir con ML: {e}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            return None
    
    def predecir_respuesta_glucemica(self, perfil: PerfilPaciente, alimento: Dict, contexto: Dict = None) -> Optional[Dict]:
        """
        Modelo 1: Predice la respuesta glucémica a un alimento específico
        
        Args:
            perfil: Perfil del paciente
            alimento: Diccionario con información del alimento (kcal, cho, pro, fat, fibra)
            contexto: Diccionario con contexto (tiempo_comida, hora, glucosa_baseline)
        
        Returns:
            Dict con 'glucose_increment', 'glucose_peak', 'time_to_peak' o None si no está disponible
        """
        if not ML_AVAILABLE:
            return None
        
        try:
            self._cargar_modelo_respuesta_glucemica()
            
            if self._modelo_respuesta_glucemica is None or self._scaler_respuesta_glucemica is None:
                return None
            
            modelos = self._modelo_respuesta_glucemica.get('modelos', {})
            feature_columns = self._modelo_respuesta_glucemica.get('feature_columns', [])
            
            if not modelos or not feature_columns:
                return None
            
            # Preparar features
            features = {}
            
            # Features del paciente
            features['age'] = perfil.edad
            features['gender'] = 1 if perfil.sexo == 'F' else 0
            features['bmi'] = perfil.imc
            features['weight'] = perfil.peso
            features['height'] = perfil.talla
            features['a1c'] = perfil.hba1c if perfil.hba1c else np.nan
            features['fasting_glucose'] = perfil.glucosa_ayunas if perfil.glucosa_ayunas else np.nan
            features['homa_ir'] = np.nan  # Se calcularía si tuviéramos insulina
            features['triglycerides'] = perfil.trigliceridos if perfil.trigliceridos else np.nan
            features['tg_hdl_ratio'] = np.nan  # Se calcularía si tuviéramos HDL
            
            # Features del alimento
            features['calories'] = alimento.get('kcal', 0) or 0
            features['carbs'] = alimento.get('cho', 0) or 0
            features['protein'] = alimento.get('pro', 0) or 0
            features['fat'] = alimento.get('fat', 0) or 0
            features['fiber'] = alimento.get('fibra', 0) or 0
            
            # Features derivadas
            if features['calories'] > 0:
                features['carbs_per_100cal'] = (features['carbs'] * 4 / features['calories']) * 100
                features['protein_per_100cal'] = (features['protein'] * 4 / features['calories']) * 100
                features['fat_per_100cal'] = (features['fat'] * 9 / features['calories']) * 100
                features['fiber_per_100cal'] = (features['fiber'] / features['calories']) * 100
            else:
                features['carbs_per_100cal'] = 0
                features['protein_per_100cal'] = 0
                features['fat_per_100cal'] = 0
                features['fiber_per_100cal'] = 0
            
            # Features de contexto
            if contexto:
                hora = contexto.get('hora', 12)
                features['hora'] = hora
                features['glucose_baseline'] = contexto.get('glucose_baseline', features['fasting_glucose'] if not np.isnan(features['fasting_glucose']) else 100)
                features['tiempo_desde_ultima_comida'] = contexto.get('tiempo_desde_ultima_comida', 240)  # 4 horas por defecto
            else:
                features['hora'] = 12
                features['glucose_baseline'] = features['fasting_glucose'] if not np.isnan(features['fasting_glucose']) else 100
                features['tiempo_desde_ultima_comida'] = 240
            
            # Codificar tipo de comida
            tiempo_comida = contexto.get('tiempo_comida', 'alm') if contexto else 'alm'
            meal_type_map = {'des': 0, 'mm': 1, 'alm': 2, 'mt': 3, 'cena': 4}
            features['meal_type_encoded'] = meal_type_map.get(tiempo_comida, 2)
            
            # Día de la semana (usar lunes por defecto)
            features['dia_semana_encoded'] = 0
            
            # Crear DataFrame con todas las features necesarias
            df_features = pd.DataFrame([features])
            
            # Asegurar que todas las columnas esperadas estén presentes
            for col in feature_columns:
                if col not in df_features.columns:
                    df_features[col] = np.nan
            
            # Reordenar columnas
            df_features = df_features[feature_columns]
            
            # Escalar
            df_scaled = pd.DataFrame(
                self._scaler_respuesta_glucemica.transform(df_features),
                columns=feature_columns
            )
            
            # Predecir
            resultados = {}
            for target in ['glucose_increment', 'glucose_peak', 'time_to_peak']:
                if target in modelos:
                    pred = modelos[target].predict(df_scaled)[0]
                    resultados[target] = float(pred)
            
            # Calcular pico de glucosa si no está disponible
            if 'glucose_peak' not in resultados and 'glucose_increment' in resultados:
                resultados['glucose_peak'] = features['glucose_baseline'] + resultados['glucose_increment']
            
            return resultados
            
        except Exception as e:
            print(f"[WARN]  Error al predecir respuesta glucémica: {e}")
            return None
    
    def calcular_score_idoneidad_alimento(self, perfil: PerfilPaciente, alimento: Dict, necesidades: Dict) -> Optional[float]:
        """
        Modelo 2: Calcula el score de idoneidad (0-1) de un alimento para un paciente
        
        Args:
            perfil: Perfil del paciente
            alimento: Diccionario con información del alimento
            necesidades: Diccionario con necesidades nutricionales (calorias, carbs, etc.)
        
        Returns:
            Score de idoneidad (0-1) o None si no está disponible
        """
        if not ML_AVAILABLE:
            return None
        
        try:
            self._cargar_modelo_seleccion_alimentos()
            
            if self._modelo_seleccion_alimentos is None or self._scaler_seleccion_alimentos is None:
                return None
            
            modelo_completo = self._modelo_seleccion_alimentos
            modelo = modelo_completo.get('modelo')
            feature_columns = modelo_completo.get('feature_columns', [])
            
            if modelo is None or not feature_columns:
                return None
            
            # Preparar features
            features = {}
            
            # Features del paciente
            features['age'] = perfil.edad
            features['gender'] = 1 if perfil.sexo == 'F' else 0
            features['bmi'] = perfil.imc
            features['a1c'] = perfil.hba1c if perfil.hba1c else np.nan
            features['fasting_glucose'] = perfil.glucosa_ayunas if perfil.glucosa_ayunas else np.nan
            features['homa_ir'] = np.nan  # Se calcularía si tuviéramos insulina
            
            # Features del alimento
            features['calories'] = alimento.get('kcal', 0) or 0
            features['carbs'] = alimento.get('cho', 0) or 0
            features['protein'] = alimento.get('pro', 0) or 0
            features['fat'] = alimento.get('fat', 0) or 0
            features['sodium'] = alimento.get('sodio', 0) or 0
            features['sugar'] = 0  # No disponible en BD actual
            
            # Features derivadas
            if features['calories'] > 0:
                features['carbs_per_100cal'] = (features['carbs'] * 4 / features['calories']) * 100
                features['protein_per_100cal'] = (features['protein'] * 4 / features['calories']) * 100
                features['fat_per_100cal'] = (features['fat'] * 9 / features['calories']) * 100
            else:
                features['carbs_per_100cal'] = 0
                features['protein_per_100cal'] = 0
                features['fat_per_100cal'] = 0
            
            # Frecuencia de consumo (no disponible, usar 0)
            features['frecuencia_consumo'] = 0
            
            # Crear DataFrame
            df_features = pd.DataFrame([features])
            
            # Asegurar que todas las columnas esperadas estén presentes
            for col in feature_columns:
                if col not in df_features.columns:
                    df_features[col] = np.nan
            
            # Reordenar columnas
            df_features = df_features[feature_columns]
            
            # Escalar
            df_scaled = pd.DataFrame(
                self._scaler_seleccion_alimentos.transform(df_features),
                columns=feature_columns
            )
            
            # Predecir (el modelo devuelve probabilidad de clase 1 = adecuado)
            prob_adecuado = modelo.predict_proba(df_scaled)[0][1]
            
            return float(prob_adecuado)
            
        except Exception as e:
            print(f"[WARN]  Error al calcular score de idoneidad: {e}")
            return None
    
    def evaluar_combinacion_alimentos(self, perfil, combinacion: List[Dict], contexto: Dict = None) -> Optional[float]:
        """
        Modelo 3: Evalúa el score de calidad (0-1) de una combinación de alimentos
        
        Args:
            perfil: PerfilPaciente o diccionario con perfil del paciente
            combinacion: Lista de diccionarios con alimentos y cantidades
            contexto: Diccionario con contexto (tiempo_comida, hora)
        
        Returns:
            Score de calidad (0-1) o None si no está disponible
        """
        if not ML_AVAILABLE:
            return None
        
        try:
            self._cargar_modelo_optimizacion_combinaciones()
            
            if self._modelo_optimizacion_combinaciones is None or self._scaler_combinaciones is None:
                return None
            
            modelo_completo = self._modelo_optimizacion_combinaciones
            modelos_dict = modelo_completo.get('modelos', {})
            feature_columns = modelo_completo.get('feature_columns', [])
            
            # El Modelo 3 tiene un ensemble, usar el modelo 'ensemble'
            modelo = modelos_dict.get('ensemble') if isinstance(modelos_dict, dict) else None
            
            if modelo is None or not feature_columns:
                return None
            
            # Convertir perfil a diccionario si es objeto
            if isinstance(perfil, PerfilPaciente):
                perfil_dict = {
                    'edad': perfil.edad,
                    'sexo': perfil.sexo,
                    'imc': perfil.imc,
                    'hba1c': perfil.hba1c,
                    'glucosa_ayunas': perfil.glucosa_ayunas
                }
            elif isinstance(perfil, dict):
                perfil_dict = perfil
            else:
                # Perfil básico por defecto
                perfil_dict = {'edad': 50, 'sexo': 'M', 'imc': 25, 'hba1c': None, 'glucosa_ayunas': None}
            
            # Calcular totales de la combinación
            total_calories = sum(a.get('kcal', 0) or 0 for a in combinacion)
            total_carbs = sum(a.get('cho', 0) or 0 for a in combinacion)
            total_protein = sum(a.get('pro', 0) or 0 for a in combinacion)
            total_fat = sum(a.get('fat', 0) or 0 for a in combinacion)
            total_fiber = sum(a.get('fibra', 0) or 0 for a in combinacion)
            
            # Preparar features
            features = {}
            
            # Features del paciente
            features['age'] = perfil_dict.get('edad', 50)
            features['gender'] = 1 if perfil_dict.get('sexo', 'M') == 'F' else 0
            features['bmi'] = perfil_dict.get('imc', 25)
            features['a1c'] = perfil_dict.get('hba1c') if perfil_dict.get('hba1c') else np.nan
            features['fasting_glucose'] = perfil_dict.get('glucosa_ayunas') if perfil_dict.get('glucosa_ayunas') else np.nan
            features['homa_ir'] = np.nan
            
            # Features de la combinación
            features['total_calories'] = total_calories
            features['total_carbs'] = total_carbs
            features['total_protein'] = total_protein
            features['total_fat'] = total_fat
            features['total_fiber'] = total_fiber
            
            # Features derivadas
            if total_calories > 0:
                features['carbs_percent'] = (total_carbs * 4 / total_calories) * 100
                features['protein_percent'] = (total_protein * 4 / total_calories) * 100
                features['fat_percent'] = (total_fat * 9 / total_calories) * 100
            else:
                features['carbs_percent'] = 0
                features['protein_percent'] = 0
                features['fat_percent'] = 0
            
            # Diversidad (número de tipos de comida diferentes)
            grupos = set(a.get('grupo', '') for a in combinacion)
            features['tipos_comida'] = len(grupos)
            
            # Contexto
            if contexto:
                hora = contexto.get('hora', 12)
                features['hora_primera_comida'] = hora
            else:
                features['hora_primera_comida'] = 12
            
            # Duración de la combinación (asumir 0 si es una sola comida)
            features['duracion_combinacion'] = 0
            
            # Crear DataFrame
            df_features = pd.DataFrame([features])
            
            # Asegurar que todas las columnas esperadas estén presentes
            for col in feature_columns:
                if col not in df_features.columns:
                    df_features[col] = np.nan
            
            # Reordenar columnas
            df_features = df_features[feature_columns]
            
            # Escalar
            df_scaled = pd.DataFrame(
                self._scaler_combinaciones.transform(df_features),
                columns=feature_columns
            )
            
            # Predecir
            score = modelo.predict(df_scaled)[0]
            
            # Asegurar que esté en rango [0, 1]
            score = max(0.0, min(1.0, float(score)))
            
            return score
            
        except Exception as e:
            print(f"[WARN]  Error al evaluar combinación: {e}")
            return None

    def obtener_perfil_paciente(self, paciente_id: int) -> PerfilPaciente:
        """Obtiene el perfil completo del paciente desde la BD"""
        
        # Datos básicos del paciente
        paciente_data = fetch_one("""
            SELECT p.id, p.sexo, p.fecha_nac
            FROM paciente p
            WHERE p.id = %s
        """, (paciente_id,))
        
        if not paciente_data:
            raise ValueError(f"Paciente {paciente_id} no encontrado")
        
        # Última antropometría
        antropometria = fetch_one("""
            SELECT peso, talla, actividad, fecha
            FROM antropometria
            WHERE paciente_id = %s
            ORDER BY fecha DESC
            LIMIT 1
        """, (paciente_id,))
        
        # Últimos datos clínicos
        clinico = fetch_one("""
            SELECT hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia, fecha
            FROM clinico
            WHERE paciente_id = %s
            ORDER BY fecha DESC
            LIMIT 1
        """, (paciente_id,))
        
        # Alergias
        alergias = fetch_all("""
            SELECT i.nombre
            FROM paciente_alergia pa
            LEFT JOIN ingrediente i ON i.id = pa.ingrediente_id
            WHERE pa.paciente_id = %s
        """, (paciente_id,))
        
        # Medicamentos
        medicamentos = fetch_all("""
            SELECT nombre
            FROM paciente_medicamento
            WHERE paciente_id = %s AND activo = true
        """, (paciente_id,))
        
        # Preferencias
        preferencias_excluir = fetch_all("""
            SELECT i.nombre
            FROM paciente_preferencia pp
            LEFT JOIN ingrediente i ON i.id = pp.ingrediente_id
            WHERE pp.paciente_id = %s AND pp.tipo = 'excluir'
        """, (paciente_id,))
        
        preferencias_incluir = fetch_all("""
            SELECT i.nombre
            FROM paciente_preferencia pp
            LEFT JOIN ingrediente i ON i.id = pp.ingrediente_id
            WHERE pp.paciente_id = %s AND pp.tipo = 'incluir'
        """, (paciente_id,))
        
        # Calcular edad
        fecha_nac = paciente_data[2]
        edad = (date.today() - fecha_nac).days // 365 if fecha_nac else 30
        
        # Datos antropométricos
        peso = float(antropometria[0]) if antropometria and antropometria[0] else 70.0
        talla = float(antropometria[1]) if antropometria and antropometria[1] else 1.70
        actividad = antropometria[2] if antropometria and antropometria[2] else 'moderada'
        
        # Calcular IMC
        imc = peso / (talla ** 2)
        
        # Datos clínicos
        hba1c = float(clinico[0]) if clinico and clinico[0] else None
        glucosa_ayunas = float(clinico[1]) if clinico and clinico[1] else None
        ldl = float(clinico[2]) if clinico and clinico[2] else None
        trigliceridos = float(clinico[3]) if clinico and clinico[3] else None
        pa_sis = clinico[4] if clinico and clinico[4] else None
        pa_dia = clinico[5] if clinico and clinico[5] else None
        
        print(f"DEBUG: Perfil del paciente {paciente_id}:")
        print(f"  - Edad: {edad}, Sexo: {paciente_data[1]}")
        print(f"  - Peso: {peso}kg, Talla: {talla}m, IMC: {imc:.2f}")
        print(f"  - Actividad: {actividad}")
        print(f"  - HbA1c: {hba1c}, Glucosa: {glucosa_ayunas}")
        print(f"  - Alergias: {len(alergias) if alergias else 0}")
        print(f"  - Medicamentos: {len(medicamentos) if medicamentos else 0}")
        
        return PerfilPaciente(
            paciente_id=paciente_id,
            edad=edad,
            sexo=paciente_data[1],
            peso=peso,
            talla=talla,
            imc=imc,
            actividad=actividad,
            hba1c=hba1c,
            glucosa_ayunas=glucosa_ayunas,
            ldl=ldl,
            trigliceridos=trigliceridos,
            pa_sis=pa_sis,
            pa_dia=pa_dia,
            alergias=[a[0] for a in alergias if a[0]],
            medicamentos=[m[0] for m in medicamentos if m[0]],
            preferencias_excluir=[p[0] for p in preferencias_excluir if p[0]],
            preferencias_incluir=[p[0] for p in preferencias_incluir if p[0]]
        )

    def calcular_metabolismo_basal(self, perfil: PerfilPaciente) -> float:
        """Calcula el metabolismo basal usando la ecuación de Mifflin-St Jeor"""
        if perfil.sexo == 'M':
            mb = 10 * perfil.peso + 6.25 * (perfil.talla * 100) - 5 * perfil.edad + 5
        else:
            mb = 10 * perfil.peso + 6.25 * (perfil.talla * 100) - 5 * perfil.edad - 161
        
        return mb

    def calcular_factor_actividad(self, actividad: str) -> float:
        """Factor de actividad física"""
        factores = {
            'baja': 1.2,
            'moderada': 1.4,
            'alta': 1.6
        }
        return factores.get(actividad, 1.4)

    def calcular_factor_diabetes(self, perfil: PerfilPaciente) -> float:
        """Factor de ajuste específico para diabetes tipo 2
        
        Para pacientes con obesidad (IMC > 30) y diabetes, aplica déficit calórico
        para pérdida de peso (20-25% de reducción)"""
        factor = 1.0
        
        # Ajuste por IMC - PRIORITARIO para pérdida de peso en obesidad
        if perfil.imc >= 35:
            # Obesidad grado II/III: déficit del 25% (factor 0.75)
            factor = 0.75
            print(f"[AJUSTE] Obesidad grado II/III (IMC {perfil.imc:.2f}): aplicando déficit calórico del 25% para pérdida de peso")
        elif perfil.imc >= 30:
            # Obesidad grado I: déficit del 20% (factor 0.80)
            factor = 0.80
            print(f"[AJUSTE] Obesidad grado I (IMC {perfil.imc:.2f}): aplicando déficit calórico del 20% para pérdida de peso")
        elif perfil.imc < 18.5:
            factor = 1.1  # Aumentar calorías para bajo peso
        
        # Ajuste adicional por HbA1c (solo si no hay obesidad)
        if perfil.imc < 30 and perfil.hba1c:
            if perfil.hba1c > 8.0:
                factor -= 0.1  # Reducir calorías si HbA1c alto
            elif perfil.hba1c < 6.5:
                factor += 0.05  # Ligero aumento si HbA1c controlado
        
        # Ajuste adicional por glucosa en ayunas (solo si no hay obesidad)
        if perfil.imc < 30 and perfil.glucosa_ayunas:
            if perfil.glucosa_ayunas > 140:
                factor -= 0.05
        
        return max(0.75, min(1.2, factor))  # Limitar entre 0.75 y 1.2

    def calcular_metas_nutricionales(self, perfil: PerfilPaciente, configuracion: Dict = None, skip_ml_ajuste: bool = False) -> MetaNutricional:
        """Calcula las metas nutricionales personalizadas usando ML si está disponible
        
        Args:
            perfil: Perfil del paciente
            configuracion: Configuración personalizada (opcional)
            skip_ml_ajuste: Si es True, no aplica ajuste ML (la configuración ya viene ajustada)
        """
        
        # Calcular calorías base (usar configuración si está disponible, sino calcular)
        if configuracion and configuracion.get('kcal_objetivo'):
            calorias_diarias = configuracion.get('kcal_objetivo', 0)
        else:
            # Calcular calorías totales usando el método original
            mb = self.calcular_metabolismo_basal(perfil)
            factor_actividad = self.calcular_factor_actividad(perfil.actividad)
            factor_diabetes = self.calcular_factor_diabetes(perfil)
            calorias_diarias = int(mb * factor_actividad * factor_diabetes)
        
        # Obtener porcentajes base (de configuración o valores por defecto)
        if configuracion:
            carbohidratos_porcentaje_base = configuracion.get('cho_pct', self.PARAMETROS_DIABETES['carbohidratos_min'])
            proteinas_porcentaje_base = configuracion.get('pro_pct', self.PARAMETROS_DIABETES['proteinas_min'])
        else:
            carbohidratos_porcentaje_base = self.PARAMETROS_DIABETES['carbohidratos_min']
            proteinas_porcentaje_base = self.PARAMETROS_DIABETES['proteinas_min']
        
        # Aplicar ajuste ML solo si no se solicita saltarlo (cuando la configuración ya viene ajustada)
        if not skip_ml_ajuste:
            # Intentar usar predicción ML para ajustar metas (incluso con configuración)
            probabilidad_mal_control = self.predecir_control_glucemico_ml(perfil)
            
            # Guardar probabilidad ML cruda para incluirla en la respuesta
            self._ultima_probabilidad_ml = probabilidad_mal_control
        else:
            # Si se salta el ajuste ML, mantener valores de configuración tal cual
            probabilidad_mal_control = None
            self._ultima_probabilidad_ml = None
        
        if probabilidad_mal_control is not None and not skip_ml_ajuste:
            # COMBINAR predicción ML con reglas basadas en HbA1c/glucosa para casos obvios
            # Ajustar probabilidad si hay valores clínicos elevados que el ML no considera directamente
            probabilidad_ajustada = probabilidad_mal_control
            
            # Si HbA1c o glucosa están elevadas, aumentar la probabilidad
            if perfil.hba1c and perfil.hba1c >= 7.0:
                # HbA1c >= 7.0 indica mal control definitivo
                probabilidad_ajustada = max(probabilidad_ajustada, 0.7)
                print(f"[WARN]  HbA1c elevado ({perfil.hba1c}%), ajustando probabilidad a {probabilidad_ajustada:.2f}")
            elif perfil.hba1c and perfil.hba1c >= 6.5:
                # HbA1c 6.5-6.9: prediabetes/diabetes temprana
                probabilidad_ajustada = max(probabilidad_ajustada, 0.5)
                print(f"[WARN]  HbA1c en rango prediabetes ({perfil.hba1c}%), ajustando probabilidad a {probabilidad_ajustada:.2f}")
            
            if perfil.glucosa_ayunas and perfil.glucosa_ayunas >= 140:
                # Glucosa >= 140: diabetes no controlada
                probabilidad_ajustada = max(probabilidad_ajustada, 0.65)
                print(f"[WARN]  Glucosa elevada ({perfil.glucosa_ayunas} mg/dL), ajustando probabilidad a {probabilidad_ajustada:.2f}")
            elif perfil.glucosa_ayunas and perfil.glucosa_ayunas >= 126:
                # Glucosa 126-139: diabetes
                probabilidad_ajustada = max(probabilidad_ajustada, 0.45)
                print(f"[WARN]  Glucosa en rango diabetes ({perfil.glucosa_ayunas} mg/dL), ajustando probabilidad a {probabilidad_ajustada:.2f}")
            
            # Ajustes adicionales por IMC y control glucémico combinado
            # Si hay obesidad + diabetes mal controlada, reducir CHO más agresivamente
            # (tiene_obesidad y tiene_obesidad_severa ya están definidas arriba, pero las redefinimos aquí para el scope)
            tiene_obesidad_ml = perfil.imc >= 30
            tiene_obesidad_severa_ml = perfil.imc >= 35
            diabetes_mal_controlada = (perfil.hba1c and perfil.hba1c >= 6.9) or (perfil.glucosa_ayunas and perfil.glucosa_ayunas >= 140)
            
            # Usar probabilidad ajustada para decidir ajustes
            if probabilidad_ajustada > 0.6:
                # Control malo, ajustar más agresivamente
                if tiene_obesidad_severa_ml and diabetes_mal_controlada:
                    # Obesidad severa + diabetes mal controlada: CHO 25-30%
                    carbohidratos_porcentaje = max(25, min(30, carbohidratos_porcentaje_base - 10))
                    proteinas_porcentaje = min(proteinas_porcentaje_base + 2, 20)  # 18-20%
                    print(f"[ML] Obesidad severa + diabetes mal controlada: CHO muy restrictivo (25-30%)")
                elif tiene_obesidad_ml and diabetes_mal_controlada:
                    # Obesidad + diabetes mal controlada: CHO 30-35%
                    carbohidratos_porcentaje = max(30, min(35, carbohidratos_porcentaje_base - 8))
                    proteinas_porcentaje = min(proteinas_porcentaje_base + 3, 20)  # 18-20%
                    print(f"[ML] Obesidad + diabetes mal controlada: CHO restrictivo (30-35%)")
                else:
                    # Control malo sin obesidad severa
                    carbohidratos_porcentaje = max(
                        carbohidratos_porcentaje_base - 5,
                        35  # Mínimo 35% (reducido de 40%)
                    )
                    proteinas_porcentaje = min(
                        proteinas_porcentaje_base + 4,
                        22  # Máximo 22%
                    )
                
                # Reducir calorías ligeramente si probabilidad muy alta (solo si no hay obesidad, porque ya se aplicó déficit)
                if probabilidad_ajustada > 0.8 and not tiene_obesidad:
                    calorias_diarias = int(calorias_diarias * 0.95)
                
                print(f"[ML] Control glucémico MALO (prob_ml={probabilidad_mal_control:.2f}, prob_ajustada={probabilidad_ajustada:.2f})")
                print(f"   Ajustando: CHO {carbohidratos_porcentaje_base}% -> {carbohidratos_porcentaje}%, PRO {proteinas_porcentaje_base}% -> {proteinas_porcentaje}%")
            elif probabilidad_ajustada > 0.4:
                # Control moderado, ajuste ligero
                carbohidratos_porcentaje = max(carbohidratos_porcentaje_base - 2, 43)
                proteinas_porcentaje = min(proteinas_porcentaje_base + 2, 20)
                print(f"[ML] Control glucémico MODERADO (prob_ml={probabilidad_mal_control:.2f}, prob_ajustada={probabilidad_ajustada:.2f})")
                print(f"   Ajustando: CHO {carbohidratos_porcentaje_base}% -> {carbohidratos_porcentaje}%, PRO {proteinas_porcentaje_base}% -> {proteinas_porcentaje}%")
            else:
                # Control bueno, mantener valores base
                carbohidratos_porcentaje = carbohidratos_porcentaje_base
                proteinas_porcentaje = proteinas_porcentaje_base
                print(f"[ML] Control glucémico BUENO (prob_ml={probabilidad_mal_control:.2f}, prob_ajustada={probabilidad_ajustada:.2f})")
                print(f"   Manteniendo valores base: CHO {carbohidratos_porcentaje}%, PRO {proteinas_porcentaje}%")
            
            # Guardar probabilidad AJUSTADA para que otros métodos la usen
            self._ultima_probabilidad_ajustada = probabilidad_ajustada
        else:
            # Si ML no está disponible o se saltó el ajuste, usar valores de configuración directamente
            self._ultima_probabilidad_ajustada = None
            if skip_ml_ajuste:
                # Si se saltó el ajuste ML, usar valores de configuración tal cual (ya vienen ajustados)
                carbohidratos_porcentaje = carbohidratos_porcentaje_base
                proteinas_porcentaje = proteinas_porcentaje_base
                print(f"[ML] Saltando ajuste ML - usando configuración tal cual: CHO {carbohidratos_porcentaje}%, PRO {proteinas_porcentaje}%")
            else:
                # Fallback a sistema rule-based si ML no está disponible
                carbohidratos_porcentaje = carbohidratos_porcentaje_base
                proteinas_porcentaje = proteinas_porcentaje_base
                
                # Ajustar según control glucémico (método tradicional)
                if perfil.hba1c and perfil.hba1c > 7.0:
                    carbohidratos_porcentaje = self.PARAMETROS_DIABETES['carbohidratos_min']
                    proteinas_porcentaje = self.PARAMETROS_DIABETES['proteinas_max']
        
        # Ajustes adicionales por IMC y LDL para grasas y proteínas
        tiene_obesidad = perfil.imc >= 30
        tiene_obesidad_severa = perfil.imc >= 35
        ldl_alto = perfil.ldl and perfil.ldl > 100
        
        # Ajustar proteínas según IMC (limitar a 130g para obesidad - objetivo clínico adecuado)
        if tiene_obesidad:
            # Para obesidad, limitar proteínas a 130g máximo (suficiente para preservar masa magra sin exceso calórico)
            # Esto evita marcar días como "No cumple" cuando están en 120-130g, que es clínicamente adecuado
            proteinas_max_g = 130
            proteinas_porcentaje_max = min(proteinas_porcentaje, int((proteinas_max_g * 4 * 100) / calorias_diarias))
            if proteinas_porcentaje > proteinas_porcentaje_max:
                proteinas_porcentaje = proteinas_porcentaje_max
                print(f"[AJUSTE] Limitando proteínas a {proteinas_max_g}g para paciente con obesidad (objetivo clínico adecuado)")
        
        # Calcular grasas
        grasas_porcentaje = 100 - carbohidratos_porcentaje - proteinas_porcentaje
        
        # Calcular gramos
        carbohidratos_g = int((calorias_diarias * carbohidratos_porcentaje / 100) / 4)
        proteinas_g = int((calorias_diarias * proteinas_porcentaje / 100) / 4)
        grasas_g = int((calorias_diarias * grasas_porcentaje / 100) / 9)
        
        # Aplicar límite de proteínas DESPUÉS de calcular gramos (si hay obesidad)
        # Objetivo: 130g máximo para evitar marcar días como "No cumple" cuando están en 120-130g
        if tiene_obesidad and proteinas_g > 130:
            # Ajustar proteínas a máximo 130g y redistribuir calorías
            deficit_proteinas = proteinas_g - 130
            deficit_kcal = deficit_proteinas * 4
            proteinas_g = 130
            # Redistribuir a carbohidratos (mejor que grasas para diabéticos)
            carbohidratos_extra_g = int(deficit_kcal / 4)
            carbohidratos_g += carbohidratos_extra_g
            # Recalcular porcentajes
            proteinas_porcentaje = int((proteinas_g * 4 * 100) / calorias_diarias)
            carbohidratos_porcentaje = int((carbohidratos_g * 4 * 100) / calorias_diarias)
            grasas_porcentaje = 100 - carbohidratos_porcentaje - proteinas_porcentaje
            grasas_g = int((calorias_diarias * grasas_porcentaje / 100) / 9)
            print(f"[AJUSTE] Ajustando proteínas a {proteinas_g}g (objetivo clínico adecuado para obesidad)")
        
        # Limitar grasas según IMC y LDL (máximo 75-80g para mejor control lipídico)
        if tiene_obesidad or ldl_alto:
            # Limitar a 75g para obesidad severa, 80g para obesidad general (mejor control)
            grasas_max_g = 75 if tiene_obesidad_severa else 80
            if grasas_g > grasas_max_g:
                # Reducir grasas y redistribuir a proteínas (respetando límite máximo)
                deficit_grasas = grasas_g - grasas_max_g
                deficit_kcal = deficit_grasas * 9
                grasas_g = grasas_max_g
                
                # Redistribuir calorías a proteínas, pero respetando el límite máximo
                proteinas_max_actual = 130 if tiene_obesidad else 999
                proteinas_extra_g = min(int(deficit_kcal / 4), proteinas_max_actual - proteinas_g)
                proteinas_g += proteinas_extra_g
                
                # Si aún hay calorías sobrantes, reducir calorías totales ligeramente
                if proteinas_extra_g < deficit_kcal / 4:
                    calorias_diarias = int(calorias_diarias - ((deficit_kcal / 4 - proteinas_extra_g) * 4))
                
                # Recalcular porcentajes
                grasas_porcentaje = int((grasas_g * 9 * 100) / calorias_diarias)
                proteinas_porcentaje = int((proteinas_g * 4 * 100) / calorias_diarias)
                carbohidratos_porcentaje = 100 - grasas_porcentaje - proteinas_porcentaje
                carbohidratos_g = int((calorias_diarias * carbohidratos_porcentaje / 100) / 4)
                
                print(f"[AJUSTE] Limitando grasas a {grasas_max_g}g para paciente con {'obesidad' if tiene_obesidad else 'LDL alto'} (mejor control lipídico)")
        
        # Fibra (25-35g para diabetes)
        fibra_g = max(25, int(perfil.peso * 0.4))
        
        # Sodio (máximo 2300mg, ideal 1500mg)
        sodio_mg = 1500 if perfil.pa_sis and perfil.pa_sis > 140 else 2300
        
        # Distribución de carbohidratos por comida
        # Para pacientes con diabetes, limitar CHO en cenas (máximo 20-30g)
        distribucion_cho = dict(self.DISTRIBUCION_CHO)
        
        # Si es paciente con diabetes, ajustar distribución para limitar CHO en cenas
        tiene_diabetes = (perfil.hba1c and perfil.hba1c >= 6.5) or (perfil.glucosa_ayunas and perfil.glucosa_ayunas >= 126)
        
        if tiene_diabetes:
            # Limitar CHO en cena a máximo 20-30g (5-8% del total de CHO)
            cho_cena_max_g = 30 if tiene_obesidad else 35
            cho_cena_max_pct = cho_cena_max_g / carbohidratos_g if carbohidratos_g > 0 else 0.15
            
            if distribucion_cho['cena'] > cho_cena_max_pct:
                # Redistribuir el exceso a otras comidas (principalmente desayuno y almuerzo)
                exceso_cena = distribucion_cho['cena'] - cho_cena_max_pct
                distribucion_cho['cena'] = cho_cena_max_pct
                
                # Redistribuir: 60% al almuerzo, 40% al desayuno
                distribucion_cho['alm'] = min(0.40, distribucion_cho['alm'] + (exceso_cena * 0.6))
                distribucion_cho['des'] = min(0.25, distribucion_cho['des'] + (exceso_cena * 0.4))
                
                print(f"[INFO] Limitando CHO en cena a {cho_cena_max_g}g ({cho_cena_max_pct*100:.1f}%) para mejor control glucemico")
        
        carbohidratos_por_comida = {}
        for comida, porcentaje in distribucion_cho.items():
            carbohidratos_por_comida[comida] = int(carbohidratos_g * porcentaje)
        
        # Calcular porciones de intercambio por grupo
        porciones_por_grupo = self.calcular_porciones_por_grupo(perfil, {
            'calorias_diarias': calorias_diarias,
            'carbohidratos_g': carbohidratos_g,
            'proteinas_g': proteinas_g,
            'grasas_g': grasas_g,
            'carbohidratos_porcentaje': carbohidratos_porcentaje,
            'proteinas_porcentaje': proteinas_porcentaje,
            'grasas_porcentaje': grasas_porcentaje
        })
        
        return MetaNutricional(
            calorias_diarias=calorias_diarias,
            carbohidratos_g=carbohidratos_g,
            carbohidratos_porcentaje=carbohidratos_porcentaje,
            proteinas_g=proteinas_g,
            proteinas_porcentaje=proteinas_porcentaje,
            grasas_g=grasas_g,
            grasas_porcentaje=grasas_porcentaje,
            fibra_g=fibra_g,
            sodio_mg=sodio_mg,
            carbohidratos_por_comida=carbohidratos_por_comida,
            porciones_por_grupo=porciones_por_grupo
        )

    def calcular_porciones_por_grupo(self, perfil: PerfilPaciente, metas_dict: Dict) -> Dict[str, float]:
        """
        Calcula porciones de intercambio por grupo basándose en:
        - Calorías totales personalizadas
        - Distribución de macronutrientes
        - Control glucémico
        - IMC
        - Actividad física
        """
        # Obtener valores estándar de la guía
        estandares = fetch_all("""
            SELECT grupo, subgrupo, kcal_por_porcion, cho_por_porcion, pro_por_porcion, fat_por_porcion
            FROM guia_intercambio_estandar
            WHERE activo = TRUE
        """) or []
        
        # Crear diccionario de estándares
        estandares_dict = {}
        for est in estandares:
            grupo = est[0]
            subgrupo = est[1] or 'default'
            key = f"{grupo}_{subgrupo}" if subgrupo != 'default' else grupo
            estandares_dict[key] = {
                'kcal': float(est[2]),
                'cho': float(est[3]),
                'pro': float(est[4]),
                'fat': float(est[5])
            }
        
        # Obtener valores de metas
        calorias_diarias = metas_dict['calorias_diarias']
        carbohidratos_g = metas_dict['carbohidratos_g']
        proteinas_g = metas_dict['proteinas_g']
        grasas_g = metas_dict['grasas_g']
        
        # Calcular porciones base para cada grupo
        porciones = {}
        
        # GRUPO1_CEREALES: basado en CHO
        if 'GRUPO1_CEREALES' in estandares_dict:
            est = estandares_dict['GRUPO1_CEREALES']
            porciones_cereales = carbohidratos_g / est['cho'] if est['cho'] > 0 else 0
            # Ajustar por control glucémico
            probabilidad = getattr(self, '_ultima_probabilidad_ajustada', None)
            if probabilidad and probabilidad > 0.6:
                porciones_cereales *= 0.85  # Reducir 15% si mal control
            elif probabilidad and probabilidad > 0.4:
                porciones_cereales *= 0.92  # Reducir 8% si control moderado
            # Ajustar por actividad
            if perfil.actividad == 'baja':
                porciones_cereales *= 0.9
            elif perfil.actividad == 'alta':
                porciones_cereales *= 1.1
            porciones['GRUPO1_CEREALES'] = max(3.0, round(porciones_cereales, 1))
        
        # GRUPO2_VERDURAS: mínimo 3 porciones (importante para fibra)
        if 'GRUPO2_VERDURAS' in estandares_dict:
            porciones['GRUPO2_VERDURAS'] = 3.0
        
        # GRUPO3_FRUTAS: basado en CHO restante
        if 'GRUPO3_FRUTAS' in estandares_dict:
            est = estandares_dict['GRUPO3_FRUTAS']
            # Calcular CHO ya asignado a cereales
            cho_cereales = porciones.get('GRUPO1_CEREALES', 0) * estandares_dict.get('GRUPO1_CEREALES', {}).get('cho', 25)
            cho_restante = max(0, carbohidratos_g - cho_cereales)
            porciones_frutas = cho_restante / est['cho'] if est['cho'] > 0 else 0
            # Ajustar por control glucémico (menos restrictivo)
            probabilidad = getattr(self, '_ultima_probabilidad_ajustada', None)
            if probabilidad and probabilidad > 0.6:
                porciones_frutas *= 0.85  # Reducir solo 15% si mal control (antes era 0.8)
            porciones['GRUPO3_FRUTAS'] = max(2.0, min(4.5, round(porciones_frutas, 1)))  # Aumentar máximo a 4.5
        
        # GRUPO4_LACTEOS: basado en PRO y preferir bajos en grasa
        if 'GRUPO4_LACTEOS_bajos_grasa' in estandares_dict:
            est = estandares_dict['GRUPO4_LACTEOS_bajos_grasa']
            # Asignar 1-2 porciones de lácteos
            porciones_lacteos = 2.0
            # Ajustar por IMC
            if perfil.imc > 30:
                porciones_lacteos = 1.5  # Reducir si obesidad
            porciones['GRUPO4_LACTEOS'] = round(porciones_lacteos, 1)
        
        # GRUPO5_CARNES: basado en PRO, preferir bajas en grasa
        if 'GRUPO5_CARNES_bajas_grasa' in estandares_dict:
            est = estandares_dict['GRUPO5_CARNES_bajas_grasa']
            # Calcular PRO ya asignado a lácteos
            pro_lacteos = porciones.get('GRUPO4_LACTEOS', 0) * estandares_dict.get('GRUPO4_LACTEOS_bajos_grasa', {}).get('pro', 5)
            pro_restante = max(0, proteinas_g - pro_lacteos)
            porciones_carnes = pro_restante / est['pro'] if est['pro'] > 0 else 0
            # Ajustar por IMC (menos restrictivo)
            if perfil.imc > 30:
                porciones_carnes *= 0.95  # Reducir solo 5% si obesidad (antes era 0.9)
            porciones['GRUPO5_CARNES'] = max(2.5, min(4.5, round(porciones_carnes, 1)))  # Aumentar mínimo a 2.5 y máximo a 4.5
        
        # GRUPO6_AZUCARES: mínimo (solo para diabetes controlada)
        if 'GRUPO6_AZUCARES' in estandares_dict:
            probabilidad = getattr(self, '_ultima_probabilidad_ajustada', None)
            if probabilidad and probabilidad < 0.4:
                porciones['GRUPO6_AZUCARES'] = 2.0  # Solo si control bueno
            else:
                porciones['GRUPO6_AZUCARES'] = 0.0  # Evitar si mal control
        
        # GRUPO7_GRASAS: basado en FAT - AUMENTAR para cumplir metas
        if 'GRUPO7_GRASAS_aceites' in estandares_dict:
            est = estandares_dict['GRUPO7_GRASAS_aceites']
            # Calcular FAT ya asignado a otros grupos
            fat_cereales = porciones.get('GRUPO1_CEREALES', 0) * estandares_dict.get('GRUPO1_CEREALES', {}).get('fat', 1)
            fat_frutas = porciones.get('GRUPO3_FRUTAS', 0) * estandares_dict.get('GRUPO3_FRUTAS', {}).get('fat', 1)
            fat_lacteos = porciones.get('GRUPO4_LACTEOS', 0) * estandares_dict.get('GRUPO4_LACTEOS_bajos_grasa', {}).get('fat', 1)
            fat_carnes = porciones.get('GRUPO5_CARNES', 0) * estandares_dict.get('GRUPO5_CARNES_bajas_grasa', {}).get('fat', 1)
            fat_asignado = fat_cereales + fat_frutas + fat_lacteos + fat_carnes
            fat_restante = max(0, grasas_g - fat_asignado)
            porciones_grasas = fat_restante / est['fat'] if est['fat'] > 0 else 0
            # Aumentar porciones de grasas para asegurar cumplimiento (factor 2.0 para compensar mejor)
            # El factor más alto compensa la subestimación de grasas en otros grupos
            porciones_grasas *= 2.0  # Aumentado de 1.5 a 2.0
            # Ajustar por IMC (menos restrictivo)
            if perfil.imc > 30:
                porciones_grasas *= 0.97  # Reducir solo 3% si obesidad (antes era 0.95)
            porciones['GRUPO7_GRASAS'] = max(5.0, min(10.0, round(porciones_grasas, 1)))  # Aumentar mínimo a 5.0 y máximo a 10.0 para cumplir mejor las metas
        
        return porciones

    def _convertir_porciones_a_gramos(self, ingrediente: Dict, porciones: float) -> float:
        """
        Convierte porciones de intercambio a gramos del ingrediente.
        
        Si ingrediente.porciones_intercambio = 2.0 (2 porciones por 100g)
        y necesitamos 1 porcion -> 50g
        """
        porciones_intercambio = ingrediente.get('porciones_intercambio')
        
        if porciones_intercambio and porciones_intercambio > 0:
            # Si 100g = X porciones, entonces 1 porción = 100/X gramos
            gramos_por_porcion = 100.0 / porciones_intercambio
            return round(gramos_por_porcion * porciones, 1)
        else:
            # Fallback: calcular basándose en valores nutricionales
            return self._calcular_gramos_por_valores_nutricionales(ingrediente, porciones)
    
    def _calcular_gramos_por_valores_nutricionales(self, ingrediente: Dict, porciones: float) -> float:
        """
        Calcula gramos basándose en valores nutricionales del ingrediente
        comparados con los estándares de la guía.
        """
        grupo = ingrediente.get('grupo')
        subgrupo = ingrediente.get('subgrupo_intercambio')
        
        # Obtener estándar de la guía
        if subgrupo:
            estandar = fetch_one("""
                SELECT kcal_por_porcion, cho_por_porcion, pro_por_porcion, fat_por_porcion
                FROM guia_intercambio_estandar
                WHERE grupo = %s AND subgrupo = %s AND activo = TRUE
            """, (grupo, subgrupo))
        else:
            estandar = fetch_one("""
                SELECT kcal_por_porcion, cho_por_porcion, pro_por_porcion, fat_por_porcion
                FROM guia_intercambio_estandar
                WHERE grupo = %s AND subgrupo IS NULL AND activo = TRUE
            """, (grupo,))
        
        if not estandar:
            # Si no hay estándar, usar valores del ingrediente directamente
            return 100.0 * porciones  # Asumir 1 porción = 100g
        
        # Calcular basándose en el nutriente crítico del grupo
        kcal_estandar = float(estandar[0])
        cho_estandar = float(estandar[1])
        pro_estandar = float(estandar[2])
        fat_estandar = float(estandar[3])
        
        kcal_ing = float(ingrediente.get('kcal', 0))
        cho_ing = float(ingrediente.get('cho', 0))
        pro_ing = float(ingrediente.get('pro', 0))
        fat_ing = float(ingrediente.get('fat', 0))
        
        # Determinar nutriente crítico según grupo
        if grupo in ['GRUPO1_CEREALES', 'GRUPO2_VERDURAS', 'GRUPO3_FRUTAS', 'GRUPO6_AZUCARES']:
            # Nutriente crítico: CHO
            if cho_estandar > 0 and cho_ing > 0:
                gramos = (cho_estandar * porciones * 100.0) / cho_ing
            else:
                gramos = (kcal_estandar * porciones * 100.0) / kcal_ing if kcal_ing > 0 else 100.0 * porciones
        elif grupo == 'GRUPO5_CARNES':
            # Nutriente crítico: PRO
            if pro_estandar > 0 and pro_ing > 0:
                gramos = (pro_estandar * porciones * 100.0) / pro_ing
            else:
                gramos = (kcal_estandar * porciones * 100.0) / kcal_ing if kcal_ing > 0 else 100.0 * porciones
        elif grupo == 'GRUPO7_GRASAS':
            # Nutriente crítico: FAT
            if fat_estandar > 0 and fat_ing > 0:
                gramos = (fat_estandar * porciones * 100.0) / fat_ing
            else:
                gramos = (kcal_estandar * porciones * 100.0) / kcal_ing if kcal_ing > 0 else 100.0 * porciones
        else:
            # Por defecto, usar kcal
            gramos = (kcal_estandar * porciones * 100.0) / kcal_ing if kcal_ing > 0 else 100.0 * porciones
        
        return round(gramos, 1)

    def _calcular_porciones_para_comida(self, tiempo: str, metas: MetaNutricional, perfil: PerfilPaciente) -> Dict[str, float]:
        """
        Calcula porciones de intercambio por grupo para una comida específica.
        Se basa en las calorías objetivo de la comida y distribuye los grupos apropiados.
        """
        if not metas.porciones_por_grupo:
            return {}
        
        # Distribución de calorías por comida (suma = 100%)
        distribucion_calorias = {
            'des': 0.25,    # 25% de las calorías diarias
            'mm': 0.10,     # 10% de las calorías diarias
            'alm': 0.35,    # 35% de las calorías diarias
            'mt': 0.10,     # 10% de las calorías diarias
            'cena': 0.20    # 20% de las calorías diarias
        }
        
        # Calorías objetivo para esta comida
        calorias_comida = metas.calorias_diarias * distribucion_calorias.get(tiempo, 0.25)
        
        # Obtener estándares de la guía de intercambio
        estandares = {}
        for grupo in ['GRUPO1_CEREALES', 'GRUPO2_VERDURAS', 'GRUPO3_FRUTAS', 
                      'GRUPO4_LACTEOS', 'GRUPO5_CARNES', 'GRUPO7_GRASAS']:
            est = fetch_one("""
                SELECT kcal_por_porcion, cho_por_porcion, pro_por_porcion, fat_por_porcion
                FROM guia_intercambio_estandar
                WHERE grupo = %s AND subgrupo IS NULL AND activo = TRUE
                LIMIT 1
            """, (grupo,))
            if est:
                estandares[grupo] = {
                    'kcal': float(est[0]),
                    'cho': float(est[1]),
                    'pro': float(est[2]),
                    'fat': float(est[3])
                }
        
        # Distribución de grupos por comida (basada en composición nutricional típica)
        # Para desayuno: más ligero, cereales + lácteos + fruta
        # Para almuerzo/cena: más completo con todos los grupos
        distribucion_grupos_por_comida = {
            'des': {
                'GRUPO1_CEREALES': 0.30,  # 30% de las calorías del desayuno (reducido para agregar verduras)
                'GRUPO4_LACTEOS': 0.30,   # 30% de las calorías del desayuno
                'GRUPO3_FRUTAS': 0.20,    # 20% de las calorías del desayuno
                'GRUPO2_VERDURAS': 0.10,  # 10% de las calorías del desayuno (nuevo: verduras para fibra)
                'GRUPO7_GRASAS': 0.10     # 10% de las calorías del desayuno (reducido para agregar verduras)
            },
            'mm': {
                'GRUPO3_FRUTAS': 0.50,    # 50% de las calorías de la merienda (reducido para agregar verduras)
                'GRUPO4_LACTEOS': 0.30,   # 30% de las calorías de la merienda (reducido)
                'GRUPO2_VERDURAS': 0.20   # 20% de las calorías de la merienda (nuevo: verduras para fibra)
            },
            'alm': {
                'GRUPO1_CEREALES': 0.30,  # 30% de las calorías del almuerzo
                'GRUPO5_CARNES': 0.30,    # 30% de las calorías del almuerzo
                'GRUPO2_VERDURAS': 0.15,  # 15% de las calorías del almuerzo
                'GRUPO7_GRASAS': 0.25     # 25% de las calorías del almuerzo
            },
            'mt': {
                'GRUPO3_FRUTAS': 0.50,    # 50% de las calorías de la merienda (reducido para agregar verduras)
                'GRUPO4_LACTEOS': 0.30,   # 30% de las calorías de la merienda (reducido)
                'GRUPO2_VERDURAS': 0.20   # 20% de las calorías de la merienda (nuevo: verduras para fibra)
            },
            'cena': {
                'GRUPO5_CARNES': 0.35,    # 35% de las calorías de la cena (reducido de 40%)
                'GRUPO2_VERDURAS': 0.25,  # 25% de las calorías de la cena (reducido de 30%)
                'GRUPO1_CEREALES': 0.15,  # 15% de las calorías de la cena (reducido de 20%)
                'GRUPO7_GRASAS': 0.25     # 25% de las calorías de la cena (aumentado de 10%)
            }
        }
        
        # Asegurar que las distribuciones sumen 100%
        for tiempo_key, grupos_dist in distribucion_grupos_por_comida.items():
            total = sum(grupos_dist.values())
            if total > 0 and abs(total - 1.0) > 0.01:  # Si no suma 100%, normalizar
                for grupo_key in grupos_dist:
                    grupos_dist[grupo_key] = grupos_dist[grupo_key] / total
        
        distribucion = distribucion_grupos_por_comida.get(tiempo, {})
        porciones_comida = {}
        
        # Calcular porciones basándose en las calorías objetivo de cada grupo
        # El objetivo es cumplir con las calorías de la comida
        porciones_ideales = {}
        calorias_calculadas = 0
        
        for grupo, porcentaje_calorias in distribucion.items():
            if grupo not in estandares:
                continue
            
            # Calorías objetivo para este grupo en esta comida
            calorias_grupo = calorias_comida * porcentaje_calorias
            
            # Calcular cuántas porciones se necesitan para alcanzar esas calorías
            kcal_por_porcion = estandares[grupo]['kcal']
            if kcal_por_porcion > 0:
                porciones_ideales[grupo] = calorias_grupo / kcal_por_porcion
                calorias_calculadas += calorias_grupo
        
        # Ajustar proporcionalmente si las calorías calculadas no coinciden con las objetivo
        # Asegurar que siempre se alcance al menos el 100% de las calorías objetivo
        if calorias_calculadas > 0:
            if calorias_calculadas < calorias_comida:
                # Si estamos por debajo del 100%, aumentar todas las porciones proporcionalmente
                factor_calorias = calorias_comida / calorias_calculadas
                for grupo in porciones_ideales:
                    porciones_ideales[grupo] *= factor_calorias
            elif abs(calorias_calculadas - calorias_comida) > 10:
                # Si estamos cerca pero no exactos, ajustar ligeramente
                factor_calorias = calorias_comida / calorias_calculadas
                for grupo in porciones_ideales:
                    porciones_ideales[grupo] *= factor_calorias
        
        # Aplicar límites razonables basados en porciones diarias disponibles
        # pero priorizando cumplir con las calorías objetivo
        for grupo, porciones_ideal in porciones_ideales.items():
            porciones_diarias = metas.porciones_por_grupo.get(grupo, 0)
            
            # Porcentajes máximos de porciones diarias por comida (más flexibles para cumplir metas)
            # ESPECIALMENTE para grasas, que necesitan cumplir mejor las metas
            max_porcentaje = {
                'des': 0.40,   # Desayuno: hasta 40% de las porciones diarias
                'mm': 0.60,    # Merienda: hasta 60%
                'alm': 0.70,   # Almuerzo: hasta 70% (comida principal)
                'mt': 0.60,    # Merienda: hasta 60%
                'cena': 0.50   # Cena: hasta 50%
            }.get(tiempo, 0.50)
            
            # Para grasas, ser más generoso para cumplir metas
            if grupo == 'GRUPO7_GRASAS':
                max_porcentaje *= 2.0  # Permitir 100% más para grasas (aumentado de 50%) para cumplir mejor las metas
            
            # PRIORIZAR cumplir con las calorías objetivo sobre los límites de porciones
            # Si las porciones ideales exceden el máximo, usar un factor de ajuste más generoso
            if porciones_ideal > porciones_diarias * max_porcentaje:
                # Si necesitamos más porciones para cumplir calorías, permitir hasta 1.5x el máximo (aumentado de 1.3x)
                # Para grasas, ser aún más generoso para cumplir metas
                factor_max = 1.5 if grupo != 'GRUPO7_GRASAS' else 2.0  # Aumentado de 1.8 a 2.0 para grasas
                porciones_final = min(porciones_ideal, porciones_diarias * max_porcentaje * factor_max)
            else:
                porciones_final = porciones_ideal
            
            # Asegurar mínimo de 0.1 porciones si se requiere
            # Para grasas, asegurar mínimo más alto si se necesita
            if grupo == 'GRUPO7_GRASAS' and porciones_ideal > 0.05:
                porciones_comida[grupo] = max(0.5, round(porciones_final, 1))  # Aumentado mínimo de 0.2 a 0.5 para grasas
            elif porciones_ideal > 0.05:
                porciones_comida[grupo] = max(0.1, round(porciones_final, 1))
            else:
                porciones_comida[grupo] = 0
        
        return porciones_comida

    def _filtrar_ingredientes_personalizados(self, perfil: PerfilPaciente, metas: MetaNutricional, ingredientes: Dict) -> List[Dict]:
        """Filtra ingredientes según las preferencias del usuario"""
        # Obtener ingredientes base
        ingredientes_base = self.obtener_ingredientes_recomendados(perfil, metas)
        
        # Aplicar filtros de inclusión
        ingredientes_incluir = ingredientes.get('incluir', [])
        ingredientes_excluir = ingredientes.get('excluir', [])
        grupos_excluidos = ingredientes.get('grupos_excluidos', [])
        
        # Función auxiliar para extraer nombre o ID de un ingrediente (puede ser string o dict)
        def _extraer_nombre_o_id(item):
            if isinstance(item, dict):
                # Si es un diccionario, usar el ID si está disponible, sino el nombre
                return item.get('id') or item.get('nombre', '')
            return item  # Si es string, devolverlo directamente
        
        # Función auxiliar para extraer nombre como string para comparación
        def _extraer_nombre_str(item):
            if isinstance(item, dict):
                return str(item.get('nombre', ''))
            return str(item)
        
        # Filtrar por ingredientes a incluir
        if ingredientes_incluir:
            # Extraer IDs y nombres de los ingredientes a incluir
            ids_incluir = {_extraer_nombre_o_id(inc) for inc in ingredientes_incluir if isinstance(inc, dict) and inc.get('id')}
            nombres_incluir = {_extraer_nombre_str(inc).lower() for inc in ingredientes_incluir}
            
            ingredientes_base = [ing for ing in ingredientes_base 
                               if (ing.get('id') in ids_incluir or 
                                   any(nom.lower() in ing['nombre'].lower() for nom in nombres_incluir))]
        
        # Filtrar por ingredientes a excluir
        if ingredientes_excluir:
            # Extraer IDs y nombres de los ingredientes a excluir
            ids_excluir = {_extraer_nombre_o_id(exc) for exc in ingredientes_excluir if isinstance(exc, dict) and exc.get('id')}
            nombres_excluir = {_extraer_nombre_str(exc).lower() for exc in ingredientes_excluir}
            
            ingredientes_base = [ing for ing in ingredientes_base 
                               if (ing.get('id') not in ids_excluir and 
                                   not any(nom.lower() in ing['nombre'].lower() for nom in nombres_excluir))]
        
        # Filtrar por grupos excluidos
        if grupos_excluidos:
            ingredientes_base = [ing for ing in ingredientes_base 
                               if ing.get('grupo') not in grupos_excluidos]
        
        # Verificar que no queden grupos vacíos después del filtrado
        grupos_disponibles = set(ing.get('grupo') for ing in ingredientes_base)
        grupos_requeridos = {'GRUPO1_CEREALES', 'GRUPO2_VERDURAS', 'GRUPO3_FRUTAS', 'GRUPO5_CARNES'}
        
        grupos_faltantes = grupos_requeridos - grupos_disponibles
        if grupos_faltantes:
            print(f"[WARN] Advertencia: Grupos faltantes después del filtrado: {grupos_faltantes}")
            # Agregar algunos ingredientes básicos para evitar errores
            ingredientes_fallback = self.obtener_ingredientes_recomendados(perfil, metas)
            for grupo_faltante in grupos_faltantes:
                ingredientes_grupo = [ing for ing in ingredientes_fallback if ing.get('grupo') == grupo_faltante]
                if ingredientes_grupo:
                    # Tomar el primer ingrediente del grupo faltante
                    ingredientes_base.append(ingredientes_grupo[0])
                    print(f"[OK] Agregado ingrediente fallback para {grupo_faltante}: {ingredientes_grupo[0]['nombre']}")
        
        return ingredientes_base

    # NOTA: Esta función fue reemplazada por la versión con integración ML más abajo (línea ~2998)
    # Se mantiene comentada para referencia, pero NO se usa
    # def obtener_ingredientes_recomendados_OLD(self, perfil: PerfilPaciente, metas: MetaNutricional) -> List[Dict]:
    #     """VERSIÓN ANTIGUA SIN INTEGRACIÓN ML - NO SE USA"""
    #     pass
    
    def _agrupar_ingredientes(self, ingredientes: List[Dict]) -> Dict:
        """Agrupa ingredientes por tipo para facilitar la selección variada"""
        grupos = {
            'GRUPO2_VERDURAS': [],
            'GRUPO5_CARNES': [],
            'GRUPO1_CEREALES': [],
            'GRUPO3_FRUTAS': [],
            'GRUPO4_LACTEOS': [],
            'GRUPO7_GRASAS': []
        }
        
        for ingrediente in ingredientes:
            grupo = ingrediente['grupo']
            if grupo in grupos:
                grupos[grupo].append(ingrediente)
        
        return grupos
    
    def debug_ingredientes_disponibles(self, paciente_id: int) -> Dict:
        """Función de debug para ver qué ingredientes están disponibles"""
        perfil = self.obtener_perfil_paciente(paciente_id)
        metas = self.calcular_metas_nutricionales(perfil)
        ingredientes = self.obtener_ingredientes_recomendados(perfil, metas)
        grupos = self._agrupar_ingredientes(ingredientes)
        
        return {
            'total_ingredientes': len(ingredientes),
            'grupos': {k: len(v) for k, v in grupos.items()},
            'ingredientes_por_grupo': grupos
        }

    def generar_recomendacion_diaria(self, paciente_id: int) -> Dict:
        """Genera una recomendación nutricional completa para un día"""
        
        # Obtener perfil del paciente
        perfil = self.obtener_perfil_paciente(paciente_id)
        
        # Calcular metas nutricionales
        metas = self.calcular_metas_nutricionales(perfil)
        
        # Obtener ingredientes recomendados
        ingredientes = self.obtener_ingredientes_recomendados(perfil, metas)
        
        # Generar distribución por comidas
        comidas = self._generar_distribucion_comidas(ingredientes, metas, perfil)
        
        return {
            'paciente_id': paciente_id,
            'fecha': date.today().isoformat(),
            'perfil': {
                'edad': perfil.edad,
                'sexo': perfil.sexo,
                'peso': perfil.peso,
                'talla': perfil.talla,
                'imc': round(perfil.imc, 2),
                'actividad': perfil.actividad,
                'hba1c': perfil.hba1c,
                'glucosa_ayunas': perfil.glucosa_ayunas
            },
            'metas_nutricionales': {
                'calorias_diarias': metas.calorias_diarias,
                'carbohidratos_g': metas.carbohidratos_g,
                'carbohidratos_porcentaje': metas.carbohidratos_porcentaje,
                'proteinas_g': metas.proteinas_g,
                'proteinas_porcentaje': metas.proteinas_porcentaje,
                'grasas_g': metas.grasas_g,
                'grasas_porcentaje': metas.grasas_porcentaje,
                'fibra_g': metas.fibra_g,
                'sodio_mg': metas.sodio_mg
            },
            'comidas': comidas,
            'ingredientes_disponibles': len(ingredientes),
            'recomendaciones_especiales': self._generar_recomendaciones_especiales(perfil)
        }
    
    def generar_recomendacion_semanal(self, paciente_id: int, dias: int = 7, filtros: Dict = None) -> Dict:
        """Genera una recomendación semanal con variedad real y validaciones"""
        
        # Obtener perfil del paciente
        perfil = self.obtener_perfil_paciente(paciente_id)
        
        # Calcular metas nutricionales
        metas = self.calcular_metas_nutricionales(perfil)
        
        # Aplicar filtros si se proporcionan
        if filtros:
            metas = self._aplicar_filtros_metas(metas, filtros)
        
        # Obtener ingredientes recomendados con filtros
        ingredientes = self.obtener_ingredientes_recomendados(perfil, metas, filtros)
        
        # Agrupar ingredientes por tipo
        grupos_alimentos = self._agrupar_ingredientes(ingredientes)
        
        # Generar múltiples planes si es necesario
        planes_generados = self._generar_planes_multiples(grupos_alimentos, dias, metas, filtros, perfil)
        
        # Generar lista de compras para todos los planes
        lista_compras = self._generar_lista_compras_multiples(planes_generados)
        
        # Calcular validaciones del plan completo
        validaciones = self._calcular_validaciones_plan_completo(planes_generados, metas, filtros)
        
        return {
            'paciente_id': paciente_id,
            'fecha': date.today().isoformat(),
            'perfil': {
                'edad': perfil.edad,
                'sexo': perfil.sexo,
                'peso': perfil.peso,
                'talla': perfil.talla,
                'imc': round(perfil.imc, 2),
                'actividad': perfil.actividad,
                'hba1c': perfil.hba1c,
                'glucosa_ayunas': perfil.glucosa_ayunas
            },
            'metas_nutricionales': {
                'calorias_diarias': metas.calorias_diarias,
                'carbohidratos_g': metas.carbohidratos_g,
                'carbohidratos_porcentaje': metas.carbohidratos_porcentaje,
                'proteinas_g': metas.proteinas_g,
                'proteinas_porcentaje': metas.proteinas_porcentaje,
                'grasas_g': metas.grasas_g,
                'grasas_porcentaje': metas.grasas_porcentaje,
                'fibra_g': metas.fibra_g,
                'sodio_mg': metas.sodio_mg
            },
            'plan_completo': planes_generados,  # Todos los planes generados
            'lista_compras': lista_compras,  # Lista de compras generada
            'validaciones': validaciones,  # Validaciones de cumplimiento
            'ingredientes_disponibles': len(ingredientes),
            'recomendaciones_especiales': self._generar_recomendaciones_especiales(perfil),
            'total_semanas': len(planes_generados),
            'filtros_aplicados': filtros
        }

    def _generar_distribucion_comidas(self, ingredientes: List[Dict], metas: MetaNutricional, perfil: PerfilPaciente) -> Dict:
        """Genera la distribución de alimentos por comida"""
        
        comidas = {}
        grupos_alimentos = {
            'GRUPO2_VERDURAS': [i for i in ingredientes if i['grupo'] == 'GRUPO2_VERDURAS'],
            'GRUPO5_CARNES': [i for i in ingredientes if i['grupo'] == 'GRUPO5_CARNES'],
            'GRUPO1_CEREALES': [i for i in ingredientes if i['grupo'] == 'GRUPO1_CEREALES'],
            'GRUPO3_FRUTAS': [i for i in ingredientes if i['grupo'] == 'GRUPO3_FRUTAS'],
            'GRUPO4_LACTEOS': [i for i in ingredientes if i['grupo'] == 'GRUPO4_LACTEOS'],
            'GRUPO7_GRASAS': [i for i in ingredientes if i['grupo'] == 'GRUPO7_GRASAS']
        }
        
        tiempos_comida = ['des', 'mm', 'alm', 'mt', 'cena']
        
        for tiempo in tiempos_comida:
            comidas[tiempo] = {
                'carbohidratos_meta': metas.carbohidratos_por_comida[tiempo],
                'alimentos_sugeridos': [],
                'calorias_estimadas': 0,
                'carbohidratos_estimados': 0
            }
            
            # Sugerir alimentos según el tiempo de comida (usando funciones variadas)
            if tiempo == 'des':
                comidas[tiempo]['alimentos_sugeridos'] = self._sugerir_desayuno_variado(grupos_alimentos, 1)
            elif tiempo in ['mm', 'mt']:
                comidas[tiempo]['alimentos_sugeridos'] = self._sugerir_merienda_variada(grupos_alimentos, 1)
            elif tiempo == 'alm':
                comidas[tiempo]['alimentos_sugeridos'] = self._sugerir_almuerzo_variado(grupos_alimentos, 1)
            elif tiempo == 'cena':
                comidas[tiempo]['alimentos_sugeridos'] = self._sugerir_cena_variada(grupos_alimentos, 1)
        
        return comidas
    
    def generar_plan_semanal(self, perfil: PerfilPaciente, metas: MetaNutricional, dias: int = 7, configuracion: Dict = None, ingredientes: Dict = None) -> Dict:
        """Genera un plan semanal con variedad de alimentos"""
        
        # Usar ingredientes personalizados si están disponibles
        if ingredientes:
            ingredientes_recomendados = self._filtrar_ingredientes_personalizados(perfil, metas, ingredientes)
        else:
            ingredientes_recomendados = self.obtener_ingredientes_recomendados(perfil, metas)
        
        grupos_alimentos = self._agrupar_ingredientes(ingredientes_recomendados)
        
        plan_semanal = {}
        
        # Sistema de seguimiento de alimentos usados para evitar repeticiones excesivas
        # Estructura: {nombre_alimento: [días donde se usó]}
        alimentos_usados = {}
        # Máximo de veces que un alimento puede aparecer en la semana
        max_repeticiones_semana = 3
        # Días mínimos entre repeticiones del mismo alimento
        dias_minimos_entre_repeticiones = 2
        # Para proteínas: reglas más estrictas
        max_repeticiones_proteinas = 2  # Máximo 2 veces por semana
        dias_minimos_entre_proteinas = 3  # Mínimo 3 días entre repeticiones
        
        # Usar fechas del frontend si están disponibles
        fecha_inicio = configuracion.get('fecha_inicio') if configuracion else None
        
        for dia in range(1, dias + 1):
            # Calcular fecha real si se proporciona fecha_inicio
            if fecha_inicio:
                from datetime import datetime, timedelta
                fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
                fecha_dia = fecha_inicio_dt + timedelta(days=dia-1)
                fecha_str = fecha_dia.strftime('%Y-%m-%d')
            else:
                fecha_str = f"2025-10-{19 + dia}"
            
            # Generar día con seguimiento de alimentos usados
            dia_generado = self._generar_dia_variado(
                grupos_alimentos, dia, metas, configuracion, perfil,
                alimentos_usados=alimentos_usados,
                max_repeticiones=max_repeticiones_semana,
                dias_minimos_entre_repeticiones=dias_minimos_entre_repeticiones,
                max_repeticiones_proteinas=max_repeticiones_proteinas,
                dias_minimos_entre_proteinas=dias_minimos_entre_proteinas
            )
            
            # Actualizar seguimiento de alimentos usados
            for tiempo, comida in dia_generado.items():
                if isinstance(comida, dict) and 'alimentos' in comida:
                    for alimento in comida.get('alimentos', []):
                        nombre = alimento.get('nombre', '')
                        if nombre:
                            if nombre not in alimentos_usados:
                                alimentos_usados[nombre] = []
                            alimentos_usados[nombre].append(dia)
            
            plan_semanal[f'dia_{dia}'] = {
                'fecha': fecha_str,
                **dia_generado
            }
        
        return {
            'plan_semanal': plan_semanal,
            'metas_nutricionales': metas,
            'resumen': self._generar_resumen_semanal(plan_semanal, metas)
        }
    
    def _generar_dia_completo(self, grupos: Dict, dia: int, metas: MetaNutricional, perfil: PerfilPaciente = None, alimentos_usados: Dict = None, max_repeticiones: int = 3, dias_minimos_entre_repeticiones: int = 2, max_repeticiones_proteinas: int = 2, dias_minimos_entre_proteinas: int = 3) -> Dict:
        """Genera un día completo con estructura compatible con el frontend, evitando repeticiones"""
        comidas = {}
        
        # Inicializar seguimiento si no se proporciona
        if alimentos_usados is None:
            alimentos_usados = {}
        
        # Ajustar distribución de calorías por comida según predicción ML
        # Obtener probabilidad ML ajustada si está disponible
        probabilidad_mal_control = getattr(self, '_ultima_probabilidad_ajustada', None)
        
        # Distribución base (sin ML)
        distribucion_base = {
            'des': 0.25,  # 25%
            'mm': 0.10,   # 10%
            'alm': 0.35,  # 35%
            'mt': 0.10,   # 10%
            'cena': 0.20  # 20%
        }
        
        # Ajustar distribución según ML si está disponible
        if probabilidad_mal_control is not None and probabilidad_mal_control > 0.6:
            # Mal control: reducir CHO en desayuno, aumentar en almuerzo
            # Redistribuir para mejor control glucémico
            distribucion_calorias = {
                'des': metas.calorias_diarias * 0.20,  # 20% (reducido de 25%)
                'mm': metas.calorias_diarias * 0.12,   # 12% (aumentado de 10%)
                'alm': metas.calorias_diarias * 0.38,  # 38% (aumentado de 35%)
                'mt': metas.calorias_diarias * 0.12,   # 12% (aumentado de 10%)
                'cena': metas.calorias_diarias * 0.18  # 18% (reducido de 20%)
            }
            print(f"[ML] Ajustando distribución calórica por comida (prob={probabilidad_mal_control:.2f})")
        elif probabilidad_mal_control is not None and probabilidad_mal_control > 0.4:
            # Control moderado: ajuste ligero
            distribucion_calorias = {
                'des': metas.calorias_diarias * 0.23,  # 23% (ligera reducción)
                'mm': metas.calorias_diarias * 0.11,   # 11%
                'alm': metas.calorias_diarias * 0.36,  # 36% (ligero aumento)
                'mt': metas.calorias_diarias * 0.11,   # 11%
                'cena': metas.calorias_diarias * 0.19  # 19% (ligera reducción)
            }
            print(f"[ML] Ajuste ligero de distribución calórica (prob={probabilidad_mal_control:.2f})")
        else:
            # Control bueno o ML no disponible: usar distribución base
            distribucion_calorias = {
                'des': metas.calorias_diarias * distribucion_base['des'],
                'mm': metas.calorias_diarias * distribucion_base['mm'],
                'alm': metas.calorias_diarias * distribucion_base['alm'],
                'mt': metas.calorias_diarias * distribucion_base['mt'],
                'cena': metas.calorias_diarias * distribucion_base['cena']
            }
        
        # Definir orden correcto de comidas
        orden_comidas = ['des', 'mm', 'alm', 'mt', 'cena']
        
        # Generar cada comida con variedad basada en el día en el orden correcto
        for tiempo in orden_comidas:
            calorias_objetivo = distribucion_calorias[tiempo]
            alimentos_sugeridos = self._sugerir_alimentos_tiempo_variado(
                tiempo, grupos, dia, perfil, metas,
                alimentos_usados=alimentos_usados,
                max_repeticiones=max_repeticiones,
                dias_minimos_entre_repeticiones=dias_minimos_entre_repeticiones,
                max_repeticiones_proteinas=max_repeticiones_proteinas,
                dias_minimos_entre_proteinas=dias_minimos_entre_proteinas
            )
            
            # Actualizar seguimiento de alimentos usados para este día (antes de generar siguiente comida)
            for alimento in alimentos_sugeridos:
                nombre = alimento.get('ingrediente', {}).get('nombre', '')
                if nombre:
                    if nombre not in alimentos_usados:
                        alimentos_usados[nombre] = []
                    if dia not in alimentos_usados[nombre]:
                        alimentos_usados[nombre].append(dia)
            
            # Calcular totales nutricionales
            kcal_total = sum(alimento['ingrediente']['kcal'] * alimento['cantidad_sugerida'] / 100 for alimento in alimentos_sugeridos)
            cho_total = sum(alimento['ingrediente']['cho'] * alimento['cantidad_sugerida'] / 100 for alimento in alimentos_sugeridos)
            pro_total = sum(alimento['ingrediente']['pro'] * alimento['cantidad_sugerida'] / 100 for alimento in alimentos_sugeridos)
            fat_total = sum(alimento['ingrediente']['fat'] * alimento['cantidad_sugerida'] / 100 for alimento in alimentos_sugeridos)
            
            comidas[tiempo] = {
                'kcal_total': round(kcal_total, 1),
                'cho_total': round(cho_total, 1),
                'pro_total': round(pro_total, 1),
                'fat_total': round(fat_total, 1),
                'alimentos': [
                    {
                        'nombre': alimento['ingrediente']['nombre'],
                        'grupo': alimento['ingrediente']['grupo'],
                        'cantidad': alimento['cantidad_sugerida'],
                        'unidad': alimento['unidad'],
                        'kcal': round(alimento['ingrediente']['kcal'] * alimento['cantidad_sugerida'] / 100, 1),
                        'cho': round(alimento['ingrediente']['cho'] * alimento['cantidad_sugerida'] / 100, 1),
                        'pro': round(alimento['ingrediente']['pro'] * alimento['cantidad_sugerida'] / 100, 1),
                        'fat': round(alimento['ingrediente']['fat'] * alimento['cantidad_sugerida'] / 100, 1)
                    }
                    for alimento in alimentos_sugeridos
                ]
            }
        
        return comidas

    def _generar_dia_variado(self, grupos: Dict, dia: int, metas: MetaNutricional, configuracion: Dict = None, perfil: PerfilPaciente = None, alimentos_usados: Dict = None, max_repeticiones: int = 3, dias_minimos_entre_repeticiones: int = 2, max_repeticiones_proteinas: int = 2, dias_minimos_entre_proteinas: int = 3) -> Dict:
        """Genera un día completo con variedad, evitando repeticiones excesivas"""
        comidas = {}
        
        # Inicializar seguimiento si no se proporciona
        if alimentos_usados is None:
            alimentos_usados = {}
        
        # Usar patrón de comidas personalizado si está disponible
        patron_comidas = configuracion.get('patron_comidas', ['des', 'mm', 'alm', 'mt', 'cena']) if configuracion else ['des', 'mm', 'alm', 'mt', 'cena']
        
        # Convertir patrón de comidas de string a lista si es necesario
        if isinstance(patron_comidas, str):
            patron_comidas = [c.strip() for c in patron_comidas.split(',')]
        
        # Ajustar distribución de calorías por comida según predicción ML
        probabilidad_mal_control = getattr(self, '_ultima_probabilidad_ajustada', None)
        
        # Distribución base (sin ML)
        distribucion_base = {
            'des': 0.25,  # 25%
            'mm': 0.10,   # 10%
            'alm': 0.35,  # 35%
            'mt': 0.10,   # 10%
            'cena': 0.20  # 20%
        }
        
        # Ajustar distribución según ML si está disponible
        if probabilidad_mal_control is not None and probabilidad_mal_control > 0.6:
            # Mal control: reducir CHO en desayuno, aumentar en almuerzo
            distribucion_calorias = {
                'des': metas.calorias_diarias * 0.20,  # 20% (reducido)
                'mm': metas.calorias_diarias * 0.12,   # 12% (aumentado)
                'alm': metas.calorias_diarias * 0.38,  # 38% (aumentado)
                'mt': metas.calorias_diarias * 0.12,   # 12% (aumentado)
                'cena': metas.calorias_diarias * 0.18  # 18% (reducido)
            }
        elif probabilidad_mal_control is not None and probabilidad_mal_control > 0.4:
            # Control moderado: ajuste ligero
            distribucion_calorias = {
                'des': metas.calorias_diarias * 0.23,  # 23%
                'mm': metas.calorias_diarias * 0.11,   # 11%
                'alm': metas.calorias_diarias * 0.36,  # 36%
                'mt': metas.calorias_diarias * 0.11,   # 11%
                'cena': metas.calorias_diarias * 0.19  # 19%
            }
        else:
            # Control bueno o ML no disponible: usar distribución base
            distribucion_calorias = {
                'des': metas.calorias_diarias * distribucion_base['des'],
                'mm': metas.calorias_diarias * distribucion_base['mm'],
                'alm': metas.calorias_diarias * distribucion_base['alm'],
                'mt': metas.calorias_diarias * distribucion_base['mt'],
                'cena': metas.calorias_diarias * distribucion_base['cena']
            }
        
        # Generar solo las comidas del patrón personalizado
        for tiempo in patron_comidas:
            if tiempo in distribucion_calorias:
                calorias_objetivo = distribucion_calorias[tiempo]
                alimentos_sugeridos = self._sugerir_alimentos_tiempo_variado(
                    tiempo, grupos, dia, perfil, metas,
                    alimentos_usados=alimentos_usados,
                    max_repeticiones=max_repeticiones,
                    dias_minimos_entre_repeticiones=dias_minimos_entre_repeticiones,
                    max_repeticiones_proteinas=max_repeticiones_proteinas,
                    dias_minimos_entre_proteinas=dias_minimos_entre_proteinas
                )
                
                # Convertir a formato esperado por el frontend
                comidas[tiempo] = {
                    'nombre': self._obtener_nombre_comida(tiempo),
                    'horario': self._obtener_horario_comida(tiempo),
                    'alimentos': [
                        {
                            'nombre': alimento['ingrediente']['nombre'],
                            'grupo': alimento['ingrediente']['grupo'],
                            'cantidad': f"{alimento['cantidad_sugerida']}{alimento['unidad']}",
                            'kcal': round(alimento['ingrediente']['kcal'] * alimento['cantidad_sugerida'] / 100, 1),
                            'cho': round(alimento['ingrediente']['cho'] * alimento['cantidad_sugerida'] / 100, 1),
                            'pro': round(alimento['ingrediente']['pro'] * alimento['cantidad_sugerida'] / 100, 1),
                            'fat': round(alimento['ingrediente']['fat'] * alimento['cantidad_sugerida'] / 100, 1)
                        }
                        for alimento in alimentos_sugeridos
                    ]
                }
        
        return comidas
    
    def _obtener_nombre_comida(self, tiempo: str) -> str:
        """Obtiene el nombre legible de la comida"""
        nombres = {
            'des': 'Desayuno',
            'mm': 'Media Mañana',
            'alm': 'Almuerzo',
            'mt': 'Media Tarde',
            'cena': 'Cena'
        }
        return nombres.get(tiempo, tiempo)
    
    def _obtener_horario_comida(self, tiempo: str) -> str:
        """Obtiene el horario de la comida"""
        horarios = {
            'des': '07:00',
            'mm': '10:00',
            'alm': '12:00',
            'mt': '15:00',
            'cena': '19:00'
        }
        return horarios.get(tiempo, '00:00')
    
    def _sugerir_alimentos_tiempo_variado(self, tiempo: str, grupos: Dict, dia: int, perfil: PerfilPaciente = None, metas: MetaNutricional = None, alimentos_usados: Dict = None, max_repeticiones: int = 3, dias_minimos_entre_repeticiones: int = 2, max_repeticiones_proteinas: int = 2, dias_minimos_entre_proteinas: int = 3) -> List[Dict]:
        """Sugiere alimentos variados para un tiempo específico usando porciones de intercambio, evitando repeticiones"""
        if alimentos_usados is None:
            alimentos_usados = {}
        
        if tiempo == 'des':
            return self._sugerir_desayuno_variado(grupos, dia, perfil, metas, alimentos_usados, max_repeticiones, dias_minimos_entre_repeticiones, max_repeticiones_proteinas, dias_minimos_entre_proteinas)
        elif tiempo in ['mm', 'mt']:
            return self._sugerir_merienda_variada(grupos, dia, perfil, metas, alimentos_usados, max_repeticiones, dias_minimos_entre_repeticiones, max_repeticiones_proteinas, dias_minimos_entre_proteinas)
        elif tiempo == 'alm':
            return self._sugerir_almuerzo_variado(grupos, dia, perfil, metas, alimentos_usados, max_repeticiones, dias_minimos_entre_repeticiones, max_repeticiones_proteinas, dias_minimos_entre_proteinas)
        elif tiempo == 'cena':
            return self._sugerir_cena_variada(grupos, dia, perfil, metas, alimentos_usados, max_repeticiones, dias_minimos_entre_repeticiones, max_repeticiones_proteinas, dias_minimos_entre_proteinas)
        return []
    
    def _filtrar_alimentos_por_repeticion(self, alimentos: List[Dict], alimentos_usados: Dict, dia: int, max_repeticiones: int = 3, dias_minimos_entre_repeticiones: int = 2, grupo_alimento: str = None, max_repeticiones_proteinas: int = 2, dias_minimos_entre_proteinas: int = 3) -> List[Dict]:
        """
        Filtra alimentos para evitar repeticiones excesivas.
        Prioriza alimentos no usados, luego los usados hace más días.
        Para proteínas (GRUPO5_CARNES), aplica reglas más estrictas.
        """
        if not alimentos_usados:
            return alimentos
        
        # Detectar si es un grupo de proteínas
        es_proteina = grupo_alimento == 'GRUPO5_CARNES'
        
        # Usar reglas más estrictas para proteínas
        if es_proteina:
            max_rep = max_repeticiones_proteinas
            dias_min = dias_minimos_entre_proteinas
        else:
            max_rep = max_repeticiones
            dias_min = dias_minimos_entre_repeticiones
        
        alimentos_priorizados = []
        alimentos_evitados = []
        alimentos_prohibidos = []  # Para proteínas usadas en días consecutivos
        
        for alimento in alimentos:
            nombre = alimento.get('nombre', '')
            if not nombre:
                alimentos_priorizados.append(alimento)
                continue
            
            # Si no se ha usado, priorizar
            if nombre not in alimentos_usados:
                alimentos_priorizados.append(alimento)
                continue
            
            dias_uso = alimentos_usados[nombre]
            veces_usado = len(dias_uso)
            
            # Si ya se usó el máximo de veces, evitar
            if veces_usado >= max_rep:
                alimentos_evitados.append(alimento)
                continue
            
            # Para proteínas: verificar si se usó en días consecutivos (muy estricto)
            if es_proteina and dias_uso:
                dias_uso_ordenados = sorted(dias_uso)
                # Verificar si se usó en el día anterior (día - 1)
                if (dia - 1) in dias_uso_ordenados:
                    alimentos_prohibidos.append(alimento)
                    continue
                # Verificar si hay días consecutivos en el historial
                tiene_dias_consecutivos = False
                for i in range(len(dias_uso_ordenados) - 1):
                    if dias_uso_ordenados[i+1] - dias_uso_ordenados[i] == 1:
                        # Se usó en días consecutivos, prohibir
                        tiene_dias_consecutivos = True
                        break
                if tiene_dias_consecutivos:
                    alimentos_prohibidos.append(alimento)
                    continue
            
            # Si se usó recientemente (menos de X días), evitar
            ultimo_uso = max(dias_uso)
            dias_desde_ultimo_uso = dia - ultimo_uso
            if dias_desde_ultimo_uso < dias_min:
                alimentos_evitados.append(alimento)
                continue
            
            # Si se puede usar, agregar con prioridad menor (al final de priorizados)
            alimentos_priorizados.append(alimento)
        
        # Si no hay suficientes alimentos priorizados, agregar algunos evitados (pero con menor prioridad)
        # NUNCA agregar proteínas prohibidas (días consecutivos)
        if len(alimentos_priorizados) < 2 and alimentos_evitados:
            # Ordenar evitados por días desde último uso (más antiguo primero)
            alimentos_evitados.sort(key=lambda x: (
                max(alimentos_usados.get(x.get('nombre', ''), [0])) if x.get('nombre', '') in alimentos_usados else 0
            ))
            # Agregar solo 1-2 de los menos recientes
            alimentos_priorizados.extend(alimentos_evitados[:min(2, len(alimentos_evitados))])
        
        return alimentos_priorizados
    
    def _generar_resumen_semanal(self, plan_semanal: Dict, metas: MetaNutricional) -> Dict:
        """Genera un resumen del plan semanal"""
        total_calorias = 0
        total_carbohidratos = 0
        total_proteinas = 0
        total_grasas = 0
        
        for dia_key, dia_data in plan_semanal.items():
            # Saltar la clave 'fecha' que es un string
            if isinstance(dia_data, str):
                continue
                
            for tiempo, comida in dia_data.items():
                # Verificar que comida sea un diccionario con 'alimentos'
                if isinstance(comida, dict) and 'alimentos' in comida:
                    for alimento in comida.get('alimentos', []):
                        total_calorias += alimento.get('kcal', 0)
                        total_carbohidratos += alimento.get('cho', 0)
                        total_proteinas += alimento.get('pro', 0)
                        total_grasas += alimento.get('fat', 0)
        
        return {
            'calorias_totales_semana': round(total_calorias, 2),
            'carbohidratos_totales_semana': round(total_carbohidratos, 2),
            'proteinas_totales_semana': round(total_proteinas, 2),
            'grasas_totales_semana': round(total_grasas, 2),
            'calorias_promedio_dia': round(total_calorias / len(plan_semanal), 2)
        }
    
    def generar_plan_semanal_completo(self, paciente_id: int, dias: int = 7, configuracion: Dict = None, ingredientes: Dict = None) -> Dict:
        """Genera un plan semanal completo con variedad para un paciente y lo optimiza"""
        try:
            # Cargar modelos ML nuevos al inicio
            print("[DEBUG] Verificando modelos ML nuevos...")
            self._cargar_modelo_respuesta_glucemica()
            self._cargar_modelo_seleccion_alimentos()
            self._cargar_modelo_optimizacion_combinaciones()
            
            # Obtener perfil del paciente
            perfil = self.obtener_perfil_paciente(paciente_id)
            
            # Si la configuración viene del frontend después de "Recomendación inteligente",
            # ya está ajustada por ML, así que saltamos el ajuste ML para evitar doble ajuste
            # La configuración original (base) debería venir en el dataset del frontend
            # Por ahora, asumimos que si hay configuración, ya viene ajustada
            skip_ml = configuracion is not None  # Saltar ML si hay configuración (ya viene ajustada)
            
            # Guardar configuración original (si está disponible, se usará desde el frontend)
            # Si no está disponible, usar la configuración actual como referencia
            configuracion_original = None
            if configuracion:
                # La configuración ya viene ajustada por ML desde "Recomendación inteligente"
                # La configuración original (base) debería venir del frontend en el dataset
                # Por ahora, guardamos la configuración actual como referencia
                configuracion_original = {
                    'kcal_objetivo': configuracion.get('kcal_objetivo'),
                    'cho_pct': configuracion.get('cho_pct'),
                    'pro_pct': configuracion.get('pro_pct'),
                    'fat_pct': configuracion.get('fat_pct')
                }
            
            # Calcular metas nutricionales (sin aplicar ML nuevamente si ya viene ajustada)
            metas = self.calcular_metas_nutricionales(perfil, configuracion, skip_ml_ajuste=skip_ml)
            
            # Guardar configuración original en el objeto para que esté disponible después
            self._configuracion_original = configuracion_original
            print(f"[DEBUG] Configuración original guardada: {configuracion_original}")
            
            # Generar plan semanal con variedad y configuración personalizada
            plan_semanal = self.generar_plan_semanal(perfil, metas, dias, configuracion, ingredientes)
            
            # OPTIMIZAR EL PLAN para cumplir objetivos nutricionales
            print("[DEBUG] Iniciando optimización del plan...")
            try:
                from Core.optimizador_plan import OptimizadorPlan
                
                # Preparar grupos de alimentos para el optimizador
                if ingredientes:
                    ingredientes_recomendados = self._filtrar_ingredientes_personalizados(perfil, metas, ingredientes)
                else:
                    ingredientes_recomendados = self.obtener_ingredientes_recomendados(perfil, metas)
                grupos_alimentos = self._agrupar_ingredientes(ingredientes_recomendados)
                
                # Convertir metas a formato dict para el optimizador
                metas_dict = {
                    'calorias_diarias': metas.calorias_diarias,
                    'carbohidratos_g': metas.carbohidratos_g,
                    'proteinas_g': metas.proteinas_g,
                    'grasas_g': metas.grasas_g,
                    'fibra_g': metas.fibra_g
                }
                
                # Motor de IA desactivado - ahora usamos Modelo 3 para optimizar combinaciones
                # motor_ia = None  # Ya no se usa para validar combinaciones
                
                # Crear optimizador (sin motor_ia, usará Modelo 3 en su lugar)
                optimizador = OptimizadorPlan(umbral_cumplimiento=0.90, max_iteraciones=20, motor_ia=None, perfil_paciente=perfil, motor_recomendacion=self)
                plan_optimizado, estadisticas = optimizador.optimizar_plan(
                    plan_semanal, 
                    metas_dict, 
                    grupos_alimentos, 
                    perfil,
                    self
                )
                
                print(f"[OK] Optimización completada:")
                print(f"   - Iteraciones: {estadisticas['iteraciones']}")
                print(f"   - Días optimizados: {estadisticas['dias_optimizados']}")
                print(f"   - Mejoras aplicadas: {len(estadisticas['mejoras_aplicadas'])}")
                
                # Usar plan optimizado
                plan_semanal = plan_optimizado
                
                # Agregar estadísticas de optimización al resultado
                if 'resumen' not in plan_semanal:
                    plan_semanal['resumen'] = {}
                plan_semanal['resumen']['optimizacion'] = estadisticas
                
            except ImportError as e:
                print(f"[WARN]  Optimizador no disponible: {e}. Continuando sin optimización.")
            except Exception as e:
                print(f"[WARN]  Error en optimización: {e}. Continuando con plan sin optimizar.")
                import traceback
                traceback.print_exc()
            
            # Convertir a formato compatible con la UI existente
            return self._convertir_plan_semanal_a_formato_ui(plan_semanal, perfil, metas)
            
        except Exception as e:
            raise ValueError(f"Error generando plan semanal: {str(e)}")
    
    def _convertir_plan_semanal_a_formato_ui(self, plan_semanal: Dict, perfil: PerfilPaciente, metas: MetaNutricional) -> Dict:
        """Convierte el plan semanal al formato esperado por la UI"""
        # Tomar el primer día como ejemplo para la estructura de comidas
        primer_dia = list(plan_semanal['plan_semanal'].values())[0]
        
        # Obtener probabilidad ML si está disponible
        probabilidad_ml = getattr(self, '_ultima_probabilidad_ml', None)
        
        # Obtener configuración original si está disponible
        configuracion_original = getattr(self, '_configuracion_original', None)
        print(f"[DEBUG] Configuración original al convertir a UI: {configuracion_original}")
        
        return {
            'perfil': {
                'edad': perfil.edad,
                'sexo': perfil.sexo,
                'peso': perfil.peso,
                'talla': perfil.talla,
                'imc': round(perfil.imc, 2),
                'actividad': perfil.actividad,
                'hba1c': perfil.hba1c,
                'glucosa_ayunas': perfil.glucosa_ayunas
            },
            'metas_nutricionales': {
                'calorias_diarias': metas.calorias_diarias,
                'carbohidratos_g': metas.carbohidratos_g,
                'carbohidratos_porcentaje': metas.carbohidratos_porcentaje,
                'proteinas_g': metas.proteinas_g,
                'proteinas_porcentaje': metas.proteinas_porcentaje,
                'grasas_g': metas.grasas_g,
                'grasas_porcentaje': metas.grasas_porcentaje,
                'fibra_g': metas.fibra_g,
                'sodio_mg': metas.sodio_mg
            },
            'debug_ml': {
                'probabilidad_mal_control': probabilidad_ml,
                'probabilidad_ajustada': getattr(self, '_ultima_probabilidad_ajustada', probabilidad_ml),
                'ml_disponible': probabilidad_ml is not None
            },
            'configuracion_original': configuracion_original,  # Configuración antes del ajuste ML
            'comidas': primer_dia,  # Estructura de comidas para compatibilidad
            'plan_semanal': plan_semanal['plan_semanal'],  # Plan completo
            'resumen_semanal': plan_semanal['resumen'],
            'recomendaciones_especiales': self._generar_recomendaciones_especiales(perfil)
        }
    
    def _guardar_probabilidad_ml(self, probabilidad: float):
        """Guarda la probabilidad ML para incluirla en la respuesta"""
        self._ultima_probabilidad_ml = probabilidad

    def _sugerir_desayuno(self, grupos: Dict) -> List[Dict]:
        """Sugiere alimentos para el desayuno"""
        sugerencias = []
        
        # Cereal integral
        if grupos['GRUPO1_CEREALES']:
            cereal = grupos['GRUPO1_CEREALES'][0]
            sugerencias.append({
                'ingrediente': cereal,
                'cantidad_sugerida': 30,
                'unidad': 'g',
                'motivo': 'Cereal integral con bajo índice glucémico'
            })
        
        # Proteína
        if grupos['GRUPO5_CARNES']:
            proteina = grupos['GRUPO5_CARNES'][0]
            sugerencias.append({
                'ingrediente': proteina,
                'cantidad_sugerida': 20,
                'unidad': 'g',
                'motivo': 'Proteína para estabilizar glucosa'
            })
        
        # Fruta
        if grupos['GRUPO3_FRUTAS']:
            fruta = grupos['GRUPO3_FRUTAS'][0]
            sugerencias.append({
                'ingrediente': fruta,
                'cantidad_sugerida': 100,
                'unidad': 'g',
                'motivo': 'Fruta con fibra'
            })
        
        return sugerencias
    
    def _obtener_limites_cantidad_grupo(self, grupo: str) -> Dict[str, int]:
        """
        Retorna los límites máximos de cantidad por grupo de alimentos.
        Si se necesita más, se debe agregar un segundo alimento del mismo grupo.
        """
        limites = {
            'GRUPO1_CEREALES': 200,    # Máximo 200g de cereales por alimento
            'GRUPO2_VERDURAS': 300,    # Máximo 300g de verduras por alimento
            'GRUPO3_FRUTAS': 150,      # Máximo 150g de frutas por alimento
            'GRUPO4_LACTEOS': 250,     # Máximo 250g de lácteos por alimento
            'GRUPO5_CARNES': 250,      # Máximo 250g de carnes por alimento (aumentado, no se combinan)
            'GRUPO7_GRASAS': 50,       # Máximo 50g de grasas por alimento
        }
        return {'max_por_alimento': limites.get(grupo, 200), 'max_total_grupo': limites.get(grupo, 200) * 2}
    
    def _clasificar_alimento_grupo1(self, alimento: Dict) -> str:
        """
        Clasifica un alimento del GRUPO1_CEREALES en subcategorías:
        - 'cereal': arroz, pasta, pan, quinoa, etc.
        - 'tuberculo': papa, camote, yuca, etc.
        - 'legumbre': lentejas, frijoles, garbanzos, etc.
        """
        nombre = str(alimento.get('nombre', '')).lower()
        
        # Tubérculos
        tuberculos = ['papa', 'camote', 'batata', 'yuca', 'ñame', 'oca']
        if any(t in nombre for t in tuberculos):
            return 'tuberculo'
        
        # Legumbres
        legumbres = ['lenteja', 'frijol', 'garbanzo', 'alubia', 'haba', 'pallar', 'tarwi', 'judía', 'fréjol']
        if any(l in nombre for l in legumbres):
            return 'legumbre'
        
        # Cereales (por defecto)
        return 'cereal'
    
    def _es_combinacion_valida_grupo1(self, alimento1: Dict, alimento2: Dict) -> bool:
        """
        Verifica si dos alimentos del GRUPO1_CEREALES pueden combinarse.
        Reglas:
        - NO combinar el mismo alimento (ej: lenteja + lenteja)
        - SÍ combinar diferentes subcategorías (cereal + legumbre, tuberculo + tuberculo diferente)
        - SÍ combinar diferentes cereales (arroz + pasta)
        """
        nombre1 = str(alimento1.get('nombre', '')).lower()
        nombre2 = str(alimento2.get('nombre', '')).lower()
        
        # No combinar el mismo alimento
        if nombre1 == nombre2:
            return False
        
        # Clasificar ambos alimentos
        cat1 = self._clasificar_alimento_grupo1(alimento1)
        cat2 = self._clasificar_alimento_grupo1(alimento2)
        
        # Combinaciones válidas:
        # 1. Cereal + Legumbre (ej: arroz + lenteja)
        if (cat1 == 'cereal' and cat2 == 'legumbre') or (cat1 == 'legumbre' and cat2 == 'cereal'):
            return True
        
        # 2. Cereal + Tubérculo (ej: arroz + papa)
        if (cat1 == 'cereal' and cat2 == 'tuberculo') or (cat1 == 'tuberculo' and cat2 == 'cereal'):
            return True
        
        # 3. Diferentes cereales (ej: arroz + pasta)
        if cat1 == 'cereal' and cat2 == 'cereal':
            return True
        
        # 4. Diferentes tubérculos (ej: papa + camote)
        if cat1 == 'tuberculo' and cat2 == 'tuberculo':
            return True
        
        # 5. NO combinar legumbres entre sí (ej: lenteja + frijol) - puede ser pesado
        # Pero permitirlo si son muy diferentes (ej: lenteja + garbanzo está bien)
        if cat1 == 'legumbre' and cat2 == 'legumbre':
            # Permitir solo si son claramente diferentes (no solo variantes del mismo)
            palabras1 = set(nombre1.split())
            palabras2 = set(nombre2.split())
            # Si comparten menos del 50% de palabras, están bien
            if len(palabras1.intersection(palabras2)) / max(len(palabras1), len(palabras2)) < 0.5:
                return True
            return False
        
        return False
    
    def _agregar_alimento_con_limite(self, grupo: str, alimentos_grupo: List[Dict], porciones_necesarias: float, 
                                     sugerencias: List[Dict], alimentos_usados: Dict, dia: int, factor_variedad: int,
                                     max_repeticiones: int, dias_minimos_entre_repeticiones: int,
                                     perfil_alimentario: Dict = None) -> float:
        """
        Agrega un alimento del grupo con límite de cantidad. Si se necesitan más porciones,
        agrega un segundo alimento del mismo grupo en lugar de aumentar la cantidad del primero.
        Retorna las porciones restantes que no se pudieron cubrir.
        """
        if not alimentos_grupo or porciones_necesarias <= 0:
            return porciones_necesarias
        
        limites = self._obtener_limites_cantidad_grupo(grupo)
        max_gramos_por_alimento = limites['max_por_alimento']
        
        # Filtrar por repetición
        alimentos_filtrados = self._filtrar_alimentos_por_repeticion(
            alimentos_grupo, alimentos_usados or {}, dia, max_repeticiones, dias_minimos_entre_repeticiones
        )
        if not alimentos_filtrados:
            alimentos_filtrados = alimentos_grupo
        
        # Seleccionar primer alimento
        alimento_idx = factor_variedad % len(alimentos_filtrados)
        alimento1 = alimentos_filtrados[alimento_idx]
        
        # Calcular gramos necesarios
        gramos_necesarios = self._convertir_porciones_a_gramos(alimento1, porciones_necesarias)
        
        # Si excede el límite, usar el máximo y calcular porciones restantes
        if gramos_necesarios > max_gramos_por_alimento:
            gramos_alimento1 = max_gramos_por_alimento
            # Recalcular porciones usadas
            if alimento1.get('porciones_intercambio'):
                porciones_usadas = (gramos_alimento1 / 100.0) * alimento1['porciones_intercambio']
            else:
                # Estimar: si 100g = 1 porción estándar
                porciones_usadas = gramos_alimento1 / 100.0
            porciones_restantes = porciones_necesarias - porciones_usadas
        else:
            gramos_alimento1 = gramos_necesarios
            porciones_usadas = porciones_necesarias
            porciones_restantes = 0
        
        # Agregar primer alimento
        sugerencias.append({
            'ingrediente': alimento1,
            'cantidad_sugerida': round(gramos_alimento1, 1),
            'porciones_intercambio': porciones_usadas,
            'unidad': 'g',
            'motivo': f'{grupo} - día {dia}'
        })
        
        # Si hay porciones restantes, decidir si agregar segundo alimento o aumentar cantidad
        if porciones_restantes > 0:
            # REGLA ESPECIAL: Para carnes, solo aumentar cantidad (no combinar tipos)
            if grupo == 'GRUPO5_CARNES':
                # Aumentar límite máximo para carnes a 250g si es necesario
                max_gramos_carnes = 250
                if gramos_alimento1 < max_gramos_carnes:
                    # Calcular cuánto más podemos agregar
                    gramos_adicionales = min(
                        max_gramos_carnes - gramos_alimento1,
                        self._convertir_porciones_a_gramos(alimento1, porciones_restantes)
                    )
                    if gramos_adicionales > 0:
                        # Actualizar cantidad del primer alimento
                        sugerencias[-1]['cantidad_sugerida'] = round(gramos_alimento1 + gramos_adicionales, 1)
                        # Recalcular porciones
                        if alimento1.get('porciones_intercambio'):
                            porciones_totales = ((gramos_alimento1 + gramos_adicionales) / 100.0) * alimento1['porciones_intercambio']
                        else:
                            porciones_totales = (gramos_alimento1 + gramos_adicionales) / 100.0
                        sugerencias[-1]['porciones_intercambio'] = porciones_totales
                        sugerencias[-1]['motivo'] = f'{grupo} (cantidad aumentada) - día {dia}'
            
            # Para GRUPO1_CEREALES: combinar inteligentemente diferentes subcategorías
            elif grupo == 'GRUPO1_CEREALES' and len(alimentos_filtrados) > 1:
                # Buscar alimentos que se puedan combinar válidamente
                alimentos_combinables = [
                    a for a in alimentos_filtrados 
                    if a.get('nombre') != alimento1.get('nombre') 
                    and self._es_combinacion_valida_grupo1(alimento1, a)
                ]
                
                if alimentos_combinables:
                    alimento2_idx = (factor_variedad + 10) % len(alimentos_combinables)
                    alimento2 = alimentos_combinables[alimento2_idx]
                    
                    # Calcular gramos para el segundo alimento
                    gramos_alimento2 = self._convertir_porciones_a_gramos(alimento2, porciones_restantes)
                    
                    # Limitar también el segundo alimento
                    if gramos_alimento2 > max_gramos_por_alimento:
                        gramos_alimento2 = max_gramos_por_alimento
                        # Recalcular porciones
                        if alimento2.get('porciones_intercambio'):
                            porciones_alimento2 = (gramos_alimento2 / 100.0) * alimento2['porciones_intercambio']
                        else:
                            porciones_alimento2 = gramos_alimento2 / 100.0
                        porciones_restantes = porciones_restantes - porciones_alimento2
                    else:
                        porciones_alimento2 = porciones_restantes
                        porciones_restantes = 0
                    
                    sugerencias.append({
                        'ingrediente': alimento2,
                        'cantidad_sugerida': round(gramos_alimento2, 1),
                        'porciones_intercambio': porciones_alimento2,
                        'unidad': 'g',
                        'motivo': f'{grupo} (complemento) - día {dia}'
                    })
            
            # Para otros grupos: combinar normalmente (diferente al primero)
            elif grupo != 'GRUPO5_CARNES' and len(alimentos_filtrados) > 1:
                # Seleccionar segundo alimento (diferente al primero)
                alimentos_restantes = [a for a in alimentos_filtrados if a.get('nombre') != alimento1.get('nombre')]
                if alimentos_restantes:
                    alimento2_idx = (factor_variedad + 10) % len(alimentos_restantes)
                    alimento2 = alimentos_restantes[alimento2_idx]
                    
                    # Calcular gramos para el segundo alimento
                    gramos_alimento2 = self._convertir_porciones_a_gramos(alimento2, porciones_restantes)
                    
                    # Limitar también el segundo alimento
                    if gramos_alimento2 > max_gramos_por_alimento:
                        gramos_alimento2 = max_gramos_por_alimento
                        # Recalcular porciones
                        if alimento2.get('porciones_intercambio'):
                            porciones_alimento2 = (gramos_alimento2 / 100.0) * alimento2['porciones_intercambio']
                        else:
                            porciones_alimento2 = gramos_alimento2 / 100.0
                        porciones_restantes = porciones_restantes - porciones_alimento2
                    else:
                        porciones_alimento2 = porciones_restantes
                        porciones_restantes = 0
                    
                    sugerencias.append({
                        'ingrediente': alimento2,
                        'cantidad_sugerida': round(gramos_alimento2, 1),
                        'porciones_intercambio': porciones_alimento2,
                        'unidad': 'g',
                        'motivo': f'{grupo} (complemento) - día {dia}'
                    })
        
        return porciones_restantes
    
    def _sugerir_desayuno_variado(self, grupos: Dict, dia: int, perfil: PerfilPaciente = None, metas: MetaNutricional = None, alimentos_usados: Dict = None, max_repeticiones: int = 3, dias_minimos_entre_repeticiones: int = 2, max_repeticiones_proteinas: int = 2, dias_minimos_entre_proteinas: int = 3) -> List[Dict]:
        """Sugiere alimentos variados para el desayuno según el día y perfil del paciente usando porciones de intercambio"""
        sugerencias = []
        
        # Calcular porciones necesarias para esta comida
        porciones_comida = self._calcular_porciones_para_comida('des', metas, perfil) if metas else {}
        
        # Calcular perfil alimentario
        perfil_alimentario = self._calcular_perfil_alimentario_paciente(perfil) if perfil else {}
        
        # Usar perfil del paciente para personalizar selección con factor único por paciente
        # Mejorar aleatoriedad usando hash más robusto para variar entre generaciones
        if perfil:
            import time
            import hashlib
            timestamp_factor = int(time.time()) % 1000  # Usar más dígitos para más variación
            
            # Crear un hash único combinando múltiples características + timestamp
            datos_hash = f"{perfil.paciente_id}_{perfil.edad}_{perfil.peso}_{perfil.imc}_{dia}_{timestamp_factor}"
            hash_obj = hashlib.md5(datos_hash.encode())
            hash_int = int(hash_obj.hexdigest()[:8], 16)  # Primeros 8 caracteres del hash
            
            # Crear un "ID de perfil alimentario" único combinando múltiples características
            perfil_id = (
                (perfil.paciente_id % 13) * 7 +
                (int(perfil.edad) % 11) * 5 +
                (int(perfil.peso * 10) % 17) * 3 +
                (int(perfil.imc * 10) % 19) * 2 +
                (int((perfil.hba1c or 0) * 10) % 23) +
                (int((perfil.glucosa_ayunas or 0)) % 29) +
                (dia % 7) * 4 +
                (hash_int % 100)  # Usar hash en lugar de timestamp simple
            ) % 1000
            
            factor_variedad = perfil_id % 50
        else:
            import time
            import hashlib
            timestamp_factor = int(time.time()) % 1000
            datos_hash = f"{dia}_{timestamp_factor}"
            hash_int = int(hashlib.md5(datos_hash.encode()).hexdigest()[:8], 16)
            factor_variedad = (dia % 7) + (hash_int % 50)
        
        # Para desayuno: seleccionar alimentos apropiados y con bajo IG
        # Priorizar cereales integrales, lácteos bajos en grasa, frutas con bajo IG
        
        # 1. Cereales integrales: priorizar los con tags "desayuno" o "pan", luego por IG
        if grupos.get('GRUPO1_CEREALES'):
            # Separar cereales con tags de desayuno/pan
            cereales_desayuno = []
            cereales_otros = []
            
            for c in grupos['GRUPO1_CEREALES']:
                tags = c.get('tags', [])
                if isinstance(tags, str):
                    try:
                        import json
                        tags = json.loads(tags) if tags else []
                    except:
                        tags = []
                
                # Verificar si tiene tags relacionados con desayuno
                tags_lower = [str(t).lower() for t in tags] if isinstance(tags, list) else []
                nombre_lower = str(c.get('nombre', '')).lower()
                
                if any(tag in ['desayuno', 'pan', 'breakfast'] for tag in tags_lower) or 'pan' in nombre_lower:
                    cereales_desayuno.append(c)
                else:
                    cereales_otros.append(c)
            
            # Priorizar cereales de desayuno, pero mantener variedad
            if cereales_desayuno and (factor_variedad % 3 != 0):  # 2 de cada 3 veces usar cereales de desayuno
                cereales_prioritarios = cereales_desayuno
            else:
                # Combinar ambos grupos, priorizando los de desayuno
                cereales_prioritarios = cereales_desayuno + cereales_otros
            
            if not cereales_prioritarios:
                cereales_prioritarios = grupos['GRUPO1_CEREALES']
            
            # Ordenar por IG (menor primero) y fibra (mayor primero)
            cereales_ordenados = sorted(
                cereales_prioritarios,
                key=lambda x: (x.get('ig', 100) or 100, -(x.get('fibra', 0) or 0))
            )
            cereal_idx = factor_variedad % len(cereales_ordenados)
            cereal = cereales_ordenados[cereal_idx]
            porciones_cereal = porciones_comida.get('GRUPO1_CEREALES', 1.0)
            if porciones_cereal > 0:
                gramos_cereal = self._convertir_porciones_a_gramos(cereal, porciones_cereal)
                sugerencias.append({
                    'ingrediente': cereal,
                    'cantidad_sugerida': gramos_cereal,
                    'porciones_intercambio': porciones_cereal,
                    'unidad': 'g',
                    'motivo': f'Cereal integral (IG bajo) - día {dia}'
                })
        
        # 2. Lácteos bajos en grasa: priorizar descremados
        if grupos.get('GRUPO4_LACTEOS'):
            # Filtrar lácteos bajos en grasa si es posible
            lacteos_bajos_grasa = [l for l in grupos['GRUPO4_LACTEOS'] 
                                  if l.get('fat', 0) and l.get('fat', 0) < 5]
            lacteos_disponibles = lacteos_bajos_grasa if lacteos_bajos_grasa else grupos['GRUPO4_LACTEOS']
            
            # Filtrar por repetición
            lacteos_filtrados = self._filtrar_alimentos_por_repeticion(
                lacteos_disponibles, alimentos_usados or {}, dia, max_repeticiones, dias_minimos_entre_repeticiones
            )
            if not lacteos_filtrados:
                lacteos_filtrados = lacteos_disponibles
            
            porciones_lacteo = porciones_comida.get('GRUPO4_LACTEOS', 0.5)
            if porciones_lacteo > 0:
                # Usar función que limita cantidad y agrega segundo alimento si es necesario
                self._agregar_alimento_con_limite(
                    'GRUPO4_LACTEOS', lacteos_filtrados, porciones_lacteo,
                    sugerencias, alimentos_usados, dia, factor_variedad + 1,
                    max_repeticiones, dias_minimos_entre_repeticiones, perfil_alimentario
                )
        
        # 3. Frutas: priorizar las de menor IG y limitar a máximo 100g por comida
        if grupos.get('GRUPO3_FRUTAS'):
            # Ordenar por IG (menor primero) y fibra (mayor primero)
            frutas_ordenadas = sorted(
                grupos['GRUPO3_FRUTAS'],
                key=lambda x: (x.get('ig', 100) or 100, -(x.get('fibra', 0) or 0))
            )
            
            # Filtrar por repetición
            frutas_filtradas = self._filtrar_alimentos_por_repeticion(
                frutas_ordenadas, alimentos_usados or {}, dia, max_repeticiones, dias_minimos_entre_repeticiones
            )
            if not frutas_filtradas:
                frutas_filtradas = frutas_ordenadas
            
            porciones_fruta = porciones_comida.get('GRUPO3_FRUTAS', 1.0)
            if porciones_fruta > 0:
                # Usar función que limita cantidad y agrega segundo alimento si es necesario
                self._agregar_alimento_con_limite(
                    'GRUPO3_FRUTAS', frutas_filtradas, porciones_fruta,
                    sugerencias, alimentos_usados, dia, factor_variedad + 2,
                    max_repeticiones, dias_minimos_entre_repeticiones, perfil_alimentario
                )
        
        # 4. Verduras: agregar verduras al desayuno para aumentar fibra
        if grupos.get('GRUPO2_VERDURAS'):
            # Filtrar por repetición
            verduras_filtradas = self._filtrar_alimentos_por_repeticion(
                grupos['GRUPO2_VERDURAS'], alimentos_usados or {}, dia, max_repeticiones, dias_minimos_entre_repeticiones
            )
            if not verduras_filtradas:
                verduras_filtradas = grupos['GRUPO2_VERDURAS']
            porciones_verdura = porciones_comida.get('GRUPO2_VERDURAS', 0.5)
            if porciones_verdura > 0:
                # Ajustar porciones según perfil alimentario (más verduras si se requiere)
                factor_verduras = perfil_alimentario.get('priorizar_verduras', 1.0)
                porciones_verdura = porciones_verdura * factor_verduras
                
                # Usar función que limita cantidad y agrega segundo alimento si es necesario
                self._agregar_alimento_con_limite(
                    'GRUPO2_VERDURAS', verduras_filtradas, porciones_verdura,
                    sugerencias, alimentos_usados, dia, factor_variedad + 4,
                    max_repeticiones, dias_minimos_entre_repeticiones, perfil_alimentario
                )
        
        # 5. Grasas saludables: usar porciones calculadas o valor por defecto mejorado
        if grupos.get('GRUPO7_GRASAS'):
            # Priorizar aceites y grasas saludables
            grasas_ordenadas = sorted(
                grupos['GRUPO7_GRASAS'],
                key=lambda x: x.get('nombre', '')
            )
            # Filtrar por repetición
            grasas_filtradas = self._filtrar_alimentos_por_repeticion(
                grasas_ordenadas, alimentos_usados or {}, dia, max_repeticiones, dias_minimos_entre_repeticiones
            )
            if not grasas_filtradas:
                grasas_filtradas = grasas_ordenadas
            grasa_idx = (factor_variedad + 3) % len(grasas_filtradas)
            grasa = grasas_filtradas[grasa_idx]
            # Usar porciones calculadas si están disponibles, sino usar valor por defecto mejorado
            porciones_grasa = porciones_comida.get('GRUPO7_GRASAS')
            if porciones_grasa is None or porciones_grasa == 0:
                # Si no se calculó, usar valor por defecto basado en necesidades del desayuno
                # Desayuno necesita ~15% de calorías en grasas = 0.8 porciones
                porciones_grasa = 0.8
            if porciones_grasa > 0:
                gramos_grasa = self._convertir_porciones_a_gramos(grasa, porciones_grasa)
                sugerencias.append({
                    'ingrediente': grasa,
                    'cantidad_sugerida': gramos_grasa,
                    'porciones_intercambio': porciones_grasa,
                    'unidad': 'g',
                    'motivo': f'Grasa saludable - día {dia} ({porciones_grasa} porciones)'
                })
        
        # NO incluir carnes en desayuno (no es típico para desayuno)
        
        return sugerencias

    def _sugerir_merienda(self, grupos: Dict) -> List[Dict]:
        """Sugiere alimentos para meriendas"""
        sugerencias = []
        
        # Fruta o lácteo
        if grupos['GRUPO3_FRUTAS']:
            fruta = grupos['GRUPO3_FRUTAS'][0]
            sugerencias.append({
                'ingrediente': fruta,
                'cantidad_sugerida': 80,
                'unidad': 'g',
                'motivo': 'Fruta para control glucémico'
            })
        
        return sugerencias
    
    def _sugerir_merienda_variada(self, grupos: Dict, dia: int, perfil: PerfilPaciente = None, metas: MetaNutricional = None, alimentos_usados: Dict = None, max_repeticiones: int = 3, dias_minimos_entre_repeticiones: int = 2, max_repeticiones_proteinas: int = 2, dias_minimos_entre_proteinas: int = 3) -> List[Dict]:
        """Sugiere alimentos variados para meriendas según el día usando porciones de intercambio"""
        sugerencias = []
        
        # Calcular perfil alimentario
        perfil_alimentario = self._calcular_perfil_alimentario_paciente(perfil) if perfil else {}
        max_frutas_por_dia = perfil_alimentario.get('max_frutas_por_dia', 3)
        
        # Calcular porciones necesarias (usar 'mm' para media mañana, 'mt' para media tarde)
        tiempo = 'mm' if dia % 2 == 0 else 'mt'
        porciones_comida = self._calcular_porciones_para_comida(tiempo, metas, perfil) if metas else {}
        
        # Contar frutas usadas hoy
        frutas_usadas_hoy = sum(1 for nombre, dias in (alimentos_usados or {}).items() 
                               if any(d == dia for d in dias) and 
                               any(f.get('nombre', '') == nombre for f in grupos.get('GRUPO3_FRUTAS', [])))
        
        # Alternar entre fruta y lácteo según el día, pero respetar máximo de frutas
        if dia % 2 == 0 and grupos.get('GRUPO3_FRUTAS') and frutas_usadas_hoy < max_frutas_por_dia:
            # Filtrar por repetición
            frutas_filtradas = self._filtrar_alimentos_por_repeticion(
                grupos['GRUPO3_FRUTAS'], alimentos_usados or {}, dia, max_repeticiones, dias_minimos_entre_repeticiones
            )
            if not frutas_filtradas:
                frutas_filtradas = grupos['GRUPO3_FRUTAS']
            fruta_idx = (dia + 3) % len(frutas_filtradas)
            fruta = frutas_filtradas[fruta_idx]
            porciones_fruta = porciones_comida.get('GRUPO3_FRUTAS', 1.0)
            gramos_fruta = self._convertir_porciones_a_gramos(fruta, porciones_fruta)
            # Limitar a máximo 100g por comida para mejor control glucémico
            if gramos_fruta > 100:
                gramos_fruta = 100
                # Recalcular porciones basándose en los gramos limitados
                if fruta.get('porciones_intercambio'):
                    porciones_fruta = (gramos_fruta / 100.0) * fruta['porciones_intercambio']
                else:
                    porciones_fruta = 1.0
            sugerencias.append({
                'ingrediente': fruta,
                'cantidad_sugerida': gramos_fruta,
                'porciones_intercambio': porciones_fruta,
                'unidad': 'g',
                'motivo': f'Fruta variada - día {dia} ({porciones_fruta} porciones)'
            })
        elif grupos.get('GRUPO4_LACTEOS'):
            # Filtrar por repetición
            lacteos_filtrados = self._filtrar_alimentos_por_repeticion(
                grupos['GRUPO4_LACTEOS'], alimentos_usados or {}, dia, max_repeticiones, dias_minimos_entre_repeticiones
            )
            if not lacteos_filtrados:
                lacteos_filtrados = grupos['GRUPO4_LACTEOS']
            lacteo_idx = (dia + 1) % len(lacteos_filtrados)
            lacteo = lacteos_filtrados[lacteo_idx]
            porciones_lacteo = porciones_comida.get('GRUPO4_LACTEOS', 1.0)
            gramos_lacteo = self._convertir_porciones_a_gramos(lacteo, porciones_lacteo)
            sugerencias.append({
                'ingrediente': lacteo,
                'cantidad_sugerida': gramos_lacteo,
                'porciones_intercambio': porciones_lacteo,
                'unidad': 'g',
                'motivo': f'Lácteo variado - día {dia} ({porciones_lacteo} porciones)'
            })
        
        # Agregar verduras a las meriendas para aumentar fibra y volumen
        if grupos.get('GRUPO2_VERDURAS'):
            # Filtrar por repetición
            verduras_filtradas = self._filtrar_alimentos_por_repeticion(
                grupos['GRUPO2_VERDURAS'], alimentos_usados or {}, dia, max_repeticiones, dias_minimos_entre_repeticiones
            )
            if not verduras_filtradas:
                verduras_filtradas = grupos['GRUPO2_VERDURAS']
            verdura_idx = (dia + 2) % len(verduras_filtradas)
            verdura = verduras_filtradas[verdura_idx]
            porciones_verdura = porciones_comida.get('GRUPO2_VERDURAS', 0.5)
            if porciones_verdura > 0:
                gramos_verdura = self._convertir_porciones_a_gramos(verdura, porciones_verdura)
                sugerencias.append({
                    'ingrediente': verdura,
                    'cantidad_sugerida': gramos_verdura,
                    'porciones_intercambio': porciones_verdura,
                    'unidad': 'g',
                    'motivo': f'Verdura para fibra - día {dia}'
                })
        
        return sugerencias

    def _sugerir_almuerzo(self, grupos: Dict) -> List[Dict]:
        """Sugiere alimentos para el almuerzo"""
        sugerencias = []
        
        # Proteína principal
        if grupos['GRUPO5_CARNES']:
            proteina = grupos['GRUPO5_CARNES'][0]
            sugerencias.append({
                'ingrediente': proteina,
                'cantidad_sugerida': 120,
                'unidad': 'g',
                'motivo': 'Proteína magra'
            })
        
        # Cereal integral
        if grupos['GRUPO1_CEREALES']:
            cereal = grupos['GRUPO1_CEREALES'][0]
            sugerencias.append({
                'ingrediente': cereal,
                'cantidad_sugerida': 60,
                'unidad': 'g',
                'motivo': 'Carbohidrato complejo'
            })
        
        # Verduras
        if grupos['GRUPO2_VERDURAS']:
            verdura = grupos['GRUPO2_VERDURAS'][0]
            sugerencias.append({
                'ingrediente': verdura,
                'cantidad_sugerida': 150,
                'unidad': 'g',
                'motivo': 'Verduras con fibra'
            })
        
        return sugerencias
    
    def _sugerir_almuerzo_variado(self, grupos: Dict, dia: int, perfil: PerfilPaciente = None, metas: MetaNutricional = None, alimentos_usados: Dict = None, max_repeticiones: int = 3, dias_minimos_entre_repeticiones: int = 2, max_repeticiones_proteinas: int = 2, dias_minimos_entre_proteinas: int = 3) -> List[Dict]:
        """Sugiere alimentos variados para el almuerzo según el día usando porciones de intercambio"""
        sugerencias = []
        
        # Calcular porciones necesarias para esta comida
        porciones_comida = self._calcular_porciones_para_comida('alm', metas, perfil) if metas else {}
        
        # Calcular perfil alimentario
        perfil_alimentario = self._calcular_perfil_alimentario_paciente(perfil) if perfil else {}
        
        # Mejorar factor de variedad usando hash más robusto
        if perfil:
            import time
            import hashlib
            timestamp_factor = int(time.time()) % 1000
            datos_hash = f"{perfil.paciente_id}_{perfil.edad}_{perfil.peso}_{perfil.imc}_{dia}_{timestamp_factor}_alm"
            hash_int = int(hashlib.md5(datos_hash.encode()).hexdigest()[:8], 16)
            perfil_id = (
                (perfil.paciente_id % 13) * 7 +
                (int(perfil.edad) % 11) * 5 +
                (int(perfil.peso * 10) % 17) * 3 +
                (int(perfil.imc * 10) % 19) * 2 +
                (int((perfil.hba1c or 0) * 10) % 23) +
                (int((perfil.glucosa_ayunas or 0)) % 29) +
                (dia % 7) * 4 +
                (hash_int % 100)
            ) % 1000
            factor_variedad = perfil_id % 50
        else:
            import time
            import hashlib
            timestamp_factor = int(time.time()) % 1000
            datos_hash = f"{dia}_{timestamp_factor}_alm"
            hash_int = int(hashlib.md5(datos_hash.encode()).hexdigest()[:8], 16)
            factor_variedad = (dia % 7) + (hash_int % 50)
        
        # Rotar proteínas según el día, priorizando según perfil del paciente
        if grupos.get('GRUPO5_CARNES'):
            # Separar pescados de otras carnes si el perfil lo requiere
            if perfil_alimentario.get('priorizar_pescado', 1.0) > 1.0:
                # Priorizar pescados
                pescados = [p for p in grupos['GRUPO5_CARNES'] 
                           if any(palabra in p.get('nombre', '').lower() 
                                 for palabra in ['sardina', 'atún', 'salmón', 'trucha', 'pescado', 'camarón', 'marisco'])]
                otras_carnes = [p for p in grupos['GRUPO5_CARNES'] if p not in pescados]
                
                # Si hay pescados, priorizarlos (70% de las veces)
                if pescados and (factor_variedad % 10 < 7):
                    proteinas_disponibles = pescados + otras_carnes
                else:
                    proteinas_disponibles = grupos['GRUPO5_CARNES']
            elif perfil_alimentario.get('evitar_carnes_rojas', False):
                # Evitar carnes rojas (res, cerdo)
                proteinas_disponibles = [p for p in grupos['GRUPO5_CARNES']
                                         if not any(palabra in p.get('nombre', '').lower() 
                                                   for palabra in ['res', 'cerdo', 'carne de res', 'carne de cerdo'])]
                if not proteinas_disponibles:
                    proteinas_disponibles = grupos['GRUPO5_CARNES']
            else:
                proteinas_disponibles = grupos['GRUPO5_CARNES']
            
            # Filtrar por repetición (reglas más estrictas para proteínas)
            proteinas_filtradas = self._filtrar_alimentos_por_repeticion(
                proteinas_disponibles, alimentos_usados or {}, dia, max_repeticiones, dias_minimos_entre_repeticiones,
                grupo_alimento='GRUPO5_CARNES', max_repeticiones_proteinas=max_repeticiones_proteinas, dias_minimos_entre_proteinas=dias_minimos_entre_proteinas
            )
            if not proteinas_filtradas:
                proteinas_filtradas = proteinas_disponibles
            
            porciones_proteina = porciones_comida.get('GRUPO5_CARNES', 1.5)
            if porciones_proteina > 0:
                # Usar función que limita cantidad y agrega segundo alimento si es necesario
                self._agregar_alimento_con_limite(
                    'GRUPO5_CARNES', proteinas_filtradas, porciones_proteina,
                    sugerencias, alimentos_usados, dia, factor_variedad + 2,
                    max_repeticiones, dias_minimos_entre_repeticiones, perfil_alimentario
                )
        
        # Rotar cereales según el día
        if grupos.get('GRUPO1_CEREALES'):
            # Filtrar por repetición
            cereales_filtrados = self._filtrar_alimentos_por_repeticion(
                grupos['GRUPO1_CEREALES'], alimentos_usados or {}, dia, max_repeticiones, dias_minimos_entre_repeticiones
            )
            if not cereales_filtrados:
                cereales_filtrados = grupos['GRUPO1_CEREALES']
            
            porciones_cereal = porciones_comida.get('GRUPO1_CEREALES', 2.0)
            if porciones_cereal > 0:
                # Usar función que limita cantidad y agrega segundo alimento si es necesario
                self._agregar_alimento_con_limite(
                    'GRUPO1_CEREALES', cereales_filtrados, porciones_cereal,
                    sugerencias, alimentos_usados, dia, factor_variedad + 1,
                    max_repeticiones, dias_minimos_entre_repeticiones, perfil_alimentario
                )
        
        # Rotar verduras según el día
        if grupos.get('GRUPO2_VERDURAS'):
            # Filtrar por repetición
            verduras_filtradas = self._filtrar_alimentos_por_repeticion(
                grupos['GRUPO2_VERDURAS'], alimentos_usados or {}, dia, max_repeticiones, dias_minimos_entre_repeticiones
            )
            if not verduras_filtradas:
                verduras_filtradas = grupos['GRUPO2_VERDURAS']
            
            porciones_verdura = porciones_comida.get('GRUPO2_VERDURAS', 1.5)
            # Ajustar porciones según perfil alimentario
            factor_verduras = perfil_alimentario.get('priorizar_verduras', 1.0)
            porciones_verdura = porciones_verdura * factor_verduras
            
            if porciones_verdura > 0:
                # Usar función que limita cantidad y agrega segundo alimento si es necesario
                self._agregar_alimento_con_limite(
                    'GRUPO2_VERDURAS', verduras_filtradas, porciones_verdura,
                    sugerencias, alimentos_usados, dia, factor_variedad + 3,
                    max_repeticiones, dias_minimos_entre_repeticiones, perfil_alimentario
                )
        
        # Grasas: usar porciones calculadas o valor por defecto mejorado
        if grupos.get('GRUPO7_GRASAS'):
            # Filtrar por repetición
            grasas_filtradas = self._filtrar_alimentos_por_repeticion(
                grupos['GRUPO7_GRASAS'], alimentos_usados or {}, dia, max_repeticiones, dias_minimos_entre_repeticiones
            )
            if not grasas_filtradas:
                grasas_filtradas = grupos['GRUPO7_GRASAS']
            
            # Usar porciones calculadas si están disponibles, sino usar valor por defecto mejorado
            porciones_grasa = porciones_comida.get('GRUPO7_GRASAS')
            if porciones_grasa is None or porciones_grasa == 0:
                # Si no se calculó, usar valor por defecto basado en necesidades del almuerzo
                # Almuerzo necesita ~25% de calorías en grasas = 1.5 porciones
                porciones_grasa = 1.5
            if porciones_grasa > 0:
                # Usar función que limita cantidad y agrega segundo alimento si es necesario
                self._agregar_alimento_con_limite(
                    'GRUPO7_GRASAS', grasas_filtradas, porciones_grasa,
                    sugerencias, alimentos_usados, dia, factor_variedad + 4,
                    max_repeticiones, dias_minimos_entre_repeticiones, perfil_alimentario
                )
        
        return sugerencias

    def _sugerir_cena(self, grupos: Dict) -> List[Dict]:
        """Sugiere alimentos para la cena"""
        sugerencias = []
        
        # Proteína ligera
        if grupos['GRUPO5_CARNES']:
            proteina = grupos['GRUPO5_CARNES'][0]
            sugerencias.append({
                'ingrediente': proteina,
                'cantidad_sugerida': 100,
                'unidad': 'g',
                'motivo': 'Proteína para la noche'
            })
        
        # Verduras
        if grupos['GRUPO2_VERDURAS']:
            verdura = grupos['GRUPO2_VERDURAS'][0]
            sugerencias.append({
                'ingrediente': verdura,
                'cantidad_sugerida': 120,
                'unidad': 'g',
                'motivo': 'Verduras cocidas'
            })
        
        return sugerencias
    
    def _sugerir_cena_variada(self, grupos: Dict, dia: int, perfil: PerfilPaciente = None, metas: MetaNutricional = None, alimentos_usados: Dict = None, max_repeticiones: int = 3, dias_minimos_entre_repeticiones: int = 2, max_repeticiones_proteinas: int = 2, dias_minimos_entre_proteinas: int = 3) -> List[Dict]:
        """Sugiere alimentos variados para la cena según el día usando porciones de intercambio"""
        sugerencias = []
        
        # Calcular porciones necesarias para esta comida
        porciones_comida = self._calcular_porciones_para_comida('cena', metas, perfil) if metas else {}
        
        # Calcular perfil alimentario
        perfil_alimentario = self._calcular_perfil_alimentario_paciente(perfil) if perfil else {}
        
        # Mejorar factor de variedad usando hash más robusto
        if perfil:
            import time
            import hashlib
            timestamp_factor = int(time.time()) % 1000
            datos_hash = f"{perfil.paciente_id}_{perfil.edad}_{perfil.peso}_{perfil.imc}_{dia}_{timestamp_factor}_cena"
            hash_int = int(hashlib.md5(datos_hash.encode()).hexdigest()[:8], 16)
            perfil_id = (
                (perfil.paciente_id % 13) * 7 +
                (int(perfil.edad) % 11) * 5 +
                (int(perfil.peso * 10) % 17) * 3 +
                (int(perfil.imc * 10) % 19) * 2 +
                (int((perfil.hba1c or 0) * 10) % 23) +
                (int((perfil.glucosa_ayunas or 0)) % 29) +
                (dia % 7) * 4 +
                (hash_int % 100)
            ) % 1000
            factor_variedad = perfil_id % 50
        else:
            import time
            import hashlib
            timestamp_factor = int(time.time()) % 1000
            datos_hash = f"{dia}_{timestamp_factor}_cena"
            hash_int = int(hashlib.md5(datos_hash.encode()).hexdigest()[:8], 16)
            factor_variedad = (dia % 7) + (hash_int % 50)
        
        # Rotar proteínas según el día, priorizando según perfil del paciente
        if grupos.get('GRUPO5_CARNES'):
            # Separar pescados de otras carnes si el perfil lo requiere
            if perfil_alimentario.get('priorizar_pescado', 1.0) > 1.0:
                # Priorizar pescados
                pescados = [p for p in grupos['GRUPO5_CARNES'] 
                           if any(palabra in p.get('nombre', '').lower() 
                                 for palabra in ['sardina', 'atún', 'salmón', 'trucha', 'pescado', 'camarón', 'marisco'])]
                otras_carnes = [p for p in grupos['GRUPO5_CARNES'] if p not in pescados]
                
                # Si hay pescados, priorizarlos (70% de las veces)
                if pescados and (factor_variedad % 10 < 7):
                    proteinas_disponibles = pescados + otras_carnes
                else:
                    proteinas_disponibles = grupos['GRUPO5_CARNES']
            elif perfil_alimentario.get('evitar_carnes_rojas', False):
                # Evitar carnes rojas (res, cerdo)
                proteinas_disponibles = [p for p in grupos['GRUPO5_CARNES']
                                         if not any(palabra in p.get('nombre', '').lower() 
                                                   for palabra in ['res', 'cerdo', 'carne de res', 'carne de cerdo'])]
                if not proteinas_disponibles:
                    proteinas_disponibles = grupos['GRUPO5_CARNES']
            else:
                proteinas_disponibles = grupos['GRUPO5_CARNES']
            
            # Filtrar por repetición (reglas más estrictas para proteínas)
            proteinas_filtradas = self._filtrar_alimentos_por_repeticion(
                proteinas_disponibles, alimentos_usados or {}, dia, max_repeticiones, dias_minimos_entre_repeticiones,
                grupo_alimento='GRUPO5_CARNES', max_repeticiones_proteinas=max_repeticiones_proteinas, dias_minimos_entre_proteinas=dias_minimos_entre_proteinas
            )
            if not proteinas_filtradas:
                proteinas_filtradas = proteinas_disponibles
            
            porciones_proteina = porciones_comida.get('GRUPO5_CARNES', 1.0)
            if porciones_proteina > 0:
                # Usar función que limita cantidad y agrega segundo alimento si es necesario
                self._agregar_alimento_con_limite(
                    'GRUPO5_CARNES', proteinas_filtradas, porciones_proteina,
                    sugerencias, alimentos_usados, dia, factor_variedad + 4,
                    max_repeticiones, dias_minimos_entre_repeticiones, perfil_alimentario
                )
        
        # Rotar verduras según el día, aumentando cantidad si el perfil lo requiere
        if grupos.get('GRUPO2_VERDURAS'):
            factor_verduras = perfil_alimentario.get('priorizar_verduras', 1.0)
            
            # Filtrar por repetición
            verduras_filtradas = self._filtrar_alimentos_por_repeticion(
                grupos['GRUPO2_VERDURAS'], alimentos_usados or {}, dia, max_repeticiones, dias_minimos_entre_repeticiones
            )
            if not verduras_filtradas:
                verduras_filtradas = grupos['GRUPO2_VERDURAS']
            
            porciones_verdura = porciones_comida.get('GRUPO2_VERDURAS', 1.5)
            
            # Aumentar porciones si el perfil requiere más verduras
            porciones_verdura = porciones_verdura * factor_verduras
            
            if porciones_verdura > 0:
                # Usar función que limita cantidad y agrega segundo alimento si es necesario
                self._agregar_alimento_con_limite(
                    'GRUPO2_VERDURAS', verduras_filtradas, porciones_verdura,
                    sugerencias, alimentos_usados, dia, factor_variedad + 5,
                    max_repeticiones, dias_minimos_entre_repeticiones, perfil_alimentario
                )
        
        # Grasas: usar porciones calculadas o valor por defecto mejorado
        if grupos.get('GRUPO7_GRASAS'):
            # Filtrar por repetición
            grasas_filtradas = self._filtrar_alimentos_por_repeticion(
                grupos['GRUPO7_GRASAS'], alimentos_usados or {}, dia, max_repeticiones, dias_minimos_entre_repeticiones
            )
            if not grasas_filtradas:
                grasas_filtradas = grupos['GRUPO7_GRASAS']
            
            # Usar porciones calculadas si están disponibles, sino usar valor por defecto mejorado
            porciones_grasa = porciones_comida.get('GRUPO7_GRASAS')
            if porciones_grasa is None or porciones_grasa == 0:
                # Si no se calculó, usar valor por defecto basado en necesidades de la cena
                # Cena necesita ~25% de calorías en grasas = 1.2 porciones
                porciones_grasa = 1.2
            if porciones_grasa > 0:
                # Usar función que limita cantidad y agrega segundo alimento si es necesario
                self._agregar_alimento_con_limite(
                    'GRUPO7_GRASAS', grasas_filtradas, porciones_grasa,
                    sugerencias, alimentos_usados, dia, factor_variedad + 6,
                    max_repeticiones, dias_minimos_entre_repeticiones, perfil_alimentario
                )
        
        # Agregar cereales a la cena si no se alcanzan las calorías objetivo
        # Filtrar solo cereales con IG bajo (< 55) para mejor control glucémico nocturno
        if grupos.get('GRUPO1_CEREALES'):
            # Filtrar cereales con IG < 55 para cenas
            cereales_bajo_ig = [
                c for c in grupos['GRUPO1_CEREALES']
                if (c.get('ig') or 100) < 55
            ]
            # Si no hay cereales con IG bajo, usar los disponibles pero priorizar los de menor IG
            if not cereales_bajo_ig:
                cereales_bajo_ig = sorted(
                    grupos['GRUPO1_CEREALES'],
                    key=lambda x: (x.get('ig', 100) or 100)
                )[:3]  # Tomar los 3 con menor IG
            
            if cereales_bajo_ig:
                # Filtrar por repetición
                cereales_filtrados = self._filtrar_alimentos_por_repeticion(
                    cereales_bajo_ig, alimentos_usados or {}, dia, max_repeticiones, dias_minimos_entre_repeticiones
                )
                if not cereales_filtrados:
                    cereales_filtrados = cereales_bajo_ig
                
                porciones_cereal = porciones_comida.get('GRUPO1_CEREALES', 0.5)
                if porciones_cereal > 0:
                    # Usar función que limita cantidad y agrega segundo alimento si es necesario
                    self._agregar_alimento_con_limite(
                        'GRUPO1_CEREALES', cereales_filtrados, porciones_cereal,
                        sugerencias, alimentos_usados, dia, factor_variedad + 7,
                        max_repeticiones, dias_minimos_entre_repeticiones, perfil_alimentario
                    )
        
        return sugerencias

    def _generar_recomendaciones_especiales(self, perfil: PerfilPaciente) -> List[str]:
        """Genera recomendaciones especiales basadas en el perfil"""
        recomendaciones = []
        
        # Recomendaciones por HbA1c
        if perfil.hba1c:
            if perfil.hba1c > 8.0:
                recomendaciones.append("HbA1c elevado: Reducir carbohidratos simples y aumentar fibra")
            elif perfil.hba1c < 6.5:
                recomendaciones.append("Excelente control glucémico: Mantener hábitos actuales")
        
        # Recomendaciones por presión arterial
        if perfil.pa_sis and perfil.pa_sis > 140:
            recomendaciones.append("Presión arterial elevada: Reducir sodio a máximo 1500mg/día")
        
        # Recomendaciones por LDL
        if perfil.ldl and perfil.ldl > 100:
            recomendaciones.append("LDL elevado: Preferir grasas insaturadas y aumentar fibra")
        
        # Recomendaciones por IMC
        if perfil.imc > 30:
            recomendaciones.append("Obesidad: Enfoque en déficit calórico moderado")
        elif perfil.imc < 18.5:
            recomendaciones.append("Bajo peso: Asegurar ingesta calórica adecuada")
        
        # Recomendaciones por medicamentos
        if perfil.medicamentos:
            for med in perfil.medicamentos:
                if 'metformina' in med.lower():
                    recomendaciones.append("Con metformina: Asegurar ingesta de vitamina B12")
                elif 'insulina' in med.lower():
                    recomendaciones.append("Con insulina: Monitorear carbohidratos por comida")
        
        return recomendaciones

    def _generar_lista_compras(self, plan_semanal: Dict) -> List[Dict]:
        """Genera una lista de compras basada en el plan semanal"""
        ingredientes_totales = {}
        
        # Recopilar todos los ingredientes del plan semanal
        for dia, comidas_dia in plan_semanal.items():
            for tiempo, comida in comidas_dia.items():
                for alimento in comida['alimentos']:
                    nombre = alimento['nombre']
                    cantidad = alimento['cantidad']
                    unidad = alimento['unidad']
                    
                    if nombre in ingredientes_totales:
                        ingredientes_totales[nombre]['cantidad'] += cantidad
                    else:
                        ingredientes_totales[nombre] = {
                            'nombre': nombre,
                            'cantidad': cantidad,
                            'unidad': unidad
                        }
        
        # Convertir a lista y ordenar por nombre
        lista_compras = list(ingredientes_totales.values())
        lista_compras.sort(key=lambda x: x['nombre'])
        
        return lista_compras

    def _aplicar_filtros_metas(self, metas: MetaNutricional, filtros: Dict) -> MetaNutricional:
        """Aplica los filtros de metas nutricionales"""
        # Si se especifican calorías personalizadas
        if filtros.get('calorias_objetivo'):
            metas.calorias_diarias = filtros['calorias_objetivo']
        
        # Si se especifican porcentajes de macros personalizados
        if filtros.get('carbohidratos_porcentaje'):
            metas.carbohidratos_porcentaje = filtros['carbohidratos_porcentaje']
            metas.carbohidratos_g = int((metas.calorias_diarias * metas.carbohidratos_porcentaje / 100) / 4)
        
        if filtros.get('proteinas_porcentaje'):
            metas.proteinas_porcentaje = filtros['proteinas_porcentaje']
            metas.proteinas_g = int((metas.calorias_diarias * metas.proteinas_porcentaje / 100) / 4)
        
        if filtros.get('grasas_porcentaje'):
            metas.grasas_porcentaje = filtros['grasas_porcentaje']
            metas.grasas_g = int((metas.calorias_diarias * metas.grasas_porcentaje / 100) / 9)
        
        return metas

    def _calcular_perfil_alimentario_paciente(self, perfil: PerfilPaciente) -> Dict:
        """
        Calcula un perfil alimentario único para el paciente basado en sus características clínicas.
        Esto influye en qué tipos de alimentos se priorizan.
        """
        perfil_alimentario = {
            'priorizar_verduras': 1.0,  # Factor de priorización (1.0 = normal, >1.0 = más, <1.0 = menos)
            'priorizar_frutas': 1.0,
            'priorizar_pescado': 1.0,
            'priorizar_legumbres': 1.0,
            'priorizar_cereales_integrales': 1.0,
            'evitar_carnes_rojas': False,
            'max_frutas_por_dia': 3,  # Número máximo de porciones de fruta por día
            'min_verduras_por_dia': 4,  # Número mínimo de porciones de verdura por día
        }
        
        # Ajustar según control glucémico
        if perfil.hba1c and perfil.hba1c >= 7.0:
            # Diabetes mal controlada: más verduras, menos frutas
            perfil_alimentario['priorizar_verduras'] = 1.5
            perfil_alimentario['priorizar_frutas'] = 0.7
            perfil_alimentario['max_frutas_por_dia'] = 2
            perfil_alimentario['min_verduras_por_dia'] = 5
        elif perfil.hba1c and perfil.hba1c >= 6.5:
            # Prediabetes/diabetes temprana: moderar frutas
            perfil_alimentario['priorizar_verduras'] = 1.2
            perfil_alimentario['priorizar_frutas'] = 0.8
            perfil_alimentario['max_frutas_por_dia'] = 2
            perfil_alimentario['min_verduras_por_dia'] = 4
        
        # Ajustar según glucosa en ayunas
        if perfil.glucosa_ayunas and perfil.glucosa_ayunas >= 140:
            # Glucosa muy elevada: más verduras, menos frutas
            perfil_alimentario['priorizar_verduras'] = max(perfil_alimentario['priorizar_verduras'], 1.4)
            perfil_alimentario['priorizar_frutas'] = min(perfil_alimentario['priorizar_frutas'], 0.6)
            perfil_alimentario['max_frutas_por_dia'] = min(perfil_alimentario['max_frutas_por_dia'], 2)
        
        # Ajustar según triglicéridos
        if perfil.trigliceridos and perfil.trigliceridos >= 150:
            # Triglicéridos altos: más pescado, menos carnes rojas
            perfil_alimentario['priorizar_pescado'] = 1.5
            perfil_alimentario['evitar_carnes_rojas'] = True
        
        # Ajustar según LDL
        if perfil.ldl and perfil.ldl >= 130:
            # LDL alto: priorizar grasas insaturadas (pescado, frutos secos)
            perfil_alimentario['priorizar_pescado'] = max(perfil_alimentario['priorizar_pescado'], 1.3)
        
        # Ajustar según IMC
        if perfil.imc >= 35:
            # Obesidad severa: más verduras para volumen y saciedad
            perfil_alimentario['priorizar_verduras'] = max(perfil_alimentario['priorizar_verduras'], 1.3)
            perfil_alimentario['min_verduras_por_dia'] = max(perfil_alimentario['min_verduras_por_dia'], 5)
        elif perfil.imc >= 30:
            # Obesidad: moderar frutas
            perfil_alimentario['priorizar_verduras'] = max(perfil_alimentario['priorizar_verduras'], 1.2)
            perfil_alimentario['max_frutas_por_dia'] = min(perfil_alimentario['max_frutas_por_dia'], 3)
        
        return perfil_alimentario
    
    def obtener_ingredientes_recomendados(self, perfil: PerfilPaciente, metas: MetaNutricional, filtros: Dict = None) -> List[Dict]:
        """Obtiene ingredientes recomendados basados en el perfil del paciente y filtros"""
        
        # Calcular perfil alimentario único para este paciente
        perfil_alimentario = self._calcular_perfil_alimentario_paciente(perfil)
        
        # Usar probabilidad AJUSTADA si está disponible (calculada en calcular_metas_nutricionales)
        probabilidad_mal_control = getattr(self, '_ultima_probabilidad_ajustada', None)
        
        if probabilidad_mal_control is None:
            # Fallback: calcular probabilidad ML cruda si no hay ajustada
            probabilidad_mal_control = self.predecir_control_glucemico_ml(perfil)
            print(f"[WARN]  Usando probabilidad ML cruda en obtener_ingredientes_recomendados: {probabilidad_mal_control}")
        
        # Construir filtros SQL
        filtros_sql = ["i.activo = true"]
        params = []
        
        # Filtrar por índice glucémico (ajustado dinámicamente por ML o filtros)
        ig_max = self.PARAMETROS_DIABETES['ig_max']
        
        # Si hay filtros explícitos, usarlos (tienen prioridad)
        if filtros and filtros.get('ig_max'):
            ig_max = filtros['ig_max']
            # Validar que el IG no sea extremadamente restrictivo
            if ig_max < 10:
                print(f"ADVERTENCIA: IG máximo muy bajo ({ig_max}). Usando mínimo recomendado de 30.")
                ig_max = 30
            elif ig_max > 100:
                print(f"ADVERTENCIA: IG máximo muy alto ({ig_max}). Usando máximo recomendado de 70.")
                ig_max = 70
        # Si no hay filtros explícitos, usar predicción ML (probabilidad ajustada)
        elif probabilidad_mal_control is not None:
            if probabilidad_mal_control > 0.6:
                # Control malo: IG más restrictivo (50-55)
                ig_max = 50
                print(f"[ML] Control glucémico malo (prob={probabilidad_mal_control:.2f}), usando IG máximo restrictivo: {ig_max}")
            elif probabilidad_mal_control > 0.4:
                # Control moderado: IG intermedio (60-65)
                ig_max = 60
                print(f"[ML] Control glucémico moderado (prob={probabilidad_mal_control:.2f}), usando IG máximo intermedio: {ig_max}")
            else:
                # Control bueno: IG estándar (70)
                ig_max = self.PARAMETROS_DIABETES['ig_max']
                print(f"[ML] Control glucémico bueno (prob={probabilidad_mal_control:.2f}), usando IG máximo estándar: {ig_max}")
        
        filtros_sql.append("(i.ig IS NULL OR i.ig <= %s)")
        params.append(ig_max)
        
        # Excluir alergias
        if perfil.alergias:
            placeholders = ','.join(['%s'] * len(perfil.alergias))
            filtros_sql.append(f"i.nombre NOT IN ({placeholders})")
            params.extend(perfil.alergias)
        
        # Excluir preferencias de exclusión
        if perfil.preferencias_excluir:
            placeholders = ','.join(['%s'] * len(perfil.preferencias_excluir))
            filtros_sql.append(f"i.nombre NOT IN ({placeholders})")
            params.extend(perfil.preferencias_excluir)
        
        # Excluir grupos de alimentos si se especifican en filtros
        if filtros and filtros.get('grupos_excluir'):
            grupos_excluir = filtros['grupos_excluir']
            if grupos_excluir:
                placeholders = ','.join(['%s'] * len(grupos_excluir))
                filtros_sql.append(f"i.grupo NOT IN ({placeholders})")
                params.extend(grupos_excluir)
        
        # Incluir preferencias específicas
        preferencias_sql = ""
        if perfil.preferencias_incluir:
            placeholders = ','.join(['%s'] * len(perfil.preferencias_incluir))
            preferencias_sql = f"UNION ALL SELECT id, nombre, grupo, kcal, cho, pro, fat, fibra, ig, sodio, tags_json, porciones_intercambio, subgrupo_intercambio FROM ingrediente WHERE nombre IN ({placeholders}) AND activo = true"
            params.extend(perfil.preferencias_incluir)
        
        # Ajustar ordenamiento según predicción ML
        # Si control es malo, priorizar más fibra y menos IG
        if probabilidad_mal_control is not None and probabilidad_mal_control > 0.6:
            # Control malo: priorizar fibra alta y IG bajo
            orden_sql = """
                ORDER BY 
                    CASE i.grupo 
                        WHEN 'GRUPO2_VERDURAS' THEN 1
                        WHEN 'GRUPO5_CARNES' THEN 2
                        WHEN 'GRUPO1_CEREALES' THEN 3
                        WHEN 'GRUPO3_FRUTAS' THEN 4
                        WHEN 'GRUPO4_LACTEOS' THEN 5
                        WHEN 'GRUPO7_GRASAS' THEN 6
                        ELSE 7
                    END,
                    i.fibra DESC NULLS LAST,
                    i.ig ASC NULLS LAST,
                    i.nombre ASC
            """
        else:
            # Control bueno/moderado: ordenamiento estándar
            orden_sql = """
                ORDER BY 
                    CASE i.grupo 
                        WHEN 'GRUPO2_VERDURAS' THEN 1
                        WHEN 'GRUPO5_CARNES' THEN 2
                        WHEN 'GRUPO1_CEREALES' THEN 3
                        WHEN 'GRUPO3_FRUTAS' THEN 4
                        WHEN 'GRUPO4_LACTEOS' THEN 5
                        WHEN 'GRUPO7_GRASAS' THEN 6
                        ELSE 7
                    END,
                    i.fibra DESC,
                    i.ig ASC NULLS LAST
            """
        
        sql = f"""
            SELECT i.id, i.nombre, i.grupo, i.kcal, i.cho, i.pro, i.fat, 
                   i.fibra, i.ig, i.sodio, i.tags_json, i.porciones_intercambio, i.subgrupo_intercambio
            FROM ingrediente i
            WHERE {' AND '.join(filtros_sql)}
            {preferencias_sql}
            {orden_sql}
        """
        
        ingredientes = fetch_all(sql, tuple(params))
        
        resultado = []
        for ing in ingredientes:
            resultado.append({
                'id': ing[0],
                'nombre': ing[1],
                'grupo': ing[2],
                'kcal': float(ing[3]),
                'cho': float(ing[4]),
                'pro': float(ing[5]),
                'fat': float(ing[6]),
                'fibra': float(ing[7]),
                'ig': ing[8],
                'sodio': float(ing[9]) if ing[9] else 0,
                'tags': ing[10] or {},
                'porciones_intercambio': float(ing[11]) if len(ing) > 11 and ing[11] else None,
                'subgrupo_intercambio': ing[12] if len(ing) > 12 else None
            })
        
        # Validar que hay suficientes ingredientes
        if len(resultado) < 10:
            print(f"ADVERTENCIA: Solo {len(resultado)} ingredientes disponibles. Los filtros pueden ser muy restrictivos.")
            if len(resultado) < 5:
                raise ValueError(f"No hay suficientes ingredientes disponibles ({len(resultado)}). Los filtros son demasiado restrictivos. Intenta aumentar el límite de IG o excluir menos grupos.")
        
        # INTEGRACIÓN MODELOS ML: Filtrar y rankear usando Modelo 1 y Modelo 2
        print(f"[DEBUG] ML_AVAILABLE={ML_AVAILABLE}, len(resultado)={len(resultado)}")
        if ML_AVAILABLE and len(resultado) > 0:
            try:
                print("[ML] Aplicando modelos ML para filtrar y rankear alimentos...")
                print(f"  - Modelo 1 disponible: {self._modelo_respuesta_glucemica is not None}")
                print(f"  - Modelo 2 disponible: {self._modelo_seleccion_alimentos is not None}")
                
                # Preparar necesidades nutricionales para Modelo 2
                necesidades = {
                    'calorias': metas.calorias_diarias,
                    'carbs': metas.carbohidratos_g,
                    'protein': metas.proteinas_g,
                    'fat': metas.grasas_g
                }
                
                # Evaluar cada alimento con los modelos ML
                alimentos_evaluados = []
                for alimento in resultado:
                    # Modelo 1: Predecir respuesta glucémica
                    contexto = {
                        'tiempo_comida': 'alm',  # Por defecto, se ajustará por comida
                        'hora': 12,
                        'glucose_baseline': perfil.glucosa_ayunas if perfil.glucosa_ayunas else 100
                    }
                    
                    respuesta_glucemica = self.predecir_respuesta_glucemica(perfil, alimento, contexto)
                    
                    # Filtrar alimentos con respuesta glucémica muy alta
                    if respuesta_glucemica:
                        glucose_peak = respuesta_glucemica.get('glucose_peak', 200)
                        if glucose_peak > 180:  # Umbral de seguridad
                            print(f"  [WARN]  Excluyendo {alimento['nombre']}: pico glucémico predicho {glucose_peak:.1f} mg/dL")
                            continue
                    
                    # Modelo 2: Calcular score de idoneidad
                    score_idoneidad = self.calcular_score_idoneidad_alimento(perfil, alimento, necesidades)
                    
                    # Agregar scores al alimento
                    alimento['ml_score_idoneidad'] = score_idoneidad if score_idoneidad else 0.5
                    if respuesta_glucemica:
                        alimento['ml_glucose_peak'] = respuesta_glucemica.get('glucose_peak', 150)
                        alimento['ml_glucose_increment'] = respuesta_glucemica.get('glucose_increment', 30)
                    
                    alimentos_evaluados.append(alimento)
                
                # Ordenar por score de idoneidad (mayor a menor)
                alimentos_evaluados.sort(key=lambda x: x.get('ml_score_idoneidad', 0.5), reverse=True)
                
                print(f"[OK] {len(alimentos_evaluados)} alimentos evaluados y rankeados por ML")
                return alimentos_evaluados
                
            except Exception as e:
                print(f"[WARN]  Error al aplicar modelos ML, usando resultados sin ML: {e}")
                import traceback
                traceback.print_exc()
        
        return resultado

    def _generar_dia_completo(self, grupos: Dict, dia: int, metas: MetaNutricional, filtros: Dict = None, perfil: PerfilPaciente = None) -> Dict:
        """Genera un día completo con estructura compatible con el frontend y validaciones"""
        comidas = {}
        
        # Definir distribución de calorías por comida
        distribucion_calorias = {
            'des': metas.calorias_diarias * 0.25,  # 25%
            'mm': metas.calorias_diarias * 0.10,   # 10%
            'alm': metas.calorias_diarias * 0.35,  # 35%
            'mt': metas.calorias_diarias * 0.10,   # 10%
            'cena': metas.calorias_diarias * 0.20  # 20%
        }
        
        # Aplicar patrón de comidas si se especifica en filtros
        patron_comidas = filtros.get('patron_comidas', ['des', 'mm', 'alm', 'mt', 'cena']) if filtros else ['des', 'mm', 'alm', 'mt', 'cena']
        
        # Definir orden correcto de comidas
        orden_comidas = ['des', 'mm', 'alm', 'mt', 'cena']
        
        # Generar cada comida con variedad basada en el día en el orden correcto
        for tiempo in orden_comidas:
            if tiempo in patron_comidas:  # Solo generar comidas que están en el patrón
                calorias_objetivo = distribucion_calorias[tiempo]
                alimentos_sugeridos = self._sugerir_alimentos_tiempo_variado(tiempo, grupos, dia, perfil, metas)
                
                # Calcular totales nutricionales
                kcal_total = sum(alimento['ingrediente']['kcal'] * alimento['cantidad_sugerida'] / 100 for alimento in alimentos_sugeridos)
                cho_total = sum(alimento['ingrediente']['cho'] * alimento['cantidad_sugerida'] / 100 for alimento in alimentos_sugeridos)
                pro_total = sum(alimento['ingrediente']['pro'] * alimento['cantidad_sugerida'] / 100 for alimento in alimentos_sugeridos)
                fat_total = sum(alimento['ingrediente']['fat'] * alimento['cantidad_sugerida'] / 100 for alimento in alimentos_sugeridos)
                
                comidas[tiempo] = {
                    'kcal_total': round(kcal_total, 1),
                    'cho_total': round(cho_total, 1),
                    'pro_total': round(pro_total, 1),
                    'fat_total': round(fat_total, 1),
                    'alimentos': [
                        {
                            'nombre': alimento['ingrediente']['nombre'],
                            'grupo': alimento['ingrediente']['grupo'],
                            'cantidad': alimento['cantidad_sugerida'],
                            'unidad': alimento['unidad'],
                            'kcal': round(alimento['ingrediente']['kcal'] * alimento['cantidad_sugerida'] / 100, 1),
                            'cho': round(alimento['ingrediente']['cho'] * alimento['cantidad_sugerida'] / 100, 1),
                            'pro': round(alimento['ingrediente']['pro'] * alimento['cantidad_sugerida'] / 100, 1),
                            'fat': round(alimento['ingrediente']['fat'] * alimento['cantidad_sugerida'] / 100, 1),
                            'ig': alimento['ingrediente']['ig']
                        }
                        for alimento in alimentos_sugeridos
                    ]
                }
            else:
                # Comida no incluida en el patrón
                comidas[tiempo] = {
                    'kcal_total': 0,
                    'cho_total': 0,
                    'pro_total': 0,
                    'fat_total': 0,
                    'alimentos': []
                }
        
        return comidas

    def _calcular_validaciones_plan(self, plan_semanal: Dict, metas: MetaNutricional, filtros: Dict = None) -> Dict:
        """Calcula las validaciones de cumplimiento del plan"""
        validaciones = {}
        
        for dia, datos_dia in plan_semanal.items():
            validaciones[dia] = self._validar_dia(datos_dia, metas, filtros)
        
        return validaciones

    def _validar_dia(self, datos_dia: Dict, metas: MetaNutricional, filtros: Dict = None) -> Dict:
        """Valida el cumplimiento de un día específico"""
        totales_dia = {
            'kcal': 0,
            'cho': 0,
            'pro': 0,
            'fat': 0,
            'ig_max': 0,
            'grupos_usados': set()
        }
        
        # Calcular totales del día
        for tiempo, comida in datos_dia.items():
            totales_dia['kcal'] += comida['kcal_total']
            totales_dia['cho'] += comida['cho_total']
            totales_dia['pro'] += comida['pro_total']
            totales_dia['fat'] += comida['fat_total']
            
            for alimento in comida['alimentos']:
                if alimento['ig']:
                    totales_dia['ig_max'] = max(totales_dia['ig_max'], alimento['ig'])
                totales_dia['grupos_usados'].add(alimento['grupo'])
        
        # Validaciones
        validaciones = {
            'calorias': {
                'objetivo': metas.calorias_diarias,
                'actual': round(totales_dia['kcal'], 1),
                'cumple': abs(totales_dia['kcal'] - metas.calorias_diarias) <= metas.calorias_diarias * 0.1,  # ±10%
                'porcentaje': round((totales_dia['kcal'] / metas.calorias_diarias) * 100, 1)
            },
            'macros': {
                'cho': {
                    'objetivo': metas.carbohidratos_g,
                    'actual': round(totales_dia['cho'], 1),
                    'porcentaje': round((totales_dia['cho'] * 4 / metas.calorias_diarias) * 100, 1) if metas.calorias_diarias > 0 else 0
                },
                'pro': {
                    'objetivo': metas.proteinas_g,
                    'actual': round(totales_dia['pro'], 1),
                    'porcentaje': round((totales_dia['pro'] * 4 / metas.calorias_diarias) * 100, 1) if metas.calorias_diarias > 0 else 0
                },
                'fat': {
                    'objetivo': metas.grasas_g,
                    'actual': round(totales_dia['fat'], 1),
                    'porcentaje': round((totales_dia['fat'] * 9 / metas.calorias_diarias) * 100, 1) if metas.calorias_diarias > 0 else 0
                }
            },
            'ig': {
                'maximo': totales_dia['ig_max'],
                'limite': filtros.get('ig_max', self.PARAMETROS_DIABETES['ig_max']) if filtros else self.PARAMETROS_DIABETES['ig_max'],
                'cumple': totales_dia['ig_max'] <= (filtros.get('ig_max', self.PARAMETROS_DIABETES['ig_max']) if filtros else self.PARAMETROS_DIABETES['ig_max'])
            },
            'grupos_excluidos': {
                'grupos_usados': list(totales_dia['grupos_usados']),
                'grupos_excluir': filtros.get('grupos_excluir', []) if filtros else [],
                'cumple': len(set(totales_dia['grupos_usados']) & set(filtros.get('grupos_excluir', []))) == 0 if filtros else True
            }
        }
        
        return validaciones

    def _generar_planes_multiples(self, grupos: Dict, dias_totales: int, metas: MetaNutricional, filtros: Dict = None, perfil: PerfilPaciente = None) -> Dict:
        """Genera múltiples planes semanales según la cantidad de días solicitados"""
        
        # Usar el día de inicio del frontend si está disponible, sino usar lunes por defecto
        dia_inicio = 0  # lunes por defecto
        if filtros and 'dia_inicio' in filtros:
            dia_inicio = filtros['dia_inicio']
            print(f"DEBUG: Usando día de inicio del frontend: {dia_inicio}")
        else:
            print(f"DEBUG: Usando lunes (0) como día de inicio por defecto")
        
        print(f"DEBUG: filtros recibidos: {filtros}")
        print(f"DEBUG: dia_inicio final: {dia_inicio}")
        
        # Convertir a entero si viene como string
        if isinstance(dia_inicio, str):
            dia_inicio = int(dia_inicio)
            print(f"DEBUG: dia_inicio convertido a int: {dia_inicio}")
        
        # Calcular cuántas semanas completas necesitamos
        semanas_completas = dias_totales // 7
        dias_restantes = dias_totales % 7
        
        print(f"DEBUG: dias_totales: {dias_totales}")
        print(f"DEBUG: semanas_completas: {semanas_completas}")
        print(f"DEBUG: dias_restantes: {dias_restantes}")
        
        planes_generados = {}
        nombres_dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        
        print(f"DEBUG: nombres_dias: {nombres_dias}")
        print(f"DEBUG: dia_inicio final: {dia_inicio}")
        print(f"DEBUG: El plan debería empezar en: {nombres_dias[dia_inicio]}")
        
        dia_actual = 0
        
        # Generar semanas completas
        for semana in range(semanas_completas):
            semana_key = f"Semana_{semana + 1}"
            planes_generados[semana_key] = {}
            
            for i in range(7):
                indice_dia = (dia_inicio + i) % 7
                nombre_dia = nombres_dias[indice_dia]
                print(f"DEBUG: Semana {semana + 1}, Día {i + 1}: indice_dia={indice_dia}, nombre_dia={nombre_dia}")
                planes_generados[semana_key][nombre_dia] = self._generar_dia_completo(grupos, dia_actual + 1, metas, filtros, perfil)
                dia_actual += 1
        
        # Generar días restantes si los hay
        if dias_restantes > 0:
            semana_key = f"Semana_{semanas_completas + 1}"
            print(f"DEBUG: Generando semana adicional: {semana_key} con {dias_restantes} días")
            planes_generados[semana_key] = {}
            
            for i in range(dias_restantes):
                indice_dia = (dia_inicio + i) % 7
                nombre_dia = nombres_dias[indice_dia]
                print(f"DEBUG: Semana adicional, Día {i + 1}: indice_dia={indice_dia}, nombre_dia={nombre_dia}")
                planes_generados[semana_key][nombre_dia] = self._generar_dia_completo(grupos, dia_actual + 1, metas, filtros, perfil)
                dia_actual += 1
        
        print(f"DEBUG: Total de semanas generadas: {len(planes_generados)}")
        print(f"DEBUG: Claves de semanas: {list(planes_generados.keys())}")
        
        return planes_generados

    def _generar_lista_compras_multiples(self, planes_generados: Dict) -> List[Dict]:
        """Genera lista de compras para múltiples planes"""
        
        ingredientes_totales = {}
        
        # Procesar cada semana
        for semana_key, semana in planes_generados.items():
            for dia_key, datos_dia in semana.items():
                for tiempo, comida in datos_dia.items():
                    for alimento in comida['alimentos']:
                        nombre = alimento['nombre']
                        cantidad = alimento['cantidad']
                        unidad = alimento['unidad']
                        
                        if nombre in ingredientes_totales:
                            ingredientes_totales[nombre]['cantidad_total'] += cantidad
                        else:
                            ingredientes_totales[nombre] = {
                                'nombre': nombre,
                                'grupo': alimento['grupo'],
                                'cantidad_total': cantidad,
                                'unidad': unidad
                            }
        
        # Convertir a lista y ordenar por nombre
        lista_compras = list(ingredientes_totales.values())
        lista_compras.sort(key=lambda x: x['nombre'])
        
        return lista_compras

    def _calcular_validaciones_plan_completo(self, planes_generados: Dict, metas: MetaNutricional, filtros: Dict = None) -> Dict:
        """Calcula validaciones para el plan completo con múltiples semanas"""
        
        validaciones = {}
        
        # Procesar cada semana
        for semana_key, semana in planes_generados.items():
            validaciones[semana_key] = {}
            
            for dia_key, datos_dia in semana.items():
                validaciones[semana_key][dia_key] = self._validar_dia(datos_dia, metas, filtros)
        
        return validaciones

    def guardar_recomendacion(self, paciente_id: int, recomendacion: Dict) -> int:
        """Guarda la recomendación como un plan nutricional"""
        
        # Crear el plan
        result = fetch_one("""
            INSERT INTO plan (paciente_id, metas_json, fecha_ini, fecha_fin, estado, version_modelo)
            VALUES (%s, %s, %s, %s, 'borrador', 'motor_recomendacion_v1')
            RETURNING id
        """, (
            paciente_id,
            json.dumps(recomendacion['metas_nutricionales']),
            date.today(),
            date.today() + timedelta(days=7),
        ))
        
        plan_id = result[0]
        
        # Crear detalles del plan para cada comida
        for tiempo_comida, comida_data in recomendacion['comidas'].items():
            detalle_result = fetch_one("""
                INSERT INTO plan_detalle (plan_id, dia, tiempo)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (plan_id, date.today(), tiempo_comida))
            
            plan_detalle_id = detalle_result[0]
            
            # Agregar alimentos sugeridos
            for alimento in comida_data['alimentos_sugeridos']:
                ing = alimento['ingrediente']
                execute("""
                    INSERT INTO plan_alimento (plan_detalle_id, ingrediente_id, cantidad, unidad, kcal, cho, pro, fat, fibra)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    plan_detalle_id,
                    ing['id'],
                    alimento['cantidad_sugerida'],
                    alimento['unidad'],
                    ing['kcal'] * alimento['cantidad_sugerida'] / 100,
                    ing['cho'] * alimento['cantidad_sugerida'] / 100,
                    ing['pro'] * alimento['cantidad_sugerida'] / 100,
                    ing['fat'] * alimento['cantidad_sugerida'] / 100,
                    ing['fibra'] * alimento['cantidad_sugerida'] / 100
                ))
        
        return plan_id
