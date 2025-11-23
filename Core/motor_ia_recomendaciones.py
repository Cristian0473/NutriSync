# motor_ia_recomendaciones.py
# Motor de IA para mejorar recomendaciones nutricionales usando OpenAI GPT API

import os
import json
from typing import Dict, List, Optional
from dataclasses import dataclass

# Intentar importar OpenAI (instalar con: pip install openai)
try:
    from openai import OpenAI
    from openai import APIError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  OpenAI no disponible. Instala con: pip install openai")

@dataclass
class RecomendacionIA:
    """Recomendación mejorada por IA"""
    explicacion_personalizada: str
    sugerencias_adicionales: List[str]
    alimentos_priorizados: List[str]
    razones_ajuste: List[str]


class MotorIARecomendaciones:
    """Motor de IA para mejorar recomendaciones nutricionales"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa el motor de IA
        
        Args:
            api_key: Clave API de OpenAI. Si no se proporciona, busca en variable de entorno OPENAI_API_KEY
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.client = None
        
        if OPENAI_AVAILABLE and self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                print("✅ Motor de IA inicializado correctamente")
            except Exception as e:
                print(f"⚠️  Error al inicializar OpenAI: {e}")
                self.client = None
        else:
            if not OPENAI_AVAILABLE:
                print("⚠️  OpenAI no está instalado. Instala con: pip install openai")
            if not self.api_key:
                print("⚠️  OPENAI_API_KEY no configurada. Configura la variable de entorno o pasa api_key")
    
    def analizar_preferencias_texto(self, texto_preferencias: str, perfil_paciente: Dict) -> RecomendacionIA:
        """
        Analiza preferencias del paciente en texto libre usando GPT
        
        Args:
            texto_preferencias: Texto con preferencias del paciente
            perfil_paciente: Diccionario con perfil del paciente
            
        Returns:
            RecomendacionIA con sugerencias personalizadas
        """
        if not self.client:
            return RecomendacionIA(
                explicacion_personalizada="IA no disponible",
                sugerencias_adicionales=[],
                alimentos_priorizados=[],
                razones_ajuste=[]
            )
        
        try:
            prompt = f"""Eres un nutricionista experto en diabetes tipo 2. Analiza las preferencias del paciente y genera recomendaciones personalizadas.

PERFIL DEL PACIENTE:
- Edad: {perfil_paciente.get('edad', 'N/A')} años
- IMC: {perfil_paciente.get('imc', 'N/A')}
- HbA1c: {perfil_paciente.get('hba1c', 'N/A')}%

PREFERENCIAS DEL PACIENTE:
{texto_preferencias}

INSTRUCCIONES:
1. Analiza las preferencias del paciente
2. Genera una explicación personalizada de cómo adaptar el plan a sus preferencias
3. Sugiere 3-5 alimentos específicos que se alineen con sus preferencias y sean adecuados para diabetes tipo 2
4. Proporciona razones específicas para cada ajuste

Responde SOLO con un JSON válido en este formato:
{{
    "explicacion_personalizada": "Explicación detallada...",
    "sugerencias_adicionales": ["Sugerencia 1", "Sugerencia 2"],
    "alimentos_priorizados": ["Alimento 1", "Alimento 2"],
    "razones_ajuste": ["Razón 1", "Razón 2"]
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un nutricionista experto. Responde SOLO con JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=500
            )
            
            resultado_texto = response.choices[0].message.content.strip()
            if resultado_texto.startswith("```json"):
                resultado_texto = resultado_texto[7:]
            if resultado_texto.endswith("```"):
                resultado_texto = resultado_texto[:-3]
            resultado_texto = resultado_texto.strip()
            
            resultado = json.loads(resultado_texto)
            return RecomendacionIA(
                explicacion_personalizada=resultado.get("explicacion_personalizada", ""),
                sugerencias_adicionales=resultado.get("sugerencias_adicionales", []),
                alimentos_priorizados=resultado.get("alimentos_priorizados", []),
                razones_ajuste=resultado.get("razones_ajuste", [])
            )
            
        except Exception as e:
            print(f"⚠️  Error al analizar preferencias con IA: {e}")
            return RecomendacionIA(
                explicacion_personalizada="Error al procesar preferencias",
                sugerencias_adicionales=[],
                alimentos_priorizados=[],
                razones_ajuste=[]
            )
    
    def generar_explicacion_plan(self, plan_semanal: Dict, perfil_paciente: Dict, metas: Dict) -> str:
        """
        Genera una explicación personalizada del plan nutricional usando GPT
        
        Args:
            plan_semanal: Plan semanal generado
            perfil_paciente: Diccionario con perfil del paciente
            metas: Metas nutricionales
            
        Returns:
            Explicación personalizada del plan
        """
        if not self.client:
            return "IA no disponible para generar explicación"
        
        try:
            # Resumir el plan (solo estructura, no todos los alimentos)
            resumen_plan = f"Plan de {len([k for k in plan_semanal.keys() if k.startswith('dia_')])} días"
            
            prompt = f"""Eres un nutricionista experto en diabetes tipo 2. Genera una explicación clara y motivadora del plan nutricional.

PERFIL DEL PACIENTE:
- Edad: {perfil_paciente.get('edad', 'N/A')} años
- IMC: {perfil_paciente.get('imc', 'N/A')}
- HbA1c: {perfil_paciente.get('hba1c', 'N/A')}%

METAS NUTRICIONALES:
- Calorías: {metas.get('calorias_diarias', 'N/A')} kcal/día
- Carbohidratos: {metas.get('carbohidratos_g', 'N/A')}g/día
- Proteínas: {metas.get('proteinas_g', 'N/A')}g/día
- Grasas: {metas.get('grasas_g', 'N/A')}g/día

PLAN:
{resumen_plan}

INSTRUCCIONES:
Genera una explicación clara, motivadora y educativa del plan nutricional que:
1. Explique por qué este plan es adecuado para el paciente
2. Destaque los beneficios para el control glucémico
3. Proporcione consejos prácticos para seguir el plan
4. Sea alentadora y positiva

Responde con un texto claro y conciso (máximo 300 palabras)."""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un nutricionista experto y empático."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"⚠️  Error al generar explicación con IA: {e}")
            return "No se pudo generar explicación personalizada"
    
    def sugerir_mejoras_plan(self, cumplimiento_objetivos: Dict, perfil_paciente: Dict) -> List[str]:
        """
        Sugiere mejoras al plan basándose en el cumplimiento de objetivos usando GPT
        
        Args:
            cumplimiento_objetivos: Diccionario con porcentajes de cumplimiento
            perfil_paciente: Diccionario con perfil del paciente
            
        Returns:
            Lista de sugerencias de mejora
        """
        if not self.client:
            return []
        
        try:
            prompt = f"""Eres un nutricionista experto en diabetes tipo 2. Analiza el cumplimiento de objetivos nutricionales y sugiere mejoras específicas.

PERFIL DEL PACIENTE:
- Edad: {perfil_paciente.get('edad', 'N/A')} años
- IMC: {perfil_paciente.get('imc', 'N/A')}
- HbA1c: {perfil_paciente.get('hba1c', 'N/A')}%

CUMPLIMIENTO DE OBJETIVOS:
- Calorías: {cumplimiento_objetivos.get('kcal', 0)}% del objetivo
- Carbohidratos: {cumplimiento_objetivos.get('cho', 0)}% del objetivo
- Proteínas: {cumplimiento_objetivos.get('pro', 0)}% del objetivo
- Grasas: {cumplimiento_objetivos.get('fat', 0)}% del objetivo

INSTRUCCIONES:
Analiza el cumplimiento y genera 3-5 sugerencias específicas y accionables para mejorar el plan.
Cada sugerencia debe ser:
- Específica y concreta
- Basada en evidencia científica
- Aplicable al perfil del paciente
- Enfocada en mejorar el control glucémico

Responde SOLO con un JSON válido en este formato:
{{
    "sugerencias": [
        "Sugerencia 1",
        "Sugerencia 2",
        "Sugerencia 3"
    ]
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un nutricionista experto. Responde SOLO con JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=400
            )
            
            resultado_texto = response.choices[0].message.content.strip()
            if resultado_texto.startswith("```json"):
                resultado_texto = resultado_texto[7:]
            if resultado_texto.endswith("```"):
                resultado_texto = resultado_texto[:-3]
            resultado_texto = resultado_texto.strip()
            
            resultado = json.loads(resultado_texto)
            return resultado.get("sugerencias", [])
            
        except Exception as e:
            print(f"⚠️  Error al generar sugerencias con IA: {e}")
            return []
    
    def optimizar_seleccion_alimentos(self, alimentos_candidatos: List[Dict], perfil_paciente: Dict, objetivos: Dict) -> List[Dict]:
        """
        Optimiza la selección de alimentos usando IA
        
        Args:
            alimentos_candidatos: Lista de alimentos candidatos con sus propiedades nutricionales
            perfil_paciente: Diccionario con perfil del paciente
            objetivos: Diccionario con objetivos nutricionales
            
        Returns:
            Lista de alimentos priorizados y optimizados
        """
        if not self.client:
            return alimentos_candidatos[:5]  # Fallback: primeros 5
        
        try:
            # Preparar resumen de alimentos
            resumen_alimentos = "\n".join([
                f"- {a.get('nombre', 'N/A')}: {a.get('kcal', 0)} kcal, CHO: {a.get('cho', 0)}g, PRO: {a.get('pro', 0)}g, FAT: {a.get('fat', 0)}g, IG: {a.get('ig', 'N/A')}"
                for a in alimentos_candidatos[:20]  # Limitar a 20 para no exceder tokens
            ])
            
            prompt = f"""Eres un nutricionista experto en diabetes tipo 2. Prioriza y selecciona los mejores alimentos para el paciente.

PERFIL DEL PACIENTE:
- Edad: {perfil_paciente.get('edad', 'N/A')} años
- IMC: {perfil_paciente.get('imc', 'N/A')}
- HbA1c: {perfil_paciente.get('hba1c', 'N/A')}%
- Actividad: {perfil_paciente.get('actividad', 'N/A')}

OBJETIVOS NUTRICIONALES:
- Calorías: {objetivos.get('calorias', 'N/A')} kcal
- Carbohidratos: {objetivos.get('carbohidratos', 'N/A')}g
- Proteínas: {objetivos.get('proteinas', 'N/A')}g
- Grasas: {objetivos.get('grasas', 'N/A')}g

ALIMENTOS CANDIDATOS:
{resumen_alimentos}

INSTRUCCIONES:
Selecciona y prioriza los 5-7 mejores alimentos considerando:
1. Control glucémico (IG bajo)
2. Cumplimiento de objetivos nutricionales
3. Variedad y balance
4. Apropiados para diabetes tipo 2

Responde SOLO con un JSON válido en este formato:
{{
    "alimentos_priorizados": ["Alimento 1", "Alimento 2", "Alimento 3"]
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un nutricionista experto. Responde SOLO con JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=300
            )
            
            resultado_texto = response.choices[0].message.content.strip()
            if resultado_texto.startswith("```json"):
                resultado_texto = resultado_texto[7:]
            if resultado_texto.endswith("```"):
                resultado_texto = resultado_texto[:-3]
            resultado_texto = resultado_texto.strip()
            
            resultado = json.loads(resultado_texto)
            alimentos_priorizados_nombres = resultado.get("alimentos_priorizados", [])
            
            # Filtrar alimentos candidatos por los nombres priorizados
            alimentos_priorizados = [
                a for a in alimentos_candidatos 
                if a.get('nombre', '').lower() in [n.lower() for n in alimentos_priorizados_nombres]
            ]
            
            return alimentos_priorizados if alimentos_priorizados else alimentos_candidatos[:5]
            
        except Exception as e:
            print(f"⚠️  Error al optimizar selección con IA: {e}")
            return alimentos_candidatos[:5]
    
    def validar_combinacion_comida(self, alimentos_comida: List[Dict], tiempo_comida: str, perfil_paciente: Dict, alimentos_disponibles: Optional[List[Dict]] = None) -> Dict:
        """
        Valida si una combinación de alimentos es apetitosa y balanceada usando GPT
        
        Args:
            alimentos_comida: Lista de alimentos en la comida
            tiempo_comida: 'des', 'mm', 'alm', 'mt', 'cena'
            perfil_paciente: Diccionario con perfil del paciente
            alimentos_disponibles: Lista opcional de alimentos disponibles en la BD para sugerir reemplazos
            
        Returns:
            Dict con 'es_apetitosa': bool, 'sugerencias': List[str], 'alimentos_a_remover': List[str], 'alimentos_a_agregar': List[str]
        """
        if not self.client:
            return {"es_apetitosa": True, "razon": "IA no disponible", "alimentos_a_remover": [], "alimentos_a_agregar": []}

        print(f"📞 Llamando a API de OpenAI para validar combinación ({tiempo_comida}, {len(alimentos_comida)} alimentos)...")

        try:
            nombres_tiempo = {
                'des': 'Desayuno', 'mm': 'Media Mañana', 'alm': 'Almuerzo',
                'mt': 'Media Tarde', 'cena': 'Cena'
            }
            
            nombres_alimentos = [a.get('nombre', '') for a in alimentos_comida]
            grupos_alimentos_comida = [a.get('grupo', '') for a in alimentos_comida]

            # Preparar lista de alimentos disponibles para el prompt
            disponibles_por_grupo = {}
            if alimentos_disponibles:
                for al_db in alimentos_disponibles:
                    grupo = al_db.get('grupo', 'Otros')
                    if grupo not in disponibles_por_grupo:
                        disponibles_por_grupo[grupo] = []
                    disponibles_por_grupo[grupo].append(al_db.get('nombre', ''))
            
            disponibles_str = ""
            for grupo, nombres_grupo in disponibles_por_grupo.items():
                if nombres_grupo:
                    disponibles_str += f"- {grupo}: {', '.join(nombres_grupo[:15])}\n"  # Limitar a 15 por grupo

            prompt = f"""Eres un nutricionista experto en diabetes tipo 2. Evalúa si esta combinación de alimentos es APETITOSA, REALISTA y BALANCEADA para un {nombres_tiempo.get(tiempo_comida, 'tiempo de comida')}.

TIEMPO DE COMIDA: {nombres_tiempo.get(tiempo_comida, tiempo_comida)}

ALIMENTOS EN LA COMIDA:
{chr(10).join([f"- {nombre} ({grupo})" for nombre, grupo in zip(nombres_alimentos, grupos_alimentos_comida)])}

PERFIL DEL PACIENTE:
- Edad: {perfil_paciente.get('edad', 'N/A')} años
- IMC: {perfil_paciente.get('imc', 'N/A')}
- Sexo: {perfil_paciente.get('sexo', 'N/A')}
- HbA1c: {perfil_paciente.get('hba1c', 'N/A')}%

ALIMENTOS DISPONIBLES EN LA BD (para sugerencias):
{disponibles_str if disponibles_str else "No hay alimentos disponibles en la BD."}

INSTRUCCIONES CRÍTICAS:
Evalúa si esta combinación es REALMENTE apetitosa y sensata. Sé ESTRICTO. Rechaza combinaciones que:
1. No sean típicas o apetitosas para este tiempo de comida (ej: mantequilla sola en merienda, demasiados alimentos pesados en desayuno, avena en almuerzo).
2. Tengan demasiados alimentos del mismo grupo o tipo.
3. No se complementen bien entre sí (ej: múltiples grasas pesadas juntas, legumbres grandes con carnes en desayuno).
4. Sean poco realistas o difíciles de preparar juntos.
5. Para pacientes diabéticos, evita combinaciones con exceso de carbohidratos simples o azúcares, y limita la cantidad total de alimentos en una comida.

Para DESAYUNO: Debe ser ligero, balanceado, no más de 4-5 alimentos diferentes. Prioriza cereales integrales, lácteos bajos en grasa, frutas de bajo IG.
Para ALMUERZO/CENA: Puede ser más completo, pero debe ser balanceado y apetitoso. Limita la cantidad de verduras a un máximo de 200-300g.

Si la combinación NO es apetitosa:
- Identifica los alimentos específicos a REMOVER.
- Sugiere 1-2 alimentos específicos a AGREGAR de la lista de "ALIMENTOS DISPONIBLES EN LA BD" que mejoren la combinación y sean apropiados para el tiempo de comida y el perfil del paciente. Prioriza alimentos que ayuden a balancear los macronutrientes si se removieron alimentos importantes.

Responde SOLO con un JSON válido en este formato:
{{
    "es_apetitosa": true/false,
    "razon": "Explicación breve de por qué es o no apetitosa",
    "alimentos_a_remover": ["nombre_alimento1", "nombre_alimento2"],
    "alimentos_a_agregar": ["nombre_alimento_sugerido1", "nombre_alimento_sugerido2"]
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un nutricionista experto. Responde SOLO con JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )
            
            resultado_texto = response.choices[0].message.content.strip()
            if resultado_texto.startswith("```json"):
                resultado_texto = resultado_texto[7:]
            if resultado_texto.endswith("```"):
                resultado_texto = resultado_texto[:-3]
            resultado_texto = resultado_texto.strip()
            
            resultado = json.loads(resultado_texto)
            print(f"✅ Respuesta de OpenAI recibida: es_apetitosa={resultado.get('es_apetitosa', True)}")
            return {
                'es_apetitosa': resultado.get('es_apetitosa', True),
                'razon': resultado.get('razon', ''),
                'alimentos_a_remover': resultado.get('alimentos_a_remover', []),
                'alimentos_a_agregar': resultado.get('alimentos_a_agregar', [])
            }
            
        except APIError as e:
            if e.code == 'insufficient_quota':
                print(f"❌ Error de cuota de OpenAI: {e}. Por favor, recarga tus créditos.")
                return {'es_apetitosa': True, 'razon': 'Error de cuota de API', 'alimentos_a_remover': [], 'alimentos_a_agregar': []}
            else:
                print(f"❌ Error de API de OpenAI: {e}")
                return {'es_apetitosa': True, 'razon': 'Error de API', 'alimentos_a_remover': [], 'alimentos_a_agregar': []}
        except Exception as e:
            print(f"❌ Error al validar combinación con IA: {e}")
            return {'es_apetitosa': True, 'razon': 'Error interno de IA', 'alimentos_a_remover': [], 'alimentos_a_agregar': []}
    
    def validar_plan_completo(self, plan_semanal: Dict, perfil_paciente: Dict, configuracion: Dict, metas: Dict, alimentos_disponibles: Optional[List[Dict]] = None) -> Dict:
        """
        Valida el plan completo analizando todos los días juntos, los datos del paciente y la configuración
        
        Args:
            plan_semanal: Plan semanal completo con todos los días
            perfil_paciente: Diccionario con perfil completo del paciente
            configuracion: Configuración nutricional del plan (kcal, CHO%, PRO%, FAT%)
            metas: Metas nutricionales finales (gramos de cada macronutriente)
            alimentos_disponibles: Lista de alimentos disponibles en la BD
            
        Returns:
            Dict con 'es_adecuado': bool, 'problemas': List[str], 'correcciones_por_dia': Dict[str, Dict]
        """
        if not self.client:
            return {
                'es_adecuado': True,
                'problemas': [],
                'correcciones_por_dia': {}
            }
        
        print(f"📞 Llamando a API de OpenAI para validar plan COMPLETO (7 días)...")
        
        try:
            # Preparar resumen del plan por día
            resumen_plan = []
            for dia_key in sorted([k for k in plan_semanal.keys() if k.startswith('dia_')]):
                dia_data = plan_semanal[dia_key]
                resumen_dia = f"\n{dia_key.upper()}:\n"
                
                # Resumir cada comida
                for tiempo in ['des', 'mm', 'alm', 'mt', 'cena']:
                    if tiempo in dia_data:
                        comida = dia_data[tiempo]
                        if isinstance(comida, dict) and 'alimentos' in comida:
                            alimentos = comida.get('alimentos', [])
                            if alimentos:
                                nombres = [a.get('nombre', '') for a in alimentos]
                                resumen_dia += f"  {tiempo}: {', '.join(nombres[:5])}\n"
                
                resumen_plan.append(resumen_dia)
            
            resumen_plan_str = "\n".join(resumen_plan)
            
            # Preparar alimentos disponibles agrupados
            disponibles_por_grupo = {}
            if alimentos_disponibles:
                for al_db in alimentos_disponibles:
                    grupo = al_db.get('grupo', 'Otros')
                    if grupo not in disponibles_por_grupo:
                        disponibles_por_grupo[grupo] = []
                    disponibles_por_grupo[grupo].append(al_db.get('nombre', ''))
            
            disponibles_str = ""
            for grupo, nombres_grupo in disponibles_por_grupo.items():
                if nombres_grupo:
                    disponibles_str += f"- {grupo}: {', '.join(nombres_grupo[:20])}\n"
            
            # Calcular cumplimiento aproximado por día (para contexto)
            cumplimiento_por_dia = {}
            for dia_key in [k for k in plan_semanal.keys() if k.startswith('dia_')]:
                dia_data = plan_semanal[dia_key]
                totales = {'kcal': 0, 'cho': 0, 'pro': 0, 'fat': 0}
                for tiempo in ['des', 'mm', 'alm', 'mt', 'cena']:
                    if tiempo in dia_data:
                        comida = dia_data[tiempo]
                        if isinstance(comida, dict):
                            totales['kcal'] += float(comida.get('total_kcal', 0) or 0)
                            totales['cho'] += float(comida.get('total_cho', 0) or 0)
                            totales['pro'] += float(comida.get('total_pro', 0) or 0)
                            totales['fat'] += float(comida.get('total_fat', 0) or 0)
                
                cumplimiento_por_dia[dia_key] = {
                    'kcal': round((totales['kcal'] / metas.get('calorias_diarias', 1800)) * 100, 1) if metas.get('calorias_diarias') else 0,
                    'cho': round((totales['cho'] / metas.get('carbohidratos_g', 117)) * 100, 1) if metas.get('carbohidratos_g') else 0,
                    'pro': round((totales['pro'] / metas.get('proteinas_g', 153)) * 100, 1) if metas.get('proteinas_g') else 0,
                    'fat': round((totales['fat'] / metas.get('grasas_g', 80)) * 100, 1) if metas.get('grasas_g') else 0
                }
            
            cumplimiento_str = "\n".join([
                f"{dia}: Kcal {c['kcal']:.0f}%, CHO {c['cho']:.0f}%, PRO {c['pro']:.0f}%, FAT {c['fat']:.0f}%"
                for dia, c in cumplimiento_por_dia.items()
            ])
            
            prompt = f"""Eres un nutricionista experto en diabetes tipo 2 con especialización en obesidad. Analiza este plan nutricional COMPLETO de 7 días y evalúa si es adecuado para la paciente.

PERFIL DEL PACIENTE:
- Edad: {perfil_paciente.get('edad', 'N/A')} años
- Sexo: {perfil_paciente.get('sexo', 'N/A')}
- Peso: {perfil_paciente.get('peso', 'N/A')} kg
- Talla: {perfil_paciente.get('talla', 'N/A')} m
- IMC: {perfil_paciente.get('imc', 'N/A')} kg/m²
- Circunferencia de cintura: {perfil_paciente.get('cc', 'N/A')} cm
- Actividad física: {perfil_paciente.get('actividad', 'N/A')}
- HbA1c: {perfil_paciente.get('hba1c', 'N/A')}%
- Glucosa en ayunas: {perfil_paciente.get('glucosa_ayunas', 'N/A')} mg/dL
- LDL: {perfil_paciente.get('ldl', 'N/A')} mg/dL

CONFIGURACIÓN DEL PLAN:
- Calorías objetivo: {configuracion.get('kcal_objetivo', 'N/A')} kcal/día
- Carbohidratos: {configuracion.get('cho_pct', 'N/A')}% ({metas.get('carbohidratos_g', 'N/A')}g)
- Proteínas: {configuracion.get('pro_pct', 'N/A')}% ({metas.get('proteinas_g', 'N/A')}g)
- Grasas: {configuracion.get('fat_pct', 'N/A')}% ({metas.get('grasas_g', 'N/A')}g)
- Fibra objetivo: {metas.get('fibra_g', 'N/A')}g

CUMPLIMIENTO POR DÍA (aproximado):
{cumplimiento_str}

PLAN COMPLETO (7 días):
{resumen_plan_str}

ALIMENTOS DISPONIBLES EN LA BD:
{disponibles_str if disponibles_str else "No hay alimentos disponibles."}

INSTRUCCIONES CRÍTICAS:
Esta paciente tiene OBESIDAD GRADO II (IMC 37.6) + DIABETES MAL CONTROLADA (HbA1c 6.9%, glucosa 140 mg/dL). 
El plan DEBE estar diseñado para:
1. PÉRDIDA DE PESO (déficit calórico)
2. REDUCIR GLUCOSA EN AYUNAS (cenas muy bajas en CHO, máximo 15-20g)
3. MEJORAR HbA1c (carbohidratos controlados, 150-180g/día máximo)
4. REDUCIR RESISTENCIA A LA INSULINA (evitar picos glucémicos)

EVALÚA:
1. ¿Los carbohidratos están adecuados? (150-180g/día para esta paciente, NO 200g+)
2. ¿Las cenas son bajas en CHO? (máximo 15-20g, solo verduras + proteína + grasas saludables)
3. ¿Las calorías son adecuadas para pérdida de peso? (1800-1900 kcal)
4. ¿Las proteínas están en rango adecuado? (110-120g, NO 140g+)
5. ¿Las grasas están controladas? (70-80g, NO 100g+)
6. ¿Hay días que NO cumplen las metas? (todos deben estar entre 90-100%)
7. ¿Las combinaciones de alimentos son apetitosas y realistas?
8. ¿Hay demasiados alimentos en una sola comida? (especialmente para diabéticos)

Si encuentras problemas:
- Identifica los días problemáticos
- Especifica qué está mal en cada día
- Sugiere correcciones específicas (alimentos a remover/agregar por día y comida)

Responde SOLO con un JSON válido en este formato:
{{
    "es_adecuado": true/false,
    "problemas": ["Problema 1", "Problema 2"],
    "correcciones_por_dia": {{
        "dia_1": {{
            "cena": {{
                "alimentos_a_remover": ["alimento1"],
                "alimentos_a_agregar": ["alimento2"]
            }}
        }},
        "dia_7": {{
            "alm": {{
                "alimentos_a_remover": ["alimento1"],
                "alimentos_a_agregar": ["alimento2"]
            }}
        }}
    }}
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un nutricionista experto en diabetes tipo 2 y obesidad. Responde SOLO con JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000  # Aumentado para permitir correcciones detalladas
            )
            
            resultado_texto = response.choices[0].message.content.strip()
            if resultado_texto.startswith("```json"):
                resultado_texto = resultado_texto[7:]
            if resultado_texto.endswith("```"):
                resultado_texto = resultado_texto[:-3]
            resultado_texto = resultado_texto.strip()
            
            resultado = json.loads(resultado_texto)
            print(f"✅ Validación de plan completo recibida: es_adecuado={resultado.get('es_adecuado', True)}")
            if resultado.get('problemas'):
                print(f"   Problemas detectados: {len(resultado.get('problemas', []))}")
            if resultado.get('correcciones_por_dia'):
                print(f"   Correcciones sugeridas para {len(resultado.get('correcciones_por_dia', {}))} días")
            
            return {
                'es_adecuado': resultado.get('es_adecuado', True),
                'problemas': resultado.get('problemas', []),
                'correcciones_por_dia': resultado.get('correcciones_por_dia', {})
            }
            
        except APIError as e:
            if e.code == 'insufficient_quota':
                print(f"❌ Error de cuota de OpenAI: {e}. Por favor, recarga tus créditos.")
                return {'es_adecuado': True, 'problemas': [], 'correcciones_por_dia': {}}
            else:
                print(f"❌ Error de API de OpenAI: {e}")
                return {'es_adecuado': True, 'problemas': [], 'correcciones_por_dia': {}}
        except Exception as e:
            print(f"❌ Error al validar plan completo con IA: {e}")
            import traceback
            traceback.print_exc()
            return {'es_adecuado': True, 'problemas': [], 'correcciones_por_dia': {}}
