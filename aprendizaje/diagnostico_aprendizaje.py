#!/usr/bin/env python3
# diagnostico_aprendizaje.py
# Script para diagnosticar problemas con el aprendizaje continuo

import sys
import os
from pathlib import Path

# Agregar directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("DIAGNÓSTICO DE APRENDIZAJE CONTINUO")
print("=" * 60)
print()

# 1. Verificar variable de entorno
print("1. Verificando variable de entorno...")
# Buscar .env en la raíz del proyecto (subir un nivel desde aprendizaje/)
base_dir = Path(__file__).parent.parent
env_file = base_dir / ".env"
if env_file.exists():
    print(f"   ✓ Archivo .env encontrado")
    with open(env_file, 'r', encoding='utf-8') as f:
        contenido = f.read()
        if "APRENDIZAJE_CONTINUO=true" in contenido or "APRENDIZAJE_CONTINUO=True" in contenido:
            print("   ✓ APRENDIZAJE_CONTINUO está en true en .env")
        else:
            print("   ✗ APRENDIZAJE_CONTINUO no está en true en .env")
            lineas_relevantes = [l for l in contenido.split('\n') if 'APRENDIZAJE' in l]
            print(f"   Contenido relevante: {lineas_relevantes}")
else:
    print("   ✗ Archivo .env no encontrado")

# Verificar variable de entorno del sistema
valor_env = os.getenv("APRENDIZAJE_CONTINUO")
print(f"   Variable de entorno del sistema: {valor_env}")
print()

# 2. Verificar módulo de aprendizaje
print("2. Verificando módulo de aprendizaje...")
try:
    from aprendizaje.aprendizaje_continuo import obtener_aprendizaje, APRENDIZAJE_HABILITADO
    print(f"   ✓ Módulo importado correctamente")
    print(f"   APRENDIZAJE_HABILITADO (global): {APRENDIZAJE_HABILITADO}")
    
    aprendizaje = obtener_aprendizaje()
    print(f"   aprendizaje.habilitado: {aprendizaje.habilitado}")
    
    if not aprendizaje.habilitado:
        print("   ⚠️  Aprendizaje está DESHABILITADO")
        print("   Verifica que .env tenga: APRENDIZAJE_CONTINUO=true")
        print("   Y que el servidor se haya reiniciado después de cambiar .env")
except Exception as e:
    print(f"   ✗ Error importando módulo: {e}")
    import traceback
    traceback.print_exc()
print()

# 3. Verificar conexión a BD y tabla
print("3. Verificando base de datos...")
try:
    from Core.bd_conexion import fetch_one
    
    # Verificar si la tabla existe
    tabla_existe = fetch_one("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'plan_resultado'
        )
    """)
    
    if tabla_existe and tabla_existe[0]:
        print("   ✓ Tabla 'plan_resultado' existe")
        
        # Contar registros
        count = fetch_one("SELECT COUNT(*) FROM plan_resultado")
        print(f"   Registros en plan_resultado: {count[0] if count else 0}")
    else:
        print("   ✗ Tabla 'plan_resultado' NO existe")
        print("   Ejecuta: psql -U postgres -d proyecto_tesis -f SQL/aprendizaje_continuo.sql")
        
except Exception as e:
    print(f"   ✗ Error verificando BD: {e}")
    import traceback
    traceback.print_exc()
print()

# 4. Verificar hook de integración
print("4. Verificando hook de integración...")
try:
    from aprendizaje.integracion_aprendizaje import hook_plan_guardado
    print("   ✓ Hook importado correctamente")
except Exception as e:
    print(f"   ✗ Error importando hook: {e}")
    import traceback
    traceback.print_exc()
print()

print("=" * 60)
print("DIAGNÓSTICO COMPLETADO")
print("=" * 60)

