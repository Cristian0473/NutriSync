#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para iniciar el servidor Flask del sistema de recomendaciones nutricionales
"""

import sys
import os
from datetime import datetime

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def iniciar_servidor():
    """Inicia el servidor Flask"""
    print("=" * 80)
    print("SISTEMA DE RECOMENDACIONES NUTRICIONALES")
    print("=" * 80)
    print(f"Iniciando servidor: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        print("\n1. VERIFICANDO SISTEMA")
        print("-" * 40)
        
        # Verificar importaciones
        print("   a) Verificando importaciones...")
        from main import app
        from Core.motor_recomendacion_basico import MotorRecomendacionBasico
        from Core.bd_conexion import fetch_one
        print("   ✓ Todas las importaciones exitosas")
        
        # Verificar conexión a BD
        print("   b) Verificando conexión a base de datos...")
        result = fetch_one("SELECT 1")
        if result and result[0] == 1:
            print("   ✓ Conexión a base de datos exitosa")
        else:
            print("   ✗ Error de conexión a base de datos")
            return False
        
        # Verificar datos
        print("   c) Verificando datos disponibles...")
        pacientes = fetch_one("SELECT COUNT(*) FROM paciente")
        ingredientes = fetch_one("SELECT COUNT(*) FROM ingrediente WHERE activo = true")
        print(f"   ✓ Pacientes: {pacientes[0]}")
        print(f"   ✓ Ingredientes activos: {ingredientes[0]}")
        
        print("\n2. CONFIGURACIÓN DEL SERVIDOR")
        print("-" * 40)
        
        # Configuración del servidor
        host = '127.0.0.1'  # localhost
        port = 5000
        debug = True
        
        print(f"   - Host: {host}")
        print(f"   - Puerto: {port}")
        print(f"   - Debug: {debug}")
        print(f"   - URL: http://{host}:{port}")
        
        print("\n3. INICIANDO SERVIDOR")
        print("-" * 40)
        print("   ✓ Servidor iniciado correctamente")
        print("   ✓ Sistema listo para recibir peticiones")
        print("\n   Para acceder al sistema:")
        print(f"   🌐 Abrir navegador en: http://{host}:{port}")
        print("   👤 Usuario admin: admin@nutrisync.com")
        print("   🔑 Contraseña: (configurar en la base de datos)")
        print("\n   Para detener el servidor: Ctrl+C")
        print("=" * 80)
        
        # Iniciar el servidor Flask
        app.run(host=host, port=port, debug=debug)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Servidor detenido por el usuario")
        print("=" * 80)
    except Exception as e:
        print(f"\n❌ Error iniciando el servidor: {e}")
        import traceback
        traceback.print_exc()
        return False

def mostrar_ayuda():
    """Muestra información de ayuda"""
    print("=" * 80)
    print("AYUDA - SISTEMA DE RECOMENDACIONES NUTRICIONALES")
    print("=" * 80)
    print("\nEste script inicia el servidor web del sistema de recomendaciones.")
    print("\nREQUISITOS:")
    print("   ✓ PostgreSQL ejecutándose")
    print("   ✓ Base de datos 'proyecto_tesis' creada")
    print("   ✓ Tablas y datos cargados")
    print("   ✓ Dependencias Python instaladas")
    print("\nUSO:")
    print("   python iniciar_servidor.py")
    print("\nACCESO:")
    print("   🌐 URL: http://127.0.0.1:5000")
    print("   👤 Login: admin@nutrisync.com")
    print("\nFUNCIONALIDADES:")
    print("   ✓ Generación de recomendaciones nutricionales")
    print("   ✓ Personalización con filtros")
    print("   ✓ Gestión de pacientes")
    print("   ✓ Motor de IA para diabetes tipo 2")
    print("=" * 80)

def main():
    """Función principal"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        mostrar_ayuda()
    else:
        iniciar_servidor()

if __name__ == "__main__":
    main()
