"""
Script maestro para ejecutar todo el pipeline de ML:
1. Preparar datos para cada modelo
2. Entrenar los 3 modelos
3. Validar resultados

Ejecuta todo el proceso de forma secuencial.
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

def ejecutar_script(script_path, nombre):
    """Ejecuta un script Python y muestra su salida."""
    print("\n" + "=" * 70)
    print(f"🚀 EJECUTANDO: {nombre}")
    print("=" * 70)
    print()
    
    try:
        resultado = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        print(resultado.stdout)
        
        if resultado.stderr:
            print("⚠️  Warnings/Errors:")
            print(resultado.stderr)
        
        if resultado.returncode != 0:
            print(f"\n❌ Error ejecutando {nombre}")
            return False
        
        print(f"\n✅ {nombre} completado exitosamente")
        return True
        
    except Exception as e:
        print(f"\n❌ Error ejecutando {nombre}: {e}")
        return False

def pipeline_completo():
    """
    Ejecuta el pipeline completo de preparación y entrenamiento de modelos ML.
    """
    inicio = datetime.now()
    
    print("=" * 70)
    print("🎯 PIPELINE COMPLETO DE MACHINE LEARNING")
    print("=" * 70)
    print(f"\n⏰ Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Los scripts ahora están en ml/, así que usar rutas relativas desde este archivo
    ml_dir = Path(__file__).parent
    
    scripts = [
        # Fase 1: Preparación de datos
        (ml_dir / "preparar_datos_modelo1_respuesta_glucemica.py", "Preparación Datos Modelo 1"),
        (ml_dir / "preparar_datos_modelo2_seleccion_alimentos.py", "Preparación Datos Modelo 2"),
        (ml_dir / "preparar_datos_modelo3_combinaciones.py", "Preparación Datos Modelo 3"),
        
        # Fase 2: Entrenamiento de modelos
        (ml_dir / "entrenar_modelo1_respuesta_glucemica.py", "Entrenamiento Modelo 1"),
        (ml_dir / "entrenar_modelo2_seleccion_alimentos.py", "Entrenamiento Modelo 2"),
        (ml_dir / "entrenar_modelo3_combinaciones.py", "Entrenamiento Modelo 3"),
    ]
    
    resultados = {}
    
    for script, nombre in scripts:
        if not script.exists():
            print(f"\n⚠️  Archivo no encontrado: {script}")
            resultados[nombre] = False
            continue
        
        exito = ejecutar_script(script, nombre)
        resultados[nombre] = exito
        
        if not exito:
            print(f"\n⚠️  {nombre} falló. ¿Continuar con el siguiente? (s/n)")
            # En modo automático, continuamos
            print("   Continuando automáticamente...")
    
    # Resumen final
    fin = datetime.now()
    duracion = fin - inicio
    
    print("\n" + "=" * 70)
    print("📊 RESUMEN DEL PIPELINE")
    print("=" * 70)
    print(f"\n⏰ Inicio: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏰ Fin: {fin.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Duración total: {duracion}")
    print()
    
    print("📋 Resultados:")
    for nombre, exito in resultados.items():
        estado = "✅ EXITOSO" if exito else "❌ FALLIDO"
        print(f"   {estado}: {nombre}")
    
    exitos = sum(1 for exito in resultados.values() if exito)
    total = len(resultados)
    
    print(f"\n📊 Total: {exitos}/{total} procesos completados exitosamente")
    
    if exitos == total:
        print("\n🎉 ¡Pipeline completado exitosamente!")
        print("\n📝 Próximos pasos:")
        print("   1. Revisar métricas de los modelos entrenados")
        print("   2. Integrar modelos en motor_recomendacion.py")
        print("   3. Probar el sistema completo")
    else:
        print("\n⚠️  Algunos procesos fallaron. Revisa los errores arriba.")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    pipeline_completo()

