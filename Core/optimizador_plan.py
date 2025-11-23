# optimizador_plan.py
# Optimizador de planes nutricionales para cumplir objetivos

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import copy
import re

@dataclass
class CumplimientoObjetivos:
    """Resultado del análisis de cumplimiento de objetivos"""
    kcal_porcentaje: float
    cho_porcentaje: float
    pro_porcentaje: float
    fat_porcentaje: float
    fibra_porcentaje: float
    promedio_cumplimiento: float
    cumple_objetivos: bool
    detalles: Dict


class OptimizadorPlan:
    """Optimizador de planes nutricionales para cumplir objetivos"""
    
    def __init__(self, umbral_cumplimiento: float = 0.90, max_iteraciones: int = 20, motor_ia=None, perfil_paciente=None, motor_recomendacion=None):
        """
        Inicializa el optimizador
        
        Args:
            umbral_cumplimiento: Porcentaje mínimo de cumplimiento (0.90 = 90%)
            max_iteraciones: Número máximo de iteraciones de optimización
            motor_ia: Instancia opcional de MotorIARecomendaciones (DESACTIVADO - ya no se usa)
            perfil_paciente: Perfil del paciente para validaciones con ML
            motor_recomendacion: Instancia de MotorRecomendacion para usar Modelo 3
        """
        self.umbral_cumplimiento = umbral_cumplimiento
        self.max_iteraciones = max_iteraciones
        self.motor_ia = None  # Desactivado - ya no se usa ChatGPT
        self.motor_recomendacion = motor_recomendacion  # Para usar Modelo 3
        # Convertir perfil_paciente a diccionario si es un objeto
        if perfil_paciente:
            if isinstance(perfil_paciente, dict):
                self.perfil_paciente = perfil_paciente
            else:
                # Es un objeto, convertirlo a diccionario
                self.perfil_paciente = {
                    'edad': getattr(perfil_paciente, 'edad', 0),
                    'imc': getattr(perfil_paciente, 'imc', 0),
                    'sexo': getattr(perfil_paciente, 'sexo', ''),
                    'hba1c': getattr(perfil_paciente, 'hba1c', None)
                }
        else:
            self.perfil_paciente = {}
    
    def calcular_cumplimiento_dia(self, dia: Dict, metas: Dict) -> CumplimientoObjetivos:
        """
        Calcula el cumplimiento de objetivos para un día
        
        Args:
            dia: Diccionario con las comidas del día
            metas: Diccionario con las metas nutricionales
            
        Returns:
            CumplimientoObjetivos con los porcentajes de cumplimiento
        """
        # Calcular totales del día
        totales = {
            'kcal': 0.0,
            'cho': 0.0,
            'pro': 0.0,
            'fat': 0.0,
            'fibra': 0.0
        }
        
        # Recorrer todas las comidas del día
        for tiempo, comida in dia.items():
            if tiempo == 'fecha':
                continue
            
            if isinstance(comida, dict) and 'alimentos' in comida:
                for alimento in comida['alimentos']:
                    totales['kcal'] += float(alimento.get('kcal', 0) or 0)
                    totales['cho'] += float(alimento.get('cho', 0) or 0)
                    totales['pro'] += float(alimento.get('pro', 0) or 0)
                    totales['fat'] += float(alimento.get('fat', 0) or 0)
                    totales['fibra'] += float(alimento.get('fibra', 0) or 0)
        
        # Calcular porcentajes de cumplimiento
        metas_kcal = metas.get('calorias_diarias', 2000)
        metas_cho = metas.get('carbohidratos_g', 250)
        metas_pro = metas.get('proteinas_g', 100)
        metas_fat = metas.get('grasas_g', 65)
        metas_fibra = metas.get('fibra_g', 25)
        
        porcentajes = {
            'kcal': (totales['kcal'] / metas_kcal * 100) if metas_kcal > 0 else 0,
            'cho': (totales['cho'] / metas_cho * 100) if metas_cho > 0 else 0,
            'pro': (totales['pro'] / metas_pro * 100) if metas_pro > 0 else 0,
            'fat': (totales['fat'] / metas_fat * 100) if metas_fat > 0 else 0,
            'fibra': (totales['fibra'] / metas_fibra * 100) if metas_fibra > 0 else 0
        }
        
        # Calcular promedio (sin fibra para el cálculo principal)
        promedio = (porcentajes['kcal'] + porcentajes['cho'] + porcentajes['pro'] + porcentajes['fat']) / 4.0
        
        # Considerar que cumple si está entre 83% y 100% (solo para visualización)
        # El optimizador sigue trabajando hasta 90% como objetivo
        # No exceder más del 100% para evitar valores demasiado altos
        cumple = (
            porcentajes['kcal'] >= 83 and
            porcentajes['kcal'] <= 100 and
            porcentajes['cho'] >= 83 and
            porcentajes['cho'] <= 100 and
            porcentajes['pro'] >= 83 and
            porcentajes['pro'] <= 100 and
            porcentajes['fat'] >= 83 and
            porcentajes['fat'] <= 100
        )
        
        return CumplimientoObjetivos(
            kcal_porcentaje=porcentajes['kcal'],
            cho_porcentaje=porcentajes['cho'],
            pro_porcentaje=porcentajes['pro'],
            fat_porcentaje=porcentajes['fat'],
            fibra_porcentaje=porcentajes['fibra'],
            promedio_cumplimiento=promedio,
            cumple_objetivos=cumple,
            detalles={
                'totales': totales,
                'metas': {
                    'kcal': metas_kcal,
                    'cho': metas_cho,
                    'pro': metas_pro,
                    'fat': metas_fat,
                    'fibra': metas_fibra
                }
            }
        )
    
    def optimizar_plan(self, plan_semanal: Dict, metas: Dict, grupos_alimentos: Dict, perfil, motor_recomendacion) -> Tuple[Dict, Dict]:
        """
        Optimiza un plan nutricional para cumplir objetivos
        
        Args:
            plan_semanal: Plan semanal generado
            metas: Metas nutricionales
            grupos_alimentos: Grupos de alimentos disponibles
            perfil: Perfil del paciente
            motor_recomendacion: Instancia del motor de recomendación
            
        Returns:
            Tupla (plan_optimizado, estadisticas_optimizacion)
        """
        # Guardar grupos_alimentos y motor_recomendacion para uso en validación IA
        self.grupos_alimentos = grupos_alimentos
        self.motor_recomendacion = motor_recomendacion
        self.metas_nutricionales = metas  # Guardar metas para validación post-IA
        
        # Guardar perfil del paciente para validaciones con IA (si no se pasó en __init__)
        if perfil and not self.perfil_paciente:
            self.perfil_paciente = {
                'edad': getattr(perfil, 'edad', 0),
                'imc': getattr(perfil, 'imc', 0),
                'sexo': getattr(perfil, 'sexo', ''),
                'hba1c': getattr(perfil, 'hba1c', None),
                'peso': getattr(perfil, 'peso', None),
                'talla': getattr(perfil, 'talla', None),
                'cc': getattr(perfil, 'cc', None),  # Circunferencia de cintura
                'glucosa_ayunas': getattr(perfil, 'glucosa_ayunas', None),
                'ldl': getattr(perfil, 'ldl', None),
                'actividad': getattr(perfil, 'actividad', 'baja')
            }
        elif not self.perfil_paciente:
            self.perfil_paciente = {}
        elif perfil:
            # Actualizar perfil existente con datos adicionales si están disponibles
            if not self.perfil_paciente.get('peso'):
                self.perfil_paciente['peso'] = getattr(perfil, 'peso', None)
            if not self.perfil_paciente.get('talla'):
                self.perfil_paciente['talla'] = getattr(perfil, 'talla', None)
            if not self.perfil_paciente.get('cc'):
                self.perfil_paciente['cc'] = getattr(perfil, 'cc', None)
            if not self.perfil_paciente.get('glucosa_ayunas'):
                self.perfil_paciente['glucosa_ayunas'] = getattr(perfil, 'glucosa_ayunas', None)
            if not self.perfil_paciente.get('ldl'):
                self.perfil_paciente['ldl'] = getattr(perfil, 'ldl', None)
            if not self.perfil_paciente.get('actividad'):
                self.perfil_paciente['actividad'] = getattr(perfil, 'actividad', 'baja')
        
        plan_optimizado = copy.deepcopy(plan_semanal)
        estadisticas = {
            'iteraciones': 0,
            'dias_optimizados': 0,
            'mejoras_aplicadas': [],
            'cumplimiento_inicial': {},
            'cumplimiento_final': {}
        }
        
        # Obtener el plan_semanal del diccionario si existe, o usar el plan directamente
        plan_semanal_data = plan_optimizado.get('plan_semanal', plan_optimizado)
        if not isinstance(plan_semanal_data, dict):
            plan_semanal_data = plan_optimizado
        
        # Calcular cumplimiento inicial
        cumplimiento_promedio_inicial = {}
        for dia_key, dia_data in plan_semanal_data.items():
            if not dia_key.startswith('dia_'):
                continue
            cumplimiento = self.calcular_cumplimiento_dia(dia_data, metas)
            cumplimiento_promedio_inicial[dia_key] = cumplimiento.promedio_cumplimiento
        
        estadisticas['cumplimiento_inicial'] = cumplimiento_promedio_inicial
        
        # Optimizar cada día
        for iteracion in range(self.max_iteraciones):
            estadisticas['iteraciones'] = iteracion + 1
            mejoras_en_iteracion = 0
            
            for dia_key, dia_data in plan_semanal_data.items():
                if not dia_key.startswith('dia_'):
                    continue
                cumplimiento = self.calcular_cumplimiento_dia(dia_data, metas)
                
                print(f"[DEBUG] DEBUG Optimizador - {dia_key}: Kcal={cumplimiento.kcal_porcentaje:.1f}%, CHO={cumplimiento.cho_porcentaje:.1f}%, PRO={cumplimiento.pro_porcentaje:.1f}%, FAT={cumplimiento.fat_porcentaje:.1f}%, Cumple={cumplimiento.cumple_objetivos}")
                
                # Si ya cumple (entre 90% y 100%), continuar sin optimizar
                if cumplimiento.cumple_objetivos:
                    print(f"[OK] {dia_key} ya cumple objetivos, saltando optimización")
                    continue
                
                # Si excede (más del 100%), reducir valores primero
                # Reducir excesos antes de optimizar para evitar que se acumulen
                exceso_significativo = (
                    cumplimiento.kcal_porcentaje > 100 or 
                    cumplimiento.cho_porcentaje > 100 or 
                    cumplimiento.pro_porcentaje > 100 or 
                    cumplimiento.fat_porcentaje > 100
                )
                
                if exceso_significativo:
                    # Reducir valores que exceden
                    dia_reducido = self._reducir_excesos_dia(
                        dia_data,
                        cumplimiento,
                        metas
                    )
                    # Actualizar el plan con el día reducido
                    plan_semanal_data[dia_key] = dia_reducido
                    if 'plan_semanal' in plan_optimizado:
                        plan_optimizado['plan_semanal'][dia_key] = dia_reducido
                    mejoras_en_iteracion += 1
                    # Continuar optimizando después de reducir excesos
                    dia_data = dia_reducido
                    cumplimiento = self.calcular_cumplimiento_dia(dia_data, metas)
                
                # Intentar optimizar este día
                print(f"[OPT] Intentando optimizar {dia_key}...")
                dia_mejorado = self._optimizar_dia(
                    dia_data, 
                    cumplimiento, 
                    metas, 
                    grupos_alimentos,
                    perfil,
                    motor_recomendacion
                )
                
                # Verificar si mejoró
                cumplimiento_mejorado = self.calcular_cumplimiento_dia(dia_mejorado, metas)
                
                # Considerar mejora si:
                # 1. El promedio mejoró, O
                # 2. Al menos un macronutriente que estaba bajo ahora está mejor
                mejora_detectada = False
                if cumplimiento_mejorado.promedio_cumplimiento > cumplimiento.promedio_cumplimiento:
                    mejora_detectada = True
                else:
                    # Verificar si algún macronutriente bajo mejoró significativamente
                    mejoras_individuales = [
                        (cumplimiento.kcal_porcentaje < 90 and cumplimiento_mejorado.kcal_porcentaje > cumplimiento.kcal_porcentaje + 1),
                        (cumplimiento.fat_porcentaje < 90 and cumplimiento_mejorado.fat_porcentaje > cumplimiento.fat_porcentaje + 1),
                        (cumplimiento.pro_porcentaje < 90 and cumplimiento_mejorado.pro_porcentaje > cumplimiento.pro_porcentaje + 1),
                        (cumplimiento.cho_porcentaje < 90 and cumplimiento_mejorado.cho_porcentaje > cumplimiento.cho_porcentaje + 1)
                    ]
                    if any(mejoras_individuales):
                        mejora_detectada = True
                
                if mejora_detectada:
                    # Verificar que no haya excedido el 100% después de la mejora
                    # Si excedió, reducir excesos antes de guardar
                    if cumplimiento_mejorado.kcal_porcentaje > 100 or cumplimiento_mejorado.cho_porcentaje > 100 or \
                       cumplimiento_mejorado.pro_porcentaje > 100 or cumplimiento_mejorado.fat_porcentaje > 100:
                        print(f"  [WARN]  {dia_key} excedió después de optimizar, reduciendo excesos...")
                        dia_mejorado = self._reducir_excesos_dia(dia_mejorado, cumplimiento_mejorado, metas)
                        cumplimiento_mejorado = self.calcular_cumplimiento_dia(dia_mejorado, metas)
                    
                    plan_semanal_data[dia_key] = dia_mejorado
                    # Actualizar también en plan_optimizado si tiene la estructura con 'plan_semanal'
                    if 'plan_semanal' in plan_optimizado:
                        plan_optimizado['plan_semanal'][dia_key] = dia_mejorado
                    mejoras_en_iteracion += 1
                    estadisticas['dias_optimizados'] += 1
                    estadisticas['mejoras_aplicadas'].append({
                        'iteracion': iteracion + 1,
                        'dia': dia_key,
                        'mejora': cumplimiento_mejorado.promedio_cumplimiento - cumplimiento.promedio_cumplimiento
                    })
                    print(f"[OK] {dia_key} mejorado: {cumplimiento.promedio_cumplimiento:.1f}% → {cumplimiento_mejorado.promedio_cumplimiento:.1f}%")
                else:
                    print(f"[WARN] {dia_key} no mejoró significativamente")
            
            # Si no hubo mejoras en esta iteración, detener
            if mejoras_en_iteracion == 0:
                break
        
        # Calcular cumplimiento final
        cumplimiento_promedio_final = {}
        for dia_key, dia_data in plan_semanal_data.items():
            if not dia_key.startswith('dia_'):
                continue
            cumplimiento = self.calcular_cumplimiento_dia(dia_data, metas)
            cumplimiento_promedio_final[dia_key] = cumplimiento.promedio_cumplimiento
        
        estadisticas['cumplimiento_final'] = cumplimiento_promedio_final
        
        # Validar todas las comidas con IA después de optimizar
        if self.motor_ia and self.motor_ia.client:
            print("[ML] Validando todas las comidas con IA para mejorar combinaciones...")
            plan_optimizado = self._validar_comidas_con_ia(plan_optimizado, plan_semanal_data)
            
            # Validar el plan COMPLETO con IA (análisis global)
            print("[ML] Validando plan COMPLETO con IA (análisis global)...")
            # Validación con IA desactivada - ahora usamos Modelo 3
            # plan_optimizado = self._validar_plan_completo_ia(plan_optimizado, plan_semanal_data, metas)
        
        return plan_optimizado, estadisticas
    
    def _optimizar_dia(self, dia: Dict, cumplimiento: CumplimientoObjetivos, metas: Dict, 
                      grupos_alimentos: Dict, perfil, motor_recomendacion) -> Dict:
        """
        Optimiza un día específico del plan
        
        Args:
            dia: Datos del día a optimizar
            cumplimiento: Cumplimiento actual del día
            metas: Metas nutricionales
            grupos_alimentos: Grupos de alimentos disponibles
            motor_recomendacion: Instancia del motor de recomendación
            
        Returns:
            Día optimizado
        """
        dia_optimizado = copy.deepcopy(dia)
        
        # Identificar qué macronutrientes faltan (solo si están por debajo de 90%)
        # Calcular déficit basado en llegar al 90% como mínimo
        porcentaje_objetivo = 90.0  # Objetivo mínimo de cumplimiento
        
        deficit_kcal = 0
        if cumplimiento.kcal_porcentaje < porcentaje_objetivo:
            deficit_kcal = metas.get('calorias_diarias', 2000) * ((porcentaje_objetivo - cumplimiento.kcal_porcentaje) / 100)
            print(f"  [INFO] Déficit Kcal: {deficit_kcal:.1f} kcal (actual: {cumplimiento.kcal_porcentaje:.1f}%, objetivo: {porcentaje_objetivo}%)")
        
        deficit_cho = 0
        if cumplimiento.cho_porcentaje < porcentaje_objetivo:
            deficit_cho = metas.get('carbohidratos_g', 250) * ((porcentaje_objetivo - cumplimiento.cho_porcentaje) / 100)
            print(f"  [INFO] Déficit CHO: {deficit_cho:.1f} g (actual: {cumplimiento.cho_porcentaje:.1f}%, objetivo: {porcentaje_objetivo}%)")
        
        deficit_pro = 0
        if cumplimiento.pro_porcentaje < porcentaje_objetivo:
            deficit_pro = metas.get('proteinas_g', 100) * ((porcentaje_objetivo - cumplimiento.pro_porcentaje) / 100)
            print(f"  [INFO] Déficit PRO: {deficit_pro:.1f} g (actual: {cumplimiento.pro_porcentaje:.1f}%, objetivo: {porcentaje_objetivo}%)")
        
        deficit_fat = 0
        if cumplimiento.fat_porcentaje < porcentaje_objetivo:
            deficit_fat = metas.get('grasas_g', 65) * ((porcentaje_objetivo - cumplimiento.fat_porcentaje) / 100)
            print(f"  [INFO] Déficit FAT: {deficit_fat:.1f} g (actual: {cumplimiento.fat_porcentaje:.1f}%, objetivo: {porcentaje_objetivo}%)")
        
        # Priorizar ajustes: primero calorías (si están muy bajas), luego grasas, proteínas, carbohidratos
        # Si las calorías están muy bajas (< 80%), priorizar ajustarlas primero
        # Para calorías, usar grupos que aporten calorías: grasas (más densas) y proteínas
        if cumplimiento.kcal_porcentaje < 80:
            ajustes_prioritarios = [
                ('fat', deficit_fat, 'GRUPO7_GRASAS', 'GRUPO5_CARNES'),  # Grasas aportan muchas calorías
                ('pro', deficit_pro, 'GRUPO5_CARNES', 'GRUPO4_LACTEOS'),  # Proteínas también aportan calorías
                ('kcal', deficit_kcal, 'GRUPO7_GRASAS', 'GRUPO5_CARNES'),  # Para calorías, usar grasas y proteínas
                ('cho', deficit_cho, 'GRUPO1_CEREALES', 'GRUPO3_FRUTAS')
            ]
        else:
            ajustes_prioritarios = [
                ('fat', deficit_fat, 'GRUPO7_GRASAS', 'GRUPO5_CARNES'),
                ('pro', deficit_pro, 'GRUPO5_CARNES', 'GRUPO4_LACTEOS'),
                ('cho', deficit_cho, 'GRUPO1_CEREALES', 'GRUPO3_FRUTAS'),
                ('kcal', deficit_kcal, 'GRUPO7_GRASAS', 'GRUPO5_CARNES')  # Para calorías, usar grasas y proteínas
            ]
        
        for macronutriente, deficit, grupo_principal, grupo_secundario in ajustes_prioritarios:
            # Verificar porcentaje actual antes de ajustar
            porcentaje_actual = 0
            if macronutriente == 'fat':
                porcentaje_actual = cumplimiento.fat_porcentaje
            elif macronutriente == 'pro':
                porcentaje_actual = cumplimiento.pro_porcentaje
            elif macronutriente == 'cho':
                porcentaje_actual = cumplimiento.cho_porcentaje
            elif macronutriente == 'kcal':
                porcentaje_actual = cumplimiento.kcal_porcentaje
            
            # Solo ajustar si hay déficit significativo (está por debajo de 90%) Y no excede el 100%
            if deficit > 0.1 and porcentaje_actual < 100 and porcentaje_actual < porcentaje_objetivo:
                # Priorizar ajustar en comidas principales (almuerzo y cena) para mantener desayunos ligeros
                # Solo ajustar en desayuno si el déficit es muy grande
                comidas_para_ajustar = ['alm', 'cena']  # Priorizar comidas principales
                if deficit > 100:  # Déficit muy grande, también ajustar en otras comidas
                    comidas_para_ajustar = ['alm', 'cena', 'mm', 'mt']
                elif deficit > 50:  # Déficit moderado, incluir desayuno
                    comidas_para_ajustar = ['alm', 'cena', 'des']
                # Para déficits pequeños, solo ajustar en comidas principales
                
                for tiempo in comidas_para_ajustar:
                    if tiempo in dia_optimizado:
                        comida = dia_optimizado[tiempo]
                        if isinstance(comida, dict) and 'alimentos' in comida:
                            # Agregar información del tiempo a la comida para las validaciones
                            if 'tiempo' not in comida:
                                comida['tiempo'] = tiempo
                            
                            # Guardar déficit antes del ajuste
                            deficit_antes = deficit
                            
                            # Ajustar alimentos existentes o agregar nuevos
                            self._ajustar_comida_para_macronutriente(
                                comida, 
                                macronutriente, 
                                deficit, 
                                grupo_principal, 
                                grupo_secundario,
                                grupos_alimentos,
                                motor_recomendacion
                            )
                            
                            # Recalcular déficit después del ajuste
                            cumplimiento_actualizado = self.calcular_cumplimiento_dia(dia_optimizado, metas)
                            porcentaje_objetivo = 90.0
                            
                            if macronutriente == 'fat':
                                porcentaje_actual = cumplimiento_actualizado.fat_porcentaje
                                if porcentaje_actual < porcentaje_objetivo:
                                    deficit = metas.get('grasas_g', 65) * ((porcentaje_objetivo - porcentaje_actual) / 100)
                                else:
                                    deficit = 0
                            elif macronutriente == 'pro':
                                porcentaje_actual = cumplimiento_actualizado.pro_porcentaje
                                if porcentaje_actual < porcentaje_objetivo:
                                    deficit = metas.get('proteinas_g', 100) * ((porcentaje_objetivo - porcentaje_actual) / 100)
                                else:
                                    deficit = 0
                            elif macronutriente == 'cho':
                                porcentaje_actual = cumplimiento_actualizado.cho_porcentaje
                                if porcentaje_actual < porcentaje_objetivo:
                                    deficit = metas.get('carbohidratos_g', 250) * ((porcentaje_objetivo - porcentaje_actual) / 100)
                                else:
                                    deficit = 0
                            elif macronutriente == 'kcal':
                                porcentaje_actual = cumplimiento_actualizado.kcal_porcentaje
                                if porcentaje_actual < porcentaje_objetivo:
                                    deficit = metas.get('calorias_diarias', 2000) * ((porcentaje_objetivo - porcentaje_actual) / 100)
                                else:
                                    deficit = 0
                            
                            # Si no hubo cambio significativo, continuar a la siguiente comida
                            if abs(deficit_antes - deficit) < 1.0:
                                continue
                            
                            # Detener si ya se cumplió el objetivo (>= 90%) o se excedió (>= 100%)
                            if deficit <= 0.1 or porcentaje_actual >= porcentaje_objetivo or porcentaje_actual >= 100:
                                break
        
        return dia_optimizado
    
    def _reducir_excesos_dia(self, dia: Dict, cumplimiento: CumplimientoObjetivos, metas: Dict) -> Dict:
        """
        Reduce los valores que exceden el 100% de las metas
        
        Args:
            dia: Datos del día a ajustar
            cumplimiento: Cumplimiento actual del día
            metas: Metas nutricionales
            
        Returns:
            Día con valores reducidos
        """
        dia_reducido = copy.deepcopy(dia)
        
        # Calcular excesos
        exceso_kcal = max(0, cumplimiento.kcal_porcentaje - 100) / 100
        exceso_cho = max(0, cumplimiento.cho_porcentaje - 100) / 100
        exceso_pro = max(0, cumplimiento.pro_porcentaje - 100) / 100
        exceso_fat = max(0, cumplimiento.fat_porcentaje - 100) / 100
        
        # Factor de reducción para llevar a 100% (reducir completamente el exceso)
        # Si está al 120%, necesitamos reducir a 100/120 = 0.833
        factor_reduccion_kcal = 100.0 / max(100.0, cumplimiento.kcal_porcentaje) if cumplimiento.kcal_porcentaje > 100 else 1.0
        factor_reduccion_cho = 100.0 / max(100.0, cumplimiento.cho_porcentaje) if cumplimiento.cho_porcentaje > 100 else 1.0
        factor_reduccion_pro = 100.0 / max(100.0, cumplimiento.pro_porcentaje) if cumplimiento.pro_porcentaje > 100 else 1.0
        factor_reduccion_fat = 100.0 / max(100.0, cumplimiento.fat_porcentaje) if cumplimiento.fat_porcentaje > 100 else 1.0
        
        print(f"   [AJUSTE] Reduciendo excesos: Kcal {cumplimiento.kcal_porcentaje:.1f}% (factor: {factor_reduccion_kcal:.3f}), CHO {cumplimiento.cho_porcentaje:.1f}% (factor: {factor_reduccion_cho:.3f}), PRO {cumplimiento.pro_porcentaje:.1f}% (factor: {factor_reduccion_pro:.3f}), FAT {cumplimiento.fat_porcentaje:.1f}% (factor: {factor_reduccion_fat:.3f})")
        
        # Aplicar reducción a todas las comidas
        for tiempo in ['des', 'mm', 'alm', 'mt', 'cena']:
            if tiempo in dia_reducido:
                comida = dia_reducido[tiempo]
                if isinstance(comida, dict) and 'alimentos' in comida:
                    for alimento in comida['alimentos']:
                        # Reducir cantidades proporcionalmente
                        cantidad_str = alimento.get('cantidad', '0')
                        if isinstance(cantidad_str, str):
                            match = re.search(r'(\d+\.?\d*)', cantidad_str)
                            cantidad_actual = float(match.group(1)) if match else 0
                            unidad_match = re.search(r'[a-zA-Z]+', cantidad_str)
                            unidad = unidad_match.group(0) if unidad_match else 'g'
                            
                            # Determinar qué reducir según el grupo del alimento
                            grupo = alimento.get('grupo', '')
                            factor = 1.0
                            
                            # Aplicar el factor de reducción específico según el grupo del alimento
                            # Si es un alimento de CHO y hay exceso de CHO, usar factor de CHO
                            if grupo in ['GRUPO1_CEREALES', 'GRUPO3_FRUTAS'] and cumplimiento.cho_porcentaje > 100:
                                factor = factor_reduccion_cho
                            # Si es un alimento de PRO y hay exceso de PRO, usar factor de PRO
                            elif grupo in ['GRUPO5_CARNES', 'GRUPO4_LACTEOS'] and cumplimiento.pro_porcentaje > 100:
                                factor = factor_reduccion_pro
                            # Si es un alimento de FAT y hay exceso de FAT, usar factor de FAT
                            elif grupo == 'GRUPO7_GRASAS' and cumplimiento.fat_porcentaje > 100:
                                factor = factor_reduccion_fat
                            # Para otros grupos o si hay exceso general de calorías, usar factor de calorías
                            elif cumplimiento.kcal_porcentaje > 100:
                                factor = factor_reduccion_kcal
                            
                            # Si hay múltiples excesos, usar el factor más restrictivo (menor)
                            factores_aplicables = []
                            if cumplimiento.kcal_porcentaje > 100:
                                factores_aplicables.append(factor_reduccion_kcal)
                            if grupo in ['GRUPO1_CEREALES', 'GRUPO3_FRUTAS'] and cumplimiento.cho_porcentaje > 100:
                                factores_aplicables.append(factor_reduccion_cho)
                            if grupo in ['GRUPO5_CARNES', 'GRUPO4_LACTEOS'] and cumplimiento.pro_porcentaje > 100:
                                factores_aplicables.append(factor_reduccion_pro)
                            if grupo == 'GRUPO7_GRASAS' and cumplimiento.fat_porcentaje > 100:
                                factores_aplicables.append(factor_reduccion_fat)
                            
                            if factores_aplicables:
                                factor = min(factores_aplicables)
                            
                            # Reducir cantidad según el factor calculado
                            nueva_cantidad = cantidad_actual * factor
                            alimento['cantidad'] = f"{round(nueva_cantidad, 1)}{unidad}"
                            
                            # Recalcular macros
                            if 'kcal' in alimento:
                                alimento['kcal'] = round(float(alimento.get('kcal', 0) or 0) * factor, 1)
                            if 'cho' in alimento:
                                alimento['cho'] = round(float(alimento.get('cho', 0) or 0) * factor, 1)
                            if 'pro' in alimento:
                                alimento['pro'] = round(float(alimento.get('pro', 0) or 0) * factor, 1)
                            if 'fat' in alimento:
                                alimento['fat'] = round(float(alimento.get('fat', 0) or 0) * factor, 1)
                            if 'fibra' in alimento:
                                alimento['fibra'] = round(float(alimento.get('fibra', 0) or 0) * factor, 1)
        
        # Recalcular totales de todas las comidas después de reducir
        for tiempo in ['des', 'mm', 'alm', 'mt', 'cena']:
            if tiempo in dia_reducido:
                comida = dia_reducido[tiempo]
                if isinstance(comida, dict) and 'alimentos' in comida:
                    self._recalcular_totales_comida(comida)
        
        return dia_reducido
    
    def _es_combinacion_apetitosa(self, comida: Dict, nuevo_grupo: str, nuevo_nombre: str) -> bool:
        """
        Verifica si agregar un alimento de un grupo específico resultaría en una combinación apetitosa
        
        Args:
            comida: Diccionario de la comida actual
            nuevo_grupo: Grupo del alimento que se quiere agregar
            nuevo_nombre: Nombre del alimento que se quiere agregar
            
        Returns:
            True si la combinación es apetitosa, False si no
        """
        if 'alimentos' not in comida or not comida['alimentos']:
            return True  # Si la comida está vacía, cualquier alimento es válido
        
        alimentos_actuales = comida['alimentos']
        grupos_actuales = [a.get('grupo', '') for a in alimentos_actuales]
        nombres_actuales = [a.get('nombre', '').lower() for a in alimentos_actuales]
        
        # Obtener el tiempo de comida del contexto (si está disponible)
        tiempo = comida.get('tiempo', '')
        
        # Reglas de combinación no apetitosa:
        
        # 1. No agregar mantequilla/aceites en meriendas si ya hay grasas
        if nuevo_grupo == 'GRUPO7_GRASAS' and tiempo in ['mm', 'mt']:
            if 'GRUPO7_GRASAS' in grupos_actuales:
                return False
            # No agregar mantequilla si ya hay otros alimentos grasos
            if 'mantequilla' in nuevo_nombre.lower():
                tiene_grasas = any('grasa' in g.lower() or 'aceite' in n.lower() or 'mantequilla' in n.lower() 
                                  for g, n in zip(grupos_actuales, nombres_actuales))
                if tiene_grasas:
                    return False
        
        # 2. No agregar carnes en desayuno si ya hay legumbres grandes (frijoles, lentejas, garbanzos)
        if nuevo_grupo == 'GRUPO5_CARNES' and tiempo == 'des':
            legumbres_grandes = ['frijol', 'lenteja', 'garbanzo', 'alubia', 'haba']
            tiene_legumbres = any(legumbre in nombre for nombre in nombres_actuales for legumbre in legumbres_grandes)
            if tiene_legumbres:
                return False
        
        # 3. No agregar múltiples grasas en meriendas (media mañana/media tarde)
        if tiempo in ['mm', 'mt']:
            if nuevo_grupo == 'GRUPO7_GRASAS' and 'GRUPO7_GRASAS' in grupos_actuales:
                return False
        
        # 4. Limitar cantidad de grupos diferentes en desayuno (máximo 4-5 grupos)
        if tiempo == 'des':
            grupos_unicos = len(set(grupos_actuales))
            if grupos_unicos >= 5 and nuevo_grupo not in grupos_actuales:
                return False
        
        # 5. Evitar combinaciones extrañas en meriendas (ej: mantequilla + batata repetida)
        if tiempo in ['mm', 'mt']:
            # Si ya hay mantequilla, no agregar más grasas
            if 'mantequilla' in ' '.join(nombres_actuales).lower() and nuevo_grupo == 'GRUPO7_GRASAS':
                return False
        
        return True
    
    def _ajustar_comida_para_macronutriente(self, comida: Dict, macronutriente: str, deficit: float,
                                           grupo_principal: Optional[str], grupo_secundario: Optional[str],
                                           grupos_alimentos: Dict, motor_recomendacion) -> None:
        """
        Ajusta una comida para aumentar un macronutriente específico
        
        Args:
            comida: Diccionario de la comida a ajustar
            macronutriente: 'fat', 'pro', 'cho', 'kcal'
            deficit: Cantidad que falta (en gramos o kcal)
            grupo_principal: Grupo de alimentos principal para este macronutriente
            grupo_secundario: Grupo secundario
            grupos_alimentos: Grupos de alimentos disponibles
            motor_recomendacion: Instancia del motor de recomendación
        """
        if 'alimentos' not in comida:
            return
        
        # Buscar alimentos del grupo principal en la comida
        alimentos_grupo_principal = [
            a for a in comida['alimentos']
            if grupo_principal and a.get('grupo') == grupo_principal
        ]
        
        # Si hay alimentos del grupo principal, aumentar su cantidad
        # Priorizar aumentar el alimento existente en lugar de agregar uno nuevo
        if alimentos_grupo_principal:
            # Si hay múltiples alimentos del mismo grupo, aumentar el que más aporta del macronutriente
            mejor_alimento_existente = max(
                alimentos_grupo_principal,
                key=lambda x: float(x.get(macronutriente, 0) or 0) if macronutriente in ['fat', 'pro', 'cho'] else float(x.get('kcal', 0) or 0)
            )
            
            # Calcular cuánto aumentar
            valor_actual = float(mejor_alimento_existente.get(macronutriente, 0) or 0)
            
            # Manejar cantidad que puede ser string ("100g") o número
            cantidad_str = mejor_alimento_existente.get('cantidad', '0')
            if isinstance(cantidad_str, str):
                # Extraer número del string (ej: "100g" -> 100)
                match = re.search(r'(\d+\.?\d*)', cantidad_str)
                cantidad_actual = float(match.group(1)) if match else 0
                unidad_match = re.search(r'[a-zA-Z]+', cantidad_str)
                unidad = unidad_match.group(0) if unidad_match else 'g'
            else:
                cantidad_actual = float(cantidad_str or 0)
                unidad = mejor_alimento_existente.get('unidad', 'g')
            
            if cantidad_actual > 0 and valor_actual > 0:
                # Calcular factor de aumento necesario
                valor_por_gramo = valor_actual / cantidad_actual
                gramos_necesarios = deficit / valor_por_gramo if valor_por_gramo > 0 else 0
                
                # Aumentar cantidad (máximo 80% más para mantener comidas balanceadas)
                # Si el déficit es muy grande, permitir hasta 100% más
                max_aumento = cantidad_actual * 1.0 if deficit > 50 else cantidad_actual * 0.8
                aumento = min(gramos_necesarios, max_aumento)
                nueva_cantidad = cantidad_actual + aumento
                
                # Actualizar cantidad (mantener formato string si era string)
                if isinstance(cantidad_str, str):
                    mejor_alimento_existente['cantidad'] = f"{round(nueva_cantidad, 1)}{unidad}"
                else:
                    mejor_alimento_existente['cantidad'] = round(nueva_cantidad, 1)
                
                # Recalcular valores nutricionales proporcionalmente
                factor = nueva_cantidad / cantidad_actual
                mejor_alimento_existente['kcal'] = round(float(mejor_alimento_existente.get('kcal', 0) or 0) * factor, 1)
                mejor_alimento_existente['cho'] = round(float(mejor_alimento_existente.get('cho', 0) or 0) * factor, 1)
                mejor_alimento_existente['pro'] = round(float(mejor_alimento_existente.get('pro', 0) or 0) * factor, 1)
                mejor_alimento_existente['fat'] = round(float(mejor_alimento_existente.get('fat', 0) or 0) * factor, 1)
                if 'fibra' in mejor_alimento_existente:
                    mejor_alimento_existente['fibra'] = round(float(mejor_alimento_existente.get('fibra', 0) or 0) * factor, 1)
                
                # Actualizar totales de la comida
                self._recalcular_totales_comida(comida)
                
                # Reducir déficit
                deficit -= aumento * valor_por_gramo
        
        # Si aún falta, intentar agregar alimento nuevo del grupo principal primero
        # PERO solo si no existe ya un alimento de ese grupo en la comida (para evitar duplicados)
        if deficit > 0.1 and grupo_principal and grupo_principal in grupos_alimentos:
            # Verificar si ya existe un alimento del grupo principal en la comida
            alimentos_existentes_grupo = [
                a for a in comida['alimentos']
                if a.get('grupo') == grupo_principal
            ]
            
            # Solo agregar si NO existe ya un alimento de ese grupo
            # (para mantener comidas balanceadas, máximo 1 alimento por grupo)
            if not alimentos_existentes_grupo:
                alimentos_disponibles = grupos_alimentos[grupo_principal]
                if alimentos_disponibles:
                    # Filtrar alimentos que resulten en combinaciones apetitosas
                    alimentos_apetitosos = []
                    for alimento in alimentos_disponibles:
                        nombre_alimento = alimento.get('nombre', '')
                        if self._es_combinacion_apetitosa(comida, grupo_principal, nombre_alimento):
                            alimentos_apetitosos.append(alimento)
                    
                    # Si no hay alimentos apetitosos, usar todos (mejor algo que nada)
                    if not alimentos_apetitosos:
                        alimentos_apetitosos = alimentos_disponibles
                    
                    # Seleccionar alimento con alto contenido del macronutriente
                    mejor_alimento = max(
                        alimentos_apetitosos,
                        key=lambda x: float(x.get(macronutriente, 0) or 0) if macronutriente in ['fat', 'pro', 'cho'] else float(x.get('kcal', 0) or 0)
                    )
                    
                    # Calcular cantidad necesaria (valores en grupos_alimentos son por 100g)
                    valor_por_100g = float(mejor_alimento.get(macronutriente, 0) or 0) if macronutriente in ['fat', 'pro', 'cho'] else float(mejor_alimento.get('kcal', 0) or 0)
                    cantidad_necesaria = (deficit / valor_por_100g * 100) if valor_por_100g > 0 else 0
                    
                    # Limitar cantidad razonable (máximo 200g para mantener comidas balanceadas)
                    cantidad_necesaria = min(cantidad_necesaria, 200)
                    
                    if cantidad_necesaria > 5:  # Solo agregar si es una cantidad significativa
                        nuevo_alimento = {
                            'nombre': mejor_alimento.get('nombre', ''),
                            'grupo': mejor_alimento.get('grupo', ''),
                            'cantidad': f"{round(cantidad_necesaria, 1)}g",
                            'unidad': 'g',
                            'kcal': round(float(mejor_alimento.get('kcal', 0) or 0) * cantidad_necesaria / 100, 1),
                            'cho': round(float(mejor_alimento.get('cho', 0) or 0) * cantidad_necesaria / 100, 1),
                            'pro': round(float(mejor_alimento.get('pro', 0) or 0) * cantidad_necesaria / 100, 1),
                            'fat': round(float(mejor_alimento.get('fat', 0) or 0) * cantidad_necesaria / 100, 1),
                            'fibra': round(float(mejor_alimento.get('fibra', 0) or 0) * cantidad_necesaria / 100, 1)
                        }
                        
                        # Validar combinación con IA si está disponible (solo para comidas principales)
                        tiempo = comida.get('tiempo', '')
                        # Usar Modelo 3 para evaluar combinaciones (reemplaza ChatGPT)
                        if self.motor_recomendacion and tiempo in ['des', 'alm', 'cena']:
                            alimentos_temporal = comida['alimentos'] + [nuevo_alimento]
                            # Convertir a formato para Modelo 3
                            combinacion_ml = [
                                {
                                    'nombre': a.get('nombre', ''),
                                    'grupo': a.get('grupo', ''),
                                    'kcal': a.get('kcal', 0),
                                    'cho': a.get('cho', 0),
                                    'pro': a.get('pro', 0),
                                    'fat': a.get('fat', 0),
                                    'fibra': 0  # No disponible en este contexto
                                }
                                for a in alimentos_temporal
                            ]
                            contexto = {
                                'tiempo_comida': tiempo,
                                'hora': 12 if tiempo == 'alm' else (8 if tiempo == 'des' else 20)
                            }
                            # Preparar perfil como diccionario para el modelo
                            if isinstance(self.perfil_paciente, dict):
                                perfil_dict = self.perfil_paciente
                            else:
                                perfil_dict = {
                                    'edad': getattr(self.perfil_paciente, 'edad', 50),
                                    'sexo': getattr(self.perfil_paciente, 'sexo', 'M'),
                                    'imc': getattr(self.perfil_paciente, 'imc', 25),
                                    'hba1c': getattr(self.perfil_paciente, 'hba1c', None),
                                    'glucosa_ayunas': getattr(self.perfil_paciente, 'glucosa_ayunas', None)
                                }
                            
                            score_combinacion = self.motor_recomendacion.evaluar_combinacion_alimentos(
                                perfil_dict,
                                combinacion_ml,
                                contexto
                            )
                            
                            if score_combinacion is not None:
                                print(f"  [ML] Modelo 3 - Score combinación: {score_combinacion:.3f}")
                            
                            # Si el score es muy bajo (< 0.4), rechazar la combinación
                            if score_combinacion is not None and score_combinacion < 0.4:
                                # Si la combinación no es apetitosa, intentar con otro alimento
                                alimentos_alternativos = [a for a in alimentos_apetitosos if a.get('nombre') != mejor_alimento.get('nombre')]
                                if alimentos_alternativos:
                                    mejor_alimento = max(
                                        alimentos_alternativos,
                                        key=lambda x: float(x.get(macronutriente, 0) or 0) if macronutriente in ['fat', 'pro', 'cho'] else float(x.get('kcal', 0) or 0)
                                    )
                                    # Recalcular con el nuevo alimento
                                    valor_por_100g = float(mejor_alimento.get(macronutriente, 0) or 0) if macronutriente in ['fat', 'pro', 'cho'] else float(mejor_alimento.get('kcal', 0) or 0)
                                    cantidad_necesaria = (deficit / valor_por_100g * 100) if valor_por_100g > 0 else 0
                                    cantidad_necesaria = min(cantidad_necesaria, 200)
                                    
                                    nuevo_alimento = {
                                        'nombre': mejor_alimento.get('nombre', ''),
                                        'grupo': mejor_alimento.get('grupo', ''),
                                        'cantidad': f"{round(cantidad_necesaria, 1)}g",
                                        'unidad': 'g',
                                        'kcal': round(float(mejor_alimento.get('kcal', 0) or 0) * cantidad_necesaria / 100, 1),
                                        'cho': round(float(mejor_alimento.get('cho', 0) or 0) * cantidad_necesaria / 100, 1),
                                        'pro': round(float(mejor_alimento.get('pro', 0) or 0) * cantidad_necesaria / 100, 1),
                                        'fat': round(float(mejor_alimento.get('fat', 0) or 0) * cantidad_necesaria / 100, 1),
                                        'fibra': round(float(mejor_alimento.get('fibra', 0) or 0) * cantidad_necesaria / 100, 1)
                                    }
                        
                        comida['alimentos'].append(nuevo_alimento)
                        
                        # Verificar y limitar verduras después de agregar
                        self._limitar_verduras_por_comida(comida, tiempo_comida=None)
                        
                        self._recalcular_totales_comida(comida)
                        return  # Salir después de agregar alimento del grupo principal
        
        # Si aún falta y hay grupo secundario, agregar alimento nuevo
        # PERO solo si no existe ya un alimento de ese grupo en la comida
        if deficit > 0.1 and grupo_secundario and grupo_secundario in grupos_alimentos:
            # Verificar si ya existe un alimento del grupo secundario en la comida
            alimentos_existentes_grupo_sec = [
                a for a in comida['alimentos']
                if a.get('grupo') == grupo_secundario
            ]
            
            # Solo agregar si NO existe ya un alimento de ese grupo
            if not alimentos_existentes_grupo_sec:
                alimentos_disponibles = grupos_alimentos[grupo_secundario]
                if alimentos_disponibles:
                    # Seleccionar alimento con alto contenido del macronutriente
                    # Los ingredientes en grupos_alimentos tienen valores por 100g
                    mejor_alimento = max(
                        alimentos_disponibles,
                        key=lambda x: float(x.get(macronutriente, 0) or 0) if macronutriente in ['fat', 'pro', 'cho'] else float(x.get('kcal', 0) or 0)
                    )
                    
                    # Calcular cantidad necesaria (valores en grupos_alimentos son por 100g)
                    valor_por_100g = float(mejor_alimento.get(macronutriente, 0) or 0) if macronutriente in ['fat', 'pro', 'cho'] else float(mejor_alimento.get('kcal', 0) or 0)
                    cantidad_necesaria = (deficit / valor_por_100g * 100) if valor_por_100g > 0 else 0
                    
                    # Limitar cantidad razonable (máximo 200g para mantener comidas balanceadas)
                    cantidad_necesaria = min(cantidad_necesaria, 200)
                    
                    if cantidad_necesaria > 5:  # Solo agregar si es una cantidad significativa
                        nuevo_alimento = {
                            'nombre': mejor_alimento.get('nombre', ''),
                            'grupo': mejor_alimento.get('grupo', ''),
                            'cantidad': f"{round(cantidad_necesaria, 1)}g",  # Formato string como espera el frontend
                            'unidad': 'g',
                            'kcal': round(float(mejor_alimento.get('kcal', 0) or 0) * cantidad_necesaria / 100, 1),
                            'cho': round(float(mejor_alimento.get('cho', 0) or 0) * cantidad_necesaria / 100, 1),
                            'pro': round(float(mejor_alimento.get('pro', 0) or 0) * cantidad_necesaria / 100, 1),
                            'fat': round(float(mejor_alimento.get('fat', 0) or 0) * cantidad_necesaria / 100, 1),
                            'fibra': round(float(mejor_alimento.get('fibra', 0) or 0) * cantidad_necesaria / 100, 1)
                        }
                        
                        comida['alimentos'].append(nuevo_alimento)
                        self._recalcular_totales_comida(comida)
    
    def _limitar_verduras_por_comida(self, comida: Dict, tiempo_comida: Optional[str] = None) -> None:
        """Limita la cantidad de verduras por comida según el tiempo de comida"""
        if not tiempo_comida:
            # Intentar inferir el tiempo de comida desde el contexto
            # Si no se puede, usar límite por defecto
            tiempo_comida = 'cena'  # Por defecto, más restrictivo
        
        # Límites de verduras por comida (en gramos)
        max_verduras_g = {
            'des': 150,   # Desayuno: máximo 150g de verduras
            'mm': 100,    # Merienda: máximo 100g
            'alm': 300,   # Almuerzo: máximo 300g
            'mt': 100,    # Merienda: máximo 100g
            'cena': 200   # Cena: máximo 200g (reducido para diabéticos)
        }.get(tiempo_comida, 200)
        
        # Obtener todas las verduras en la comida
        verduras_en_comida = [al for al in comida.get('alimentos', []) if al.get('grupo', '').startswith('GRUPO2_VERDURAS')]
        
        if not verduras_en_comida:
            return
        
        # Calcular total de verduras en gramos
        total_verduras_g = 0
        for al in verduras_en_comida:
            cantidad_str = str(al.get('cantidad', '0g'))
            cantidad_num = float(re.sub(r'[^\d.]', '', cantidad_str))
            total_verduras_g += cantidad_num
        
        # Si excede el límite, reducir proporcionalmente
        if total_verduras_g > max_verduras_g:
            factor_reduccion = max_verduras_g / total_verduras_g
            for al in verduras_en_comida:
                cantidad_str = str(al.get('cantidad', '0g'))
                cantidad_num = float(re.sub(r'[^\d.]', '', cantidad_str))
                cantidad_nueva = cantidad_num * factor_reduccion
                al['cantidad'] = f"{round(cantidad_nueva, 1)}g"
                # Recalcular nutrientes
                factor = cantidad_nueva / 100.0
                al['kcal'] = round(float(al.get('kcal', 0) or 0) * factor, 1)
                al['cho'] = round(float(al.get('cho', 0) or 0) * factor, 1)
                al['pro'] = round(float(al.get('pro', 0) or 0) * factor, 1)
                al['fat'] = round(float(al.get('fat', 0) or 0) * factor, 1)
                al['fibra'] = round(float(al.get('fibra', 0) or 0) * factor, 1)
    
    def _recalcular_totales_comida(self, comida: Dict) -> None:
        """Recalcula los totales nutricionales de una comida"""
        if 'alimentos' not in comida:
            return
        
        totales = {
            'kcal': 0.0,
            'cho': 0.0,
            'pro': 0.0,
            'fat': 0.0,
            'fibra': 0.0
        }
        
        for alimento in comida['alimentos']:
            totales['kcal'] += float(alimento.get('kcal', 0) or 0)
            totales['cho'] += float(alimento.get('cho', 0) or 0)
            totales['pro'] += float(alimento.get('pro', 0) or 0)
            totales['fat'] += float(alimento.get('fat', 0) or 0)
            totales['fibra'] += float(alimento.get('fibra', 0) or 0)
        
        # Actualizar totales en la comida
        if 'kcal_total' in comida:
            comida['kcal_total'] = round(totales['kcal'], 1)
        if 'cho_total' in comida:
            comida['cho_total'] = round(totales['cho'], 1)
        if 'pro_total' in comida:
            comida['pro_total'] = round(totales['pro'], 1)
        if 'fat_total' in comida:
            comida['fat_total'] = round(totales['fat'], 1)
        if 'fibra_total' in comida:
            comida['fibra_total'] = round(totales['fibra'], 1)
    
    def _validar_comidas_con_ia(self, plan_optimizado: Dict, plan_semanal_data: Dict) -> Dict:
        """
        Valida todas las comidas del plan con Modelo 3 (ML) para mejorar combinaciones
        
        Args:
            plan_optimizado: Plan optimizado completo
            plan_semanal_data: Datos del plan semanal
            
        Returns:
            Plan optimizado con validaciones de ML aplicadas
        """
        if not self.motor_recomendacion:
            print("[WARN]  Motor de recomendación no disponible para validación ML")
            return plan_optimizado
        
        print(f"[DEBUG] Iniciando validación IA - perfil_paciente: {getattr(self, 'perfil_paciente', {})}")
        comidas_validadas = 0
        comidas_mejoradas = 0
        
        # Obtener todos los alimentos disponibles de grupos_alimentos
        alimentos_disponibles = []
        if hasattr(self, 'grupos_alimentos') and self.grupos_alimentos:
            for grupo, lista_alimentos in self.grupos_alimentos.items():
                if isinstance(lista_alimentos, list):
                    alimentos_disponibles.extend(lista_alimentos)
        
        # Usar plan_optimizado directamente para asegurar que los cambios se reflejen
        plan_data = plan_optimizado.get('plan_semanal', plan_semanal_data)
        
        for dia_key, dia_data in plan_data.items():
            if not dia_key.startswith('dia_'):
                continue
            
            # Las comidas están directamente en el día como claves (des, mm, alm, mt, cena)
            tiempos_comida = ['des', 'mm', 'alm', 'mt', 'cena']
            
            for tiempo in tiempos_comida:
                if tiempo not in dia_data:
                    continue
                
                comida = dia_data[tiempo]
                if not isinstance(comida, dict):
                    continue
                
                alimentos = comida.get('alimentos', [])
                
                # Validar solo comidas principales
                if tiempo in ['des', 'alm', 'cena'] and len(alimentos) > 0:
                    nombres_alimentos = [a.get('nombre', 'N/A') for a in alimentos]
                    print(f"[ML] Validando con IA: {dia_key} - {tiempo} ({len(alimentos)} alimentos: {', '.join(nombres_alimentos[:3])}...)")
                    
                    try:
                        # Usar Modelo 3 para evaluar combinación
                        combinacion_ml = [
                            {
                                'nombre': a.get('nombre', ''),
                                'grupo': a.get('grupo', ''),
                                'kcal': float(a.get('kcal', 0) or 0),
                                'cho': float(a.get('cho', 0) or 0),
                                'pro': float(a.get('pro', 0) or 0),
                                'fat': float(a.get('fat', 0) or 0),
                                'fibra': float(a.get('fibra', 0) or 0)
                            }
                            for a in alimentos
                        ]
                        contexto = {
                            'tiempo_comida': tiempo,
                            'hora': 12 if tiempo == 'alm' else (8 if tiempo == 'des' else 20)
                        }
                        # Preparar perfil como diccionario para el modelo
                        if isinstance(self.perfil_paciente, dict):
                            perfil_dict = self.perfil_paciente
                        else:
                            perfil_dict = {
                                'edad': getattr(self.perfil_paciente, 'edad', 50),
                                'sexo': getattr(self.perfil_paciente, 'sexo', 'M'),
                                'imc': getattr(self.perfil_paciente, 'imc', 25),
                                'hba1c': getattr(self.perfil_paciente, 'hba1c', None),
                                'glucosa_ayunas': getattr(self.perfil_paciente, 'glucosa_ayunas', None)
                            }
                        
                        score_combinacion = self.motor_recomendacion.evaluar_combinacion_alimentos(
                            perfil_dict,
                            combinacion_ml,
                            contexto
                        )
                        comidas_validadas += 1
                        
                        # Si el score es muy bajo (< 0.4), considerar la combinación como no adecuada
                        if score_combinacion is not None and score_combinacion < 0.4:
                            print(f"[WARN]  Modelo 3 detectó combinación de baja calidad en {dia_key} - {tiempo}: score={score_combinacion:.2f}")
                            
                            # El Modelo 3 no sugiere alimentos específicos, solo evalúa la combinación
                            # Por ahora, solo registramos la advertencia
                            alimentos_a_remover = []
                            alimentos_a_agregar = []
                            
                            if alimentos_a_remover or alimentos_a_agregar:
                                print(f"   [OPT] Aplicando correcciones: remover {len(alimentos_a_remover)}, agregar {len(alimentos_a_agregar)}")
                                
                                # Calcular nutrientes que se perderán al remover alimentos
                                nutrientes_removidos = {'kcal': 0, 'cho': 0, 'pro': 0, 'fat': 0, 'fibra': 0}
                                nombres_a_remover = [n.lower().strip() for n in alimentos_a_remover]
                                
                                for al in alimentos:
                                    nombre_al = al.get('nombre', '').lower().strip()
                                    if nombre_al in nombres_a_remover:
                                        nutrientes_removidos['kcal'] += float(al.get('kcal', 0) or 0)
                                        nutrientes_removidos['cho'] += float(al.get('cho', 0) or 0)
                                        nutrientes_removidos['pro'] += float(al.get('pro', 0) or 0)
                                        nutrientes_removidos['fat'] += float(al.get('fat', 0) or 0)
                                        nutrientes_removidos['fibra'] += float(al.get('fibra', 0) or 0)
                                
                                # Crear nueva lista de alimentos (sin los removidos)
                                nuevos_alimentos = []
                                for al in alimentos:
                                    nombre_al = al.get('nombre', '').lower().strip()
                                    if nombre_al not in nombres_a_remover:
                                        nuevos_alimentos.append(al)
                                    else:
                                        print(f"      [WARN] Removido: {al.get('nombre', 'N/A')}")
                                
                                # Limitar cantidad de alimentos por comida (especialmente para diabéticos)
                                max_alimentos_por_comida = {
                                    'des': 4,  # Desayuno: máximo 4 alimentos
                                    'mm': 2,   # Merienda: máximo 2 alimentos
                                    'alm': 5,  # Almuerzo: máximo 5 alimentos
                                    'mt': 2,   # Merienda: máximo 2 alimentos
                                    'cena': 5  # Cena: máximo 5 alimentos
                                }.get(tiempo, 4)
                                
                                # Limitar especialmente frutas/carbohidratos por comida (máximo 1-2 frutas por comida)
                                frutas_en_comida = sum(1 for al in nuevos_alimentos if al.get('grupo', '').startswith('GRUPO3_FRUTAS'))
                                max_frutas = 1 if tiempo in ['des', 'mm', 'mt'] else 2
                                
                                # Limitar cantidad de verduras por comida (especialmente en cena para diabéticos)
                                verduras_en_comida = [al for al in nuevos_alimentos if al.get('grupo', '').startswith('GRUPO2_VERDURAS')]
                                total_verduras_g = sum(float(re.sub(r'[^\d.]', '', str(al.get('cantidad', '0g')))) for al in verduras_en_comida)
                                
                                # Límites de verduras por comida (en gramos)
                                max_verduras_g = {
                                    'des': 150,   # Desayuno: máximo 150g de verduras
                                    'mm': 100,    # Merienda: máximo 100g
                                    'alm': 300,   # Almuerzo: máximo 300g
                                    'mt': 100,    # Merienda: máximo 100g
                                    'cena': 200   # Cena: máximo 200g (reducido para diabéticos)
                                }.get(tiempo, 200)
                                
                                # Si excede el límite, reducir proporcionalmente las verduras
                                if total_verduras_g > max_verduras_g:
                                    factor_reduccion = max_verduras_g / total_verduras_g
                                    print(f"      [WARN]  Reduciendo verduras: {total_verduras_g:.1f}g → {max_verduras_g:.1f}g (factor: {factor_reduccion:.2f})")
                                    for al in nuevos_alimentos:
                                        if al.get('grupo', '').startswith('GRUPO2_VERDURAS'):
                                            cantidad_str = str(al.get('cantidad', '0g'))
                                            cantidad_num = float(re.sub(r'[^\d.]', '', cantidad_str))
                                            cantidad_nueva = cantidad_num * factor_reduccion
                                            al['cantidad'] = f"{round(cantidad_nueva, 1)}g"
                                            # Recalcular nutrientes
                                            factor = cantidad_nueva / 100.0
                                            al['kcal'] = round(float(al.get('kcal', 0) or 0) * factor, 1)
                                            al['cho'] = round(float(al.get('cho', 0) or 0) * factor, 1)
                                            al['pro'] = round(float(al.get('pro', 0) or 0) * factor, 1)
                                            al['fat'] = round(float(al.get('fat', 0) or 0) * factor, 1)
                                            al['fibra'] = round(float(al.get('fibra', 0) or 0) * factor, 1)
                                
                                # Agregar alimentos sugeridos, compensando nutrientes removidos
                                nutrientes_agregados = {'kcal': 0, 'cho': 0, 'pro': 0, 'fat': 0, 'fibra': 0}
                                alimentos_agregados_count = 0
                                
                                for nombre_sugerido in alimentos_a_agregar:
                                    # Verificar límites
                                    if len(nuevos_alimentos) >= max_alimentos_por_comida:
                                        print(f"      [WARN]  Límite de alimentos alcanzado ({max_alimentos_por_comida})")
                                        break
                                    
                                    # Buscar el alimento en la base de datos
                                    alimento_encontrado = None
                                    nombre_buscar = nombre_sugerido.lower().strip()
                                    
                                    for al_db in alimentos_disponibles:
                                        nombre_db = al_db.get('nombre', '').lower().strip()
                                        if nombre_db == nombre_buscar:
                                            alimento_encontrado = al_db
                                            break
                                    
                                    if alimento_encontrado:
                                        grupo_alimento = alimento_encontrado.get('grupo', '')
                                        
                                        # Verificar límite de frutas
                                        if grupo_alimento.startswith('GRUPO3_FRUTAS') and frutas_en_comida >= max_frutas:
                                            print(f"      [WARN]  Límite de frutas alcanzado ({max_frutas}) - omitiendo: {nombre_sugerido}")
                                            continue
                                        
                                        # Calcular cantidad para compensar nutrientes removidos
                                        # Distribuir la compensación entre los alimentos a agregar
                                        num_alimentos_restantes = len(alimentos_a_agregar) - alimentos_agregados_count
                                        if num_alimentos_restantes > 0:
                                            # Calcular qué nutrientes necesita este alimento específico
                                            # Priorizar compensar el macronutriente principal del alimento
                                            kcal_por_100g = float(alimento_encontrado.get('kcal', 0) or 0)
                                            cho_por_100g = float(alimento_encontrado.get('cho', 0) or 0)
                                            pro_por_100g = float(alimento_encontrado.get('pro', 0) or 0)
                                            fat_por_100g = float(alimento_encontrado.get('fat', 0) or 0)
                                            
                                            # Calcular cantidad basada en el nutriente principal que aporta
                                            cantidad_sugerida = 100.0  # Por defecto
                                            
                                            if kcal_por_100g > 0:
                                                # Si es un alimento rico en calorías, calcular para compensar kcal
                                                if nutrientes_removidos['kcal'] > nutrientes_agregados['kcal']:
                                                    deficit_kcal = nutrientes_removidos['kcal'] - nutrientes_agregados['kcal']
                                                    cantidad_por_kcal = (deficit_kcal / num_alimentos_restantes) / kcal_por_100g * 100
                                                    cantidad_sugerida = max(cantidad_sugerida, cantidad_por_kcal)
                                            
                                            # Ajustar según el macronutriente principal
                                            if cho_por_100g > pro_por_100g and cho_por_100g > fat_por_100g:
                                                # Es principalmente carbohidrato
                                                if nutrientes_removidos['cho'] > nutrientes_agregados['cho']:
                                                    deficit_cho = nutrientes_removidos['cho'] - nutrientes_agregados['cho']
                                                    cantidad_por_cho = (deficit_cho / num_alimentos_restantes) / cho_por_100g * 100
                                                    cantidad_sugerida = max(cantidad_sugerida, cantidad_por_cho)
                                            elif pro_por_100g > fat_por_100g:
                                                # Es principalmente proteína
                                                if nutrientes_removidos['pro'] > nutrientes_agregados['pro']:
                                                    deficit_pro = nutrientes_removidos['pro'] - nutrientes_agregados['pro']
                                                    cantidad_por_pro = (deficit_pro / num_alimentos_restantes) / pro_por_100g * 100
                                                    cantidad_sugerida = max(cantidad_sugerida, cantidad_por_pro)
                                            else:
                                                # Es principalmente grasa
                                                if nutrientes_removidos['fat'] > nutrientes_agregados['fat']:
                                                    deficit_fat = nutrientes_removidos['fat'] - nutrientes_agregados['fat']
                                                    cantidad_por_fat = (deficit_fat / num_alimentos_restantes) / fat_por_100g * 100
                                                    cantidad_sugerida = max(cantidad_sugerida, cantidad_por_fat)
                                            
                                            # Limitar cantidad razonable (30g - 200g)
                                            cantidad_sugerida = max(30.0, min(cantidad_sugerida, 200.0))
                                            
                                            # Crear nuevo alimento
                                            nuevo_alimento = {
                                                'nombre': alimento_encontrado.get('nombre', ''),
                                                'grupo': grupo_alimento,
                                                'cantidad': f"{round(cantidad_sugerida, 1)}g",
                                                'unidad': 'g',
                                                'kcal': round(kcal_por_100g * cantidad_sugerida / 100, 1),
                                                'cho': round(cho_por_100g * cantidad_sugerida / 100, 1),
                                                'pro': round(pro_por_100g * cantidad_sugerida / 100, 1),
                                                'fat': round(fat_por_100g * cantidad_sugerida / 100, 1),
                                                'fibra': round(float(alimento_encontrado.get('fibra', 0) or 0) * cantidad_sugerida / 100, 1)
                                            }
                                            
                                            nuevos_alimentos.append(nuevo_alimento)
                                            alimentos_agregados_count += 1
                                            
                                            # Actualizar nutrientes agregados
                                            nutrientes_agregados['kcal'] += nuevo_alimento['kcal']
                                            nutrientes_agregados['cho'] += nuevo_alimento['cho']
                                            nutrientes_agregados['pro'] += nuevo_alimento['pro']
                                            nutrientes_agregados['fat'] += nuevo_alimento['fat']
                                            nutrientes_agregados['fibra'] += nuevo_alimento['fibra']
                                            
                                            # Actualizar contador de frutas si es necesario
                                            if grupo_alimento.startswith('GRUPO3_FRUTAS'):
                                                frutas_en_comida += 1
                                            
                                            print(f"      [OK] Agregado: {nuevo_alimento['nombre']} - {nuevo_alimento['cantidad']}")
                                    else:
                                        print(f"      [WARN]  No se encontró en BD: {nombre_sugerido}")
                                
                                # Actualizar la comida con los nuevos alimentos
                                if nuevos_alimentos:
                                    comida['alimentos'] = nuevos_alimentos
                                    # Recalcular totales de la comida
                                    self._recalcular_totales_comida(comida)
                                    comidas_mejoradas += 1
                                    print(f"      [OK] Comida corregida: {len(nuevos_alimentos)} alimentos (removidos: {sum(nutrientes_removidos.values()):.1f} nutrientes, agregados: {sum(nutrientes_agregados.values()):.1f} nutrientes)")
                                else:
                                    print(f"      [WARN]  No se pudo corregir: lista de alimentos vacía")
                            else:
                                if validacion.get('sugerencias'):
                                    print(f"   Sugerencias: {', '.join(validacion['sugerencias'][:2])}")
                        else:
                            print(f"[OK] Modelo 3 aprobó: {dia_key} - {tiempo} (score={score_combinacion:.2f})")
                    except Exception as e:
                        print(f"[ERROR] Error al validar con Modelo 3 {dia_key} - {tiempo}: {e}")
                        import traceback
                        traceback.print_exc()
        
        print(f"[OK] Validación ML completada: {comidas_validadas} comidas validadas, {comidas_mejoradas} mejoras sugeridas")
        
        # Después de todas las correcciones, verificar y ajustar cumplimiento de metas por día
        if hasattr(self, 'metas_nutricionales') and self.metas_nutricionales:
            metas_plan = self.metas_nutricionales
            
            if metas_plan:
                print(f"[DEBUG] Verificando cumplimiento de metas después de correcciones IA...")
                for dia_key, dia_data in plan_data.items():
                    if not dia_key.startswith('dia_'):
                        continue
                    
                    # Calcular cumplimiento del día
                    cumplimiento = self.calcular_cumplimiento_dia(dia_data, metas_plan)
                    
                    # PRIMERO: Reducir excesos si hay alguno por encima del 100%
                    if cumplimiento.kcal_porcentaje > 100 or cumplimiento.cho_porcentaje > 100 or \
                       cumplimiento.pro_porcentaje > 100 or cumplimiento.fat_porcentaje > 100:
                        print(f"   [WARN]  {dia_key} tiene excesos después de correcciones IA (Kcal: {cumplimiento.kcal_porcentaje:.1f}%, CHO: {cumplimiento.cho_porcentaje:.1f}%, PRO: {cumplimiento.pro_porcentaje:.1f}%, FAT: {cumplimiento.fat_porcentaje:.1f}%)")
                        # Reducir excesos primero
                        dia_reducido = self._reducir_excesos_dia(dia_data, cumplimiento, metas_plan)
                        plan_data[dia_key] = dia_reducido
                        dia_data = dia_reducido
                        # Recalcular cumplimiento después de reducir
                        cumplimiento = self.calcular_cumplimiento_dia(dia_data, metas_plan)
                        print(f"   [AJUSTE] Excesos reducidos: Kcal: {cumplimiento.kcal_porcentaje:.1f}%, CHO: {cumplimiento.cho_porcentaje:.1f}%, PRO: {cumplimiento.pro_porcentaje:.1f}%, FAT: {cumplimiento.fat_porcentaje:.1f}%")
                    
                    # DESPUÉS: Si algún macronutriente está por debajo del 90%, intentar ajustar
                    if cumplimiento.kcal_porcentaje < 90.0 or cumplimiento.cho_porcentaje < 90.0 or \
                       cumplimiento.pro_porcentaje < 90.0 or cumplimiento.fat_porcentaje < 90.0:
                        print(f"   [WARN]  {dia_key} no cumple metas después de correcciones IA (Kcal: {cumplimiento.kcal_porcentaje:.1f}%, CHO: {cumplimiento.cho_porcentaje:.1f}%, PRO: {cumplimiento.pro_porcentaje:.1f}%, FAT: {cumplimiento.fat_porcentaje:.1f}%)")
                        # Intentar optimizar el día nuevamente (solo si hay déficit, no si hay exceso)
                        try:
                            dia_optimizado = self._optimizar_dia(dia_data, cumplimiento, metas_plan, 
                                                                  getattr(self, 'grupos_alimentos', {}), 
                                                                  getattr(self, 'perfil_paciente', {}),
                                                                  self.motor_recomendacion)
                            # Verificar que no haya empeorado (no exceder 100%)
                            cumplimiento_optimizado = self.calcular_cumplimiento_dia(dia_optimizado, metas_plan)
                            if cumplimiento_optimizado.kcal_porcentaje <= 100 and cumplimiento_optimizado.cho_porcentaje <= 100 and \
                               cumplimiento_optimizado.pro_porcentaje <= 100 and cumplimiento_optimizado.fat_porcentaje <= 100:
                                plan_data[dia_key] = dia_optimizado
                                print(f"   [OK] {dia_key} re-optimizado después de correcciones IA")
                            else:
                                # Si excedió, reducir excesos nuevamente
                                dia_optimizado = self._reducir_excesos_dia(dia_optimizado, cumplimiento_optimizado, metas_plan)
                                plan_data[dia_key] = dia_optimizado
                                print(f"   [OK] {dia_key} re-optimizado y excesos reducidos después de correcciones IA")
                        except Exception as e:
                            print(f"   [WARN]  Error al re-optimizar {dia_key}: {e}")
        
        return plan_optimizado
    
    def _validar_plan_completo_ia(self, plan_optimizado: Dict, plan_semanal_data: Dict, metas: Dict) -> Dict:
        """
        DESACTIVADO: Ya no se usa ChatGPT para validar el plan completo.
        Ahora se usa Modelo 3 para evaluar combinaciones individuales.
        """
        return plan_optimizado
        """
        Valida el plan completo usando IA, analizando todos los días juntos
        
        Args:
            plan_optimizado: Plan optimizado
            plan_semanal_data: Datos del plan semanal
            metas: Metas nutricionales
            
        Returns:
            Plan corregido según validación de IA
        """
        if not self.motor_ia or not self.motor_ia.client:
            return plan_optimizado
        
        if not hasattr(self, 'perfil_paciente') or not self.perfil_paciente:
            print("[WARN]  No hay perfil de paciente para validación completa")
            return plan_optimizado
        
        # Obtener configuración del plan (si está disponible)
        configuracion = {}
        if hasattr(self, 'motor_recomendacion') and self.motor_recomendacion:
            # Intentar obtener configuración desde el motor
            if hasattr(self.motor_recomendacion, '_configuracion_original'):
                config_orig = self.motor_recomendacion._configuracion_original
                if config_orig:
                    configuracion = {
                        'kcal_objetivo': config_orig.get('kcal_objetivo', metas.get('calorias_diarias', 1800)),
                        'cho_pct': config_orig.get('cho_pct', 30),
                        'pro_pct': config_orig.get('pro_pct', 20),
                        'fat_pct': config_orig.get('fat_pct', 50)
                    }
        
        if not configuracion:
            # Calcular desde metas
            kcal = metas.get('calorias_diarias', 1800)
            cho_g = metas.get('carbohidratos_g', 117)
            pro_g = metas.get('proteinas_g', 153)
            fat_g = metas.get('grasas_g', 80)
            configuracion = {
                'kcal_objetivo': kcal,
                'cho_pct': int((cho_g * 4 * 100) / kcal) if kcal > 0 else 30,
                'pro_pct': int((pro_g * 4 * 100) / kcal) if kcal > 0 else 20,
                'fat_pct': int((fat_g * 9 * 100) / kcal) if kcal > 0 else 50
            }
        
        # Preparar alimentos disponibles
        alimentos_disponibles = []
        if hasattr(self, 'grupos_alimentos') and self.grupos_alimentos:
            alimentos_disponibles = [item for sublist in self.grupos_alimentos.values() for item in sublist]
        
        # Llamar a la validación completa de IA
        try:
            validacion_completa = self.motor_ia.validar_plan_completo(
                plan_semanal_data,
                self.perfil_paciente,
                configuracion,
                metas,
                alimentos_disponibles
            )
            
            if not validacion_completa.get('es_adecuado', True):
                print(f"[WARN]  IA detectó problemas en el plan completo:")
                for problema in validacion_completa.get('problemas', []):
                    print(f"   - {problema}")
                
                # Aplicar correcciones por día
                correcciones = validacion_completa.get('correcciones_por_dia', {})
                if correcciones:
                    print(f"[OPT] Aplicando correcciones sugeridas por IA para {len(correcciones)} días...")
                    
                    for dia_key, correcciones_dia in correcciones.items():
                        if dia_key not in plan_semanal_data:
                            continue
                        
                        dia_data = plan_semanal_data[dia_key]
                        
                        for tiempo, correccion in correcciones_dia.items():
                            if tiempo not in dia_data:
                                continue
                            
                            comida = dia_data[tiempo]
                            if not isinstance(comida, dict) or 'alimentos' not in comida:
                                continue
                            
                            alimentos_a_remover = correccion.get('alimentos_a_remover', [])
                            alimentos_a_agregar = correccion.get('alimentos_a_agregar', [])
                            
                            if alimentos_a_remover or alimentos_a_agregar:
                                print(f"   [OPT] Corrigiendo {dia_key} - {tiempo}: remover {len(alimentos_a_remover)}, agregar {len(alimentos_a_agregar)}")
                                
                                # Calcular nutrientes removidos
                                nutrientes_removidos = {'kcal': 0, 'cho': 0, 'pro': 0, 'fat': 0, 'fibra': 0}
                                nombres_a_remover = [n.lower().strip() for n in alimentos_a_remover]
                                
                                nuevos_alimentos = []
                                for al in comida['alimentos']:
                                    nombre_al = al.get('nombre', '').lower().strip()
                                    if nombre_al not in nombres_a_remover:
                                        nuevos_alimentos.append(al)
                                    else:
                                        nutrientes_removidos['kcal'] += float(al.get('kcal', 0) or 0)
                                        nutrientes_removidos['cho'] += float(al.get('cho', 0) or 0)
                                        nutrientes_removidos['pro'] += float(al.get('pro', 0) or 0)
                                        nutrientes_removidos['fat'] += float(al.get('fat', 0) or 0)
                                        nutrientes_removidos['fibra'] += float(al.get('fibra', 0) or 0)
                                        print(f"      [WARN] Removido: {al.get('nombre', 'N/A')}")
                                
                                # Agregar alimentos sugeridos
                                nutrientes_agregados = {'kcal': 0, 'cho': 0, 'pro': 0, 'fat': 0, 'fibra': 0}
                                
                                for nombre_sugerido in alimentos_a_agregar:
                                    # Buscar en alimentos disponibles
                                    alimento_encontrado = None
                                    nombre_buscar = nombre_sugerido.lower().strip()
                                    
                                    for al_db in alimentos_disponibles:
                                        nombre_db = al_db.get('nombre', '').lower().strip()
                                        if nombre_db == nombre_buscar:
                                            alimento_encontrado = al_db
                                            break
                                    
                                    if alimento_encontrado:
                                        # Calcular cantidad para compensar nutrientes removidos
                                        cantidad_sugerida = 100.0  # Por defecto
                                        
                                        # Intentar compensar el déficit
                                        num_alimentos_restantes = len(alimentos_a_agregar) - len([a for a in nuevos_alimentos if a.get('nombre', '').lower().strip() == nombre_buscar])
                                        if num_alimentos_restantes > 0:
                                            kcal_por_100g = float(alimento_encontrado.get('kcal', 0) or 0)
                                            if kcal_por_100g > 0:
                                                deficit_kcal_restante = max(0, nutrientes_removidos['kcal'] - nutrientes_agregados['kcal'])
                                                cantidad_por_kcal = (deficit_kcal_restante / num_alimentos_restantes) / kcal_por_100g * 100
                                                cantidad_sugerida = max(50.0, min(cantidad_por_kcal, 200.0))
                                        
                                        nuevo_alimento = {
                                            'nombre': alimento_encontrado.get('nombre', ''),
                                            'grupo': alimento_encontrado.get('grupo', ''),
                                            'cantidad': f"{round(cantidad_sugerida, 1)}g",
                                            'unidad': 'g',
                                            'kcal': round(float(alimento_encontrado.get('kcal', 0) or 0) * cantidad_sugerida / 100, 1),
                                            'cho': round(float(alimento_encontrado.get('cho', 0) or 0) * cantidad_sugerida / 100, 1),
                                            'pro': round(float(alimento_encontrado.get('pro', 0) or 0) * cantidad_sugerida / 100, 1),
                                            'fat': round(float(alimento_encontrado.get('fat', 0) or 0) * cantidad_sugerida / 100, 1),
                                            'fibra': round(float(alimento_encontrado.get('fibra', 0) or 0) * cantidad_sugerida / 100, 1)
                                        }
                                        nuevos_alimentos.append(nuevo_alimento)
                                        nutrientes_agregados['kcal'] += nuevo_alimento['kcal']
                                        nutrientes_agregados['cho'] += nuevo_alimento['cho']
                                        nutrientes_agregados['pro'] += nuevo_alimento['pro']
                                        nutrientes_agregados['fat'] += nuevo_alimento['fat']
                                        nutrientes_agregados['fibra'] += nuevo_alimento['fibra']
                                        print(f"      [OK] Agregado: {nuevo_alimento['nombre']} - {round(cantidad_sugerida, 1)}g")
                                
                                comida['alimentos'] = nuevos_alimentos
                                self._recalcular_totales_comida(comida)
                                
                                # Aplicar límite de verduras
                                self._limitar_verduras_por_comida(comida, tiempo)
                    
                    # Re-optimizar días que no cumplan después de las correcciones
                    print(f"[DEBUG] Verificando cumplimiento después de correcciones del plan completo...")
                    for dia_key, dia_data in plan_semanal_data.items():
                        if not dia_key.startswith('dia_'):
                            continue
                        
                        cumplimiento = self.calcular_cumplimiento_dia(dia_data, metas)
                        
                        # Reducir excesos si hay
                        if cumplimiento.kcal_porcentaje > 100 or cumplimiento.cho_porcentaje > 100 or \
                           cumplimiento.pro_porcentaje > 100 or cumplimiento.fat_porcentaje > 100:
                            dia_data = self._reducir_excesos_dia(dia_data, cumplimiento, metas)
                            plan_semanal_data[dia_key] = dia_data
                            cumplimiento = self.calcular_cumplimiento_dia(dia_data, metas)
                        
                        # Optimizar si no cumple (está por debajo del 90%)
                        if cumplimiento.kcal_porcentaje < 90.0 or cumplimiento.cho_porcentaje < 90.0 or \
                           cumplimiento.pro_porcentaje < 90.0 or cumplimiento.fat_porcentaje < 90.0:
                            print(f"   [WARN]  {dia_key} no cumple después de correcciones del plan completo (Kcal: {cumplimiento.kcal_porcentaje:.1f}%, CHO: {cumplimiento.cho_porcentaje:.1f}%, PRO: {cumplimiento.pro_porcentaje:.1f}%, FAT: {cumplimiento.fat_porcentaje:.1f}%)")
                            try:
                                dia_optimizado = self._optimizar_dia(dia_data, cumplimiento, metas,
                                                                      getattr(self, 'grupos_alimentos', {}),
                                                                      getattr(self, 'perfil_paciente', {}),
                                                                      self.motor_recomendacion)
                                cumplimiento_optimizado = self.calcular_cumplimiento_dia(dia_optimizado, metas)
                                
                                # Reducir excesos si aparecieron
                                if cumplimiento_optimizado.kcal_porcentaje > 100 or cumplimiento_optimizado.cho_porcentaje > 100 or \
                                   cumplimiento_optimizado.pro_porcentaje > 100 or cumplimiento_optimizado.fat_porcentaje > 100:
                                    dia_optimizado = self._reducir_excesos_dia(dia_optimizado, cumplimiento_optimizado, metas)
                                    cumplimiento_optimizado = self.calcular_cumplimiento_dia(dia_optimizado, metas)
                                
                                plan_semanal_data[dia_key] = dia_optimizado
                                if 'plan_semanal' in plan_optimizado:
                                    plan_optimizado['plan_semanal'][dia_key] = dia_optimizado
                                print(f"   [OK] {dia_key} corregido y re-optimizado")
                            except Exception as e:
                                print(f"   [WARN]  Error al re-optimizar {dia_key}: {e}")
            else:
                print("[OK] IA aprobó el plan completo")
        except Exception as e:
            print(f"[ERROR] Error al validar plan completo con IA: {e}")
            import traceback
            traceback.print_exc()
        
        return plan_optimizado

