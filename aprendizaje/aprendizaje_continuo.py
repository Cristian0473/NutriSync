# aprendizaje_continuo.py
# Módulo de Aprendizaje Continuo para NutriSync
# Permite al sistema aprender de resultados reales sin afectar el funcionamiento actual

import os
import json
import hashlib
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal

from Core.bd_conexion import fetch_one, fetch_all, execute

# Flag global para habilitar/deshabilitar aprendizaje continuo
APRENDIZAJE_HABILITADO = os.getenv("APRENDIZAJE_CONTINUO", "false").lower() == "true"


@dataclass
class ResultadoPlan:
    """Resultado de seguir un plan nutricional"""
    plan_id: int
    paciente_id: int
    fecha_inicio: date
    fecha_fin: Optional[date]
    hba1c_inicial: Optional[float]
    hba1c_final: Optional[float]
    glucosa_inicial: Optional[float]
    glucosa_final: Optional[float]
    peso_inicial: Optional[float]
    peso_final: Optional[float]
    cumplimiento_pct: Optional[float]
    satisfaccion: Optional[int]
    resultado_exitoso: bool


class AprendizajeContinuo:
    """Sistema de aprendizaje continuo para mejorar recomendaciones"""
    
    def __init__(self):
        self.habilitado = APRENDIZAJE_HABILITADO
        if not self.habilitado:
            print("⚠️  Aprendizaje continuo deshabilitado. Activar con APRENDIZAJE_CONTINUO=true")
    
    # ===================================================================
    # 1. FEEDBACK LOOP: Capturar resultados de planes
    # ===================================================================
    
    def registrar_resultado_plan(
        self,
        plan_id: int,
        paciente_id: int,
        fecha_inicio: date,
        hba1c_inicial: Optional[float] = None,
        glucosa_inicial: Optional[float] = None,
        peso_inicial: Optional[float] = None,
        imc_inicial: Optional[float] = None
    ) -> Optional[int]:
        """
        Registra el inicio de seguimiento de un plan (baseline)
        Retorna el ID del registro creado
        """
        if not self.habilitado:
            return None
        
        try:
            resultado_id = fetch_one("""
                INSERT INTO plan_resultado (
                    plan_id, paciente_id, fecha_inicio,
                    hba1c_inicial, glucosa_inicial, peso_inicial, imc_inicial,
                    estado
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pendiente')
                RETURNING id
            """, (
                plan_id, paciente_id, fecha_inicio,
                hba1c_inicial, glucosa_inicial, peso_inicial, imc_inicial
            ))
            
            if resultado_id:
                print(f"✅ Registrado baseline para plan {plan_id}")
                return resultado_id[0]
        except Exception as e:
            print(f"⚠️  Error registrando baseline: {e}")
        
        return None
    
    def actualizar_resultado_plan(
        self,
        plan_id: int,
        fecha_fin: date,
        hba1c_final: Optional[float] = None,
        glucosa_final: Optional[float] = None,
        peso_final: Optional[float] = None,
        imc_final: Optional[float] = None,
        cumplimiento_pct: Optional[float] = None,
        satisfaccion: Optional[int] = None,
        feedback_texto: Optional[str] = None
    ) -> bool:
        """
        Actualiza el resultado final de un plan
        Calcula automáticamente si fue exitoso
        """
        if not self.habilitado:
            return False
        
        try:
            # Obtener datos iniciales
            resultado = fetch_one("""
                SELECT id, hba1c_inicial, glucosa_inicial, peso_inicial
                FROM plan_resultado
                WHERE plan_id = %s AND estado = 'pendiente'
                ORDER BY creado_en DESC LIMIT 1
            """, (plan_id,))
            
            if not resultado:
                print(f"⚠️  No se encontró baseline para plan {plan_id}")
                return False
            
            resultado_id, hba1c_ini, glucosa_ini, peso_ini = resultado
            
            # Calcular si fue exitoso
            resultado_exitoso = self._calcular_exito(
                hba1c_ini, hba1c_final,
                glucosa_ini, glucosa_final,
                peso_ini, peso_final
            )
            
            # Actualizar registro
            execute("""
                UPDATE plan_resultado
                SET fecha_fin = %s,
                    hba1c_final = %s,
                    glucosa_final = %s,
                    peso_final = %s,
                    imc_final = %s,
                    cumplimiento_pct = %s,
                    satisfaccion = %s,
                    feedback_texto = %s,
                    estado = 'completado',
                    actualizado_en = NOW()
                WHERE id = %s
            """, (
                fecha_fin, hba1c_final, glucosa_final, peso_final, imc_final,
                cumplimiento_pct, satisfaccion, feedback_texto, resultado_id
            ))
            
            # Aprender de este resultado
            self._aprender_de_resultado(resultado_id, plan_id, paciente_id)
            
            print(f"✅ Resultado actualizado para plan {plan_id}. Exitoso: {resultado_exitoso}")
            return True
            
        except Exception as e:
            print(f"⚠️  Error actualizando resultado: {e}")
            return False
    
    def _calcular_exito(
        self,
        hba1c_ini: Optional[float],
        hba1c_fin: Optional[float],
        glucosa_ini: Optional[float],
        glucosa_fin: Optional[float],
        peso_ini: Optional[float],
        peso_fin: Optional[float]
    ) -> bool:
        """Calcula si el plan fue exitoso basado en mejoras clínicas"""
        mejoras = []
        
        # Mejora en HbA1c (reducción es buena)
        if hba1c_ini and hba1c_fin:
            mejora_hba1c = hba1c_ini - hba1c_fin
            if mejora_hba1c >= 0.5:  # Reducción de al menos 0.5%
                mejoras.append(True)
            elif mejora_hba1c <= -0.5:  # Aumento de más de 0.5%
                mejoras.append(False)
        
        # Mejora en glucosa (reducción es buena)
        if glucosa_ini and glucosa_fin:
            mejora_glucosa = glucosa_ini - glucosa_fin
            if mejora_glucosa >= 10:  # Reducción de al menos 10 mg/dL
                mejoras.append(True)
            elif mejora_glucosa <= -10:
                mejoras.append(False)
        
        # Mejora en peso (depende del objetivo, pero pérdida moderada suele ser buena)
        if peso_ini and peso_fin:
            cambio_peso = peso_ini - peso_fin
            # Pérdida moderada (0.5-2 kg/mes) es positiva
            if 0.5 <= cambio_peso <= 2.0:
                mejoras.append(True)
            elif cambio_peso < -2.0:  # Ganancia significativa
                mejoras.append(False)
        
        # Si hay mejoras, mayoría decide
        if mejoras:
            return sum(mejoras) >= len(mejoras) / 2
        
        return False  # Sin datos suficientes, asumir no exitoso
    
    # ===================================================================
    # 2. MEMORIA A LARGO PLAZO: Aprender patrones
    # ===================================================================
    
    def _aprender_de_resultado(self, resultado_id: int, plan_id: int, paciente_id: int):
        """Extrae patrones de un resultado y los almacena en memoria"""
        if not self.habilitado:
            return
        
        try:
            # Obtener datos del plan
            plan = fetch_one("""
                SELECT metas_json, fecha_ini, fecha_fin
                FROM plan
                WHERE id = %s
            """, (plan_id,))
            
            if not plan:
                return
            
            metas_json, fecha_ini, fecha_fin = plan
            
            # Obtener ingredientes del plan
            ingredientes_plan = fetch_all("""
                SELECT DISTINCT i.id, i.nombre, i.grupo
                FROM plan_alimento pa
                JOIN plan_detalle pd ON pd.id = pa.plan_detalle_id
                JOIN ingrediente i ON i.id = pa.ingrediente_id
                WHERE pd.plan_id = %s
            """, (plan_id,))
            
            # Obtener resultado
            resultado = fetch_one("""
                SELECT resultado_exitoso, mejora_hba1c, mejora_peso
                FROM plan_resultado
                WHERE id = %s
            """, (resultado_id,))
            
            if not resultado:
                return
            
            resultado_exitoso = resultado[0]
            
            # Aprender de cada ingrediente usado
            for ing_id, ing_nombre, ing_grupo in ingredientes_plan:
                self._actualizar_patron_ingrediente(
                    ing_id, ing_nombre, ing_grupo,
                    paciente_id, resultado_exitoso
                )
            
            # Aprender de distribución de macronutrientes
            if metas_json:
                try:
                    metas = json.loads(metas_json) if isinstance(metas_json, str) else metas_json
                    self._actualizar_patron_macronutrientes(
                        metas, paciente_id, resultado_exitoso
                    )
                except:
                    pass
                    
        except Exception as e:
            print(f"⚠️  Error aprendiendo de resultado: {e}")
    
    def _actualizar_patron_ingrediente(
        self,
        ingrediente_id: int,
        ingrediente_nombre: str,
        grupo: str,
        paciente_id: int,
        resultado_exitoso: bool
    ):
        """Actualiza o crea patrón de aprendizaje para un ingrediente"""
        try:
            # Buscar patrón existente
            patron = fetch_one("""
                SELECT id, veces_observado, veces_exitoso, confianza
                FROM aprendizaje_patron
                WHERE tipo_patron = 'ingrediente_exitoso'
                AND elemento_id = %s
                AND elemento_tipo = 'ingrediente'
                LIMIT 1
            """, (ingrediente_id,))
            
            if patron:
                # Actualizar patrón existente
                patron_id, veces_obs, veces_exit, confianza = patron
                nuevas_veces_obs = veces_obs + 1
                nuevas_veces_exit = veces_exit + (1 if resultado_exitoso else 0)
                nueva_confianza = (nuevas_veces_exit / nuevas_veces_obs) * 100
                
                execute("""
                    UPDATE aprendizaje_patron
                    SET veces_observado = %s,
                        veces_exitoso = %s,
                        confianza = %s,
                        ultimo_uso = NOW(),
                        actualizado_en = NOW()
                    WHERE id = %s
                """, (nuevas_veces_obs, nuevas_veces_exit, nueva_confianza, patron_id))
            else:
                # Crear nuevo patrón
                confianza_inicial = 100.0 if resultado_exitoso else 0.0
                execute("""
                    INSERT INTO aprendizaje_patron (
                        tipo_patron, elemento_id, elemento_tipo, elemento_nombre,
                        resultado_exitoso, veces_observado, veces_exitoso, confianza
                    )
                    VALUES ('ingrediente_exitoso', %s, 'ingrediente', %s,
                            %s, 1, %s, %s)
                """, (
                    ingrediente_id, ingrediente_nombre,
                    resultado_exitoso,
                    1 if resultado_exitoso else 0,
                    confianza_inicial
                ))
        except Exception as e:
            print(f"⚠️  Error actualizando patrón de ingrediente: {e}")
    
    def _actualizar_patron_macronutrientes(
        self,
        metas: Dict,
        paciente_id: int,
        resultado_exitoso: bool
    ):
        """Aprende qué distribución de macronutrientes funciona mejor"""
        try:
            cho_pct = metas.get('carbohidratos_porcentaje')
            pro_pct = metas.get('proteinas_porcentaje')
            fat_pct = metas.get('grasas_porcentaje')
            
            if not all([cho_pct, pro_pct, fat_pct]):
                return
            
            # Crear hash del patrón de macronutrientes
            patron_hash = hashlib.md5(
                f"{cho_pct}_{pro_pct}_{fat_pct}".encode()
            ).hexdigest()
            
            # Buscar patrón existente
            patron = fetch_one("""
                SELECT id, veces_observado, veces_exitoso, confianza
                FROM aprendizaje_patron
                WHERE tipo_patron = 'macronutriente_optimo'
                AND elemento_id = %s
                LIMIT 1
            """, (int(patron_hash[:8], 16),))
            
            # Similar a _actualizar_patron_ingrediente pero para macronutrientes
            # (implementación similar)
            
        except Exception as e:
            print(f"⚠️  Error actualizando patrón de macronutrientes: {e}")
    
    # ===================================================================
    # 3. USAR MEMORIA: Consultar qué funcionó antes
    # ===================================================================
    
    def obtener_ingredientes_recomendados_por_aprendizaje(
        self,
        paciente_id: int,
        grupo: str,
        limite: int = 5
    ) -> List[Dict]:
        """
        Retorna ingredientes recomendados basados en aprendizaje previo
        Para usar en lugar de selección aleatoria
        """
        if not self.habilitado:
            return []
        
        try:
            # Obtener ingredientes exitosos de este grupo
            ingredientes = fetch_all("""
                SELECT ap.elemento_id, ap.elemento_nombre, ap.confianza,
                       i.kcal, i.cho, i.pro, i.fat, i.ig
                FROM aprendizaje_patron ap
                JOIN ingrediente i ON i.id = ap.elemento_id
                WHERE ap.tipo_patron = 'ingrediente_exitoso'
                AND ap.elemento_tipo = 'ingrediente'
                AND i.grupo = %s
                AND i.activo = true
                AND ap.confianza >= 60.0  -- Solo ingredientes con buena confianza
                ORDER BY ap.confianza DESC, ap.veces_observado DESC
                LIMIT %s
            """, (grupo, limite))
            
            return [
                {
                    'id': ing[0],
                    'nombre': ing[1],
                    'confianza': float(ing[2]),
                    'kcal': float(ing[3]) if ing[3] else 0,
                    'cho': float(ing[4]) if ing[4] else 0,
                    'pro': float(ing[5]) if ing[5] else 0,
                    'fat': float(ing[6]) if ing[6] else 0,
                    'ig': float(ing[7]) if ing[7] else 100
                }
                for ing in ingredientes
            ]
        except Exception as e:
            print(f"⚠️  Error obteniendo ingredientes por aprendizaje: {e}")
            return []
    
    # ===================================================================
    # 4. REENTRENAMIENTO AUTOMÁTICO: Actualizar modelo periódicamente
    # ===================================================================
    
    def verificar_reentrenamiento_necesario(self) -> bool:
        """
        Verifica si es necesario reentrenar el modelo
        Retorna True si hay suficientes datos nuevos
        """
        if not self.habilitado:
            return False
        
        try:
            # Contar resultados nuevos desde último reentrenamiento
            ultimo_reentrenamiento = fetch_one("""
                SELECT MAX(fecha_fin)
                FROM modelo_reentrenamiento
                WHERE estado = 'completado'
            """)
            
            fecha_limite = ultimo_reentrenamiento[0] if ultimo_reentrenamiento and ultimo_reentrenamiento[0] else date.today() - timedelta(days=365)
            
            resultados_nuevos = fetch_one("""
                SELECT COUNT(*)
                FROM plan_resultado
                WHERE fecha_fin >= %s
                AND estado = 'completado'
            """, (fecha_limite,))
            
            # Reentrenar si hay al menos 50 resultados nuevos
            return resultados_nuevos[0] >= 50 if resultados_nuevos else False
            
        except Exception as e:
            print(f"⚠️  Error verificando reentrenamiento: {e}")
            return False
    
    def iniciar_reentrenamiento(self) -> Optional[int]:
        """
        Inicia proceso de reentrenamiento del modelo
        Retorna ID del proceso de reentrenamiento
        """
        if not self.habilitado:
            return None
        
        try:
            # Obtener versión actual
            version_actual = fetch_one("""
                SELECT MAX(version_nueva)
                FROM modelo_reentrenamiento
                WHERE estado = 'completado'
            """)
            
            version_anterior = version_actual[0] if version_actual and version_actual[0] else "v1.0"
            
            # Crear nueva versión
            from datetime import datetime
            nueva_version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            reentrenamiento_id = fetch_one("""
                INSERT INTO modelo_reentrenamiento (
                    version_anterior, version_nueva, tipo_modelo,
                    fecha_inicio, estado
                )
                VALUES (%s, %s, 'xgboost', NOW(), 'en_proceso')
                RETURNING id
            """, (version_anterior, nueva_version))
            
            if reentrenamiento_id:
                print(f"🔄 Iniciado reentrenamiento: {nueva_version}")
                return reentrenamiento_id[0]
                
        except Exception as e:
            print(f"⚠️  Error iniciando reentrenamiento: {e}")
        
        return None
    
    # ===================================================================
    # 5. APRENDIZAJE POR REFUERZO: Q-Learning
    # ===================================================================
    
    def obtener_mejor_accion(self, estado_paciente: Dict) -> Optional[Dict]:
        """
        Usa Q-Learning para determinar la mejor acción a tomar
        Retorna acción recomendada basada en aprendizaje previo
        """
        if not self.habilitado:
            return None
        
        try:
            # Crear hash del estado
            estado_json = json.dumps(estado_paciente, sort_keys=True)
            estado_hash = hashlib.sha256(estado_json.encode()).hexdigest()
            
            # Buscar mejores acciones para este estado
            acciones = fetch_all("""
                SELECT accion_tipo, accion_valor, q_value, veces_ejecutada
                FROM refuerzo_q_values
                WHERE estado_hash = %s
                ORDER BY q_value DESC
                LIMIT 5
            """, (estado_hash,))
            
            if acciones:
                # Retornar mejor acción
                mejor_accion = acciones[0]
                return {
                    'tipo': mejor_accion[0],
                    'valor': json.loads(mejor_accion[1]) if isinstance(mejor_accion[1], str) else mejor_accion[1],
                    'q_value': float(mejor_accion[2]),
                    'confianza': min(100, mejor_accion[3] * 10)  # Más ejecuciones = más confianza
                }
            
        except Exception as e:
            print(f"⚠️  Error obteniendo mejor acción: {e}")
        
        return None
    
    def actualizar_q_value(
        self,
        estado_paciente: Dict,
        accion_tipo: str,
        accion_valor: Dict,
        recompensa: float
    ):
        """
        Actualiza valor Q después de ejecutar una acción y recibir recompensa
        """
        if not self.habilitado:
            return
        
        try:
            # Crear hash del estado
            estado_json = json.dumps(estado_paciente, sort_keys=True)
            estado_hash = hashlib.sha256(estado_json.encode()).hexdigest()
            
            # Buscar Q-value existente
            q_existente = fetch_one("""
                SELECT id, q_value, veces_ejecutada
                FROM refuerzo_q_values
                WHERE estado_hash = %s AND accion_tipo = %s
            """, (estado_hash, accion_tipo))
            
            # Parámetros de Q-Learning
            alpha = 0.1  # Tasa de aprendizaje
            gamma = 0.9  # Factor de descuento
            
            if q_existente:
                # Actualizar Q-value existente
                q_id, q_actual, veces = q_existente
                nuevo_q = q_actual + alpha * (recompensa - q_actual)
                nuevas_veces = veces + 1
                
                execute("""
                    UPDATE refuerzo_q_values
                    SET q_value = %s,
                        recompensa = %s,
                        veces_ejecutada = %s,
                        veces_exitosa = veces_exitosa + %s,
                        ultima_actualizacion = NOW()
                    WHERE id = %s
                """, (
                    nuevo_q, recompensa, nuevas_veces,
                    1 if recompensa > 0 else 0, q_id
                ))
            else:
                # Crear nuevo Q-value
                execute("""
                    INSERT INTO refuerzo_q_values (
                        estado_hash, estado_json, accion_tipo, accion_valor,
                        q_value, recompensa, veces_ejecutada
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 1)
                """, (
                    estado_hash, estado_json, accion_tipo,
                    json.dumps(accion_valor), recompensa, recompensa
                ))
                
        except Exception as e:
            print(f"⚠️  Error actualizando Q-value: {e}")


# Instancia global (singleton)
_instancia_aprendizaje = None

def obtener_aprendizaje() -> AprendizajeContinuo:
    """Obtiene instancia singleton del sistema de aprendizaje"""
    global _instancia_aprendizaje
    if _instancia_aprendizaje is None:
        _instancia_aprendizaje = AprendizajeContinuo()
    return _instancia_aprendizaje

