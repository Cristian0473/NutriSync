#!/usr/bin/env python3
# verificar_aprendizaje.py
# Script para verificar el estado del aprendizaje continuo

import sys
import os
from datetime import date, datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Core.bd_conexion import fetch_one, fetch_all
from aprendizaje.aprendizaje_continuo import obtener_aprendizaje

def verificar_plan(plan_id: int):
    """Verifica si un plan tiene baseline registrado"""
    print(f"\n{'='*60}")
    print(f"VERIFICANDO PLAN {plan_id}")
    print(f"{'='*60}\n")
    
    # Verificar baseline
    resultado = fetch_one("""
        SELECT id, paciente_id, fecha_inicio, estado,
               hba1c_inicial, glucosa_inicial, peso_inicial, imc_inicial,
               fecha_fin, hba1c_final, glucosa_final, peso_final,
               cumplimiento_pct, satisfaccion, resultado_exitoso,
               creado_en
        FROM plan_resultado
        WHERE plan_id = %s
        ORDER BY creado_en DESC
        LIMIT 1
    """, (plan_id,))
    
    if resultado:
        r = resultado
        print("✅ BASELINE REGISTRADO:")
        print(f"   - ID Resultado: {r[0]}")
        print(f"   - Paciente ID: {r[1]}")
        print(f"   - Fecha inicio: {r[2]}")
        print(f"   - Estado: {r[3]}")
        print(f"   - HbA1c inicial: {r[4] if r[4] else 'No registrado'}")
        print(f"   - Glucosa inicial: {r[5] if r[5] else 'No registrado'}")
        print(f"   - Peso inicial: {r[6] if r[6] else 'No registrado'}")
        print(f"   - IMC inicial: {r[7] if r[7] else 'No registrado'}")
        print(f"   - Fecha fin: {r[8] if r[8] else 'Pendiente'}")
        print(f"   - Resultado exitoso: {r[14] if r[14] is not None else 'Pendiente'}")
        print(f"   - Registrado en: {r[15]}")
        
        if r[3] == 'completado':
            print("\n✅ RESULTADO COMPLETADO:")
            print(f"   - HbA1c final: {r[9] if r[9] else 'N/A'}")
            print(f"   - Glucosa final: {r[10] if r[10] else 'N/A'}")
            print(f"   - Peso final: {r[11] if r[11] else 'N/A'}")
            print(f"   - Cumplimiento: {r[12] if r[12] else 'N/A'}%")
            print(f"   - Satisfacción: {r[13] if r[13] else 'N/A'}/5")
    else:
        print("❌ NO HAY BASELINE REGISTRADO")
        print("   El plan no tiene datos de seguimiento registrados.")
        print("   Esto puede significar:")
        print("   - El aprendizaje continuo está deshabilitado")
        print("   - Hubo un error al registrar el baseline")
        print("   - El plan se creó antes de implementar el aprendizaje")
    
    return resultado is not None

def estadisticas_aprendizaje():
    """Muestra estadísticas generales del aprendizaje"""
    print(f"\n{'='*60}")
    print("ESTADÍSTICAS DE APRENDIZAJE CONTINUO")
    print(f"{'='*60}\n")
    
    aprendizaje = obtener_aprendizaje()
    print(f"Estado: {'✅ HABILITADO' if aprendizaje.habilitado else '❌ DESHABILITADO'}")
    
    if not aprendizaje.habilitado:
        print("\n⚠️  Para activar, agregar al .env:")
        print("   APRENDIZAJE_CONTINUO=true")
        return
    
    # Contar resultados
    total_resultados = fetch_one("SELECT COUNT(*) FROM plan_resultado")[0] or 0
    completados = fetch_one("SELECT COUNT(*) FROM plan_resultado WHERE estado='completado'")[0] or 0
    pendientes = fetch_one("SELECT COUNT(*) FROM plan_resultado WHERE estado='pendiente'")[0] or 0
    
    print(f"\n📊 RESULTADOS:")
    print(f"   - Total registrados: {total_resultados}")
    print(f"   - Completados: {completados}")
    print(f"   - Pendientes: {pendientes}")
    
    # Contar patrones aprendidos
    total_patrones = fetch_one("SELECT COUNT(*) FROM aprendizaje_patron")[0] or 0
    ingredientes_exitosos = fetch_one("""
        SELECT COUNT(*) FROM aprendizaje_patron 
        WHERE tipo_patron = 'ingrediente_exitoso'
    """)[0] or 0
    
    print(f"\n🧠 PATRONES APRENDIDOS:")
    print(f"   - Total patrones: {total_patrones}")
    print(f"   - Ingredientes exitosos: {ingredientes_exitosos}")
    
    # Mostrar top ingredientes aprendidos
    if ingredientes_exitosos > 0:
        print(f"\n🏆 TOP 5 INGREDIENTES MÁS EXITOSOS:")
        top_ingredientes = fetch_all("""
            SELECT elemento_nombre, confianza, veces_observado, veces_exitoso
            FROM aprendizaje_patron
            WHERE tipo_patron = 'ingrediente_exitoso'
            ORDER BY confianza DESC, veces_observado DESC
            LIMIT 5
        """)
        
        for i, (nombre, confianza, veces_obs, veces_exit) in enumerate(top_ingredientes, 1):
            print(f"   {i}. {nombre}")
            print(f"      Confianza: {confianza:.1f}% | Observado: {veces_obs} veces | Exitoso: {veces_exit} veces")
    
    # Reentrenamientos
    reentrenamientos = fetch_one("SELECT COUNT(*) FROM modelo_reentrenamiento")[0] or 0
    completados_re = fetch_one("""
        SELECT COUNT(*) FROM modelo_reentrenamiento 
        WHERE estado = 'completado'
    """)[0] or 0
    
    print(f"\n🔄 REENTRENAMIENTOS:")
    print(f"   - Total iniciados: {reentrenamientos}")
    print(f"   - Completados: {completados_re}")
    
    if completados_re > 0:
        ultimo = fetch_one("""
            SELECT version_nueva, fecha_fin, metricas_json
            FROM modelo_reentrenamiento
            WHERE estado = 'completado'
            ORDER BY fecha_fin DESC
            LIMIT 1
        """)
        if ultimo:
            print(f"   - Última versión: {ultimo[0]}")
            print(f"   - Fecha: {ultimo[1]}")

def planes_pendientes():
    """Muestra planes que están pendientes de completar"""
    print(f"\n{'='*60}")
    print("PLANES PENDIENTES DE RESULTADO")
    print(f"{'='*60}\n")
    
    pendientes = fetch_all("""
        SELECT pr.plan_id, pr.paciente_id, pr.fecha_inicio, pr.creado_en,
               p.fecha_fin, p.estado as plan_estado
        FROM plan_resultado pr
        JOIN plan p ON p.id = pr.plan_id
        WHERE pr.estado = 'pendiente'
        ORDER BY pr.fecha_inicio DESC
        LIMIT 10
    """)
    
    if not pendientes:
        print("✅ No hay planes pendientes")
        return
    
    print(f"📋 Encontrados {len(pendientes)} planes pendientes:\n")
    for plan_id, paciente_id, fecha_ini, creado, fecha_fin, estado in pendientes:
        dias_transcurridos = (date.today() - fecha_ini).days if fecha_ini else 0
        print(f"   Plan {plan_id} (Paciente {paciente_id}):")
        print(f"      - Inicio: {fecha_ini}")
        print(f"      - Fin plan: {fecha_fin}")
        print(f"      - Estado plan: {estado}")
        print(f"      - Días transcurridos: {dias_transcurridos}")
        print(f"      - Registrado: {creado}")
        print()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Verificar estado del aprendizaje continuo')
    parser.add_argument('--plan', type=int, help='ID del plan a verificar')
    parser.add_argument('--estadisticas', action='store_true', help='Mostrar estadísticas generales')
    parser.add_argument('--pendientes', action='store_true', help='Mostrar planes pendientes')
    
    args = parser.parse_args()
    
    if args.plan:
        verificar_plan(args.plan)
    elif args.pendientes:
        planes_pendientes()
    else:
        estadisticas_aprendizaje()
        if args.estadisticas:
            planes_pendientes()

if __name__ == "__main__":
    main()

