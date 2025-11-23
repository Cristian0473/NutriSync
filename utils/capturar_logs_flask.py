"""
Script mejorado para capturar logs de Flask y guardarlos en un archivo
Ejecuta este script en lugar de 'python main.py' para capturar todos los logs
"""
import sys
import os
from datetime import datetime
from pathlib import Path
import subprocess

def capturar_logs_flask():
    """Ejecuta Flask y captura todos los logs"""
    
    # Buscar logs_sistema.md en la raíz del proyecto (subir un nivel desde utils/)
    base_dir = Path(__file__).parent.parent
    log_file = base_dir / "logs_sistema.md"
    
    # Crear encabezado del archivo de logs
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"# Logs del Sistema - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("Este archivo contiene todos los logs de la ejecución del sistema.\n\n")
        f.write("## Instrucciones\n\n")
        f.write("1. Regenera un plan nutricional desde la interfaz web\n")
        f.write("2. Los logs aparecerán aquí automáticamente\n")
        f.write("3. Comparte este archivo completo para análisis\n\n")
        f.write("---\n\n")
        f.write("## Logs de Ejecución\n\n")
        f.write("```\n")
    
    print("=" * 70)
    print("📝 CAPTURADOR DE LOGS - SISTEMA DE RECOMENDACIÓN")
    print("=" * 70)
    print()
    print(f"✅ Los logs se guardarán en: {log_file.absolute()}")
    print()
    print("INSTRUCCIONES:")
    print("1. Este script ejecutará Flask y capturará TODOS los logs")
    print("2. Abre tu navegador y regenera un plan nutricional")
    print("3. Los logs aparecerán tanto en la terminal como en el archivo")
    print("4. Cuando termines, presiona Ctrl+C para detener")
    print("5. El archivo 'logs_sistema.md' tendrá todos los logs completos")
    print()
    print("=" * 70)
    print()
    
    try:
        # Ejecutar Flask y capturar output
        base_dir = Path(__file__).parent.parent
        proceso = subprocess.Popen(
            [sys.executable, str(base_dir / "main.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Leer línea por línea y escribir tanto en terminal como en archivo
        with open(log_file, 'a', encoding='utf-8') as f:
            for linea in proceso.stdout:
                # Mostrar en terminal
                print(linea, end='')
                # Guardar en archivo
                f.write(linea)
                f.flush()
        
        proceso.wait()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Deteniendo captura de logs...")
        proceso.terminate()
        
    finally:
        # Cerrar archivo de logs
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write("\n```\n")
            f.write(f"\n**Fin de logs - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**\n")
        
        print(f"\n✅ Logs guardados en: {log_file.absolute()}")
        print(f"📄 Puedes abrir el archivo 'logs_sistema.md' para ver todos los logs completos")

if __name__ == "__main__":
    capturar_logs_flask()

