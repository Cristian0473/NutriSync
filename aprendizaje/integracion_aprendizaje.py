# integracion_aprendizaje.py
# Hooks de integración para aprendizaje continuo
# Se importa en main.py pero no afecta si está deshabilitado

from aprendizaje.aprendizaje_continuo import obtener_aprendizaje
from datetime import date
from Core.bd_conexion import fetch_one


def hook_plan_guardado(plan_id: int, paciente_id: int, fecha_inicio: date):
    """
    Hook llamado cuando se guarda un plan
    Registra baseline para seguimiento futuro
    """
    try:
        aprendizaje = obtener_aprendizaje()
        
        if not aprendizaje.habilitado:
            print(f"⚠️  Aprendizaje continuo deshabilitado para plan {plan_id}")
            return
        
        # Obtener datos clínicos actuales del paciente
        clinico = fetch_one("""
            SELECT hba1c, glucosa_ayunas
            FROM clinico
            WHERE paciente_id = %s
            ORDER BY fecha DESC LIMIT 1
        """, (paciente_id,))
        
        antropo = fetch_one("""
            SELECT peso, talla
            FROM antropometria
            WHERE paciente_id = %s
            ORDER BY fecha DESC LIMIT 1
        """, (paciente_id,))
        
        hba1c = float(clinico[0]) if clinico and clinico[0] else None
        glucosa = float(clinico[1]) if clinico and clinico[1] else None
        peso = float(antropo[0]) if antropo and antropo[0] else None
        imc = None
        if peso and antropo and antropo[1]:
            talla = float(antropo[1])
            imc = peso / (talla ** 2)
        
        # Registrar baseline
        resultado_id = aprendizaje.registrar_resultado_plan(
            plan_id=plan_id,
            paciente_id=paciente_id,
            fecha_inicio=fecha_inicio,
            hba1c_inicial=hba1c,
            glucosa_inicial=glucosa,
            peso_inicial=peso,
            imc_inicial=imc
        )
        
        if resultado_id:
            print(f"✅ Baseline registrado exitosamente para plan {plan_id} (ID: {resultado_id})")
        else:
            print(f"⚠️  No se pudo registrar baseline para plan {plan_id}")
            
    except Exception as e:
        # Log del error para debugging
        print(f"❌ Error en hook_plan_guardado para plan {plan_id}: {e}")
        import traceback
        traceback.print_exc()


def hook_plan_completado(plan_id: int, paciente_id: int, fecha_fin: date):
    """
    Hook llamado cuando un plan se completa
    Actualiza resultados y aprende
    """
    try:
        aprendizaje = obtener_aprendizaje()
        
        # Obtener datos clínicos finales
        clinico = fetch_one("""
            SELECT hba1c, glucosa_ayunas
            FROM clinico
            WHERE paciente_id = %s
            ORDER BY fecha DESC LIMIT 1
        """, (paciente_id,))
        
        antropo = fetch_one("""
            SELECT peso, talla
            FROM antropometria
            WHERE paciente_id = %s
            ORDER BY fecha DESC LIMIT 1
        """, (paciente_id,))
        
        hba1c_final = float(clinico[0]) if clinico and clinico[0] else None
        glucosa_final = float(clinico[1]) if clinico and clinico[1] else None
        peso_final = float(antropo[0]) if antropo and antropo[0] else None
        imc_final = None
        if peso_final and antropo and antropo[1]:
            talla = float(antropo[1])
            imc_final = peso_final / (talla ** 2)
        
        # Actualizar resultado
        aprendizaje.actualizar_resultado_plan(
            plan_id=plan_id,
            fecha_fin=fecha_fin,
            hba1c_final=hba1c_final,
            glucosa_final=glucosa_final,
            peso_final=peso_final,
            imc_final=imc_final,
            cumplimiento_pct=None,  # Se puede calcular después
            satisfaccion=None  # Se puede obtener de feedback
        )
    except Exception as e:
        # Silenciosamente fallar
        pass

