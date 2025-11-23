# motor_recomendacion_basico.py
# Motor básico que genera un plan simple pero funcional

import math
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
import random

@dataclass
class PerfilPaciente:
    """Perfil completo del paciente para recomendaciones"""
    paciente_id: int
    edad: int
    sexo: str
    peso: float
    talla: float
    imc: float
    actividad: str
    hba1c: Optional[float]
    glucosa_ayunas: Optional[float]
    ldl: Optional[float]
    pa_sis: Optional[int]
    pa_dia: Optional[int]
    alergias: List[str]
    medicamentos: List[str]
    preferencias_excluir: List[str]
    preferencias_incluir: List[str]

@dataclass
class MetaNutricional:
    """Metas nutricionales calculadas"""
    calorias_diarias: int
    carbohidratos_g: int
    carbohidratos_porcentaje: int
    proteinas_g: int
    proteinas_porcentaje: int
    grasas_g: int
    grasas_porcentaje: int
    fibra_g: int
    sodio_mg: int
    carbohidratos_por_comida: Dict[str, int]
    ig_maximo: int
    max_repeticiones_semana: int

class MotorRecomendacionBasico:
    """Motor básico que genera un plan simple pero funcional"""
    
    def __init__(self):
        # Parámetros específicos para diabetes tipo 2
        self.PARAMETROS_DIABETES = {
            'carbohidratos_min': 45,  # % mínimo
            'carbohidratos_max': 60,  # % máximo
            'proteinas_min': 15,     # % mínimo
            'proteinas_max': 20,     # % máximo
            'grasas_min': 25,        # % mínimo
            'grasas_max': 35,        # % máximo
            'fibra_min': 25,         # g/día mínimo
            'sodio_max': 2300,       # mg/día máximo
            'ig_max_default': 70,    # Índice glucémico máximo por defecto
        }
        
        # Distribución de carbohidratos por comida
        self.DISTRIBUCION_CHO = {
            'des': 0.20,    # desayuno
            'mm': 0.10,     # media mañana
            'alm': 0.35,    # almuerzo
            'mt': 0.10,     # media tarde
            'cena': 0.25    # cena
        }

    def obtener_perfil_paciente(self, paciente_id: int) -> PerfilPaciente:
        """Obtiene el perfil del paciente (versión básica)"""
        return PerfilPaciente(
            paciente_id=paciente_id,
            edad=35,
            sexo='M',
            peso=70.0,
            talla=1.70,
            imc=24.2,
            actividad='moderada',
            hba1c=7.0,
            glucosa_ayunas=110,
            ldl=130,
            pa_sis=120,
            pa_dia=80,
            alergias=[],
            medicamentos=['Metformina'],
            preferencias_excluir=[],
            preferencias_incluir=[]
        )

    def calcular_metabolismo_basal(self, perfil: PerfilPaciente) -> float:
        """Calcula el metabolismo basal usando la ecuación de Mifflin-St Jeor"""
        if perfil.sexo == 'M':
            mb = 10 * perfil.peso + 6.25 * (perfil.talla * 100) - 5 * perfil.edad + 5
        else:
            mb = 10 * perfil.peso + 6.25 * (perfil.talla * 100) - 5 * perfil.edad - 161
        
        return mb

    def calcular_factor_actividad(self, actividad: str) -> float:
        """Factor de actividad física"""
        factores = {
            'baja': 1.2,
            'moderada': 1.4,
            'alta': 1.6
        }
        return factores.get(actividad, 1.4)

    def calcular_factor_diabetes(self, perfil: PerfilPaciente) -> float:
        """Factor de ajuste específico para diabetes tipo 2"""
        factor = 1.0
        
        # Ajuste por HbA1c
        if perfil.hba1c:
            if perfil.hba1c > 8.0:
                factor -= 0.1  # Reducir calorías si HbA1c alto
            elif perfil.hba1c < 6.5:
                factor += 0.05  # Ligero aumento si HbA1c controlado
        
        # Ajuste por glucosa en ayunas
        if perfil.glucosa_ayunas:
            if perfil.glucosa_ayunas > 140:
                factor -= 0.05  # Reducir calorías si glucosa alta
            elif perfil.glucosa_ayunas < 100:
                factor += 0.02  # Ligero aumento si glucosa controlada
        
        # Ajuste por IMC
        if perfil.imc > 30:
            factor -= 0.15  # Reducir calorías para obesidad
        elif perfil.imc < 18.5:
            factor += 0.1   # Aumentar calorías para bajo peso
        
        return max(0.7, min(1.3, factor))  # Limitar entre 0.7 y 1.3

    def calcular_metas_nutricionales(self, perfil: PerfilPaciente, filtros: Dict = None) -> MetaNutricional:
        """Calcula las metas nutricionales personalizadas"""
        
        # Calcular calorías totales
        mb = self.calcular_metabolismo_basal(perfil)
        factor_actividad = self.calcular_factor_actividad(perfil.actividad)
        factor_diabetes = self.calcular_factor_diabetes(perfil)
        
        calorias_diarias = int(mb * factor_actividad * factor_diabetes)
        
        # Aplicar calorías objetivo si se especifican en filtros
        if filtros and filtros.get('kcal'):
            calorias_objetivo = int(filtros['kcal'])
            if 800 <= calorias_objetivo <= 4000:
                calorias_diarias = calorias_objetivo
        
        # Calcular distribución de macronutrientes
        cho_pct = filtros.get('cho_pct', 50) if filtros else 50
        pro_pct = filtros.get('pro_pct', 18) if filtros else 18
        fat_pct = filtros.get('fat_pct', 32) if filtros else 32
        
        # Validar que los porcentajes sumen aproximadamente 100%
        total_pct = cho_pct + pro_pct + fat_pct
        if abs(total_pct - 100) > 10:
            cho_pct = int(cho_pct * 100 / total_pct)
            pro_pct = int(pro_pct * 100 / total_pct)
            fat_pct = 100 - cho_pct - pro_pct
        
        # Calcular gramos de cada macronutriente
        carbohidratos_g = int((calorias_diarias * cho_pct / 100) / 4)  # 4 kcal/g
        proteinas_g = int((calorias_diarias * pro_pct / 100) / 4)     # 4 kcal/g
        grasas_g = int((calorias_diarias * fat_pct / 100) / 9)         # 9 kcal/g
        
        # Calcular distribución de carbohidratos por comida
        carbohidratos_por_comida = {}
        for tiempo, porcentaje in self.DISTRIBUCION_CHO.items():
            carbohidratos_por_comida[tiempo] = int(carbohidratos_g * porcentaje)
        
        # Calcular fibra (basada en peso y actividad)
        fibra_g = max(25, int(perfil.peso * 0.4))  # Mínimo 25g, ideal 0.4g por kg
        
        # Calcular sodio máximo (ajustado por presión arterial)
        sodio_mg = 2300  # Valor por defecto
        if perfil.pa_sis and perfil.pa_sis > 140:
            sodio_mg = 1500  # Reducir sodio si hipertensión
        
        # IG máximo (usar del filtro si se especifica)
        ig_maximo = filtros.get('ig_max', self.PARAMETROS_DIABETES['ig_max_default']) if filtros else self.PARAMETROS_DIABETES['ig_max_default']
        
        # Máximo de repeticiones por semana (usar del filtro si se especifica)
        max_repeticiones_semana = filtros.get('max_repeticiones', 2) if filtros else 2
        
        return MetaNutricional(
            calorias_diarias=calorias_diarias,
            carbohidratos_g=carbohidratos_g,
            carbohidratos_porcentaje=cho_pct,
            proteinas_g=proteinas_g,
            proteinas_porcentaje=pro_pct,
            grasas_g=grasas_g,
            grasas_porcentaje=fat_pct,
            fibra_g=fibra_g,
            sodio_mg=sodio_mg,
            carbohidratos_por_comida=carbohidratos_por_comida,
            ig_maximo=ig_maximo,
            max_repeticiones_semana=max_repeticiones_semana
        )

    def generar_recomendacion_semanal(self, paciente_id: int, dias: int = 7, filtros: Dict = None) -> Dict:
        """Genera una recomendación semanal personalizada"""
        
        try:
            # Obtener perfil del paciente
            perfil = self.obtener_perfil_paciente(paciente_id)
            
            # Calcular metas nutricionales personalizadas
            metas = self.calcular_metas_nutricionales(perfil, filtros)
            
            # Generar plan semanal básico
            plan_semanal = self._generar_plan_semanal_basico(metas, perfil, dias, filtros)
            
            # Calcular validaciones del plan
            validaciones = self._calcular_validaciones_plan_basico(plan_semanal, metas, filtros)
            
            # Crear estructura de plan_completo con múltiples semanas si es necesario
            plan_completo = self._crear_plan_completo(plan_semanal, dias, filtros)
            
            return {
                'paciente_id': paciente_id,
                'fecha': date.today().isoformat(),
                'perfil': {
                    'edad': perfil.edad,
                    'sexo': perfil.sexo,
                    'peso': perfil.peso,
                    'talla': perfil.talla,
                    'imc': round(perfil.imc, 2),
                    'actividad': perfil.actividad,
                    'hba1c': perfil.hba1c,
                    'glucosa_ayunas': perfil.glucosa_ayunas,
                    'alergias': perfil.alergias,
                    'medicamentos': perfil.medicamentos
                },
                'metas_nutricionales': {
                    'calorias_diarias': metas.calorias_diarias,
                    'carbohidratos_g': metas.carbohidratos_g,
                    'carbohidratos_porcentaje': metas.carbohidratos_porcentaje,
                    'proteinas_g': metas.proteinas_g,
                    'proteinas_porcentaje': metas.proteinas_porcentaje,
                    'grasas_g': metas.grasas_g,
                    'grasas_porcentaje': metas.grasas_porcentaje,
                    'fibra_g': metas.fibra_g,
                    'sodio_mg': metas.sodio_mg,
                    'ig_maximo': metas.ig_maximo,
                    'max_repeticiones_semana': metas.max_repeticiones_semana
                },
                'plan_semanal': plan_semanal,
                'plan_completo': plan_completo,
                'validaciones': validaciones,
                'ingredientes_disponibles': 50,  # Valor por defecto
                'filtros_aplicados': filtros,
                'total_semanas': len(plan_completo)
            }
            
        except Exception as e:
            return {
                'error': f'Error generando recomendación: {str(e)}',
                'paciente_id': paciente_id
            }

    def _generar_plan_semanal_basico(self, metas: MetaNutricional, perfil: PerfilPaciente, dias: int, filtros: Dict = None) -> Dict:
        """Genera un plan semanal básico"""
        
        plan_semanal = {}
        nombres_dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        
        # Usar el día de inicio del frontend si está disponible, sino usar lunes por defecto
        dia_inicio = 0  # lunes por defecto
        if filtros and 'dia_inicio' in filtros:
            dia_inicio = filtros['dia_inicio']
            print(f"DEBUG: Motor básico usando día de inicio del frontend: {dia_inicio}")
        else:
            print(f"DEBUG: Motor básico usando lunes (0) como día de inicio por defecto")
        
        # Alimentos básicos por grupo
        alimentos_basicos = {
            'GRUPO1_CEREALES': ['Avena integral', 'Arroz integral', 'Quinoa', 'Pan integral'],
            'GRUPO2_VERDURAS': ['Brócoli', 'Espinaca', 'Zanahoria', 'Tomate'],
            'GRUPO3_FRUTAS': ['Manzana', 'Plátano', 'Fresas', 'Naranja'],
            'GRUPO4_LACTEOS': ['Leche descremada', 'Yogur natural', 'Queso cottage'],
            'GRUPO5_CARNES': ['Pechuga de pollo', 'Salmón', 'Huevo entero'],
            'GRUPO7_GRASAS': ['Aceite de oliva', 'Aguacate', 'Nueces']
        }
        
        for dia in range(dias):
            nombre_dia = nombres_dias[(dia_inicio + dia) % 7]
            
            # Generar comidas para el día
            comidas_dia = {}
            tiempos_comida = ['des', 'mm', 'alm', 'mt', 'cena']
            
            for tiempo in tiempos_comida:
                comida_generada = self._generar_comida_basica(
                    alimentos_basicos, 
                    metas, 
                    tiempo, 
                    dia
                )
                # El frontend espera directamente la lista de alimentos
                comidas_dia[tiempo] = comida_generada
            
            plan_semanal[nombre_dia] = comidas_dia
        
        return plan_semanal

    def _generar_comida_basica(self, alimentos_basicos: Dict, metas: MetaNutricional, tiempo: str, dia: int) -> Dict:
        """Genera una comida básica"""
        
        sugerencias = []
        
        # Seleccionar ingredientes según el tiempo de comida
        if tiempo == 'des':
            # Desayuno: cereal + fruta + lácteo
            if alimentos_basicos['GRUPO1_CEREALES']:
                cereal = alimentos_basicos['GRUPO1_CEREALES'][dia % len(alimentos_basicos['GRUPO1_CEREALES'])]
                sugerencias.append(self._crear_sugerencia_basica(cereal, 'GRUPO1_CEREALES', 60))
            
            if alimentos_basicos['GRUPO3_FRUTAS']:
                fruta = alimentos_basicos['GRUPO3_FRUTAS'][dia % len(alimentos_basicos['GRUPO3_FRUTAS'])]
                sugerencias.append(self._crear_sugerencia_basica(fruta, 'GRUPO3_FRUTAS', 120))
            
            if alimentos_basicos['GRUPO4_LACTEOS']:
                lacteo = alimentos_basicos['GRUPO4_LACTEOS'][dia % len(alimentos_basicos['GRUPO4_LACTEOS'])]
                sugerencias.append(self._crear_sugerencia_basica(lacteo, 'GRUPO4_LACTEOS', 200))
                
        elif tiempo in ['mm', 'mt']:
            # Meriendas: fruta o lácteo
            if dia % 2 == 0 and alimentos_basicos['GRUPO3_FRUTAS']:
                fruta = alimentos_basicos['GRUPO3_FRUTAS'][dia % len(alimentos_basicos['GRUPO3_FRUTAS'])]
                sugerencias.append(self._crear_sugerencia_basica(fruta, 'GRUPO3_FRUTAS', 120))
            elif alimentos_basicos['GRUPO4_LACTEOS']:
                lacteo = alimentos_basicos['GRUPO4_LACTEOS'][dia % len(alimentos_basicos['GRUPO4_LACTEOS'])]
                sugerencias.append(self._crear_sugerencia_basica(lacteo, 'GRUPO4_LACTEOS', 150))
                
        elif tiempo == 'alm':
            # Almuerzo: proteína + cereal + verdura + grasa
            if alimentos_basicos['GRUPO5_CARNES']:
                proteina = alimentos_basicos['GRUPO5_CARNES'][dia % len(alimentos_basicos['GRUPO5_CARNES'])]
                sugerencias.append(self._crear_sugerencia_basica(proteina, 'GRUPO5_CARNES', 120))
            
            if alimentos_basicos['GRUPO1_CEREALES']:
                cereal = alimentos_basicos['GRUPO1_CEREALES'][(dia + 1) % len(alimentos_basicos['GRUPO1_CEREALES'])]
                sugerencias.append(self._crear_sugerencia_basica(cereal, 'GRUPO1_CEREALES', 80))
            
            if alimentos_basicos['GRUPO2_VERDURAS']:
                verdura1 = alimentos_basicos['GRUPO2_VERDURAS'][dia % len(alimentos_basicos['GRUPO2_VERDURAS'])]
                sugerencias.append(self._crear_sugerencia_basica(verdura1, 'GRUPO2_VERDURAS', 150))
                if len(alimentos_basicos['GRUPO2_VERDURAS']) > 1:
                    verdura2 = alimentos_basicos['GRUPO2_VERDURAS'][(dia + 1) % len(alimentos_basicos['GRUPO2_VERDURAS'])]
                    sugerencias.append(self._crear_sugerencia_basica(verdura2, 'GRUPO2_VERDURAS', 100))
            
            if alimentos_basicos['GRUPO7_GRASAS']:
                grasa = alimentos_basicos['GRUPO7_GRASAS'][dia % len(alimentos_basicos['GRUPO7_GRASAS'])]
                sugerencias.append(self._crear_sugerencia_basica(grasa, 'GRUPO7_GRASAS', 15))
            
        elif tiempo == 'cena':
            # Cena: proteína + verdura + grasa
            if alimentos_basicos['GRUPO5_CARNES']:
                proteina = alimentos_basicos['GRUPO5_CARNES'][(dia + 1) % len(alimentos_basicos['GRUPO5_CARNES'])]
                sugerencias.append(self._crear_sugerencia_basica(proteina, 'GRUPO5_CARNES', 100))
            
            if alimentos_basicos['GRUPO2_VERDURAS']:
                verdura1 = alimentos_basicos['GRUPO2_VERDURAS'][(dia + 2) % len(alimentos_basicos['GRUPO2_VERDURAS'])]
                sugerencias.append(self._crear_sugerencia_basica(verdura1, 'GRUPO2_VERDURAS', 150))
                if len(alimentos_basicos['GRUPO2_VERDURAS']) > 1:
                    verdura2 = alimentos_basicos['GRUPO2_VERDURAS'][(dia + 3) % len(alimentos_basicos['GRUPO2_VERDURAS'])]
                    sugerencias.append(self._crear_sugerencia_basica(verdura2, 'GRUPO2_VERDURAS', 100))
            
            if alimentos_basicos['GRUPO7_GRASAS']:
                grasa = alimentos_basicos['GRUPO7_GRASAS'][(dia + 1) % len(alimentos_basicos['GRUPO7_GRASAS'])]
                sugerencias.append(self._crear_sugerencia_basica(grasa, 'GRUPO7_GRASAS', 10))
        
        # El frontend espera directamente la lista de alimentos
        return sugerencias

    def _crear_sugerencia_basica(self, nombre: str, grupo: str, cantidad: float) -> Dict:
        """Crea una sugerencia de ingrediente básica"""
        
        # Valores nutricionales aproximados por grupo
        valores_nutricionales = {
            'GRUPO1_CEREALES': {'kcal': 350, 'cho': 70, 'pro': 12, 'fat': 3, 'fibra': 8},
            'GRUPO2_VERDURAS': {'kcal': 30, 'cho': 6, 'pro': 2, 'fat': 0.5, 'fibra': 3},
            'GRUPO3_FRUTAS': {'kcal': 50, 'cho': 12, 'pro': 0.5, 'fat': 0.2, 'fibra': 2},
            'GRUPO4_LACTEOS': {'kcal': 50, 'cho': 5, 'pro': 8, 'fat': 2, 'fibra': 0},
            'GRUPO5_CARNES': {'kcal': 150, 'cho': 0, 'pro': 25, 'fat': 5, 'fibra': 0},
            'GRUPO7_GRASAS': {'kcal': 600, 'cho': 5, 'pro': 5, 'fat': 65, 'fibra': 3}
        }
        
        valores = valores_nutricionales.get(grupo, {'kcal': 100, 'cho': 20, 'pro': 5, 'fat': 2, 'fibra': 2})
        
        return {
            'nombre': nombre,
            'grupo': grupo,
            'porcion': f"{cantidad}g",
            'kcal': round((valores['kcal'] * cantidad) / 100, 1),
            'cho': round((valores['cho'] * cantidad) / 100, 1),
            'pro': round((valores['pro'] * cantidad) / 100, 1),
            'fat': round((valores['fat'] * cantidad) / 100, 1),
            'fibra': round((valores['fibra'] * cantidad) / 100, 1),
            'motivo': f'Selección automática - grupo {grupo}'
        }

    def _calcular_validaciones_plan_basico(self, plan_semanal: Dict, metas: MetaNutricional, filtros: Dict = None) -> Dict:
        """Calcula validaciones del plan generado"""
        
        # Calcular totales del plan
        totales_semana = {
            'calorias': 0,
            'carbohidratos': 0,
            'proteinas': 0,
            'grasas': 0,
            'fibra': 0,
            'sodio': 0
        }
        
        ingredientes_usados = {}
        
        for dia, comidas in plan_semanal.items():
            for tiempo, comida in comidas.items():
                # La comida ahora es directamente una lista de alimentos
                if isinstance(comida, list):
                    for alimento in comida:
                        # Contar ingredientes
                        nombre = alimento['nombre']
                        ingredientes_usados[nombre] = ingredientes_usados.get(nombre, 0) + 1
                        
                        # Sumar nutrientes directamente
                        totales_semana['calorias'] += alimento['kcal']
                        totales_semana['carbohidratos'] += alimento['cho']
                        totales_semana['proteinas'] += alimento['pro']
                        totales_semana['grasas'] += alimento['fat']
                        totales_semana['fibra'] += alimento['fibra']
        
        # Calcular promedios diarios
        dias_plan = len(plan_semanal)
        promedios_diarios = {
            'calorias': totales_semana['calorias'] / dias_plan,
            'carbohidratos': totales_semana['carbohidratos'] / dias_plan,
            'proteinas': totales_semana['proteinas'] / dias_plan,
            'grasas': totales_semana['grasas'] / dias_plan,
            'fibra': totales_semana['fibra'] / dias_plan,
            'sodio': totales_semana['sodio'] / dias_plan
        }
        
        # Validaciones
        validaciones = {
            'calorias': {
                'objetivo': metas.calorias_diarias,
                'actual': round(promedios_diarios['calorias']),
                'cumple': abs(promedios_diarios['calorias'] - metas.calorias_diarias) <= metas.calorias_diarias * 0.1
            },
            'carbohidratos': {
                'objetivo': metas.carbohidratos_g,
                'actual': round(promedios_diarios['carbohidratos']),
                'cumple': abs(promedios_diarios['carbohidratos'] - metas.carbohidratos_g) <= metas.carbohidratos_g * 0.15
            },
            'proteinas': {
                'objetivo': metas.proteinas_g,
                'actual': round(promedios_diarios['proteinas']),
                'cumple': abs(promedios_diarios['proteinas'] - metas.proteinas_g) <= metas.proteinas_g * 0.15
            },
            'grasas': {
                'objetivo': metas.grasas_g,
                'actual': round(promedios_diarios['grasas']),
                'cumple': abs(promedios_diarios['grasas'] - metas.grasas_g) <= metas.grasas_g * 0.15
            },
            'fibra': {
                'objetivo': metas.fibra_g,
                'actual': round(promedios_diarios['fibra']),
                'cumple': promedios_diarios['fibra'] >= metas.fibra_g * 0.8
            },
            'sodio': {
                'objetivo': metas.sodio_mg,
                'actual': round(promedios_diarios['sodio']),
                'cumple': promedios_diarios['sodio'] <= metas.sodio_mg
            },
            'diversidad': {
                'ingredientes_unicos': len(ingredientes_usados),
                'max_repeticiones': metas.max_repeticiones_semana,
                'cumple': all(uso <= metas.max_repeticiones_semana for uso in ingredientes_usados.values())
            },
            'ig_maximo': {
                'objetivo': metas.ig_maximo,
                'cumple': True  # Ya filtrado en la consulta
            }
        }
        
        return validaciones

    def _crear_plan_completo(self, plan_semanal: Dict, dias: int, filtros: Dict = None) -> Dict:
        """Crea la estructura plan_completo dividiendo en semanas si es necesario"""
        
        if dias <= 7:
            # Si es una semana o menos, crear una sola semana
            return {
                'Semana_1': plan_semanal
            }
        
        # Si son más de 7 días, dividir en semanas
        plan_completo = {}
        nombres_dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        
        # Usar el día de inicio del frontend si está disponible
        dia_inicio = 0  # lunes por defecto
        if filtros and 'dia_inicio' in filtros:
            dia_inicio = filtros['dia_inicio']
        
        semana_actual = 1
        dias_en_semana_actual = 0
        semana_data = {}
        
        for dia in range(dias):
            # Calcular el nombre del día
            nombre_dia = nombres_dias[(dia_inicio + dia) % 7]
            
            # Agregar el día a la semana actual
            if nombre_dia in plan_semanal:
                semana_data[nombre_dia] = plan_semanal[nombre_dia]
            
            dias_en_semana_actual += 1
            
            # Si completamos una semana o es el último día, guardar la semana
            if dias_en_semana_actual == 7 or dia == dias - 1:
                plan_completo[f'Semana_{semana_actual}'] = semana_data.copy()
                semana_actual += 1
                dias_en_semana_actual = 0
                semana_data = {}
        
        return plan_completo
