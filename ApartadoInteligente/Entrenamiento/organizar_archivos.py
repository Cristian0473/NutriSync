"""
Script para organizar archivos del proyecto de entrenamiento ML.
Organiza documentación, scripts, modelos y resultados.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# Configuración de rutas
BASE_DIR = Path(__file__).parent.resolve()  # Resolver ruta absoluta
DATASETS_DIR = BASE_DIR / "Datasets"
MODELOS_DIR = BASE_DIR / "ModeloEntrenamiento"

# Crear estructura de carpetas
ESTRUCTURA = {
    "Scripts": BASE_DIR / "Scripts",
    "Docs": BASE_DIR / "Docs",
    "Modelos": {
        "Produccion": BASE_DIR / "Modelos" / "Produccion",
        "Historial": BASE_DIR / "Modelos" / "Historial"
    }
}

def crear_estructura():
    """Crea la estructura de carpetas necesaria."""
    print("📁 Creando estructura de carpetas...")
    
    for nombre, ruta in ESTRUCTURA.items():
        if isinstance(ruta, dict):
            for sub_nombre, sub_ruta in ruta.items():
                sub_ruta.mkdir(parents=True, exist_ok=True)
                print(f"  ✅ {nombre}/{sub_nombre}/")
        else:
            ruta.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ {nombre}/")
    
    print("✅ Estructura creada\n")

def mover_scripts():
    """Mueve scripts Python a carpeta Scripts/."""
    print("📝 Moviendo scripts Python...")
    
    scripts = [
        "procesar_nhanes_multi_anio.py",
        "procesar_nhanes.py",
        "entrenar_modelos.py",
        "analizar_dataset.py",
        "organizar_archivos.py"  # Este script también se mueve al final
    ]
    
    movidos = 0
    for script in scripts:
        origen = BASE_DIR / script
        if origen.exists() and origen.name != "organizar_archivos.py":  # No mover este script mientras se ejecuta
            destino = ESTRUCTURA["Scripts"] / script
            shutil.move(str(origen), str(destino))
            print(f"  ✅ {script} → Scripts/")
            movidos += 1
    
    print(f"✅ {movidos} scripts movidos\n")

def mover_documentacion():
    """Mueve archivos de documentación a carpeta Docs/."""
    print("📚 Moviendo documentación...")
    
    docs = list(BASE_DIR.glob("*.md"))
    docs = [d for d in docs if d.name != "README.md"]  # Mantener README.md en raíz
    
    movidos = 0
    for doc in docs:
        destino = ESTRUCTURA["Docs"] / doc.name
        shutil.move(str(doc), str(destino))
        print(f"  ✅ {doc.name} → Docs/")
        movidos += 1
    
    print(f"✅ {movidos} documentos movidos\n")

def organizar_modelos():
    """Organiza modelos: último a Produccion, anteriores a Historial."""
    print("🤖 Organizando modelos...")
    
    if not MODELOS_DIR.exists():
        print("  ⚠️  Carpeta ModeloEntrenamiento no encontrada")
        return
    
    # Buscar el último modelo (por timestamp)
    modelos = list(MODELOS_DIR.glob("*.pkl"))
    if not modelos:
        print("  ⚠️  No se encontraron modelos")
        return
    
    # Extraer timestamps y encontrar el más reciente
    timestamps = {}
    for modelo in modelos:
        # Formato: modelo_xgboost_20251107_185913.pkl
        partes = modelo.stem.split("_")
        if len(partes) >= 4:
            timestamp = f"{partes[-2]}_{partes[-1]}"
            if timestamp not in timestamps:
                timestamps[timestamp] = []
            timestamps[timestamp].append(modelo)
    
    if not timestamps:
        print("  ⚠️  No se pudieron extraer timestamps de los modelos")
        return
    
    # Ordenar timestamps (más reciente primero)
    timestamps_ordenados = sorted(timestamps.keys(), reverse=True)
    ultimo_timestamp = timestamps_ordenados[0]
    
    print(f"  📅 Último modelo: {ultimo_timestamp}")
    
    # Mover último modelo a Produccion
    movidos_prod = 0
    for modelo in timestamps[ultimo_timestamp]:
        destino = ESTRUCTURA["Modelos"]["Produccion"] / modelo.name
        shutil.copy2(str(modelo), str(destino))
        print(f"  ✅ {modelo.name} → Modelos/Produccion/")
        movidos_prod += 1
    
    # Mover modelos anteriores a Historial
    movidos_hist = 0
    for timestamp in timestamps_ordenados[1:]:
        for modelo in timestamps[timestamp]:
            destino = ESTRUCTURA["Modelos"]["Historial"] / modelo.name
            shutil.move(str(modelo), str(destino))
            movidos_hist += 1
    
    # Mover archivos de métricas y comparación
    metricas = list(MODELOS_DIR.glob("*.json"))
    metricas.extend(list(MODELOS_DIR.glob("*.csv")))
    
    for archivo in metricas:
        if ultimo_timestamp in archivo.name:
            # Mover métricas del último modelo a Produccion
            destino = ESTRUCTURA["Modelos"]["Produccion"] / archivo.name
            shutil.copy2(str(archivo), str(destino))
            print(f"  ✅ {archivo.name} → Modelos/Produccion/")
        else:
            # Mover métricas anteriores a Historial
            destino = ESTRUCTURA["Modelos"]["Historial"] / archivo.name
            shutil.move(str(archivo), str(destino))
    
    print(f"✅ {movidos_prod} archivos movidos a Produccion")
    print(f"✅ {movidos_hist} archivos movidos a Historial\n")
    
    # Eliminar carpeta ModeloEntrenamiento si está vacía
    if MODELOS_DIR.exists() and not list(MODELOS_DIR.iterdir()):
        MODELOS_DIR.rmdir()
        print("✅ Carpeta ModeloEntrenamiento eliminada (vacía)")

def limpiar_archivos_duplicados():
    """Elimina archivos duplicados o innecesarios."""
    print("🧹 Limpiando archivos duplicados...")
    
    # Eliminar procesar_nhanes.py (versión antigua, reemplazada por multi_anio)
    script_antiguo_base = BASE_DIR / "procesar_nhanes.py"
    script_antiguo_scripts = ESTRUCTURA["Scripts"] / "procesar_nhanes.py"
    
    if script_antiguo_base.exists():
        script_antiguo_base.unlink()
        print("  ✅ procesar_nhanes.py eliminado (reemplazado por procesar_nhanes_multi_anio.py)")
    elif script_antiguo_scripts.exists():
        script_antiguo_scripts.unlink()
        print("  ✅ procesar_nhanes.py eliminado (reemplazado por procesar_nhanes_multi_anio.py)")
    
    print("✅ Limpieza completada\n")

def crear_readme_estructura():
    """Crea README con la estructura final."""
    readme = BASE_DIR / "README.md"
    if readme.exists():
        print("✅ README.md ya existe")
    else:
        print("⚠️  README.md no existe, se creará uno básico")

def main():
    """Función principal."""
    print("="*60)
    print("ORGANIZACIÓN DE ARCHIVOS - ENTRENAMIENTO ML")
    print("="*60)
    print()
    
    try:
        # 1. Crear estructura
        crear_estructura()
        
        # 2. Mover scripts
        mover_scripts()
        
        # 3. Mover documentación
        mover_documentacion()
        
        # 4. Organizar modelos
        organizar_modelos()
        
        # 5. Limpiar duplicados
        limpiar_archivos_duplicados()
        
        # 6. Mover este script al final
        script_actual = BASE_DIR / "organizar_archivos.py"
        if script_actual.exists():
            destino_script = ESTRUCTURA["Scripts"] / "organizar_archivos.py"
            shutil.move(str(script_actual), str(destino_script))
            print("✅ organizar_archivos.py movido a Scripts/")
        
        print("="*60)
        print("✅ ORGANIZACIÓN COMPLETADA EXITOSAMENTE")
        print("="*60)
        
        # Mostrar estructura final
        print("\n📁 Estructura final:")
        print("  Scripts/")
        print("  Docs/")
        print("  Modelos/")
        print("    ├── Produccion/")
        print("    └── Historial/")
        print("  Datasets/")
        print("  README.md")
        print("  requirements_ml.txt")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()

