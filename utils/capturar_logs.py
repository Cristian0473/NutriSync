"""
Script para capturar logs del sistema y guardarlos en un archivo
"""
import sys
import os
from datetime import datetime
from pathlib import Path

class LogCapture:
    """Captura stdout y stderr y los guarda en un archivo"""
    
    def __init__(self, log_file="logs_sistema.md"):
        # Si es ruta relativa, buscar en la raíz del proyecto (subir un nivel desde utils/)
        if not Path(log_file).is_absolute():
            base_dir = Path(__file__).parent.parent
            self.log_file = base_dir / log_file
        else:
            self.log_file = Path(log_file)
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.log_buffer = []
        
    def write(self, text):
        """Escribe tanto en stdout original como en el buffer"""
        self.original_stdout.write(text)
        self.original_stdout.flush()
        self.log_buffer.append(text)
        
    def flush(self):
        """Flush del stdout original"""
        self.original_stdout.flush()
        
    def start(self):
        """Inicia la captura de logs"""
        sys.stdout = self
        sys.stderr = self
        
        # Escribir encabezado en el archivo
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"# Logs del Sistema - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("```\n")
        
        print(f"📝 Captura de logs iniciada. Los logs se guardarán en: {self.log_file}")
        print(f"🕐 Hora de inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
    def stop(self):
        """Detiene la captura y guarda los logs"""
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        # Guardar logs en el archivo
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(''.join(self.log_buffer))
            f.write("\n```\n")
            f.write(f"\n**Fin de logs - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**\n")
        
        print(f"\n✅ Logs guardados en: {self.log_file}")
        print(f"📊 Total de líneas capturadas: {len(self.log_buffer)}")

if __name__ == "__main__":
    print("=" * 70)
    print("📝 CAPTURADOR DE LOGS DEL SISTEMA")
    print("=" * 70)
    print()
    print("Este script capturará todos los logs de la ejecución.")
    print("Para usarlo, ejecuta tu aplicación Flask normalmente.")
    print("Los logs se guardarán automáticamente en 'logs_sistema.md'")
    print()
    print("=" * 70)
    print()
    
    # Crear instancia del capturador
    capturador = LogCapture("logs_sistema.md")
    
    # Iniciar captura
    capturador.start()
    
    print("✅ Captura activa. Ahora ejecuta tu aplicación Flask.")
    print("   Cuando termines, presiona Ctrl+C para detener y guardar los logs.")
    print()

