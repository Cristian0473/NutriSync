"""
Script para procesar archivos NHANES de múltiples años (.XPT) y convertirlos a formato CSV/JSON
para entrenamiento de modelos de Machine Learning.

Maneja automáticamente las diferencias entre años:
- BPX (auscultatorio) vs BPXO (oscilométrico) para presión arterial
- Diferentes sufijos de archivos según el año

Mapea variables de NHANES a las usadas en el sistema de recomendación nutricional
y crea variables derivadas necesarias para el modelado.
"""

import os
import pandas as pd
import numpy as np
import pyreadstat
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import warnings

warnings.filterwarnings('ignore')

# Configuración de rutas
BASE_DIR = Path(__file__).parent
DATASETS_DIR = BASE_DIR / "Datasets"
OUTPUT_DIR = DATASETS_DIR

# Mapeo de sufijos de archivos por año
# Formato: {año: {tipo_archivo: sufijo}}
SUFIJOS_POR_ANIO = {
    '2013-2014': 'H',
    '2015-2016': 'I',  # Nota: hay un typo en la carpeta "2015-1016", ajustar si es necesario
    '2017-2018': 'J',
    '2021-2023': 'L'
}

# Tipos de archivos NHANES
TIPOS_ARCHIVOS = {
    'demo': 'DEMO',    # Datos demográficos (edad, sexo)
    'ghb': 'GHB',      # Hemoglobina glicosilada (HbA1c)
    'glu': 'GLU',      # Glucosa en ayunas
    'ins': 'INS',      # Insulina en ayunas
    'hdl': 'HDL',      # Colesterol HDL
    'trigly': 'TRIGLY', # Triglicéridos
    'tchol': 'TCHOL',  # Colesterol total
    'bmx': 'BMX',      # Antropometría (peso, talla, IMC, cintura)
    'bpx': 'BPX',      # Presión arterial (auscultatorio - años antiguos)
    'bpxo': 'BPXO',    # Presión arterial (oscilométrico - años recientes)
}

# Mapeo de variables NHANES a variables del sistema
MAPEO_VARIABLES = {
    # Clínicas
    'LBXGH': 'hba1c',           # Hemoglobina glicosilada (%)
    'LBXGLU': 'glucosa_ayunas', # Glucosa en ayunas (mg/dL)
    'LBXIN': 'insulina_ayunas',  # Insulina en ayunas (μU/mL)
    'LBDHDD': 'hdl',            # Colesterol HDL (mg/dL)
    'LBXTLG': 'trigliceridos',  # Triglicéridos (mg/dL)
    'LBXTC': 'colesterol_total', # Colesterol total (mg/dL)
    
    # Presión arterial - Auscultatorio (BPX)
    'BPXSY1': 'pa_sis_ausc',    # Presión arterial sistólica auscultatoria
    'BPXSY2': 'pa_sis_ausc_2',
    'BPXSY3': 'pa_sis_ausc_3',
    'BPXDI1': 'pa_dia_ausc',   # Presión arterial diastólica auscultatoria
    'BPXDI2': 'pa_dia_ausc_2',
    'BPXDI3': 'pa_dia_ausc_3',
    
    # Presión arterial - Oscilométrico (BPXO)
    'BPXOSY1': 'pa_sis_osc',    # Presión arterial sistólica oscilométrica
    'BPXOSY2': 'pa_sis_osc_2',
    'BPXOSY3': 'pa_sis_osc_3',
    'BPXODI1': 'pa_dia_osc',    # Presión arterial diastólica oscilométrica
    'BPXODI2': 'pa_dia_osc_2',
    'BPXODI3': 'pa_dia_osc_3',
    
    # Antropométricas
    'BMXWT': 'peso',            # Peso (kg)
    'BMXHT': 'talla',           # Talla (cm) - se convertirá a metros
    'BMXBMI': 'imc_nhanes',     # IMC reportado por NHANES
    'BMXWAIST': 'cc',           # Circunferencia de cintura (cm)
    
    # Demográficas
    'RIAGENDR': 'sexo_codigo',  # Código de sexo (1=M, 2=F)
    'RIDAGEYR': 'edad',         # Edad en años
}

# Rangos clínicos válidos para validación (ajustados para adultos)
RANGOS_VALIDOS = {
    'hba1c': (4.0, 15.0),
    'glucosa_ayunas': (50, 500),
    'ldl': (0, 300),
    'hdl': (10, 150),
    'trigliceridos': (20, 1000),
    'colesterol_total': (100, 400),
    'pa_sis': (60, 250),
    'pa_dia': (40, 150),
    'peso': (20, 300),      # Ajustado para incluir adultos extremos
    'talla': (1.00, 2.50),  # Ajustado para incluir adultos extremos (en metros)
    'imc': (10, 60),        # Ajustado para incluir casos extremos
    'cc': (40, 250),        # Ajustado para incluir adultos extremos (en cm)
    'insulina_ayunas': (1, 300),  # Ajustado para incluir casos extremos
}


def detectar_carpetas_anios() -> List[str]:
    """
    Detecta automáticamente las carpetas de años disponibles en Datasets.
    
    Returns:
        Lista de nombres de carpetas de años
    """
    carpetas_anios = []
    
    for item in DATASETS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Verificar que tenga archivos .xpt
            archivos_xpt = list(item.glob('*.xpt'))
            if archivos_xpt:
                carpetas_anios.append(item.name)
    
    carpetas_anios.sort()
    print(f"📁 Carpetas de años detectadas: {carpetas_anios}")
    return carpetas_anios


def leer_archivo_xpt(ruta_archivo: Path) -> pd.DataFrame:
    """
    Lee un archivo .XPT de NHANES y retorna un DataFrame de pandas.
    
    Args:
        ruta_archivo: Ruta completa al archivo .XPT
        
    Returns:
        DataFrame con los datos del archivo
    """
    if not ruta_archivo.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {ruta_archivo}")
    
    print(f"  Leyendo {ruta_archivo.name}...")
    df, meta = pyreadstat.read_xport(str(ruta_archivo))
    print(f"    - Filas: {len(df)}, Columnas: {len(df.columns)}")
    
    return df


def cargar_bp_unificado(ruta_bpx: Path) -> pd.DataFrame:
    """
    Carga y unifica datos de presión arterial (BPX o BPXO) independientemente del método.
    
    Args:
        ruta_bpx: Ruta al archivo BPX o BPXO
        
    Returns:
        DataFrame con columnas SEQN, pa_sis, pa_dia, metodo_bp
    """
    df = leer_archivo_xpt(ruta_bpx)
    
    # Detectar tipo de archivo (BPX auscultatorio o BPXO oscilométrico)
    cols = df.columns
    
    if 'BPXOSY1' in cols or 'BPXOSY2' in cols:  # Oscilométrico
        metodo = 'oscilometrico'
        # Promediar las 3 mediciones si están disponibles
        cols_sis = [c for c in ['BPXOSY1', 'BPXOSY2', 'BPXOSY3'] if c in cols]
        cols_dia = [c for c in ['BPXODI1', 'BPXODI2', 'BPXODI3'] if c in cols]
        
        if cols_sis:
            df['pa_sis'] = df[cols_sis].mean(axis=1)
        else:
            df['pa_sis'] = np.nan
            
        if cols_dia:
            df['pa_dia'] = df[cols_dia].mean(axis=1)
        else:
            df['pa_dia'] = np.nan
            
    elif 'BPXSY1' in cols or 'BPXSY2' in cols:  # Auscultatorio
        metodo = 'auscultatorio'
        # Promediar las 3 mediciones si están disponibles
        cols_sis = [c for c in ['BPXSY1', 'BPXSY2', 'BPXSY3'] if c in cols]
        cols_dia = [c for c in ['BPXDI1', 'BPXDI2', 'BPXDI3'] if c in cols]
        
        if cols_sis:
            df['pa_sis'] = df[cols_sis].mean(axis=1)
        else:
            df['pa_sis'] = np.nan
            
        if cols_dia:
            df['pa_dia'] = df[cols_dia].mean(axis=1)
        else:
            df['pa_dia'] = np.nan
    else:
        raise ValueError(f"Archivo BPX desconocido: {ruta_bpx.name}. Columnas: {list(cols)}")
    
    # Crear DataFrame unificado
    df_bp = pd.DataFrame({
        'SEQN': df['SEQN'],
        'pa_sis': df['pa_sis'],
        'pa_dia': df['pa_dia'],
        'metodo_bp': metodo
    })
    
    print(f"    ✅ Presión arterial unificada ({metodo}): {df_bp['pa_sis'].notna().sum()} valores válidos")
    
    return df_bp


def procesar_anio(carpeta_anio: str) -> pd.DataFrame:
    """
    Procesa todos los archivos de un año específico.
    
    Args:
        carpeta_anio: Nombre de la carpeta del año (ej: "2015-2016")
        
    Returns:
        DataFrame combinado con todos los datos del año
    """
    print(f"\n{'='*60}")
    print(f"PROCESANDO AÑO: {carpeta_anio}")
    print(f"{'='*60}")
    
    carpeta_path = DATASETS_DIR / carpeta_anio
    
    if not carpeta_path.exists():
        print(f"  ⚠️  Carpeta no encontrada: {carpeta_path}")
        return None
    
    dataframes = {}
    
    # Procesar cada tipo de archivo
    for tipo, prefijo in TIPOS_ARCHIVOS.items():
        if tipo in ['bpx', 'bpxo']:
            # Buscar archivos BPX o BPXO
            archivos_bp = list(carpeta_path.glob('BPX*.xpt'))
            if archivos_bp:
                try:
                    df_bp = cargar_bp_unificado(archivos_bp[0])
                    dataframes['bp'] = df_bp
                except Exception as e:
                    print(f"  ⚠️  Error procesando BPX/BPXO: {e}")
        elif tipo == 'demo':
            # Buscar archivos DEMO (pueden tener diferentes sufijos)
            archivos_demo = list(carpeta_path.glob('DEMO*.xpt'))
            if not archivos_demo:
                # También buscar con sufijo del año
                archivos_demo = list(carpeta_path.glob('*DEMO*.xpt'))
            if archivos_demo:
                try:
                    df = leer_archivo_xpt(archivos_demo[0])
                    if 'SEQN' in df.columns:
                        dataframes[tipo] = df
                except Exception as e:
                    print(f"  ⚠️  Error leyendo DEMO: {e}")
        else:
            # Buscar archivo con el prefijo correspondiente
            archivo = list(carpeta_path.glob(f"{prefijo}_*.xpt"))
            if archivo:
                try:
                    df = leer_archivo_xpt(archivo[0])
                    if 'SEQN' in df.columns:
                        dataframes[tipo] = df
                except Exception as e:
                    print(f"  ⚠️  Error leyendo {prefijo}: {e}")
    
    if not dataframes:
        print(f"  ⚠️  No se encontraron archivos para {carpeta_anio}")
        return None
    
    # Unir todos los DataFrames por SEQN
    print(f"\n  Uniendo datos de {carpeta_anio}...")
    df_anio = None
    
    for clave, df in dataframes.items():
        if df_anio is None:
            df_anio = df.copy()
            print(f"    - DataFrame base: {clave} ({len(df_anio)} filas)")
        else:
            antes = len(df_anio)
            df_anio = df_anio.merge(df, on='SEQN', how='outer', suffixes=('', f'_{clave}'))
            print(f"    - Unido {clave}: {len(df_anio)} filas (antes: {antes})")
    
    # Agregar columna de año
    df_anio['anio_nhanes'] = carpeta_anio
    
    print(f"  ✅ Año {carpeta_anio} procesado: {len(df_anio)} filas")
    
    return df_anio


def unir_datos_multi_anio() -> pd.DataFrame:
    """
    Procesa y une datos de múltiples años de NHANES.
    
    Returns:
        DataFrame combinado con todos los años
    """
    print("\n" + "="*60)
    print("UNIENDO DATOS DE MÚLTIPLES AÑOS")
    print("="*60)
    
    # Detectar carpetas de años
    carpetas_anios = detectar_carpetas_anios()
    
    if not carpetas_anios:
        raise ValueError("No se encontraron carpetas de años con archivos .xpt")
    
    # Procesar cada año
    dataframes_anios = []
    
    for carpeta_anio in carpetas_anios:
        df_anio = procesar_anio(carpeta_anio)
        if df_anio is not None:
            dataframes_anios.append(df_anio)
    
    if not dataframes_anios:
        raise ValueError("No se pudieron procesar datos de ningún año")
    
    # Combinar todos los años
    print(f"\n{'='*60}")
    print("COMBINANDO TODOS LOS AÑOS")
    print(f"{'='*60}")
    
    df_final = pd.concat(dataframes_anios, ignore_index=True)
    
    print(f"✅ Dataset combinado: {len(df_final)} filas, {len(df_final.columns)} columnas")
    print(f"   Años incluidos: {df_final['anio_nhanes'].unique()}")
    
    return df_final


def mapear_variables(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mapea variables de NHANES a las usadas en el sistema.
    
    Args:
        df: DataFrame con datos de NHANES
        
    Returns:
        DataFrame con variables mapeadas
    """
    print("\nMapeando variables...")
    df_mapped = pd.DataFrame()
    df_mapped['seqn'] = df['SEQN'].copy()
    
    # Mapear variables según el diccionario
    variables_mapeadas = []
    
    for var_nhanes, var_sistema in MAPEO_VARIABLES.items():
        if var_nhanes in df.columns:
            df_mapped[var_sistema] = df[var_nhanes].copy()
            variables_mapeadas.append(f"{var_nhanes} → {var_sistema}")
        else:
            # Buscar variantes (puede haber sufijos)
            variantes = [col for col in df.columns if col.startswith(var_nhanes)]
            if variantes:
                # Usar la primera variante encontrada
                df_mapped[var_sistema] = df[variantes[0]].copy()
                variables_mapeadas.append(f"{variantes[0]} → {var_sistema}")
    
    # Presión arterial ya está unificada (pa_sis, pa_dia)
    if 'pa_sis' in df.columns:
        df_mapped['pa_sis'] = df['pa_sis'].copy()
        variables_mapeadas.append("pa_sis (unificado)")
    if 'pa_dia' in df.columns:
        df_mapped['pa_dia'] = df['pa_dia'].copy()
        variables_mapeadas.append("pa_dia (unificado)")
    if 'metodo_bp' in df.columns:
        df_mapped['metodo_bp'] = df['metodo_bp'].copy()
    
    # Año NHANES
    if 'anio_nhanes' in df.columns:
        df_mapped['anio_nhanes'] = df['anio_nhanes'].copy()
    
    print(f"  ✅ Variables mapeadas: {len(variables_mapeadas)}")
    for var in variables_mapeadas[:15]:  # Mostrar primeras 15
        print(f"     - {var}")
    if len(variables_mapeadas) > 15:
        print(f"     ... y {len(variables_mapeadas) - 15} más")
    
    return df_mapped


def convertir_unidades(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte unidades a las usadas en el sistema.
    
    Args:
        df: DataFrame con variables mapeadas
        
    Returns:
        DataFrame con unidades convertidas
    """
    print("\nConvirtiendo unidades...")
    
    # Convertir talla de cm a metros
    if 'talla' in df.columns:
        # Si la talla parece estar en cm (> 1.5), convertir a metros
        if df['talla'].max() > 1.5:
            df['talla'] = df['talla'] / 100
            print("  ✅ Talla convertida de cm a metros")
        else:
            print("  ℹ️  Talla ya está en metros")
    
    # Mapear sexo: 1=M, 2=F → 'M', 'F'
    if 'sexo_codigo' in df.columns:
        df['sexo'] = df['sexo_codigo'].map({1: 'M', 2: 'F'}).fillna('O')
        df = df.drop(columns=['sexo_codigo'])
        print("  ✅ Sexo mapeado: 1→M, 2→F")
    
    return df


def crear_variables_derivadas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crea variables derivadas necesarias para el modelado.
    (Misma función que en el script original)
    """
    print("\nCreando variables derivadas...")
    
    # 1. IMC (si no existe o recalcular)
    if 'peso' in df.columns and 'talla' in df.columns:
        df['imc'] = df['peso'] / (df['talla'] ** 2)
        print("  ✅ IMC calculado: peso / (talla²)")
    
    # 2. LDL usando fórmula de Friedewald
    if all(col in df.columns for col in ['colesterol_total', 'hdl', 'trigliceridos']):
        condicion = df['trigliceridos'] < 400
        df.loc[condicion, 'ldl'] = (
            df.loc[condicion, 'colesterol_total'] - 
            df.loc[condicion, 'hdl'] - 
            (df.loc[condicion, 'trigliceridos'] / 5)
        )
        print("  ✅ LDL calculado (Fórmula de Friedewald)")
    
    # 3. No-HDL
    if 'colesterol_total' in df.columns and 'hdl' in df.columns:
        df['no_hdl'] = df['colesterol_total'] - df['hdl']
        print("  ✅ No-HDL calculado")
    
    # 4. HOMA-IR
    if 'glucosa_ayunas' in df.columns and 'insulina_ayunas' in df.columns:
        df['homa_ir'] = (df['glucosa_ayunas'] * df['insulina_ayunas']) / 405
        print("  ✅ HOMA-IR calculado")
    
    # 5. Ratios
    if 'trigliceridos' in df.columns and 'hdl' in df.columns:
        df['tg_hdl_ratio'] = df['trigliceridos'] / df['hdl']
        print("  ✅ TG/HDL ratio calculado")
    
    if 'ldl' in df.columns and 'hdl' in df.columns:
        df['ldl_hdl_ratio'] = df['ldl'] / df['hdl']
        print("  ✅ LDL/HDL ratio calculado")
    
    # 6. AIP
    if 'tg_hdl_ratio' in df.columns:
        df['aip'] = np.log10(df['tg_hdl_ratio'].replace([0, np.inf, -np.inf], np.nan))
        print("  ✅ AIP calculado: log10(TG/HDL)")
    
    # 7. Hipertensión
    if 'pa_sis' in df.columns and 'pa_dia' in df.columns:
        df['hipertension'] = (
            (df['pa_sis'] >= 140) | (df['pa_dia'] >= 90)
        ).astype(int)
        print("  ✅ Hipertensión definida (PAS≥140 o PAD≥90)")
    
    # 8. Control glucémico
    if 'hba1c' in df.columns:
        df['control_glucemico'] = (df['hba1c'] >= 7.0).astype(int)
        print("  ✅ Control glucémico definido (HbA1c≥7.0)")
    
    # 9. Score de riesgo metabólico
    riesgo_score = pd.Series(0.0, index=df.index)
    
    if 'hba1c' in df.columns:
        riesgo_score += (df['hba1c'] > 8.0).astype(float) * 0.3
        riesgo_score += ((df['hba1c'] >= 7.0) & (df['hba1c'] <= 8.0)).astype(float) * 0.15
    
    if 'imc' in df.columns:
        riesgo_score += (df['imc'] > 30).astype(float) * 0.2
        riesgo_score += ((df['imc'] >= 25) & (df['imc'] <= 30)).astype(float) * 0.1
    
    if 'hipertension' in df.columns:
        riesgo_score += df['hipertension'] * 0.15
    
    if 'ldl' in df.columns:
        riesgo_score += (df['ldl'] > 100).astype(float) * 0.1
    
    if 'tg_hdl_ratio' in df.columns:
        riesgo_score += (df['tg_hdl_ratio'] > 3.0).astype(float) * 0.15
    
    df['riesgo_metabolico'] = np.clip(riesgo_score, 0, 1)
    print("  ✅ Score de riesgo metabólico calculado")
    
    # 10. Actividad física
    if 'actividad' not in df.columns:
        df['actividad'] = 'moderada'
        print("  ℹ️  Actividad física establecida por defecto: 'moderada'")
    
    return df


def validar_rangos_clinicos(df: pd.DataFrame) -> pd.DataFrame:
    """Valida que los valores estén en rangos clínicos razonables."""
    print("\nValidando rangos clínicos...")
    
    valores_invalidos = 0
    
    for variable, (min_val, max_val) in RANGOS_VALIDOS.items():
        if variable in df.columns:
            antes = df[variable].notna().sum()
            df.loc[(df[variable] < min_val) | (df[variable] > max_val), variable] = np.nan
            despues = df[variable].notna().sum()
            invalidados = antes - despues
            if invalidados > 0:
                valores_invalidos += invalidados
                print(f"  ⚠️  {variable}: {invalidados} valores fuera de rango [{min_val}, {max_val}]")
    
    if valores_invalidos == 0:
        print("  ✅ Todos los valores están en rangos válidos")
    else:
        print(f"  ⚠️  Total de valores invalidados: {valores_invalidos}")
    
    return df


def filtrar_pacientes_dm2(df: pd.DataFrame, incluir_prediabetes: bool = True) -> pd.DataFrame:
    """Filtra pacientes con diabetes tipo 2 (y opcionalmente prediabetes)."""
    print("\nFiltrando pacientes con diabetes tipo 2...")
    if incluir_prediabetes:
        print("  ℹ️  Incluyendo también pacientes con prediabetes para aumentar el dataset")
    antes = len(df)
    
    # Filtro 1: Edad ≥ 18
    if 'edad' in df.columns:
        df = df[df['edad'] >= 18].copy()
        print(f"  - Edad ≥ 18: {len(df)} filas (antes: {antes})")
        antes = len(df)
    else:
        print("  ⚠️  Variable 'edad' no encontrada, omitiendo filtro de edad")
    
    # Filtro 2: Criterios DM2 y/o Prediabetes
    criterios = pd.Series(False, index=df.index)
    
    if 'hba1c' in df.columns:
        criterios_dm2 = (df['hba1c'] >= 6.5)
        criterios |= criterios_dm2
        print(f"  - Pacientes con HbA1c ≥ 6.5 (DM2): {criterios_dm2.sum()}")
        
        if incluir_prediabetes:
            criterios_prediabetes = ((df['hba1c'] >= 5.7) & (df['hba1c'] < 6.5))
            criterios |= criterios_prediabetes
            print(f"  - Pacientes con HbA1c 5.7-6.4 (Prediabetes): {criterios_prediabetes.sum()}")
    
    if 'glucosa_ayunas' in df.columns:
        criterios_dm2_glu = (df['glucosa_ayunas'] >= 126)
        criterios |= criterios_dm2_glu
        print(f"  - Pacientes con Glucosa ≥ 126 (DM2): {criterios_dm2_glu.sum()}")
        
        if incluir_prediabetes:
            criterios_prediabetes_glu = ((df['glucosa_ayunas'] >= 100) & (df['glucosa_ayunas'] < 126))
            criterios |= criterios_prediabetes_glu
            print(f"  - Pacientes con Glucosa 100-125 (Prediabetes): {criterios_prediabetes_glu.sum()}")
    
    df_filtrado = df[criterios].copy()
    
    if incluir_prediabetes:
        print(f"  ✅ Pacientes con DM2 + Prediabetes: {len(df_filtrado)} filas (antes: {antes})")
    else:
        print(f"  ✅ Pacientes con DM2: {len(df_filtrado)} filas (antes: {antes})")
    
    return df_filtrado


def limpiar_datos(df: pd.DataFrame, umbral_faltantes: float = 0.5) -> pd.DataFrame:
    """Limpia el dataset eliminando filas con demasiados valores faltantes."""
    print(f"\nLimpiando datos (umbral de faltantes: {umbral_faltantes*100}%)...")
    antes = len(df)
    
    variables_clave = ['hba1c', 'glucosa_ayunas', 'peso', 'talla', 'imc']
    variables_clave = [v for v in variables_clave if v in df.columns]
    
    if variables_clave:
        faltantes_por_fila = df[variables_clave].isna().sum(axis=1) / len(variables_clave)
        df_limpio = df[faltantes_por_fila <= umbral_faltantes].copy()
        
        eliminadas = antes - len(df_limpio)
        print(f"  - Filas eliminadas por exceso de faltantes: {eliminadas}")
        print(f"  - Filas restantes: {len(df_limpio)}")
    else:
        df_limpio = df.copy()
        print("  ⚠️  No se encontraron variables clave para limpiar")
    
    print("\n  Estadísticas de valores faltantes:")
    for var in variables_clave[:10]:
        faltantes = df_limpio[var].isna().sum()
        porcentaje = (faltantes / len(df_limpio)) * 100
        print(f"     - {var}: {faltantes} faltantes ({porcentaje:.1f}%)")
    
    return df_limpio


def guardar_resultados(df: pd.DataFrame):
    """Guarda el dataset procesado en formato CSV y JSON."""
    print("\nGuardando resultados...")
    
    # Guardar CSV
    archivo_csv = OUTPUT_DIR / "nhanes_procesado.csv"
    df.to_csv(archivo_csv, index=False, encoding='utf-8')
    print(f"  ✅ CSV guardado: {archivo_csv}")
    print(f"     - Tamaño: {archivo_csv.stat().st_size / 1024 / 1024:.2f} MB")
    
    # Guardar JSON (muestra)
    archivo_json = OUTPUT_DIR / "nhanes_procesado.json"
    df_sample = df.head(1000) if len(df) > 1000 else df
    df_sample.to_json(archivo_json, orient='records', indent=2, force_ascii=False)
    print(f"  ✅ JSON guardado: {archivo_json} ({len(df_sample)} filas)")
    
    # Guardar metadatos
    archivo_meta = OUTPUT_DIR / "nhanes_metadatos.json"
    metadatos = {
        'total_filas': len(df),
        'total_columnas': len(df.columns),
        'columnas': list(df.columns),
        'anios_incluidos': df['anio_nhanes'].unique().tolist() if 'anio_nhanes' in df.columns else [],
        'metodo_bp_distribucion': df['metodo_bp'].value_counts().to_dict() if 'metodo_bp' in df.columns else {},
        'variables_clinicas': [c for c in df.columns if c in ['hba1c', 'glucosa_ayunas', 'ldl', 'hdl', 'trigliceridos', 'colesterol_total', 'pa_sis', 'pa_dia']],
        'variables_antropometricas': [c for c in df.columns if c in ['peso', 'talla', 'imc', 'cc', 'bf_pct']],
        'variables_derivadas': [c for c in df.columns if c in ['ldl', 'no_hdl', 'homa_ir', 'tg_hdl_ratio', 'ldl_hdl_ratio', 'aip', 'hipertension', 'control_glucemico', 'riesgo_metabolico']],
        'valores_faltantes': {col: int(df[col].isna().sum()) for col in df.columns},
        'estadisticas': df.describe().to_dict()
    }
    
    with open(archivo_meta, 'w', encoding='utf-8') as f:
        json.dump(metadatos, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"  ✅ Metadatos guardados: {archivo_meta}")
    
    # Mostrar resumen
    print(f"\n{'='*60}")
    print(f"RESUMEN DEL DATASET PROCESADO")
    print(f"{'='*60}")
    print(f"Total de filas: {len(df):,}")
    print(f"Total de columnas: {len(df.columns)}")
    if 'anio_nhanes' in df.columns:
        print(f"\nAños incluidos:")
        for anio in sorted(df['anio_nhanes'].unique()):
            count = (df['anio_nhanes'] == anio).sum()
            print(f"  - {anio}: {count:,} filas")
    if 'metodo_bp' in df.columns:
        print(f"\nMétodo de presión arterial:")
        for metodo, count in df['metodo_bp'].value_counts().items():
            print(f"  - {metodo}: {count:,} filas")
    print(f"\nVariables principales:")
    for var in ['seqn', 'edad', 'sexo', 'peso', 'talla', 'imc', 'hba1c', 'glucosa_ayunas', 'ldl', 'control_glucemico', 'riesgo_metabolico']:
        if var in df.columns:
            faltantes = df[var].isna().sum()
            print(f"  - {var}: {df[var].notna().sum():,} valores válidos ({faltantes} faltantes)")


def main(incluir_prediabetes: bool = True, umbral_faltantes: float = 0.5):
    """Función principal que ejecuta todo el pipeline de procesamiento."""
    print("="*60)
    print("PROCESAMIENTO DE DATOS NHANES (MÚLTIPLES AÑOS)")
    print("="*60)
    if incluir_prediabetes:
        print("⚠️  MODO: Incluyendo prediabetes para aumentar el dataset")
    print(f"⚠️  Umbral de faltantes: {umbral_faltantes*100}%")
    
    try:
        # 1. Leer y unir archivos de múltiples años
        df = unir_datos_multi_anio()
        
        # 2. Mapear variables
        df = mapear_variables(df)
        
        # 3. Convertir unidades
        df = convertir_unidades(df)
        
        # 4. Crear variables derivadas
        df = crear_variables_derivadas(df)
        
        # 5. Validar rangos clínicos
        df = validar_rangos_clinicos(df)
        
        # 6. Filtrar pacientes con DM2
        df = filtrar_pacientes_dm2(df, incluir_prediabetes=incluir_prediabetes)
        
        # 7. Limpiar datos
        df = limpiar_datos(df, umbral_faltantes=umbral_faltantes)
        
        # 8. Guardar resultados
        guardar_resultados(df)
        
        print("\n" + "="*60)
        print("✅ PROCESAMIENTO COMPLETADO EXITOSAMENTE")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()

