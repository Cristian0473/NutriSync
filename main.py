# Configurar encoding UTF-8 para evitar errores con caracteres especiales en Windows
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dotenv import load_dotenv
from urllib.parse import urlencode
import os
import uuid
import re
from datetime import timedelta, datetime
from werkzeug.security import check_password_hash, generate_password_hash
import json
from decimal import Decimal, InvalidOperation
from datetime import date
import traceback

from Core.bd_conexion import fetch_one, fetch_all, execute
from Core.motor_recomendacion import MotorRecomendacion
from Core.motor_recomendacion_basico import MotorRecomendacionBasico
from utils.envio_email import enviar_token_activacion

TOKEN_HORAS_VALIDEZ = 48  # ajusta

from werkzeug.security import generate_password_hash


load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET", "cambia-esto-en-.env")
app.permanent_session_lifetime = timedelta(minutes=5)

def build_activation_link(dni: str, token: str) -> str:
    base = url_for("activar", _external=True)
    return f"{base}?{urlencode({'dni': dni, 'token': token})}"

# ---------- Helpers de sesión/roles ----------
def login_required(view_func):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def admin_only_required(view_func):
    """Decorador que solo permite acceso a administradores (no nutricionistas)"""
    def wrapper(*args, **kwargs):
        uid = session.get("user_id")
        if not uid:
            return redirect(url_for("login"))
        roles = get_user_roles(uid)
        if "admin" not in roles:
            flash("Acceso restringido al rol Administrador", "error")
            return redirect(url_for("home"))
        return view_func(*args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def admin_required(view_func):
    """Decorador que permite acceso a administradores y nutricionistas"""
    def wrapper(*args, **kwargs):
        uid = session.get("user_id")
        if not uid:
            return redirect(url_for("login"))
        roles = get_user_roles(uid)
        if "admin" not in roles and "nutricionista" not in roles:
            flash("Acceso restringido al rol Administrador o Nutricionista", "error")
            return redirect(url_for("home"))
        return view_func(*args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def nutricionista_required(view_func):
    """Decorador que permite acceso a nutricionistas y administradores"""
    def wrapper(*args, **kwargs):
        uid = session.get("user_id")
        if not uid:
            return redirect(url_for("login"))
        roles = get_user_roles(uid)
        if "admin" not in roles and "nutricionista" not in roles:
            flash("Acceso restringido al rol Nutricionista o Administrador", "error")
            return redirect(url_for("home"))
        return view_func(*args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def paciente_required(view_func):
    def wrapper(*args, **kwargs):
        uid = session.get("user_id")
        if not uid:
            return redirect(url_for("login"))
        roles = get_user_roles(uid)
        if "paciente" not in roles:
            flash("Acceso restringido al rol Paciente", "error")
            # Si es admin, redirigir al admin, sino al login
            if "admin" in roles:
                return redirect(url_for("admin_home"))
            return redirect(url_for("logout"))
        return view_func(*args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def get_user_roles(user_id: int) -> list[str]:
    rows = fetch_all("""
        SELECT r.nombre
        FROM usuario_rol ur
        JOIN rol r ON r.id = ur.rol_id
        WHERE ur.usuario_id = %s
    """, (user_id,))
    return [r[0] for r in rows] if rows else []


def get_template_base():
    """Determina el directorio base de templates según el rol del usuario"""
    user_id = session.get("user_id")
    if not user_id:
        return "admin"
    roles = get_user_roles(user_id)
    if "nutricionista" in roles and "admin" not in roles:
        return "nutricionista"
    return "admin"


@app.context_processor
def inject_user_roles():
    """Hace disponible get_user_roles en todos los templates"""
    def get_roles():
        user_id = session.get("user_id")
        if not user_id:
            return []
        return get_user_roles(user_id)
    return dict(get_user_roles=get_roles)


# ---------- Rutas básicas ----------
@app.route("/health")
def health():
    return {"status": "ok"}
@app.route("/api/planes", methods=["POST"])
@login_required
def api_planes_crear():
    try:
        data = request.get_json() or {}
        paciente_id = data.get('paciente_id')
        estado = data.get('estado', 'borrador')
        plan = data.get('plan')
        configuracion = data.get('configuracion', {})
        ingredientes = data.get('ingredientes', {})
        configuracion_original_frontend = data.get('configuracion_original')  # Configuración propuesta por el sistema

        if not paciente_id or not plan:
            return jsonify({"error": "paciente_id y plan son obligatorios"}), 400

        # Extraer fechas de la configuración
        fecha_inicio_str = configuracion.get('fecha_inicio')
        fecha_fin_str = configuracion.get('fecha_fin')
        
        if not fecha_inicio_str:
            # Si no hay fecha de inicio, usar la fecha actual
            fecha_inicio = date.today()
        else:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            except:
                fecha_inicio = date.today()
        
        if not fecha_fin_str:
            # Calcular fecha fin basada en los días del plan
            dias_plan = plan.get('dias', 7)
            fecha_fin = fecha_inicio + timedelta(days=dias_plan - 1)
        else:
            try:
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            except:
                dias_plan = plan.get('dias', 7)
                fecha_fin = fecha_inicio + timedelta(days=dias_plan - 1)
        
        # Obtener configuración ajustada del plan si está disponible
        # El plan generado puede tener valores ajustados por ML
        configuracion_ajustada = plan.get('configuracion_ajustada', {})
        metas_ajustadas = plan.get('metas_nutricionales', {})
        
        # Guardar configuración original ANTES de usar valores ajustados
        # PRIORIDAD:
        # 1. configuracion_original del frontend (propuesta por el sistema al hacer clic en "Recomendación inteligente")
        # 2. configuracion_original del plan (viene del motor)
        # 3. configuracion del request (valores actuales del formulario)
        configuracion_original_plan = plan.get('configuracion_original')
        print(f"🔍 DEBUG api_planes_crear: configuracion_original del frontend: {configuracion_original_frontend}")
        print(f"🔍 DEBUG api_planes_crear: configuracion_original del plan: {configuracion_original_plan}")
        print(f"🔍 DEBUG api_planes_crear: configuracion del request: {configuracion}")
        
        # Priorizar configuración original del frontend (propuesta por el sistema)
        if configuracion_original_frontend:
            configuracion_original_guardar = configuracion_original_frontend
            print(f"🔍 DEBUG api_planes_crear: Usando configuración original del frontend (propuesta por sistema): {configuracion_original_guardar}")
        elif configuracion_original_plan:
            configuracion_original_guardar = configuracion_original_plan
            print(f"🔍 DEBUG api_planes_crear: Usando configuración original del plan: {configuracion_original_guardar}")
        else:
            # Si no hay configuración original, usar la del request (valores antes del ajuste ML)
            configuracion_original_guardar = {
                'kcal_objetivo': configuracion.get('kcal_objetivo'),
                'cho_pct': configuracion.get('cho_pct'),
                'pro_pct': configuracion.get('pro_pct'),
                'fat_pct': configuracion.get('fat_pct')
            }
            print(f"🔍 DEBUG api_planes_crear: Usando configuración del request como original: {configuracion_original_guardar}")
        
        # Usar valores ajustados si están disponibles, sino usar configuración original
        kcal_objetivo = metas_ajustadas.get('calorias_diarias') or configuracion.get('kcal_objetivo')
        cho_pct = metas_ajustadas.get('carbohidratos_porcentaje') or configuracion.get('cho_pct')
        pro_pct = metas_ajustadas.get('proteinas_porcentaje') or configuracion.get('pro_pct')
        fat_pct = metas_ajustadas.get('grasas_porcentaje') or configuracion.get('fat_pct')
        
        # Asegurar que los porcentajes no excedan 100%
        total_pct = (cho_pct or 0) + (pro_pct or 0) + (fat_pct or 0)
        if total_pct > 100:
            # Normalizar proporcionalmente
            factor = 100.0 / total_pct
            cho_pct = round((cho_pct or 0) * factor, 1) if cho_pct else None
            pro_pct = round((pro_pct or 0) * factor, 1) if pro_pct else None
            fat_pct = round((fat_pct or 0) * factor, 1) if fat_pct else None
        
        # Preparar metas nutricionales con valores ajustados
        metas_nutricionales = {
            'calorias_diarias': kcal_objetivo,
            'carbohidratos_porcentaje': cho_pct,
            'proteinas_porcentaje': pro_pct,
            'grasas_porcentaje': fat_pct,
            'carbohidratos_g': metas_ajustadas.get('carbohidratos_g'),
            'proteinas_g': metas_ajustadas.get('proteinas_g'),
            'grasas_g': metas_ajustadas.get('grasas_g'),
            'fibra_g': metas_ajustadas.get('fibra_g'),
            'sodio_mg': metas_ajustadas.get('sodio_mg'),
            # Guardar configuración original y ajustada para referencia
            # Usar la configuración original del plan (viene del motor con los valores ANTES del ajuste ML)
            'configuracion_original': configuracion_original_guardar,
            'configuracion_ajustada': {
                'kcal_objetivo': kcal_objetivo,
                'cho_pct': cho_pct,
                'pro_pct': pro_pct,
                'fat_pct': fat_pct,
                'probabilidad_ml': plan.get('debug_ml', {}).get('probabilidad_mal_control'),
                'ml_disponible': plan.get('debug_ml', {}).get('ml_disponible', False)
            }
        }
        
        # Calcular gramos si hay porcentajes y calorías y no están ya calculados
        if metas_nutricionales['calorias_diarias'] and not metas_nutricionales['carbohidratos_g']:
            kcal = float(metas_nutricionales['calorias_diarias'])
            if metas_nutricionales['carbohidratos_porcentaje']:
                metas_nutricionales['carbohidratos_g'] = round((kcal * float(metas_nutricionales['carbohidratos_porcentaje']) / 100) / 4, 1)
            if metas_nutricionales['proteinas_porcentaje']:
                metas_nutricionales['proteinas_g'] = round((kcal * float(metas_nutricionales['proteinas_porcentaje']) / 100) / 4, 1)
            if metas_nutricionales['grasas_porcentaje']:
                metas_nutricionales['grasas_g'] = round((kcal * float(metas_nutricionales['grasas_porcentaje']) / 100) / 9, 1)
        
        # Crear el plan en la base de datos
        user_id = session.get('user_id')
        plan_id = fetch_one("""
            INSERT INTO plan (paciente_id, metas_json, fecha_ini, fecha_fin, estado, creado_por, version_modelo)
            VALUES (%s, %s, %s, %s, %s, %s, 'motor_recomendacion_v1')
            RETURNING id
        """, (
            paciente_id,
            json.dumps(metas_nutricionales),
            fecha_inicio,
            fecha_fin,
            estado,
            user_id
        ))[0]
        
        # Hook de aprendizaje continuo (opcional, no afecta si falla)
        try:
            from aprendizaje.integracion_aprendizaje import hook_plan_guardado
            hook_plan_guardado(plan_id, paciente_id, fecha_inicio)
        except:
            pass  # Silenciosamente ignorar si no está disponible
        
        # Mapeo de nombres de comidas a códigos
        tiempo_map = {
            'desayuno': 'des',
            'media_manana': 'mm',
            'almuerzo': 'alm',
            'media_tarde': 'mt',
            'cena': 'cena'
        }
        
        # Procesar todas las semanas y días del plan
        semanas = plan.get('semanas', [])
        for semana in semanas:
            dias = semana.get('dias', [])
            for dia_data in dias:
                dia_fecha_str = dia_data.get('fecha')
                if not dia_fecha_str:
                    continue
                
                try:
                    dia_fecha = datetime.strptime(dia_fecha_str, '%Y-%m-%d').date()
                except:
                    continue
                
                comidas = dia_data.get('comidas', {})
                
                # Procesar cada comida del día
                for comida_nombre, comida_data in comidas.items():
                    tiempo_codigo = tiempo_map.get(comida_nombre)
                    if not tiempo_codigo:
                        continue
                    
                    alimentos = comida_data.get('alimentos', [])
                    if not alimentos:
                        continue
                    
                    # Crear detalle del plan (comida)
                    detalle_id = fetch_one("""
                        INSERT INTO plan_detalle (plan_id, dia, tiempo)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, (plan_id, dia_fecha, tiempo_codigo))[0]
                    
                    # Insertar cada alimento
                    for alimento in alimentos:
                        # Intentar obtener ingrediente_id directamente (más confiable)
                        ingrediente_id = alimento.get('ingrediente_id')
                        ingrediente_nombre = alimento.get('nombre') or alimento.get('ingrediente', {}).get('nombre')
                        
                        # Si no hay ID, buscar por nombre
                        if not ingrediente_id:
                            if not ingrediente_nombre:
                                print(f"⚠️ Alimento sin nombre ni ID: {alimento}")
                                continue
                            
                            # Buscar ingrediente por nombre
                            ingrediente_row = fetch_one("""
                                SELECT id, kcal, cho, pro, fat, fibra, porcion_base, unidad_base, ig
                                FROM ingrediente 
                                WHERE nombre = %s AND activo = TRUE 
                                LIMIT 1
                            """, (ingrediente_nombre,))
                            
                            if not ingrediente_row:
                                print(f"⚠️ Ingrediente no encontrado: {ingrediente_nombre}")
                                continue
                            
                            ingrediente_id = ingrediente_row[0]
                            ingrediente_kcal_100g = float(ingrediente_row[1] or 0)
                            ingrediente_cho_100g = float(ingrediente_row[2] or 0)
                            ingrediente_pro_100g = float(ingrediente_row[3] or 0)
                            ingrediente_fat_100g = float(ingrediente_row[4] or 0)
                            ingrediente_fibra_100g = float(ingrediente_row[5] or 0)
                            ingrediente_ig = float(ingrediente_row[8] or 0)
                            porcion_base = float(ingrediente_row[6] or 100)
                            unidad_base = ingrediente_row[7] or 'g'
                        else:
                            # Si tenemos el ID, obtener datos del ingrediente
                            ingrediente_row = fetch_one("""
                                SELECT id, kcal, cho, pro, fat, fibra, porcion_base, unidad_base, ig
                                FROM ingrediente 
                                WHERE id = %s AND activo = TRUE 
                                LIMIT 1
                            """, (ingrediente_id,))
                            
                            if not ingrediente_row:
                                print(f"⚠️ Ingrediente con ID {ingrediente_id} no encontrado")
                                continue
                            
                            ingrediente_kcal_100g = float(ingrediente_row[1] or 0)
                            ingrediente_cho_100g = float(ingrediente_row[2] or 0)
                            ingrediente_pro_100g = float(ingrediente_row[3] or 0)
                            ingrediente_fat_100g = float(ingrediente_row[4] or 0)
                            ingrediente_fibra_100g = float(ingrediente_row[5] or 0)
                            ingrediente_ig = float(ingrediente_row[8] or 0)
                            porcion_base = float(ingrediente_row[6] or 100)
                            unidad_base = ingrediente_row[7] or 'g'
                        
                        # Extraer cantidad y unidad
                        cantidad = alimento.get('cantidad_num')  # Intentar obtener número directamente
                        cantidad_str = alimento.get('cantidad', '')
                        unidad = alimento.get('unidad') or unidad_base
                        
                        if cantidad is None and cantidad_str:
                            # Extraer número y unidad (ej: "120g" -> 120, "g")
                            match = re.match(r'(\d+\.?\d*)\s*(\w*)', str(cantidad_str))
                            if match:
                                cantidad = float(match.group(1))
                                unidad = match.group(2) or unidad_base
                        
                        # Si no hay cantidad, usar porción base por defecto
                        if not cantidad:
                            cantidad = porcion_base
                        
                        # Valores nutricionales del alimento (del objeto o calcular desde ingrediente)
                        kcal = alimento.get('kcal')
                        cho = alimento.get('cho')
                        pro = alimento.get('pro')
                        fat = alimento.get('fat')
                        fibra = alimento.get('fibra')
                        
                        # Calcular valores nutricionales basados en la cantidad si no están presentes o son 0
                        factor = cantidad / 100.0  # Factor de conversión
                        
                        # Calcular cada valor si no está presente o es 0
                        if kcal is None or kcal == 0:
                            kcal = ingrediente_kcal_100g * factor
                        else:
                            kcal = float(kcal or 0)
                            
                        if cho is None or cho == 0:
                            cho = ingrediente_cho_100g * factor
                        else:
                            cho = float(cho or 0)
                            
                        if pro is None or pro == 0:
                            pro = ingrediente_pro_100g * factor
                        else:
                            pro = float(pro or 0)
                            
                        if fat is None or fat == 0:
                            fat = ingrediente_fat_100g * factor
                        else:
                            fat = float(fat or 0)
                            
                        if fibra is None or fibra == 0:
                            fibra = ingrediente_fibra_100g * factor
                        else:
                            fibra = float(fibra or 0)
                        
                        # Calcular CG (carbohidratos glucémicos) si hay IG
                        cg = None
                        if cho and ingrediente_ig:
                            cg = round(cho * (ingrediente_ig / 100.0), 2)
                        elif cho:
                            cg = round(cho, 2)  # Aproximación si no hay IG
                        
                        # Insertar alimento en el plan
                        execute("""
                            INSERT INTO plan_alimento (plan_detalle_id, ingrediente_id, cantidad, unidad, kcal, cho, pro, fat, fibra, cg)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            detalle_id,
                            ingrediente_id,
                            cantidad,
                            unidad,
                            round(kcal, 2),
                            round(cho, 2),
                            round(pro, 2),
                            round(fat, 2),
                            round(fibra, 2),
                            cg
                        ))
                        
                        print(f"✅ Alimento guardado: {ingrediente_nombre or 'ID ' + str(ingrediente_id)} - {cantidad}{unidad}")
        
        detalle_url = url_for('admin_plan_ver', pid=plan_id)
        return jsonify({
            'id': plan_id,
            'detalle_url': detalle_url,
            'message': f'Plan guardado correctamente con ID {plan_id}'
        }), 200
        
    except Exception as e:
        print('ERROR guardando plan:', str(e))
        import traceback
        print('TRACEBACK:', traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/planes/<plan_id>')
@login_required
def ver_plan_detalle(plan_id):
    try:
        import os, json as _json
        base_dir = os.path.join(os.getcwd(), 'planes_guardados')
        path = os.path.join(base_dir, f"plan_{plan_id}.json")
        if not os.path.exists(path):
            return "Plan no encontrado", 404
        with open(path, 'r', encoding='utf-8') as f:
            plan_data = _json.load(f)
        return render_template('admin/plan_detalle.html', plan=plan_data)
    except Exception as e:
        return f"Error cargando plan: {str(e)}", 500



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = (request.form.get("usuario") or "").strip().lower()
        password = request.form.get("password") or ""

        # ¿ingresó DNI (solo dígitos y largo 8) o email?
        es_dni = usuario.isdigit() and len(usuario) == 8

        if es_dni:
            # buscar usuario por DNI → paciente → usuario_id
            row = fetch_one("""
                SELECT u.id, u.hash_pwd, u.estado
                FROM paciente p
                JOIN usuario u ON u.id = p.usuario_id
                WHERE p.dni = %s
            """, (usuario,))
        else:
            # buscar usuario por email
            row = fetch_one("""
                SELECT id, hash_pwd, estado
                FROM usuario
                WHERE email = %s
            """, (usuario,))

        if not row:
            flash("Usuario no encontrado o no activado. Si eres paciente, usa tu enlace / token de activación.", "error")
            return render_template("login.html")

        user_id, hash_pwd, estado = row

        if estado != "activo":
            flash("Cuenta inactiva o bloqueada", "error")
            return render_template("login.html")

        if not check_password_hash(hash_pwd or "", password):
            flash("Usuario o contraseña inválidos", "error")
            return render_template("login.html")

        session.clear()
        session.permanent = True
        session["user_id"] = user_id
        session["user_email"] = fetch_one("SELECT email FROM usuario WHERE id=%s", (user_id,))[0]

        roles = get_user_roles(user_id)
        print(f"DEBUG Login: user_id={user_id}, roles={roles}")  # Debug
        
        if "admin" in roles:
            return redirect(url_for("admin_home"))
        elif "nutricionista" in roles:
            return redirect(url_for("nutricionista_home"))
        elif "paciente" in roles:
            # Verificar que el usuario tenga un registro en la tabla paciente
            paciente_data = get_paciente_by_user_id(user_id)
            if not paciente_data:
                print(f"DEBUG: Usuario {user_id} tiene rol paciente pero no tiene registro en tabla paciente")
                flash("Tu cuenta tiene el rol paciente pero no está asociada a un registro de paciente. Contacta al administrador.", "error")
                session.clear()
                return render_template("login.html")
            return redirect(url_for("paciente_dashboard"))
        # Si no tiene ningún rol conocido, mostrar error
        flash("Tu cuenta no tiene un rol asignado. Contacta al administrador.", "error")
        session.clear()
        return render_template("login.html")

    return render_template("login.html")



# Ruta /activar (DNI + token + nueva contraseña)

def valida_pwd(dni: str, pwd: str) -> tuple[bool, str]:
    if len(pwd) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."
    if dni and dni in pwd:
        return False, "La contraseña no debe contener tu DNI."
    return True, ""

@app.route("/activar", methods=["GET", "POST"])
def activar():
    if request.method == "POST":
        dni = (request.form.get("dni") or "").strip()
        token = (request.form.get("token") or "").strip()
        pwd = request.form.get("password") or ""

        ok, msg = valida_pwd(dni, pwd)
        if not ok:
            flash(msg, "error")
            return render_template("activar.html", dni=dni, token=token)

        tok = fetch_one("""
            SELECT dni, vence_en, usado
            FROM activacion_token
            WHERE dni=%s AND token=%s
        """, (dni, token))
        if not tok:
            flash("Token inválido.", "error")
            return render_template("activar.html")

        _, vence_en, usado = tok
        if usado:
            flash("Token ya fue utilizado.", "error")
            return render_template("activar.html")
        if datetime.now() > vence_en:
            flash("Token expirado.", "error")
            return render_template("activar.html")

        pr = fetch_one("""
            SELECT dni, nombres, apellidos, telefono, email, estado
            FROM pre_registro
            WHERE dni=%s
        """, (dni,))
        if not pr:
            flash("El DNI no está pre-registrado.", "error")
            return render_template("activar.html")

        _, nombres, apellidos, telefono, email, estado = pr
        if estado == "activado":
            flash("El DNI ya fue activado. Inicia sesión.", "info")
            return redirect(url_for("login"))

        # Si no hay email, generar uno genérico basado en el DNI
        if not email or email.strip() == "":
            email = f"paciente.{dni}@nutrisync.local"
            # Actualizar el email en pre_registro
            execute("UPDATE pre_registro SET email=%s WHERE dni=%s", (email, dni))

        user = fetch_one("SELECT id FROM usuario WHERE email=%s", (email,))
        if user:
            user_id = user[0]
            execute("UPDATE usuario SET hash_pwd=%s, estado='activo', mfa=FALSE WHERE id=%s",
                    (generate_password_hash(pwd), user_id))
        else:
            user_id = fetch_one("""
                INSERT INTO usuario (email, hash_pwd, estado, mfa)
                VALUES (%s, %s, 'activo', FALSE)
                RETURNING id
            """, (email, generate_password_hash(pwd)))[0]

        # ✅ Asegurar que el usuario tenga el rol de "paciente"
        ensure_role(user_id, "paciente")

        pac = fetch_one("SELECT id FROM paciente WHERE dni=%s", (dni,))
        if pac:
            execute("UPDATE paciente SET usuario_id=%s WHERE id=%s", (user_id, pac[0]))
        else:
            execute("""
                INSERT INTO paciente (usuario_id, dni, telefono)
                VALUES (%s, %s, %s)
            """, (user_id, dni, telefono))

        execute("UPDATE activacion_token SET usado=TRUE WHERE dni=%s AND token=%s", (dni, token))
        execute("UPDATE pre_registro SET estado='activado' WHERE dni=%s", (dni,))

        flash("Cuenta activada. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("login"))

    return render_template("activar.html")
















@app.route("/api/pacientes/buscar")
@admin_required
def api_pacientes_buscar():
    """API para buscar pacientes (para combo de búsqueda) - Compatible con Select2"""
    q = (request.args.get("q") or "").strip()
    
    # Permitir búsqueda desde el primer carácter (no requiere mínimo)
    if not q:
        return jsonify({"results": []})
    
    # Buscar por DNI, nombres o apellidos (búsqueda flexible con ILIKE para coincidencias parciales)
    pacientes = fetch_all("""
        SELECT p.id, p.dni, 
               COALESCE(pr.nombres, '') AS nombres,
               COALESCE(pr.apellidos, '') AS apellidos,
               p.sexo, TO_CHAR(p.fecha_nac,'YYYY-MM-DD') AS fecha_nac,
               p.telefono, u.email AS usuario_email,
               CASE 
                 WHEN p.dni = %s THEN 1
                 WHEN p.dni LIKE %s THEN 2
                 WHEN pr.nombres ILIKE %s OR pr.apellidos ILIKE %s THEN 3
                 ELSE 4
               END AS orden_prioridad
        FROM paciente p
        LEFT JOIN pre_registro pr ON pr.dni = p.dni
        LEFT JOIN usuario u ON u.id = p.usuario_id
        WHERE p.dni ILIKE %s 
           OR pr.nombres ILIKE %s 
           OR pr.apellidos ILIKE %s
        GROUP BY p.id, p.dni, pr.nombres, pr.apellidos, p.sexo, p.fecha_nac, p.telefono, u.email
        ORDER BY orden_prioridad, p.dni
        LIMIT 50
    """, (q, f"{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"))
    
    results = [{
        "id": p[0],
        "text": f"{p[1]} - {p[2]} {p[3]}".strip(),
        "dni": p[1],
        "nombres": p[2],
        "apellidos": p[3],
        "sexo": p[4] if len(p) > 4 else None,
        "fecha_nac": p[5] if len(p) > 5 else None,
        "telefono": p[6] if len(p) > 6 else None,
        "usuario_email": p[7] if len(p) > 7 else None
    } for p in pacientes]
    
    return jsonify({"results": results})

@app.route("/api/pacientes/<int:pid>/fechas")
@admin_required
def api_paciente_fechas(pid):
    """API para obtener todas las fechas de registros de un paciente"""
    # Obtener fechas de registros clínicos y antropométricos
    fechas_clinico = fetch_all("""
        SELECT DISTINCT TO_CHAR(fecha, 'YYYY-MM-DD') AS fecha
        FROM clinico
        WHERE paciente_id = %s
        ORDER BY fecha DESC
    """, (pid,))
    
    fechas_antropo = fetch_all("""
        SELECT DISTINCT TO_CHAR(fecha, 'YYYY-MM-DD') AS fecha
        FROM antropometria
        WHERE paciente_id = %s
        ORDER BY fecha DESC
    """, (pid,))
    
    # Combinar y eliminar duplicados
    todas_fechas = set()
    if fechas_clinico:
        todas_fechas.update([f[0] for f in fechas_clinico])
    if fechas_antropo:
        todas_fechas.update([f[0] for f in fechas_antropo])
    
    fechas_ordenadas = sorted(todas_fechas, reverse=True)
    
    response = jsonify({
        "ok": True,
        "fechas": fechas_ordenadas,
        "fecha_mas_reciente": fechas_ordenadas[0] if fechas_ordenadas else None
    })
    # Agregar headers para evitar caché
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/api/pacientes/<int:pid>/detalle")
@admin_required
def api_paciente_detalle(pid):
    """Obtiene datos de un paciente, opcionalmente de una fecha específica"""
    from flask import Response
    fecha_param = request.args.get("fecha")  # Fecha opcional en formato YYYY-MM-DD
    
    p = fetch_one("""
        SELECT p.id, p.dni, p.sexo, TO_CHAR(p.fecha_nac,'YYYY-MM-DD') AS fecha_nac,
               p.telefono, u.email AS usuario_email,
               COALESCE(pr.nombres,'') AS nombres, COALESCE(pr.apellidos,'') AS apellidos
          FROM paciente p
          LEFT JOIN usuario u ON u.id = p.usuario_id
          LEFT JOIN pre_registro pr ON pr.dni = p.dni
         WHERE p.id=%s
    """, (pid,))
    if not p:
        return {"ok": False, "msg": "Paciente no encontrado"}, 404
    
    # Obtener datos de antropometría (de fecha específica o más reciente)
    if fecha_param:
        antropo = fetch_one("""
            SELECT peso, talla, cc, bf_pct, actividad, TO_CHAR(fecha,'YYYY-MM-DD') AS fecha_medicion
              FROM antropometria
             WHERE paciente_id=%s AND fecha=%s
             ORDER BY fecha DESC LIMIT 1
        """, (pid, fecha_param))
    else:
        antropo = fetch_one("""
            SELECT peso, talla, cc, bf_pct, actividad, TO_CHAR(fecha,'YYYY-MM-DD') AS fecha_medicion
              FROM antropometria
             WHERE paciente_id=%s
             ORDER BY fecha DESC LIMIT 1
        """, (pid,))
    
    # Obtener datos clínicos (de fecha específica o más reciente)
    if fecha_param:
        clinico = fetch_one("""
            SELECT hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia, TO_CHAR(fecha,'YYYY-MM-DD') AS fecha_medicion
              FROM clinico
             WHERE paciente_id=%s AND fecha=%s
             ORDER BY fecha DESC LIMIT 1
        """, (pid, fecha_param))
    else:
        clinico = fetch_one("""
            SELECT hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia, TO_CHAR(fecha,'YYYY-MM-DD') AS fecha_medicion
              FROM clinico
             WHERE paciente_id=%s
             ORDER BY fecha DESC LIMIT 1
        """, (pid,))
    
    # Calcular IMC si hay peso y talla
    imc = None
    if antropo and antropo[0] and antropo[1]:
        try:
            imc = round(float(antropo[0]) / (float(antropo[1]) ** 2), 2)
        except:
            pass
    
    # Calcular edad si hay fecha de nacimiento
    edad = None
    if p[3]:
        try:
            from datetime import date
            fecha_nac = date.fromisoformat(p[3])
            edad = (date.today() - fecha_nac).days // 365
        except:
            pass
    
    response = jsonify({
        "ok": True, 
        "paciente": {
            "id": p[0], "dni": p[1], "sexo": p[2], "fecha_nac": p[3],
            "telefono": p[4], "usuario_email": p[5],
            "nombres": p[6], "apellidos": p[7],
            "edad": edad,
            "antropometria": {
                "peso": float(antropo[0]) if antropo and antropo[0] else None,
                "talla": float(antropo[1]) if antropo and antropo[1] else None,
                "cc": float(antropo[2]) if antropo and antropo[2] else None,
                "bf_pct": float(antropo[3]) if antropo and antropo[3] else None,
                "actividad": antropo[4] if antropo else None,
                "fecha_medicion": antropo[5] if antropo else None,
                "imc": imc
            },
            "clinico": {
                "hba1c": float(clinico[0]) if clinico and clinico[0] else None,
                "glucosa_ayunas": float(clinico[1]) if clinico and clinico[1] else None,
                "ldl": float(clinico[2]) if clinico and clinico[2] else None,
                "trigliceridos": float(clinico[3]) if clinico and clinico[3] else None,
                "pa_sis": int(clinico[4]) if clinico and clinico[4] else None,
                "pa_dia": int(clinico[5]) if clinico and clinico[5] else None,
                "fecha_medicion": clinico[6] if clinico else None
            }
        }
    })
    # Agregar headers para evitar caché
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route("/api/pacientes/page")
@admin_required
def api_pacientes_page():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))
    offset = (page - 1) * per_page

    total = fetch_one("SELECT COUNT(*) FROM paciente")[0]
    rows = fetch_all(f"""
        SELECT p.id, p.dni, p.sexo, TO_CHAR(p.fecha_nac,'YYYY-MM-DD') AS fecha_nac,
               p.telefono, u.email AS usuario_email,
               COALESCE(pr.nombres,'') AS nombres, COALESCE(pr.apellidos,'') AS apellidos,
               CASE 
                 WHEN (SELECT MAX(fecha) FROM antropometria WHERE paciente_id = p.id) IS NULL 
                      AND (SELECT MAX(fecha) FROM clinico WHERE paciente_id = p.id) IS NULL 
                 THEN NULL
                 ELSE GREATEST(
                   COALESCE((SELECT MAX(fecha) FROM antropometria WHERE paciente_id = p.id), '1900-01-01'::date),
                   COALESCE((SELECT MAX(fecha) FROM clinico WHERE paciente_id = p.id), '1900-01-01'::date)
                 )
               END AS ultima_fecha_registro
          FROM paciente p
          LEFT JOIN usuario u ON u.id = p.usuario_id
          LEFT JOIN pre_registro pr ON pr.dni = p.dni
         ORDER BY p.id DESC
         LIMIT %s OFFSET %s
    """, (per_page, offset)) or []

    data = []
    for r in rows:
        ultima_fecha = None
        if r[8]:
            # r[8] puede ser un objeto date o una cadena
            if hasattr(r[8], 'strftime'):
                # Es un objeto date
                if r[8].year > 1900:  # Verificar que no sea la fecha por defecto
                    ultima_fecha = r[8].strftime('%Y-%m-%d')
            elif isinstance(r[8], str) and r[8] != '1900-01-01':
                ultima_fecha = r[8]
        
        data.append(dict(
            id=r[0], dni=r[1], sexo=r[2], fecha_nac=r[3],
            telefono=r[4], usuario_email=r[5],
            nombres=r[6], apellidos=r[7],
            ultima_fecha_registro=ultima_fecha
        ))

    total_pages = (total + per_page - 1) // per_page
    return {"ok": True, "rows": data, "total_pages": total_pages}


@app.route("/simulacion/dieta")
def simulacion_dieta():
    return render_template("sim_dieta.html")




@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    # Redirigir según el rol del usuario
    user_id = session.get("user_id")
    roles = get_user_roles(user_id)
    
    if "admin" in roles:
        return redirect(url_for("admin_home"))
    elif "nutricionista" in roles:
        return redirect(url_for("nutricionista_home"))
    elif "paciente" in roles:
        return redirect(url_for("paciente_dashboard"))
    # Por defecto, redirigir al admin
    return redirect(url_for("admin_home"))


# ---------- Panel Administrador ----------
@app.route("/admin")
@admin_required
def admin_home():
    """Dashboard principal del administrador/nutricionista"""
    email = session.get("user_email")
    user_id = session.get("user_id")
    roles = get_user_roles(user_id)
    
    # Obtener nombre y apellido del usuario (si es admin, puede no tener perfil_nutricionista)
    usuario_nombre = email  # Por defecto usar email
    perfil = fetch_one("""
        SELECT nombres, apellidos
        FROM perfil_nutricionista
        WHERE usuario_id = %s
    """, (user_id,))
    if perfil and perfil[0] and perfil[1]:
        usuario_nombre = f"{perfil[0]} {perfil[1]}"
    elif perfil and perfil[0]:
        usuario_nombre = perfil[0]
    elif perfil and perfil[1]:
        usuario_nombre = perfil[1]
    
    # ========== 1. RESUMEN GENERAL (CARDS) ==========
    total_pacientes = fetch_one("SELECT COUNT(*) FROM paciente")[0] or 0
    
    # Planes generados últimos 30 días
    planes_30d = fetch_one("""
        SELECT COUNT(*) 
        FROM plan 
        WHERE creado_en >= CURRENT_DATE - INTERVAL '30 days'
    """)[0] or 0
    
    # Pacientes con datos clínicos recientes (últimos 30 días)
    pacientes_con_datos = fetch_one("""
        SELECT COUNT(DISTINCT c.paciente_id)
        FROM clinico c
        WHERE c.fecha >= CURRENT_DATE - INTERVAL '30 days'
    """)[0] or 0
    
    # Planes activos (vigentes)
    planes_activos = fetch_one("""
        SELECT COUNT(*) 
        FROM plan 
        WHERE fecha_fin >= CURRENT_DATE
    """)[0] or 0
    
    # Promedio de planes por paciente
    promedio_planes = fetch_one("""
        SELECT CASE 
            WHEN COUNT(DISTINCT paciente_id) > 0 
            THEN ROUND(COUNT(*)::numeric / COUNT(DISTINCT paciente_id), 2)
            ELSE 0
        END
        FROM plan
    """)[0] or 0
    
    # ========== 2. ESTADÍSTICAS DE PACIENTES ==========
    # Distribución por sexo
    distribucion_sexo = fetch_all("""
        SELECT 
            COALESCE(sexo, 'No especificado') as sexo,
            COUNT(*) as cantidad
        FROM paciente
        GROUP BY sexo
    """)
    
    # Distribución por rangos de edad
    distribucion_edad = fetch_all("""
        SELECT 
            CASE 
                WHEN EXTRACT(YEAR FROM AGE(fecha_nac)) < 30 THEN '18-29'
                WHEN EXTRACT(YEAR FROM AGE(fecha_nac)) < 40 THEN '30-39'
                WHEN EXTRACT(YEAR FROM AGE(fecha_nac)) < 50 THEN '40-49'
                WHEN EXTRACT(YEAR FROM AGE(fecha_nac)) < 60 THEN '50-59'
                WHEN EXTRACT(YEAR FROM AGE(fecha_nac)) < 70 THEN '60-69'
                ELSE '70+'
            END as rango_edad,
            COUNT(*) as cantidad
        FROM paciente
        WHERE fecha_nac IS NOT NULL
        GROUP BY rango_edad
        ORDER BY MIN(EXTRACT(YEAR FROM AGE(fecha_nac)))
    """)
    
    # Distribución por IMC (última medición)
    distribucion_imc = fetch_all("""
        WITH ultima_antropo AS (
            SELECT DISTINCT ON (paciente_id) 
                paciente_id,
                peso,
                talla,
                CASE 
                    WHEN peso IS NOT NULL AND talla IS NOT NULL AND talla > 0
                    THEN ROUND((peso / (talla * talla))::numeric, 2)
                    ELSE NULL
                END as imc
            FROM antropometria
            ORDER BY paciente_id, fecha DESC
        )
        SELECT 
            CASE 
                WHEN imc < 18.5 THEN 'Bajo peso'
                WHEN imc < 25 THEN 'Normal'
                WHEN imc < 30 THEN 'Sobrepeso'
                WHEN imc >= 30 THEN 'Obesidad'
                ELSE 'Sin datos'
            END as categoria_imc,
            COUNT(*) as cantidad
        FROM ultima_antropo
        GROUP BY categoria_imc
    """)
    
    # Pacientes por control glucémico (última HbA1c)
    control_glucemico = fetch_all("""
        WITH ultimo_clinico AS (
            SELECT DISTINCT ON (paciente_id) 
                paciente_id,
                hba1c
            FROM clinico
            WHERE hba1c IS NOT NULL
            ORDER BY paciente_id, fecha DESC
        )
        SELECT 
            CASE 
                WHEN hba1c < 7 THEN 'Bueno (<7%%)'
                WHEN hba1c < 8 THEN 'Moderado (7-8%%)'
                WHEN hba1c >= 8 THEN 'Malo (≥8%%)'
                ELSE 'Sin datos'
            END as control,
            COUNT(*) as cantidad
        FROM ultimo_clinico
        GROUP BY control
    """)
    
    # Pacientes con datos incompletos
    pacientes_incompletos = fetch_one("""
        SELECT COUNT(DISTINCT p.id)
        FROM paciente p
        LEFT JOIN (
            SELECT DISTINCT ON (paciente_id) paciente_id
            FROM antropometria
            WHERE fecha >= CURRENT_DATE - INTERVAL '90 days'
            ORDER BY paciente_id, fecha DESC
        ) a ON a.paciente_id = p.id
        LEFT JOIN (
            SELECT DISTINCT ON (paciente_id) paciente_id
            FROM clinico
            WHERE fecha >= CURRENT_DATE - INTERVAL '90 days'
            ORDER BY paciente_id, fecha DESC
        ) c ON c.paciente_id = p.id
        WHERE a.paciente_id IS NULL OR c.paciente_id IS NULL
    """)[0] or 0
    
    # ========== 3. MÉTRICAS CLÍNICAS (TENDENCIAS) ==========
    # Promedio de HbA1c por mes (últimos 6 meses)
    tendencia_hba1c = fetch_all("""
        SELECT 
            TO_CHAR(fecha, 'YYYY-MM') as mes,
            ROUND(AVG(hba1c)::numeric, 2) as promedio_hba1c,
            COUNT(*) as mediciones
        FROM clinico
        WHERE hba1c IS NOT NULL 
            AND fecha >= CURRENT_DATE - INTERVAL '6 months'
        GROUP BY TO_CHAR(fecha, 'YYYY-MM')
        ORDER BY mes
    """)
    
    # Promedio de glucosa en ayunas por mes
    tendencia_glucosa = fetch_all("""
        SELECT 
            TO_CHAR(fecha, 'YYYY-MM') as mes,
            ROUND(AVG(glucosa_ayunas)::numeric, 2) as promedio_glucosa,
            COUNT(*) as mediciones
        FROM clinico
        WHERE glucosa_ayunas IS NOT NULL 
            AND fecha >= CURRENT_DATE - INTERVAL '6 months'
        GROUP BY TO_CHAR(fecha, 'YYYY-MM')
        ORDER BY mes
    """)
    
    # Promedio de IMC por mes
    tendencia_imc = fetch_all("""
        SELECT 
            TO_CHAR(fecha, 'YYYY-MM') as mes,
            ROUND(AVG(CASE 
                WHEN peso IS NOT NULL AND talla IS NOT NULL AND talla > 0
                THEN peso / (talla * talla)
                ELSE NULL
            END)::numeric, 2) as promedio_imc,
            COUNT(*) as mediciones
        FROM antropometria
        WHERE peso IS NOT NULL AND talla IS NOT NULL
            AND fecha >= CURRENT_DATE - INTERVAL '6 months'
        GROUP BY TO_CHAR(fecha, 'YYYY-MM')
        ORDER BY mes
    """)
    
    # Pacientes con riesgo metabólico alto (IMC >30 + HbA1c >7%)
    riesgo_metabolico = fetch_one("""
        WITH ultima_antropo AS (
            SELECT DISTINCT ON (paciente_id) 
                paciente_id,
                CASE 
                    WHEN peso IS NOT NULL AND talla IS NOT NULL AND talla > 0
                    THEN peso / (talla * talla)
                    ELSE NULL
                END as imc
            FROM antropometria
            ORDER BY paciente_id, fecha DESC
        ),
        ultimo_clinico AS (
            SELECT DISTINCT ON (paciente_id) 
                paciente_id,
                hba1c
            FROM clinico
            ORDER BY paciente_id, fecha DESC
        )
        SELECT COUNT(DISTINCT ua.paciente_id)
        FROM ultima_antropo ua
        JOIN ultimo_clinico uc ON uc.paciente_id = ua.paciente_id
        WHERE ua.imc >= 30 AND uc.hba1c > 7
    """)[0] or 0
    
    # ========== 4. ALERTAS Y ACCIONES PENDIENTES ==========
    # Pacientes sin plan activo
    sin_plan_activo = fetch_all("""
        SELECT p.id, 
               COALESCE(pr.nombres, '') || ' ' || COALESCE(pr.apellidos, '') as nombre,
               p.dni
        FROM paciente p
        LEFT JOIN pre_registro pr ON pr.dni = p.dni
        LEFT JOIN plan pl ON pl.paciente_id = p.id AND pl.fecha_fin >= CURRENT_DATE
        WHERE pl.id IS NULL
        ORDER BY p.id
        LIMIT 10
    """)
    
    # Pacientes con datos clínicos desactualizados (>90 días)
    datos_desactualizados = fetch_all("""
        SELECT DISTINCT ON (p.id)
            p.id,
            COALESCE(pr.nombres, '') || ' ' || COALESCE(pr.apellidos, '') as nombre,
            p.dni,
            MAX(c.fecha) as ultima_fecha_clinica
        FROM paciente p
        LEFT JOIN pre_registro pr ON pr.dni = p.dni
        LEFT JOIN clinico c ON c.paciente_id = p.id
        GROUP BY p.id, pr.nombres, pr.apellidos, p.dni
        HAVING MAX(c.fecha) < CURRENT_DATE - INTERVAL '90 days' OR MAX(c.fecha) IS NULL
        ORDER BY p.id, ultima_fecha_clinica DESC NULLS LAST
        LIMIT 10
    """)
    
    # Planes próximos a vencer (próximos 7 días)
    planes_por_vencer = fetch_all("""
        SELECT 
            p.id as plan_id,
            p.fecha_fin,
            pa.id as paciente_id,
            COALESCE(pr.nombres, '') || ' ' || COALESCE(pr.apellidos, '') as nombre,
            pa.dni
        FROM plan p
        JOIN paciente pa ON pa.id = p.paciente_id
        LEFT JOIN pre_registro pr ON pr.dni = pa.dni
        WHERE p.fecha_fin >= CURRENT_DATE 
            AND p.fecha_fin <= CURRENT_DATE + INTERVAL '7 days'
        ORDER BY p.fecha_fin
        LIMIT 10
    """)
    
    # ========== DATOS ESPECÍFICOS DE ADMINISTRADOR ==========
    # Total de usuarios en el sistema
    total_usuarios = fetch_one("SELECT COUNT(*) FROM usuario")[0] or 0
    
    # Total de nutricionistas
    total_nutricionistas = fetch_one("""
        SELECT COUNT(DISTINCT u.id)
        FROM usuario u
        JOIN usuario_rol ur ON ur.usuario_id = u.id
        JOIN rol r ON r.id = ur.rol_id
        WHERE r.nombre = 'nutricionista'
    """)[0] or 0
    
    # Usuarios activos vs inactivos
    usuarios_activos = fetch_one("SELECT COUNT(*) FROM usuario WHERE estado='activo'")[0] or 0
    usuarios_inactivos = fetch_one("SELECT COUNT(*) FROM usuario WHERE estado='bloqueado'")[0] or 0
    
    # Pre-registros pendientes
    preregistros_pendientes = fetch_one("""
        SELECT COUNT(*) FROM pre_registro WHERE estado='pendiente'
    """)[0] or 0
    
    # Tokens de activación pendientes
    tokens_pendientes = fetch_one("""
        SELECT COUNT(*) 
        FROM activacion_token 
        WHERE usado=FALSE AND vence_en >= CURRENT_TIMESTAMP
    """)[0] or 0
    
    # Usuarios con MFA activado
    usuarios_mfa = fetch_one("SELECT COUNT(*) FROM usuario WHERE mfa=TRUE")[0] or 0
    
    return render_template("admin/dashboard.html",
                         email=email,
                         roles=roles,
                         usuario_nombre=usuario_nombre,
                         # Resumen general
                         total_pacientes=total_pacientes,
                         planes_30d=planes_30d,
                         pacientes_con_datos=pacientes_con_datos,
                         planes_activos=planes_activos,
                         promedio_planes=promedio_planes,
                         # Estadísticas pacientes
                         distribucion_sexo=distribucion_sexo,
                         distribucion_edad=distribucion_edad,
                         distribucion_imc=distribucion_imc,
                         control_glucemico=control_glucemico,
                         pacientes_incompletos=pacientes_incompletos,
                         # Métricas clínicas
                         tendencia_hba1c=tendencia_hba1c,
                         tendencia_glucosa=tendencia_glucosa,
                         tendencia_imc=tendencia_imc,
                         riesgo_metabolico=riesgo_metabolico,
                         # Alertas
                         sin_plan_activo=sin_plan_activo,
                         datos_desactualizados=datos_desactualizados,
                         planes_por_vencer=planes_por_vencer,
                         # Datos específicos de administrador
                         total_usuarios=total_usuarios,
                         total_nutricionistas=total_nutricionistas,
                         usuarios_activos=usuarios_activos,
                         usuarios_inactivos=usuarios_inactivos,
                         preregistros_pendientes=preregistros_pendientes,
                         tokens_pendientes=tokens_pendientes,
                         usuarios_mfa=usuarios_mfa)


# ---------- Panel Nutricionista ----------
@app.route("/nutricionista")
@nutricionista_required
def nutricionista_home():
    """Dashboard principal del nutricionista"""
    email = session.get("user_email")
    user_id = session.get("user_id")
    roles = get_user_roles(user_id)
    
    # Obtener nombre y apellido del nutricionista
    usuario_nombre = email  # Por defecto usar email
    perfil = fetch_one("""
        SELECT nombres, apellidos
        FROM perfil_nutricionista
        WHERE usuario_id = %s
    """, (user_id,))
    if perfil and perfil[0] and perfil[1]:
        usuario_nombre = f"{perfil[0]} {perfil[1]}"
    elif perfil and perfil[0]:
        usuario_nombre = perfil[0]
    elif perfil and perfil[1]:
        usuario_nombre = perfil[1]
    
    # ========== 1. RESUMEN GENERAL (CARDS) ==========
    total_pacientes = fetch_one("SELECT COUNT(*) FROM paciente")[0] or 0
    
    # Planes generados últimos 30 días
    planes_30d = fetch_one("""
        SELECT COUNT(*) 
        FROM plan 
        WHERE creado_en >= CURRENT_DATE - INTERVAL '30 days'
    """)[0] or 0
    
    # Pacientes con datos clínicos recientes (últimos 30 días)
    pacientes_con_datos = fetch_one("""
        SELECT COUNT(DISTINCT c.paciente_id)
        FROM clinico c
        WHERE c.fecha >= CURRENT_DATE - INTERVAL '30 days'
    """)[0] or 0
    
    # Planes activos (vigentes)
    planes_activos = fetch_one("""
        SELECT COUNT(*) 
        FROM plan 
        WHERE fecha_fin >= CURRENT_DATE
    """)[0] or 0
    
    # Promedio de planes por paciente
    promedio_planes = fetch_one("""
        SELECT CASE 
            WHEN COUNT(DISTINCT paciente_id) > 0 
            THEN ROUND(COUNT(*)::numeric / COUNT(DISTINCT paciente_id), 2)
            ELSE 0
        END
        FROM plan
    """)[0] or 0
    
    # ========== 2. ESTADÍSTICAS DE PACIENTES ==========
    # Distribución por sexo
    distribucion_sexo = fetch_all("""
        SELECT 
            COALESCE(sexo, 'No especificado') as sexo,
            COUNT(*) as cantidad
        FROM paciente
        GROUP BY sexo
    """)
    
    # Distribución por rangos de edad
    distribucion_edad = fetch_all("""
        SELECT 
            CASE 
                WHEN EXTRACT(YEAR FROM AGE(fecha_nac)) < 30 THEN '18-29'
                WHEN EXTRACT(YEAR FROM AGE(fecha_nac)) < 40 THEN '30-39'
                WHEN EXTRACT(YEAR FROM AGE(fecha_nac)) < 50 THEN '40-49'
                WHEN EXTRACT(YEAR FROM AGE(fecha_nac)) < 60 THEN '50-59'
                WHEN EXTRACT(YEAR FROM AGE(fecha_nac)) < 70 THEN '60-69'
                ELSE '70+'
            END as rango_edad,
            COUNT(*) as cantidad
        FROM paciente
        WHERE fecha_nac IS NOT NULL
        GROUP BY rango_edad
        ORDER BY MIN(EXTRACT(YEAR FROM AGE(fecha_nac)))
    """)
    
    # Distribución por IMC (última medición)
    distribucion_imc = fetch_all("""
        WITH ultima_antropo AS (
            SELECT DISTINCT ON (paciente_id) 
                paciente_id,
                peso,
                talla,
                CASE 
                    WHEN peso IS NOT NULL AND talla IS NOT NULL AND talla > 0
                    THEN ROUND((peso / (talla * talla))::numeric, 2)
                    ELSE NULL
                END as imc
            FROM antropometria
            ORDER BY paciente_id, fecha DESC
        )
        SELECT 
            CASE 
                WHEN imc < 18.5 THEN 'Bajo peso'
                WHEN imc < 25 THEN 'Normal'
                WHEN imc < 30 THEN 'Sobrepeso'
                WHEN imc >= 30 THEN 'Obesidad'
                ELSE 'Sin datos'
            END as categoria_imc,
            COUNT(*) as cantidad
        FROM ultima_antropo
        GROUP BY categoria_imc
    """)
    
    # Pacientes por control glucémico (última HbA1c)
    control_glucemico = fetch_all("""
        WITH ultimo_clinico AS (
            SELECT DISTINCT ON (paciente_id) 
                paciente_id,
                hba1c
            FROM clinico
            WHERE hba1c IS NOT NULL
            ORDER BY paciente_id, fecha DESC
        )
        SELECT 
            CASE 
                WHEN hba1c < 7 THEN 'Bueno (<7%%)'
                WHEN hba1c < 8 THEN 'Moderado (7-8%%)'
                WHEN hba1c >= 8 THEN 'Malo (≥8%%)'
                ELSE 'Sin datos'
            END as control,
            COUNT(*) as cantidad
        FROM ultimo_clinico
        GROUP BY control
    """)
    
    # Pacientes con datos incompletos
    pacientes_incompletos = fetch_one("""
        SELECT COUNT(DISTINCT p.id)
        FROM paciente p
        LEFT JOIN (
            SELECT DISTINCT ON (paciente_id) paciente_id
            FROM antropometria
            WHERE fecha >= CURRENT_DATE - INTERVAL '90 days'
            ORDER BY paciente_id, fecha DESC
        ) a ON a.paciente_id = p.id
        LEFT JOIN (
            SELECT DISTINCT ON (paciente_id) paciente_id
            FROM clinico
            WHERE fecha >= CURRENT_DATE - INTERVAL '90 days'
            ORDER BY paciente_id, fecha DESC
        ) c ON c.paciente_id = p.id
        WHERE a.paciente_id IS NULL OR c.paciente_id IS NULL
    """)[0] or 0
    
    # ========== 3. MÉTRICAS CLÍNICAS (TENDENCIAS) ==========
    # Promedio de HbA1c por mes (últimos 6 meses)
    tendencia_hba1c = fetch_all("""
        SELECT 
            TO_CHAR(fecha, 'YYYY-MM') as mes,
            ROUND(AVG(hba1c)::numeric, 2) as promedio_hba1c,
            COUNT(*) as mediciones
        FROM clinico
        WHERE hba1c IS NOT NULL 
            AND fecha >= CURRENT_DATE - INTERVAL '6 months'
        GROUP BY TO_CHAR(fecha, 'YYYY-MM')
        ORDER BY mes
    """)
    
    # Promedio de glucosa en ayunas por mes
    tendencia_glucosa = fetch_all("""
        SELECT 
            TO_CHAR(fecha, 'YYYY-MM') as mes,
            ROUND(AVG(glucosa_ayunas)::numeric, 2) as promedio_glucosa,
            COUNT(*) as mediciones
        FROM clinico
        WHERE glucosa_ayunas IS NOT NULL 
            AND fecha >= CURRENT_DATE - INTERVAL '6 months'
        GROUP BY TO_CHAR(fecha, 'YYYY-MM')
        ORDER BY mes
    """)
    
    # Promedio de IMC por mes
    tendencia_imc = fetch_all("""
        SELECT 
            TO_CHAR(fecha, 'YYYY-MM') as mes,
            ROUND(AVG(CASE 
                WHEN peso IS NOT NULL AND talla IS NOT NULL AND talla > 0
                THEN peso / (talla * talla)
                ELSE NULL
            END)::numeric, 2) as promedio_imc,
            COUNT(*) as mediciones
        FROM antropometria
        WHERE peso IS NOT NULL AND talla IS NOT NULL
            AND fecha >= CURRENT_DATE - INTERVAL '6 months'
        GROUP BY TO_CHAR(fecha, 'YYYY-MM')
        ORDER BY mes
    """)
    
    # Pacientes con riesgo metabólico alto (IMC >30 + HbA1c >7%)
    riesgo_metabolico = fetch_one("""
        WITH ultima_antropo AS (
            SELECT DISTINCT ON (paciente_id) 
                paciente_id,
                CASE 
                    WHEN peso IS NOT NULL AND talla IS NOT NULL AND talla > 0
                    THEN peso / (talla * talla)
                    ELSE NULL
                END as imc
            FROM antropometria
            ORDER BY paciente_id, fecha DESC
        ),
        ultimo_clinico AS (
            SELECT DISTINCT ON (paciente_id) 
                paciente_id,
                hba1c
            FROM clinico
            ORDER BY paciente_id, fecha DESC
        )
        SELECT COUNT(DISTINCT ua.paciente_id)
        FROM ultima_antropo ua
        JOIN ultimo_clinico uc ON uc.paciente_id = ua.paciente_id
        WHERE ua.imc >= 30 AND uc.hba1c > 7
    """)[0] or 0
    
    # ========== 4. ALERTAS Y ACCIONES PENDIENTES ==========
    # Pacientes sin plan activo
    sin_plan_activo = fetch_all("""
        SELECT p.id, 
               COALESCE(pr.nombres, '') || ' ' || COALESCE(pr.apellidos, '') as nombre,
               p.dni
        FROM paciente p
        LEFT JOIN pre_registro pr ON pr.dni = p.dni
        LEFT JOIN plan pl ON pl.paciente_id = p.id AND pl.fecha_fin >= CURRENT_DATE
        WHERE pl.id IS NULL
        ORDER BY p.id
        LIMIT 10
    """)
    
    # Pacientes con datos clínicos desactualizados (>90 días)
    datos_desactualizados = fetch_all("""
        SELECT DISTINCT ON (p.id)
            p.id,
            COALESCE(pr.nombres, '') || ' ' || COALESCE(pr.apellidos, '') as nombre,
            p.dni,
            MAX(c.fecha) as ultima_fecha_clinica
        FROM paciente p
        LEFT JOIN pre_registro pr ON pr.dni = p.dni
        LEFT JOIN clinico c ON c.paciente_id = p.id
        GROUP BY p.id, pr.nombres, pr.apellidos, p.dni
        HAVING MAX(c.fecha) < CURRENT_DATE - INTERVAL '90 days' OR MAX(c.fecha) IS NULL
        ORDER BY p.id, ultima_fecha_clinica DESC NULLS LAST
        LIMIT 10
    """)
    
    # Planes próximos a vencer (próximos 7 días)
    planes_por_vencer = fetch_all("""
        SELECT 
            p.id as plan_id,
            p.fecha_fin,
            pa.id as paciente_id,
            COALESCE(pr.nombres, '') || ' ' || COALESCE(pr.apellidos, '') as nombre,
            pa.dni
        FROM plan p
        JOIN paciente pa ON pa.id = p.paciente_id
        LEFT JOIN pre_registro pr ON pr.dni = pa.dni
        WHERE p.fecha_fin >= CURRENT_DATE 
            AND p.fecha_fin <= CURRENT_DATE + INTERVAL '7 days'
        ORDER BY p.fecha_fin
        LIMIT 10
    """)
    
    # ========== DATOS ESPECÍFICOS DE NUTRICIONISTA ==========
    # Planes creados por este nutricionista (si está disponible)
    user_id = session.get("user_id")
    mis_planes = fetch_one("""
        SELECT COUNT(*) 
        FROM plan 
        WHERE creado_por=%s AND creado_en >= CURRENT_DATE - INTERVAL '30 days'
    """, (user_id,))[0] or 0
    
    # Pacientes asignados a este nutricionista (planes creados por él)
    mis_pacientes = fetch_one("""
        SELECT COUNT(DISTINCT paciente_id)
        FROM plan
        WHERE creado_por=%s
    """, (user_id,))[0] or 0
    
    # Planes activos creados por este nutricionista
    mis_planes_activos = fetch_one("""
        SELECT COUNT(*) 
        FROM plan 
        WHERE creado_por=%s AND fecha_fin >= CURRENT_DATE
    """, (user_id,))[0] or 0
    
    # Pacientes que necesitan seguimiento (sin datos recientes)
    pacientes_seguimiento = fetch_all("""
        SELECT DISTINCT ON (p.id)
            p.id,
            COALESCE(pr.nombres, '') || ' ' || COALESCE(pr.apellidos, '') as nombre,
            p.dni,
            MAX(pl.fecha_fin) as ultimo_plan
        FROM paciente p
        LEFT JOIN pre_registro pr ON pr.dni = p.dni
        LEFT JOIN plan pl ON pl.paciente_id = p.id AND pl.creado_por = %s
        LEFT JOIN (
            SELECT DISTINCT ON (paciente_id) paciente_id, fecha
            FROM antropometria
            ORDER BY paciente_id, fecha DESC
        ) a ON a.paciente_id = p.id
        LEFT JOIN (
            SELECT DISTINCT ON (paciente_id) paciente_id, fecha
            FROM clinico
            ORDER BY paciente_id, fecha DESC
        ) c ON c.paciente_id = p.id
        WHERE pl.creado_por = %s
            AND (a.fecha < CURRENT_DATE - INTERVAL '90 days' OR a.fecha IS NULL)
        GROUP BY p.id, pr.nombres, pr.apellidos, p.dni
        ORDER BY p.id, ultimo_plan DESC NULLS LAST
        LIMIT 10
    """, (user_id, user_id))
    
    return render_template("nutricionista/dashboard.html",
                         email=email,
                         roles=roles,
                         usuario_nombre=usuario_nombre,
                         # Resumen general
                         total_pacientes=total_pacientes,
                         planes_30d=planes_30d,
                         pacientes_con_datos=pacientes_con_datos,
                         planes_activos=planes_activos,
                         promedio_planes=promedio_planes,
                         # Estadísticas pacientes
                         distribucion_sexo=distribucion_sexo,
                         distribucion_edad=distribucion_edad,
                         distribucion_imc=distribucion_imc,
                         control_glucemico=control_glucemico,
                         pacientes_incompletos=pacientes_incompletos,
                         # Métricas clínicas
                         tendencia_hba1c=tendencia_hba1c,
                         tendencia_glucosa=tendencia_glucosa,
                         tendencia_imc=tendencia_imc,
                         riesgo_metabolico=riesgo_metabolico,
                         # Alertas
                         sin_plan_activo=sin_plan_activo,
                         datos_desactualizados=datos_desactualizados,
                         planes_por_vencer=planes_por_vencer,
                         # Datos específicos de nutricionista
                         mis_planes=mis_planes,
                         mis_pacientes=mis_pacientes,
                         mis_planes_activos=mis_planes_activos,
                         pacientes_seguimiento=pacientes_seguimiento)


# ---- Placeholders de mantenimiento (para que los links del panel funcionen) ----
def _placeholder(nombre):
    return f"<h2 style='font-family:system-ui; padding:20px'>Módulo <b>{nombre}</b> en construcción…</h2>", 200

# --------- ADMIN: USUARIOS (CRUD) ---------
@app.route("/admin/usuarios")
@admin_only_required
def admin_usuarios():
    rows = fetch_all("""
        SELECT u.id, u.email, u.estado, u.mfa,
               COALESCE(string_agg(r.nombre, ', ' ORDER BY r.nombre), '') AS roles
        FROM usuario u
        LEFT JOIN usuario_rol ur ON ur.usuario_id = u.id
        LEFT JOIN rol r ON r.id = ur.rol_id
        GROUP BY u.id
        ORDER BY u.id DESC
    """)
    all_roles = fetch_all("SELECT id, nombre FROM rol ORDER BY nombre")  # <- NUEVO
    return render_template(
        "admin/usuarios_list.html",
        rows=rows,
        all_roles=all_roles,          
        active_nav="usuarios",
        page_title="NutriSync · Usuarios",
        header_title="Usuarios"
    )


@app.route("/api/usuarios/page")
@admin_required
def api_usuarios_page():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))
    q = (request.args.get("q") or "").strip().lower()
    offset = (page - 1) * per_page

    # Filtro
    where = ""
    params = []
    if q:
        where = "WHERE LOWER(u.email) LIKE %s"
        params.append(f"%{q}%")

    # Total filtrado
    total = fetch_one(f"""
        SELECT COUNT(*)
        FROM usuario u
        {where}
    """, tuple(params))[0]

    # Datos + roles agregados
    rows = fetch_all(f"""
        SELECT u.id, u.email, u.estado, u.mfa,
               COALESCE(string_agg(r.nombre, ', ' ORDER BY r.nombre), '') AS roles
        FROM usuario u
        LEFT JOIN usuario_rol ur ON ur.usuario_id = u.id
        LEFT JOIN rol r ON r.id = ur.rol_id
        {where}
        GROUP BY u.id
        ORDER BY u.id DESC
        LIMIT %s OFFSET %s
    """, tuple(params + [per_page, offset])) or []

    data = [{
        "id": r[0],
        "email": r[1],
        "estado": r[2],
        "mfa": bool(r[3]),
        "roles": r[4] or ""
    } for r in rows]

    total_pages = (total + per_page - 1) // per_page
    return {"ok": True, "rows": data, "total_pages": total_pages}


@app.route("/admin/generar-plan")
@admin_required
def admin_generar_plan():
    # Redirigir a la nueva página obtener_plan
    paciente_id = request.args.get('paciente_id')
    return redirect(url_for('admin_obtener_plan', paciente_id=paciente_id))

@app.route("/admin/obtener-plan")
@admin_required
def admin_obtener_plan():
    """Nueva ruta para obtener plan con paginación implementada correctamente"""
    paciente_id = request.args.get('paciente_id')
    template_base = get_template_base()
    return render_template(f"{template_base}/obtener_plan.html",
                           active_nav="obtener_plan",
                           page_title="NutriSync · Obtener plan",
                           header_title="Obtener plan",
                           paciente_id_inicial=paciente_id)






@app.get("/api/reco/ingredientes")
@admin_required
def api_reco_ingredientes():
    q = (request.args.get("q") or "").strip().lower()
    pid = request.args.get("pid")  # paciente_id para personalización
    tiempo = request.args.get("tiempo")  # des/mm/alm/mt/cena
    limit = int(request.args.get("limit") or 20)
    excluir = request.args.get("excluir")  # ID del ingrediente a excluir (para intercambio)

    # Si hay paciente y tiempo, usar motor de recomendación inteligente
    if pid and tiempo:
        try:
            from Core.motor_recomendacion import MotorRecomendacion
            motor = MotorRecomendacion()
            
            # Obtener perfil y metas del paciente
            perfil = motor.obtener_perfil_paciente(int(pid))
            metas = motor.calcular_metas_nutricionales(perfil)
            
            # Obtener información del ingrediente actual (si se está intercambiando)
            ing_actual_data = None
            if excluir:
                ing_actual_data = fetch_one("""
                    SELECT id, nombre, grupo, kcal, cho, pro, fat, fibra, ig, porcion_base, unidad_base
                    FROM ingrediente WHERE id=%s
                """, (excluir,))
            
            # Obtener contexto del plan (qué otros alimentos ya tiene ese día/tiempo)
            dia = request.args.get("dia")
            contexto_plan = []
            if dia and pid:
                # Obtener el plan_id del paciente
                plan_activo = fetch_one("""
                    SELECT id FROM plan 
                    WHERE paciente_id=%s AND estado='activo' 
                    ORDER BY fecha_ini DESC LIMIT 1
                """, (pid,))
                
                if plan_activo:
                    plan_id = plan_activo[0]
                    # Obtener otros alimentos del mismo día y tiempo
                    otros_alimentos = fetch_all("""
                        SELECT i.kcal, i.cho, i.pro, i.fat, i.fibra, a.cantidad
                        FROM plan_alimento a
                        JOIN plan_detalle d ON d.id = a.plan_detalle_id
                        JOIN ingrediente i ON i.id = a.ingrediente_id
                        WHERE d.plan_id = %s 
                          AND d.dia = %s 
                          AND d.tiempo = %s
                          AND a.ingrediente_id != %s
                    """, (plan_id, dia, tiempo, excluir or 0))
                    
                    if otros_alimentos:
                        # Calcular totales nutricionales ya presentes
                        total_kcal = sum(float(a[0] or 0) * (float(a[5] or 100) / 100.0) for a in otros_alimentos)
                        total_cho = sum(float(a[1] or 0) * (float(a[5] or 100) / 100.0) for a in otros_alimentos)
                        total_pro = sum(float(a[2] or 0) * (float(a[5] or 100) / 100.0) for a in otros_alimentos)
                        total_fat = sum(float(a[3] or 0) * (float(a[5] or 100) / 100.0) for a in otros_alimentos)
                        total_fibra = sum(float(a[4] or 0) * (float(a[5] or 100) / 100.0) for a in otros_alimentos)
                        
                        contexto_plan = {
                            'kcal': total_kcal,
                            'cho': total_cho,
                            'pro': total_pro,
                            'fat': total_fat,
                            'fibra': total_fibra
                        }
            
            # Obtener ingredientes recomendados base
            ingredientes_recomendados = motor.obtener_ingredientes_recomendados(perfil, metas)
            
            # Filtrar el ingrediente a excluir
            if excluir:
                ingredientes_recomendados = [ing for ing in ingredientes_recomendados if str(ing.get("id")) != str(excluir)]
            
            # Calcular similitud nutricional y puntuación inteligente
            ingredientes_con_puntuacion = []
            for ing in ingredientes_recomendados:
                puntuacion = 0.0
                
                # 1. Similitud nutricional con el ingrediente actual (si existe)
                if ing_actual_data:
                    # Calcular distancia euclidiana normalizada en espacio nutricional
                    # Normalizar valores a escala 0-1 para comparación justa
                    def normalizar(valor, max_valor=100):
                        return min(1.0, max(0.0, valor / max_valor)) if max_valor > 0 else 0.0
                    
                    # Valores del ingrediente actual (por 100g)
                    kcal_actual = float(ing_actual_data[3] or 0)
                    cho_actual = float(ing_actual_data[4] or 0)
                    pro_actual = float(ing_actual_data[5] or 0)
                    fat_actual = float(ing_actual_data[6] or 0)
                    fibra_actual = float(ing_actual_data[7] or 0)
                    ig_actual = float(ing_actual_data[8] or 70)
                    
                    # Valores del ingrediente candidato (por 100g)
                    kcal_cand = float(ing.get("kcal", 0))
                    cho_cand = float(ing.get("cho", 0))
                    pro_cand = float(ing.get("pro", 0))
                    fat_cand = float(ing.get("fat", 0))
                    fibra_cand = float(ing.get("fibra", 0))
                    ig_cand = float(ing.get("ig", 70))
                    
                    # Calcular similitud (menor distancia = mayor similitud)
                    # Usar pesos para dar más importancia a macronutrientes principales
                    distancia = (
                        0.2 * abs(normalizar(kcal_actual, 900) - normalizar(kcal_cand, 900)) +
                        0.3 * abs(normalizar(cho_actual, 100) - normalizar(cho_cand, 100)) +
                        0.2 * abs(normalizar(pro_actual, 50) - normalizar(pro_cand, 50)) +
                        0.15 * abs(normalizar(fat_actual, 100) - normalizar(fat_cand, 100)) +
                        0.1 * abs(normalizar(fibra_actual, 20) - normalizar(fibra_cand, 20)) +
                        0.05 * abs(normalizar(ig_actual, 100) - normalizar(ig_cand, 100))
                    )
                    
                    # Convertir distancia a similitud (1 - distancia normalizada)
                    similitud = max(0.0, 1.0 - distancia)
                    puntuacion += similitud * 40  # 40% del peso total
                    
                    # Bonus por mismo grupo
                    if ing.get("grupo") == ing_actual_data[2]:
                        puntuacion += 20
                
                # 2. Complementariedad con el contexto del plan
                if contexto_plan:
                    # Calcular qué necesita el plan para cumplir metas
                    # Obtener metas para este tiempo específico
                    distribucion_cho = motor.DISTRIBUCION_CHO.get(tiempo, 0.25)
                    cho_meta = (metas.carbohidratos_g * distribucion_cho) if hasattr(metas, 'carbohidratos_g') else 0
                    cho_faltante = max(0, cho_meta - contexto_plan.get('cho', 0))
                    
                    # Priorizar ingredientes que ayuden a cumplir las metas
                    cho_ing = float(ing.get("cho", 0))
                    if cho_faltante > 0 and cho_ing > 0:
                        # Si falta CHO, priorizar ingredientes con CHO
                        puntuacion += min(20, (cho_ing / 100.0) * 20)
                    elif cho_faltante <= 0 and cho_ing < 30:
                        # Si ya hay suficiente CHO, priorizar ingredientes bajos en CHO
                        puntuacion += 15
                    
                    # Priorizar fibra si falta
                    fibra_meta = (metas.fibra_g * distribucion_cho) if hasattr(metas, 'fibra_g') else 0
                    fibra_faltante = max(0, fibra_meta - contexto_plan.get('fibra', 0))
                    if fibra_faltante > 0:
                        fibra_ing = float(ing.get("fibra", 0))
                        puntuacion += min(15, (fibra_ing / 10.0) * 15)
                
                # 3. Ajuste según control glucémico (ya considerado en obtener_ingredientes_recomendados)
                # Pero dar bonus adicional a ingredientes con IG bajo si el control es malo
                probabilidad_mal_control = getattr(motor, '_ultima_probabilidad_ajustada', None)
                if probabilidad_mal_control and probabilidad_mal_control > 0.5:
                    ig_ing = float(ing.get("ig", 70))
                    if ig_ing and ig_ing <= 55:
                        puntuacion += 10  # Bonus por IG bajo
                
                # 4. Variación por día (para evitar repetición)
                if dia:
                    try:
                        from datetime import datetime
                        fecha = datetime.strptime(dia, "%Y-%m-%d")
                        # Usar hash del nombre del ingrediente + día para variación determinística
                        import hashlib
                        hash_val = int(hashlib.md5(f"{ing.get('nombre')}{dia}".encode()).hexdigest()[:8], 16)
                        variacion = (hash_val % 10) / 10.0  # 0-1
                        puntuacion += variacion * 5  # 5% de variación
                    except:
                        pass
                
                ingredientes_con_puntuacion.append((puntuacion, ing))
            
            # Ordenar por puntuación (mayor a menor)
            ingredientes_con_puntuacion.sort(key=lambda x: x[0], reverse=True)
            
            # Extraer solo los ingredientes ordenados
            resultados = [ing for _, ing in ingredientes_con_puntuacion[:limit]]
            
            if resultados:
                # Formatear resultados para el frontend
                formatted = []
                for ing in resultados:
                    # Obtener unidad_base y porcion_base del ingrediente
                    ing_db = fetch_one("""
                        SELECT unidad_base, porcion_base FROM ingrediente WHERE id=%s
                    """, (ing.get("id"),))
                    unidad_base = ing_db[0] if ing_db and ing_db[0] else "g"
                    porcion_base = float(ing_db[1]) if ing_db and ing_db[1] else 100.0
                    
                    formatted.append({
                        "id": ing.get("id"),
                        "nombre": ing.get("nombre"),
                        "unidad": unidad_base,
                        "porcion": porcion_base,
                        "unidad_base": unidad_base,
                        "porcion_base": porcion_base,
                        "kcal": float(ing.get("kcal", 0)) if ing.get("kcal") else None,
                        "cho": float(ing.get("cho", 0)) if ing.get("cho") else None,
                        "pro": float(ing.get("pro", 0)) if ing.get("pro") else None,
                        "fat": float(ing.get("fat", 0)) if ing.get("fat") else None,
                        "fibra": float(ing.get("fibra", 0)) if ing.get("fibra") else None,
                    })
                return {"ok": True, "results": formatted}
        except Exception as e:
            print(f"Error en recomendación inteligente: {e}")
            import traceback
            traceback.print_exc()
            # Continuar con búsqueda simple si falla
    
    # Búscador simple por nombre (solo activos) - fallback
    params = []
    where = "WHERE activo = TRUE"
    if q:
        where += " AND LOWER(nombre) LIKE %s"
        params.append(f"%{q}%")

    rows = fetch_all(f"""
        SELECT id, nombre, unidad_base, porcion_base, kcal, cho, pro, fat, fibra
        FROM ingrediente
        {where}
        ORDER BY nombre
        LIMIT %s
    """, tuple(params) + (limit,)) or []

    results = [{
        "id": r[0], "nombre": r[1],
        "unidad": r[2], "porcion": float(r[3]) if r[3] is not None else None,
        "unidad_base": r[2], "porcion_base": float(r[3]) if r[3] is not None else None,
        "kcal": float(r[4]) if r[4] is not None else None,
        "cho":  float(r[5]) if r[5] is not None else None,
        "pro":  float(r[6]) if r[6] is not None else None,
        "fat":  float(r[7]) if r[7] is not None else None,
        "fibra":float(r[8]) if r[8] is not None else None,
    } for r in rows]

    return {"ok": True, "results": results}



from datetime import datetime, timedelta

@app.post("/api/reco/plan")
@admin_required
def api_reco_plan():
    """
    Propuesta de plan MOCK para la UI:
    - Respeta los tiempos seleccionados y el número de días.
    - Toma 2 ingredientes por tiempo (si hay).
    - Calcula kcal totales como suma de kcal/100g * cantidad (si hay datos).
    """
    data = request.get_json(force=True) or {}
    paciente_id = data.get("paciente_id")
    dias_n = int(data.get("dias") or 7)
    tiempos = data.get("tiempos") or ["des", "alm", "cena"]
    kcal_obj = int(data.get("kcal") or 1800)

    # Trae un pool de ingredientes activos
    pool = fetch_all("""
        SELECT id, nombre, unidad_base, porcion_base, kcal, cho, pro, fat, fibra
        FROM ingrediente
        WHERE activo = TRUE
        ORDER BY nombre
        LIMIT 200
    """) or []

    def item_from_row(r, cantidad=100.0):
        # kcal por cantidad si hay valores por 100g/porcion_base
        kcal100 = float(r[4]) if r[4] is not None else 0.0
        kcal = round(kcal100 * (cantidad / 100.0), 1)
        return {
            "id": r[0],
            "nombre": r[1],
            "cantidad": cantidad,
            "unidad": r[2] or "g",
            "kcal": kcal
        }

    # arma días
    hoy = datetime.today().date()
    dias = []
    for d in range(dias_n):
        fecha = (hoy + timedelta(days=d)).strftime("%Y-%m-%d")
        tiempos_dict = {}
        kcal_tot = 0.0
        for t in tiempos:
            # toma 2 ingredientes distintos si hay
            pick = pool[ (d*5) % max(1,len(pool)) : (d*5) % max(1,len(pool)) + 2 ]
            items = [item_from_row(r, 100.0 if t in ("des","mm","mt") else 150.0) for r in pick]
            tiempos_dict[t] = items
            kcal_tot += sum(i["kcal"] for i in items)

        dias.append({
            "fecha": fecha,
            "titulo": f"Día {d+1}",
            "kcal_obj": kcal_obj,
            "kcal_tot": round(kcal_tot, 0),
            "cho": 0, "pro": 0, "fat": 0, "fibra": 0,   # (se calculan en la versión real)
            "tiempos": tiempos_dict
        })

    # mini lista de compras (nombres únicos)
    nombres = []
    for d in dias:
        for t, items in d["tiempos"].items():
            for it in items:
                if it["nombre"] not in nombres:
                    nombres.append(it["nombre"])

    out = {"ok": True, "plan": {"dias": dias, "listaCompras": nombres}}
    return out



@app.route("/api/usuarios/buscar")
@admin_required
def api_usuarios_buscar():
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return {"ok": True, "results": []}

    rows = fetch_all("""
        SELECT u.id, u.email
        FROM usuario u
        WHERE LOWER(u.email) LIKE %s
        ORDER BY u.email
        LIMIT 15
    """, (f"%{q}%",)) or []

    return {
        "ok": True,
        "results": [{"id": r[0], "text": r[1], "email": r[1]} for r in rows]
    }


# --------- ADMIN: PACIENTES (CRUD) ---------

def ensure_preregistro(dni: str,
                       nombres: str | None = None,
                       apellidos: str | None = None,
                       telefono: str | None = None,
                       email: str | None = None):
    """
    Upsert en pre_registro para satisfacer la FK de paciente(dni) y
    almacenar nombres/apellidos si el admin los proporciona.
    """
    execute("""
        INSERT INTO pre_registro (dni, nombres, apellidos, telefono, email, estado, creado_en, actualizado_en)
        VALUES (%s, COALESCE(%s, ''), COALESCE(%s, ''), %s, %s, 'pendiente', NOW(), NOW())
        ON CONFLICT (dni) DO UPDATE
           SET nombres = COALESCE(EXCLUDED.nombres, pre_registro.nombres),
               apellidos = COALESCE(EXCLUDED.apellidos, pre_registro.apellidos),
               telefono = COALESCE(EXCLUDED.telefono, pre_registro.telefono),
               email = COALESCE(EXCLUDED.email, pre_registro.email),
               actualizado_en = NOW()
    """, (dni, nombres, apellidos, telefono, email))



@app.route("/admin/pacientes")
@admin_required
def admin_pacientes():
    template_base = get_template_base()
    return render_template(
        f"{template_base}/pacientes_list.html",
        active_nav="pacientes",
        page_title="NutriSync · Pacientes",
        header_title="Pacientes"
    )



def get_or_create_user_with_paciente_role(email: str) -> int | None:
    if not email:
        return None

    row_u = fetch_one("SELECT id FROM usuario WHERE email=%s", (email,))
    if row_u:
        usuario_id = row_u[0]
    else:
        usuario_id = fetch_one("""
            INSERT INTO usuario (email, hash_pwd, estado, mfa)
            VALUES (%s, NULL, 'activo', FALSE)
            RETURNING id
        """, (email,))[0]

    row_r = fetch_one("SELECT id FROM rol WHERE nombre=%s", ("paciente",))
    if row_r:
        rol_paciente_id = row_r[0]
        ya = fetch_one(
            "SELECT 1 FROM usuario_rol WHERE usuario_id=%s AND rol_id=%s",
            (usuario_id, rol_paciente_id)
        )
        if not ya:
            execute(
                "INSERT INTO usuario_rol (usuario_id, rol_id) VALUES (%s,%s)",
                (usuario_id, rol_paciente_id)
            )
    return usuario_id

# ---------- ADMIN: PACIENTE INTEGRAL (un solo flujo) ----------
@app.route("/admin/pacientes/guardar", methods=["POST"])
@admin_required
def admin_paciente_guardar():
    """Guarda paciente, antropometría, clínico y meds/alergias en un solo flujo."""
    dni = request.form.get("dni", "").strip()
    nombres = request.form.get("nombres", "").strip() or None
    apellidos = request.form.get("apellidos", "").strip() or None
    sexo = request.form.get("sexo", "").strip() or None
    fecha_nac = request.form.get("fecha_nac", "").strip() or None
    telefono = request.form.get("telefono", "").strip() or None
    email = request.form.get("email", "").strip().lower() or None

    peso = request.form.get("peso") or None
    talla = request.form.get("talla") or None
    cc = request.form.get("cc") or None
    bf_pct = request.form.get("bf_pct") or None
    actividad = request.form.get("actividad") or None

    hba1c = request.form.get("hba1c") or None
    glucosa_ayunas = request.form.get("glucosa_ayunas") or None
    ldl = request.form.get("ldl") or None
    trigliceridos = request.form.get("trigliceridos") or None
    pa_sis = request.form.get("pa_sis") or None
    pa_dia = request.form.get("pa_dia") or None
    meds = (request.form.get("meds") or "").strip()
    otros = (request.form.get("otros") or "").strip()

    # ✅ Asegurar preregistro y usuario con rol paciente
    # --- Validación de límites dinámicos ---
    errores = validar_valores_paciente(request.form)
    if errores:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return {"ok": False, "errores": errores}, 400
        flash("❌ " + " | ".join(errores), "error")
        return redirect(url_for("admin_pacientes"))


    ensure_preregistro(dni, nombres, apellidos, telefono, email)
    usuario_id = get_or_create_user_with_paciente_role(email) if email else None

    # 1️⃣ Buscar paciente existente o crear uno nuevo
    paciente_existente = None
    if dni:
        paciente_existente = fetch_one("""
            SELECT id FROM paciente WHERE dni=%s LIMIT 1
        """, (dni,))
    elif usuario_id:
        paciente_existente = fetch_one("""
            SELECT id FROM paciente WHERE usuario_id=%s LIMIT 1
        """, (usuario_id,))
    
    if paciente_existente:
        # Paciente existe: actualizar datos básicos y agregar registros históricos
        pid = paciente_existente[0]
        execute("""
            UPDATE paciente
               SET usuario_id=COALESCE(%s, usuario_id), 
                   sexo=COALESCE(%s, sexo), 
                   fecha_nac=COALESCE(%s, fecha_nac), 
                   telefono=COALESCE(%s, telefono), 
                   actualizado_en=NOW()
             WHERE id=%s
        """, (usuario_id, sexo, fecha_nac, telefono, pid))
    else:
        # Paciente no existe: crear nuevo
        pid = fetch_one("""
            INSERT INTO paciente (usuario_id, dni, sexo, fecha_nac, telefono, creado_en, actualizado_en)
            VALUES (%s,%s,%s,%s,%s,NOW(),NOW())
            RETURNING id
        """, (usuario_id, dni, sexo, fecha_nac, telefono))[0]

    # 2️⃣ Insertar nuevo registro de antropometría (historial) si hay datos
    # Permitir fecha personalizada para seguimiento histórico
    fecha_medicion = request.form.get("fecha_medicion") or None
    if fecha_medicion:
        try:
            from datetime import datetime
            fecha_medicion = datetime.strptime(fecha_medicion, '%Y-%m-%d').date()
        except:
            fecha_medicion = date.today()
    else:
        fecha_medicion = date.today()
    
    if any([peso, talla, cc, bf_pct, actividad]):
        # Verificar si ya existe un registro para esta fecha
        existe_antropo = fetch_one("""
            SELECT id FROM antropometria 
            WHERE paciente_id=%s AND fecha=%s 
            LIMIT 1
        """, (pid, fecha_medicion))
        
        if existe_antropo:
            # Si ya existe registro para esta fecha, actualizar ese registro
            execute("""
                UPDATE antropometria
                   SET peso=%s, talla=%s, cc=%s, bf_pct=%s, actividad=%s
                 WHERE id=%s
            """, (peso, talla, cc, bf_pct, actividad, existe_antropo[0]))
        else:
            # Si no existe registro para esta fecha, insertar nuevo (seguimiento histórico)
            execute("""
                INSERT INTO antropometria (paciente_id, fecha, peso, talla, cc, bf_pct, actividad)
                VALUES (%s, %s, %s,%s,%s,%s,%s)
            """, (pid, fecha_medicion, peso, talla, cc, bf_pct, actividad))

    # 3️⃣ Insertar nuevo registro clínico (historial) si hay datos cuantitativos
    if any([hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia]):
        # Verificar si ya existe un registro para esta fecha
        existe_clinico = fetch_one("""
            SELECT id FROM clinico 
            WHERE paciente_id=%s AND fecha=%s 
            LIMIT 1
        """, (pid, fecha_medicion))
        
        if existe_clinico:
            # Si ya existe registro para esta fecha, actualizar ese registro
            execute("""
                UPDATE clinico
                   SET hba1c=%s, glucosa_ayunas=%s, ldl=%s, trigliceridos=%s, pa_sis=%s, pa_dia=%s
                 WHERE id=%s
            """, (hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia, existe_clinico[0]))
        else:
            # Si no existe registro para esta fecha, insertar nuevo (seguimiento histórico)
            execute("""
                INSERT INTO clinico (paciente_id, fecha, hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia)
                VALUES (%s, %s, %s,%s,%s,%s,%s,%s)
            """, (pid, fecha_medicion, hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia))

        # 4️⃣ Guardar medicamentos y alergias desde JSON enriquecido
    meds_json = request.form.get("meds_json")
    alergias_json = request.form.get("alergias_json")

    # --- MEDICAMENTOS ---
    if meds_json:
        try:
            meds = json.loads(meds_json)
            for m in meds:
                execute("""
                    INSERT INTO paciente_medicamento (paciente_id, nombre, dosis, frecuencia, activo, creado_en)
                    VALUES (%s, %s, %s, %s, TRUE, NOW())
                """, (pid, m.get("nombre"), m.get("dosis"), m.get("frecuencia")))
        except Exception as e:
            print("Error guardando medicamentos:", e)

    # --- ALERGIAS ---
    if alergias_json:
        try:
            als = json.loads(alergias_json)
            for a in als:
                execute("""
                    INSERT INTO paciente_alergia (paciente_id, ingrediente_id, descripcion, creado_en)
                    VALUES (%s, %s, %s, NOW())
                """, (pid, a.get("ingrediente_id"), a.get("descripcion")))

        except Exception as e:
            print("Error guardando alergias:", e)


    flash("✅ Registro integral guardado correctamente", "success")
    return redirect(url_for("admin_pacientes"))


# --- crear paciente ---
@app.route("/admin/pacientes/nuevo", methods=["POST"])
@admin_required
def admin_paciente_nuevo():
    dni        = (request.form.get("dni") or "").strip()
    nombres    = (request.form.get("nombres") or "").strip() or None
    apellidos  = (request.form.get("apellidos") or "").strip() or None
    sexo       = (request.form.get("sexo") or "").strip() or None
    fecha_nac  = (request.form.get("fecha_nac") or "").strip() or None
    telefono   = (request.form.get("telefono") or "").strip() or None
    user_email = (request.form.get("email") or "").strip().lower() or None

    if not dni or len(dni) != 8 or not dni.isdigit():
        flash("DNI inválido (8 dígitos).", "error")
        return redirect(url_for("admin_pacientes"))

    usuario_id = None
    created_user = False
    if user_email:
        row_u = fetch_one("SELECT id FROM usuario WHERE email=%s", (user_email,))
        if row_u:
            usuario_id = row_u[0]
        else:
            usuario_id = get_or_create_user_with_paciente_role(user_email)
            created_user = True

    # Satisface FK y guarda nombres/apellidos (sin preregistro manual)
    ensure_preregistro(dni, nombres, apellidos, telefono, user_email)

    execute("""
        INSERT INTO paciente (usuario_id, dni, sexo, fecha_nac, telefono, creado_en, actualizado_en)
        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
    """, (usuario_id, dni, sexo, fecha_nac, telefono))

    if created_user:
        flash("Se creó también un usuario para ese email (sin contraseña) y se asignó el rol 'paciente'.", "info")

    flash("Paciente creado", "success")
    return redirect(url_for("admin_pacientes"))


# --- editar paciente ---
@app.route("/admin/pacientes/<int:pid>/editar", methods=["POST"])
@admin_required
def admin_paciente_editar(pid):
    """Actualiza todos los datos del paciente (personales, antropometría, clínico, meds, alergias)."""

    # --- DATOS PERSONALES ---
    # --- Validación de límites dinámicos ---
    errores = validar_valores_paciente(request.form)
    if errores:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return {"ok": False, "errores": errores}, 400
        flash("❌ " + " | ".join(errores), "error")
        return redirect(url_for("admin_pacientes"))


    dni = (request.form.get("dni") or "").strip()
    nombres = (request.form.get("nombres") or "").strip() or None
    apellidos = (request.form.get("apellidos") or "").strip() or None
    sexo = (request.form.get("sexo") or "").strip() or None
    fecha_nac = (request.form.get("fecha_nac") or "").strip() or None
    telefono = (request.form.get("telefono") or "").strip() or None
    email = (request.form.get("email") or "").strip().lower() or None

    # Asegura preregistro y usuario con rol paciente
    ensure_preregistro(dni, nombres, apellidos, telefono, email)
    usuario_id = get_or_create_user_with_paciente_role(email) if email else None

    # Actualiza la tabla paciente
    execute("""
        UPDATE paciente
           SET usuario_id=%s, dni=%s, sexo=%s, fecha_nac=%s, telefono=%s, actualizado_en=NOW()
         WHERE id=%s
    """, (usuario_id, dni, sexo, fecha_nac, telefono, pid))

    # --- ANTROPOMETRÍA ---
    peso = request.form.get("peso") or None
    talla = request.form.get("talla") or None
    cc = request.form.get("cc") or None
    bf_pct = request.form.get("bf_pct") or None
    actividad = request.form.get("actividad") or None
    
    # Permitir fecha personalizada para seguimiento histórico, o usar fecha actual
    fecha_medicion = request.form.get("fecha_medicion") or None
    if fecha_medicion:
        try:
            from datetime import datetime
            fecha_medicion = datetime.strptime(fecha_medicion, "%Y-%m-%d").date()
        except:
            fecha_medicion = None
    
    if any([peso, talla, cc, bf_pct, actividad]):
        # Verificar si ya existe un registro para la fecha especificada (o hoy)
        fecha_a_usar = fecha_medicion if fecha_medicion else date.today()
        existe_hoy = fetch_one("""
            SELECT id FROM antropometria 
            WHERE paciente_id=%s AND fecha=%s 
            LIMIT 1
        """, (pid, fecha_a_usar))
        
        if existe_hoy:
            # Si ya existe registro para esta fecha, actualizar ese registro
            execute("""
                UPDATE antropometria
                   SET peso=%s, talla=%s, cc=%s, bf_pct=%s, actividad=%s
                 WHERE id=%s
            """, (peso, talla, cc, bf_pct, actividad, existe_hoy[0]))
        else:
            # Si no existe registro para esta fecha, insertar nuevo (seguimiento histórico)
            execute("""
                INSERT INTO antropometria (paciente_id, fecha, peso, talla, cc, bf_pct, actividad)
                VALUES (%s, %s, %s,%s,%s,%s,%s)
            """, (pid, fecha_a_usar, peso, talla, cc, bf_pct, actividad))

    # --- CLÍNICO ---
    hba1c = request.form.get("hba1c") or None
    glucosa_ayunas = request.form.get("glucosa_ayunas") or None
    ldl = request.form.get("ldl") or None
    trigliceridos = request.form.get("trigliceridos") or None
    pa_sis = request.form.get("pa_sis") or None
    pa_dia = request.form.get("pa_dia") or None
    
    # Usar la misma fecha de medición que para antropometría
    if not fecha_medicion:
        fecha_medicion = request.form.get("fecha_medicion") or None
        if fecha_medicion:
            try:
                from datetime import datetime
                fecha_medicion = datetime.strptime(fecha_medicion, "%Y-%m-%d").date()
            except:
                fecha_medicion = None
    
    if any([hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia]):
        # Verificar si ya existe un registro para la fecha especificada (o hoy)
        fecha_a_usar = fecha_medicion if fecha_medicion else date.today()
        existe_hoy = fetch_one("""
            SELECT id FROM clinico 
            WHERE paciente_id=%s AND fecha=%s 
            LIMIT 1
        """, (pid, fecha_a_usar))
        
        if existe_hoy:
            # Si ya existe registro para esta fecha, actualizar ese registro
            execute("""
                UPDATE clinico
                   SET hba1c=%s, glucosa_ayunas=%s, ldl=%s, trigliceridos=%s, pa_sis=%s, pa_dia=%s
                 WHERE id=%s
            """, (hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia, existe_hoy[0]))
        else:
            # Si no existe registro para esta fecha, insertar nuevo (seguimiento histórico)
            execute("""
                INSERT INTO clinico (paciente_id, fecha, hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia)
                VALUES (%s, %s, %s,%s,%s,%s,%s,%s)
            """, (pid, fecha_a_usar, hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia))

    # --- MEDICAMENTOS ---
    meds_json = request.form.get("meds_json")
    if meds_json:
        try:
            meds = json.loads(meds_json)
            execute("DELETE FROM paciente_medicamento WHERE paciente_id=%s", (pid,))
            for m in meds:
                execute("""
                    INSERT INTO paciente_medicamento (paciente_id, nombre, dosis, frecuencia, activo, creado_en)
                    VALUES (%s, %s, %s, %s, TRUE, NOW())
                """, (pid, m.get("nombre"), m.get("dosis"), m.get("frecuencia")))
        except Exception as e:
            print("Error guardando medicamentos:", e)

    # --- ALERGIAS ---
    alergias_json = request.form.get("alergias_json")
    if alergias_json:
        try:
            als = json.loads(alergias_json)
            execute("DELETE FROM paciente_alergia WHERE paciente_id=%s", (pid,))
            for a in als:
                execute("""
                    INSERT INTO paciente_alergia (paciente_id, ingrediente_id, descripcion, creado_en)
                    VALUES (%s, %s, %s, NOW())
                """, (pid, a.get("ingrediente_id"), a.get("descripcion")))
        except Exception as e:
            print("Error guardando alergias:", e)

    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"ok": True, "msg": "Registro actualizado correctamente"}

    flash("✅ Registro integral actualizado correctamente", "success")
    return redirect(url_for("admin_pacientes"))



# === API: ingredientes activos con filtro de búsqueda ===
@app.route("/api/ingredientes")
@admin_required
def api_ingredientes():
    """Endpoint API para obtener todos los ingredientes"""
    try:
        rows = fetch_all("""
            SELECT id, nombre, grupo, kcal, cho, pro, fat, fibra, ig, sodio, 
                   costo, unidad_base, porcion_base, tags_json, activo
            FROM ingrediente
            ORDER BY nombre
        """)
        
        data = []
        for r in rows:
            tags_full = ""
            if r[13]:  # tags_json
                try:
                    tags_list = json.loads(r[13])
                    if isinstance(tags_list, list):
                        tags_full = ", ".join(tags_list)
                except:
                    pass
            
            data.append({
                "id": r[0],
                "nombre": r[1] or "",
                "grupo": r[2] or "",
                "kcal": float(r[3]) if r[3] is not None else None,
                "cho": float(r[4]) if r[4] is not None else None,
                "pro": float(r[5]) if r[5] is not None else None,
                "fat": float(r[6]) if r[6] is not None else None,
                "fibra": float(r[7]) if r[7] is not None else None,
                "ig": int(r[8]) if r[8] is not None else None,
                "sodio": float(r[9]) if r[9] is not None else None,
                "costo": float(r[10]) if r[10] is not None else None,
                "unidad_base": r[11] or "",
                "porcion_base": float(r[12]) if r[12] is not None else None,
                "tags_full": tags_full,
                "tags_json": r[13] if r[13] else None,  # Incluir tags_json también
                "activo": bool(r[14])
            })
        
        return {"ok": True, "rows": data}
        
    except Exception as e:
        return {"ok": False, "error": f"Error interno: {str(e)}"}


@app.route("/api/ingredientes/activos", methods=["GET"])
@admin_required
def api_ingredientes_activos():
    q = (request.args.get("q") or "").strip().lower()
    if q:
        rows = fetch_all("""
            SELECT id, nombre
            FROM ingrediente
            WHERE activo = TRUE AND LOWER(nombre) LIKE %s
            ORDER BY nombre
            LIMIT 20
        """, (f"%{q}%",))
    else:
        rows = fetch_all("""
            SELECT id, nombre
            FROM ingrediente
            WHERE activo = TRUE
            ORDER BY nombre
            LIMIT 20
        """)
    return {"ok": True, "results": [{"id": r[0], "text": r[1]} for r in rows]}


@app.route("/api/ingredientes/buscar")
@admin_required
def api_ingredientes_buscar():
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return {"ok": True, "results": []}

    rows = fetch_all("""
        SELECT id, nombre, grupo, unidad_base, porcion_base
        FROM ingrediente
        WHERE activo = TRUE
          AND (LOWER(nombre) LIKE %s OR LOWER(grupo) LIKE %s)
        ORDER BY nombre
        LIMIT 15
    """, (f"%{q}%", f"%{q}%")) or []

    return {
        "ok": True,
        "results": [{
            "id": r[0], 
            "text": f"{r[1]} ({r[2]})",
            "nombre": r[1],
            "grupo": r[2],
            "unidad_base": r[3] or "g",
            "porcion_base": float(r[4]) if r[4] else 100.0
        } for r in rows]
    }


# --- API: medicamentos y alergias del paciente ---

@app.route("/api/paciente/<int:pid>/medicamentos", methods=["GET"])
@admin_required
def api_paciente_meds(pid):
    rows = fetch_all("""
        SELECT id, nombre, dosis, frecuencia, activo
        FROM paciente_medicamento
        WHERE paciente_id=%s
        ORDER BY id
    """, (pid,))
    data = [{
        "id": r[0],
        "nombre": r[1],
        "dosis": r[2],
        "frecuencia": r[3],
        "activo": bool(r[4])
    } for r in rows]
    response = jsonify({"ok": True, "data": data})
    # Agregar headers para evitar caché
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route("/api/paciente/<int:pid>/alergias", methods=["GET"])
@admin_required
def api_paciente_alergias(pid):
    rows = fetch_all("""
        SELECT pa.id,
               pa.ingrediente_id,
               COALESCE(i.nombre, '') AS ingrediente_nombre,
               COALESCE(pa.descripcion, '') AS descripcion
          FROM paciente_alergia pa
          LEFT JOIN ingrediente i ON i.id = pa.ingrediente_id
         WHERE pa.paciente_id = %s
         ORDER BY pa.id
    """, (pid,))
    data = [{
        "id": r[0],
        "ingrediente_id": r[1],
        "ingrediente_nombre": r[2],
        "descripcion": r[3]
    } for r in rows]
    response = jsonify({"ok": True, "data": data})
    # Agregar headers para evitar caché
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response



@app.route("/api/paciente/<int:pid>/medicamentos", methods=["POST"])
@admin_required
def api_paciente_meds_save(pid):
    """
    Guarda la lista de medicamentos enviada como JSON (sobrescribe los existentes).
    Body: { "items": [ { "nombre": "Metformina" }, ... ] }
    """
    data = request.get_json(force=True)
    items = data.get("items") or []
    execute("DELETE FROM paciente_medicamento WHERE paciente_id=%s", (pid,))
    for it in items:
        nombre = (it.get("nombre") or "").strip()
        if nombre:
            execute(
                "INSERT INTO paciente_medicamento (paciente_id, nombre) VALUES (%s,%s)",
                (pid, nombre)
            )
    return {"ok": True}


@app.route("/api/paciente/<int:pid>/alergias", methods=["POST"])
@admin_required
def api_paciente_alergias_save(pid):
    """
    Guarda la lista de alergias enviada como JSON (sobrescribe las existentes).
    Body: { "items": [ { "descripcion": "Alergia a mariscos" }, ... ] }
    """
    data = request.get_json(force=True)
    items = data.get("items") or []
    execute("DELETE FROM paciente_alergia WHERE paciente_id=%s", (pid,))
    for it in items:
        desc = (it.get("descripcion") or "").strip()
        if desc:
            execute(
                "INSERT INTO paciente_alergia (paciente_id, descripcion) VALUES (%s,%s)",
                (pid, desc)
            )
    return {"ok": True}


@app.route("/admin/pacientes/<int:pid>/borrar", methods=["POST"])
@admin_required
def admin_paciente_borrar(pid):
    """Elimina paciente y sus registros asociados."""
    # Borra primero dependencias
    execute("DELETE FROM paciente_medicamento WHERE paciente_id=%s", (pid,))
    execute("DELETE FROM paciente_alergia WHERE paciente_id=%s", (pid,))
    execute("DELETE FROM clinico WHERE paciente_id=%s", (pid,))
    execute("DELETE FROM antropometria WHERE paciente_id=%s", (pid,))
    execute("DELETE FROM paciente WHERE id=%s", (pid,))
    flash("🗑️ Paciente y sus datos asociados eliminados correctamente", "success")
    return redirect(url_for("admin_pacientes"))



# === Configuración dinámica de límites clínicos ===
from functools import lru_cache
from time import time

# Cachea los límites durante 60 segundos para no consultar en cada request
_CACHE_LIM = {"data": None, "ts": 0}

def cargar_limites_clinica(org_id: str = "default") -> dict:
    """Devuelve los límites configurados (desde config_clinica.limites_json)."""
    global _CACHE_LIM
    ahora = time()
    if _CACHE_LIM["data"] and ahora - _CACHE_LIM["ts"] < 60:
        return _CACHE_LIM["data"]

    row = fetch_one("SELECT limites_json FROM config_clinica WHERE org_id=%s", (org_id,))
    if not row or not row[0]:
        _CACHE_LIM = {"data": {}, "ts": ahora}
        return {}
    try:
        data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        _CACHE_LIM = {"data": data, "ts": ahora}
        return data
    except Exception as e:
        print("⚠️ Error leyendo limites_json:", e)
        _CACHE_LIM = {"data": {}, "ts": ahora}
        return {}




def validar_valores_paciente(data: dict) -> list[str]:
    """Valida datos clínicos/antropométricos usando límites dinámicos (config_clinica)."""
    limites = cargar_limites_clinica()
    errores = []

 # Valores por defecto (solo si la clínica no define límites)
    defaults = {
        "peso": (20, 300),
        "talla": (0.5, 2.5),
        "cc": (20, 200),
        "bf_pct": (1, 70),
        "hba1c": (3, 20),
        "glucosa_ayunas": (40, 600),
        "ldl": (0, 400),
        "pa_sis": (70, 250),
        "pa_dia": (40, 150)
    }
   
    def to_float(v):
        try:
            return float(v) if v not in (None, "", "null") else None
        except Exception:
            return None

    for campo, (min_def, max_def) in defaults.items():
        val = to_float(data.get(campo))
        if val is None:
            continue

        # Usa los límites desde la BD si existen
        lim = limites.get(campo) if isinstance(limites, dict) else None
        min_val = lim.get("min") if lim else min_def
        max_val = lim.get("max") if lim else max_def

        if not (min_val <= val <= max_val):
            errores.append(f"{campo} fuera de rango ({min_val}–{max_val}).")

    return errores


@app.route("/api/paciente/<int:pid>/antropometria/ultima")
@admin_required
def api_antropometria_ultima(pid):
    row = fetch_one("""
        SELECT peso, talla, cc, bf_pct, actividad
        FROM antropometria
        WHERE paciente_id=%s
        ORDER BY fecha DESC, id DESC
        LIMIT 1
    """, (pid,))
    if not row:
        return {"ok": False, "msg": "Sin datos antropométricos"}
    keys = ["peso", "talla", "cc", "bf_pct", "actividad"]
    return {"ok": True, "data": dict(zip(keys, row))}


@app.route("/api/paciente/<int:pid>/clinico/ultimo")
@admin_required
def api_clinico_ultimo(pid):
    row = fetch_one("""
        SELECT hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia
        FROM clinico
        WHERE paciente_id=%s
        ORDER BY fecha DESC, id DESC
        LIMIT 1
    """, (pid,))
    if not row:
        return {"ok": False, "msg": "Sin datos clínicos"}
    keys = ["hba1c", "glucosa_ayunas", "ldl", "trigliceridos", "pa_sis", "pa_dia"]
    data = dict(zip(keys, row))

    # si agregas columnas meds_json / otros_json, podrías devolverlas aquí:
    data["meds"] = []
    data["otros"] = []
    return {"ok": True, "data": data}









# ===== Helpers Nutricionistas =====

def _json_or_none(raw: str | None):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        # Guardamos como texto JSON (psycopg puede castear str->jsonb)
        json.loads(raw)  # validación
        return raw
    except Exception:
        return None

def ensure_role(usuario_id: int, role_name: str):
    r = fetch_one("SELECT id FROM rol WHERE nombre=%s", (role_name,))
    if not r:
        # por si falta la semilla, crea el rol
        rid = fetch_one("INSERT INTO rol (nombre) VALUES (%s) RETURNING id", (role_name,))[0]
    else:
        rid = r[0]
    has = fetch_one("SELECT 1 FROM usuario_rol WHERE usuario_id=%s AND rol_id=%s", (usuario_id, rid))
    if not has:
        execute("INSERT INTO usuario_rol (usuario_id, rol_id) VALUES (%s,%s)", (usuario_id, rid))

def _norm_sexo(val: str | None) -> str | None:
    """
    Normaliza sexo a 'M'/'F'/'O' o None.
    Acepta 'm','f','o' y sinónimos en español.
    """
    if not val:
        return None
    v = (val or "").strip().lower()
    mapa = {
        "m": "M", "masc": "M", "masculino": "M",
        "f": "F", "fem": "F", "femenino": "F",
        "o": "O", "otro": "O", "x": "O", "no binario": "O"
    }
    return mapa.get(v, None)


# ===== ADMIN: NUTRICIONISTAS =====
# --------- ADMIN: NUTRICIONISTAS (CRUD) ---------

def _list_from_text(txt: str | None) -> list[str] | None:
    """
    Convierte texto separado por comas / punto y coma / saltos de línea en lista.
    Limpia espacios y descarta vacíos. Devuelve None si queda vacío.
    """
    if not txt:
        return None
    parts = [p.strip() for p in re.split(r"[,\n;]+", txt) if p.strip()]
    return parts or None

def _clip(s: str | None, maxlen: int) -> str | None:
    """Recorta cadenas a maxlen para evitar errores de varchar."""
    if not s:
        return None
    return s[:maxlen]

def ensure_role(usuario_id: int, role_name: str):
    r = fetch_one("SELECT id FROM rol WHERE nombre=%s", (role_name,))
    if not r:
        rid = fetch_one("INSERT INTO rol (nombre) VALUES (%s) RETURNING id", (role_name,))[0]
    else:
        rid = r[0]
    has = fetch_one("SELECT 1 FROM usuario_rol WHERE usuario_id=%s AND rol_id=%s", (usuario_id, rid))
    if not has:
        execute("INSERT INTO usuario_rol (usuario_id, rol_id) VALUES (%s,%s)", (usuario_id, rid))


# ===== ADMIN: NUTRICIONISTAS =====
@app.route("/api/nutricionistas/buscar")
@admin_only_required
def api_nutricionistas_buscar():
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return {"ok": True, "results": []}

    rows = fetch_all("""
        SELECT u.id, u.email, n.nombres, n.apellidos
        FROM usuario u
        JOIN nutricionista n ON n.usuario_id = u.id
        WHERE LOWER(u.email) LIKE %s
           OR LOWER(n.nombres) LIKE %s
           OR LOWER(n.apellidos) LIKE %s
        ORDER BY n.nombres, n.apellidos
        LIMIT 15
    """, (f"%{q}%", f"%{q}%", f"%{q}%")) or []

    return {
        "ok": True,
        "results": [{
            "id": r[0], 
            "text": f"{r[2] or ''} {r[3] or ''} ({r[1]})".strip(),
            "email": r[1],
            "nombres": r[2] or "",
            "apellidos": r[3] or ""
        } for r in rows]
    }

@app.route("/admin/nutricionistas")
@admin_only_required
def admin_nutricionistas():
    rows = fetch_all("""
        SELECT u.id, u.email, u.estado, u.mfa,
               pn.colegiatura, pn.especialidad,
               pn.nombres, pn.apellidos, pn.sexo, pn.telefono, pn.activo
          FROM usuario u
          JOIN usuario_rol ur ON ur.usuario_id = u.id
          JOIN rol r ON r.id = ur.rol_id AND r.nombre='nutricionista'
     LEFT JOIN perfil_nutricionista pn ON pn.usuario_id = u.id
         ORDER BY u.id DESC
    """) or []

    out = [{
        "uid": r[0],
        "email": r[1],
        "estado": r[2],
        "mfa": bool(r[3]),
        "colegiatura": r[4] or "",
        "especialidad": r[5] or "",
        "nombres": r[6] or "",
        "apellidos": r[7] or "",
        "sexo": r[8] or "",
        "telefono": r[9] or "",
        "perfil_activo": bool(r[10]) if r[10] is not None else (r[2] == "activo"),
    } for r in rows]

    template_base = get_template_base()
    return render_template(
        f"{template_base}/nutricionistas_list.html",
        rows=out,
        active_nav="nutricionistas",
        page_title="NutriSync · Nutricionistas",
        header_title="Nutricionistas"
    )



@app.route("/admin/nutricionistas/nuevo", methods=["POST"])
@admin_only_required
def admin_nutri_nuevo():
    # Verificar si es una petición AJAX
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    
    email   = (request.form.get("email") or "").strip().lower()
    pwd     = request.form.get("password") or ""
    estado  = (request.form.get("estado") or "activo").strip()
    # Siempre guardar sin MFA para nuevos nutricionistas
    mfa     = False

    errores = {}
    
    if not email:
        errores['email'] = "El email es obligatorio."
    elif not pwd:
        errores['password'] = "La contraseña es obligatoria."
    else:
        # Validar confirmación de contraseña
        pwd_confirm = request.form.get("password_confirm") or ""
        if pwd != pwd_confirm:
            errores['password_confirm'] = "Las contraseñas no coinciden."
        elif len(pwd) < 6:
            errores['password'] = "La contraseña debe tener al menos 6 caracteres."
    
    # IMPORTANTE: Validar email ANTES que otras cosas para evitar problemas
    # Verificar si el email ya existe en la base de datos (cualquier rol)
    # Esta ruta es solo para NUEVOS nutricionistas, así que si el email existe, es un error
    if email:
        existe_email = fetch_one("SELECT id FROM usuario WHERE email=%s", (email,))
        if existe_email:
            errores['email'] = f"Ya existe un usuario registrado con el email {email} (puede ser admin, paciente u otro nutricionista)."
            if is_ajax:
                return {"ok": False, "errores": errores}, 400
            flash(errores['email'], "error")
            return redirect(url_for("admin_nutricionistas"))
    
    if errores:
        if is_ajax:
            return {"ok": False, "errores": errores}, 400
        primer_error = list(errores.values())[0]
        flash(primer_error, "error")
        return redirect(url_for("admin_nutricionistas"))
    
    # Validar teléfono si se proporciona
    telefono = (request.form.get("telefono") or "").strip() or None
    if telefono:
        # Validar formato: 9 dígitos
        import re
        telefono_limpio = re.sub(r'\D', '', telefono)
        if len(telefono_limpio) != 9:
            errores['telefono'] = "El teléfono debe tener exactamente 9 dígitos."
            if is_ajax:
                return {"ok": False, "errores": errores}, 400
            flash(errores['telefono'], "error")
            return redirect(url_for("admin_nutricionistas"))
        telefono = telefono_limpio
    
    # Validar nombres, apellidos y especialidad: solo letras
    nombres_val = (request.form.get("nombres") or "").strip() or None
    apellidos_val = (request.form.get("apellidos") or "").strip() or None
    especialidad_val = (request.form.get("especialidad") or "").strip() or None
    
    import re
    if nombres_val and re.search(r'\d', nombres_val):
        errores['nombres'] = "Los nombres solo pueden contener letras."
        if is_ajax:
            return {"ok": False, "errores": errores}, 400
        flash(errores['nombres'], "error")
        return redirect(url_for("admin_nutricionistas"))
    if apellidos_val and re.search(r'\d', apellidos_val):
        errores['apellidos'] = "Los apellidos solo pueden contener letras."
        if is_ajax:
            return {"ok": False, "errores": errores}, 400
        flash(errores['apellidos'], "error")
        return redirect(url_for("admin_nutricionistas"))
    if especialidad_val and re.search(r'\d', especialidad_val):
        errores['especialidad'] = "La especialidad solo puede contener letras."
        if is_ajax:
            return {"ok": False, "errores": errores}, 400
        flash(errores['especialidad'], "error")
        return redirect(url_for("admin_nutricionistas"))
    
    # Validar teléfono duplicado si se proporciona - buscar en toda la base de datos
    if telefono:
        # Para nuevos nutricionistas, siempre verificar sin excluir ningún usuario
        existe_telefono_nutri = fetch_one("""
            SELECT pn.usuario_id FROM perfil_nutricionista pn 
            WHERE pn.telefono = %s
        """, (telefono,))
        if existe_telefono_nutri:
            errores['telefono'] = f"Ya existe un nutricionista con el teléfono {telefono}."
            if is_ajax:
                return {"ok": False, "errores": errores}, 400
            flash(errores['telefono'], "error")
            return redirect(url_for("admin_nutricionistas"))
        
        # Verificar en paciente
        existe_telefono_paciente = fetch_one("SELECT telefono FROM paciente WHERE telefono = %s", (telefono,))
        if existe_telefono_paciente:
            errores['telefono'] = f"Ya existe un paciente con el teléfono {telefono}."
            if is_ajax:
                return {"ok": False, "errores": errores}, 400
            flash(errores['telefono'], "error")
            return redirect(url_for("admin_nutricionistas"))
        
        # Verificar en pre_registro
        existe_telefono_prereg = fetch_one("SELECT telefono FROM pre_registro WHERE telefono = %s", (telefono,))
        if existe_telefono_prereg:
            errores['telefono'] = f"Ya existe un pre-registro con el teléfono {telefono}."
            if is_ajax:
                return {"ok": False, "errores": errores}, 400
            flash(errores['telefono'], "error")
            return redirect(url_for("admin_nutricionistas"))

    # Crear nuevo usuario (ya validamos que el email no existe)
    uid = fetch_one(
        "INSERT INTO usuario (email, hash_pwd, estado, mfa) VALUES (%s,%s,%s,%s) RETURNING id",
        (email, generate_password_hash(pwd) if pwd else None, estado, mfa)
    )[0]

    # Asegurar rol nutricionista
    ensure_role(uid, "nutricionista")

    # Perfil simplificado según esquema actual
    colegiatura  = (request.form.get("colegiatura") or "").strip() or None
    especialidad = especialidad_val  # Ya validado arriba
    nombres      = nombres_val  # Ya validado arriba
    apellidos    = apellidos_val  # Ya validado arriba
    sexo         = _norm_sexo(request.form.get("sexo"))
    # telefono ya se validó arriba
    activo       = (estado == "activo")

    existe = fetch_one("SELECT 1 FROM perfil_nutricionista WHERE usuario_id=%s", (uid,))
    if existe:
        execute("""
            UPDATE perfil_nutricionista
               SET colegiatura=%s, especialidad=%s,
                   nombres=%s, apellidos=%s, sexo=%s,
                   telefono=%s, activo=%s, actualizado_en=NOW()
             WHERE usuario_id=%s
        """, (colegiatura, especialidad, nombres, apellidos, sexo, telefono, activo, uid))
    else:
        execute("""
            INSERT INTO perfil_nutricionista
            (usuario_id, colegiatura, especialidad, nombres, apellidos, sexo, telefono, activo)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (uid, colegiatura, especialidad, nombres, apellidos, sexo, telefono, activo))

    if is_ajax:
        return {"ok": True, "message": "Nutricionista guardado correctamente."}
    flash("Nutricionista guardado.", "success")
    return redirect(url_for("admin_nutricionistas"))


@app.route("/admin/nutricionistas/<int:uid>/editar", methods=["POST"])
@admin_only_required
def admin_nutri_editar(uid):
    # Verificar si es una petición AJAX
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    
    email   = (request.form.get("email") or "").strip().lower()
    pwd     = request.form.get("password") or ""
    estado  = (request.form.get("estado") or "activo").strip()
    mfa     = "mfa" in request.form

    errores = {}
    
    if not email:
        errores['email'] = "El email es obligatorio."
        if is_ajax:
            return {"ok": False, "errores": errores}, 400
        flash(errores['email'], "error")
        return redirect(url_for("admin_nutricionistas"))
    
    # Validar que el email no esté en uso por OTRO usuario (excluyendo el actual)
    existe_email_otro = fetch_one("SELECT id FROM usuario WHERE email=%s AND id != %s", (email, uid))
    if existe_email_otro:
        errores['email'] = f"Ya existe otro usuario registrado con el email {email} (puede ser admin, paciente u otro nutricionista)."
        if is_ajax:
            return {"ok": False, "errores": errores}, 400
        flash(errores['email'], "error")
        return redirect(url_for("admin_nutricionistas"))
    
    # Validar nombres, apellidos y especialidad: solo letras
    nombres_val = (request.form.get("nombres") or "").strip() or None
    apellidos_val = (request.form.get("apellidos") or "").strip() or None
    especialidad_val = (request.form.get("especialidad") or "").strip() or None
    
    import re
    if nombres_val and re.search(r'\d', nombres_val):
        errores['nombres'] = "Los nombres solo pueden contener letras."
        if is_ajax:
            return {"ok": False, "errores": errores}, 400
        flash(errores['nombres'], "error")
        return redirect(url_for("admin_nutricionistas"))
    if apellidos_val and re.search(r'\d', apellidos_val):
        errores['apellidos'] = "Los apellidos solo pueden contener letras."
        if is_ajax:
            return {"ok": False, "errores": errores}, 400
        flash(errores['apellidos'], "error")
        return redirect(url_for("admin_nutricionistas"))
    if especialidad_val and re.search(r'\d', especialidad_val):
        errores['especialidad'] = "La especialidad solo puede contener letras."
        if is_ajax:
            return {"ok": False, "errores": errores}, 400
        flash(errores['especialidad'], "error")
        return redirect(url_for("admin_nutricionistas"))
    
    # Validar teléfono si se proporciona
    telefono = (request.form.get("telefono") or "").strip() or None
    if telefono:
        # Validar formato: 9 dígitos
        telefono_limpio = re.sub(r'\D', '', telefono)
        if len(telefono_limpio) != 9:
            errores['telefono'] = "El teléfono debe tener exactamente 9 dígitos."
            if is_ajax:
                return {"ok": False, "errores": errores}, 400
            flash(errores['telefono'], "error")
            return redirect(url_for("admin_nutricionistas"))
        telefono = telefono_limpio
        
        # Validar teléfono duplicado - buscar en toda la base de datos (excluyendo el usuario actual)
        existe_telefono_nutri = fetch_one("""
            SELECT pn.usuario_id FROM perfil_nutricionista pn 
            WHERE pn.telefono = %s AND pn.usuario_id != %s
        """, (telefono, uid))
        if existe_telefono_nutri:
            errores['telefono'] = f"Ya existe un nutricionista con el teléfono {telefono}."
            if is_ajax:
                return {"ok": False, "errores": errores}, 400
            flash(errores['telefono'], "error")
            return redirect(url_for("admin_nutricionistas"))
        
        # Verificar en paciente
        existe_telefono_paciente = fetch_one("SELECT telefono FROM paciente WHERE telefono = %s", (telefono,))
        if existe_telefono_paciente:
            errores['telefono'] = f"Ya existe un paciente con el teléfono {telefono}."
            if is_ajax:
                return {"ok": False, "errores": errores}, 400
            flash(errores['telefono'], "error")
            return redirect(url_for("admin_nutricionistas"))
        
        # Verificar en pre_registro
        existe_telefono_prereg = fetch_one("SELECT telefono FROM pre_registro WHERE telefono = %s", (telefono,))
        if existe_telefono_prereg:
            errores['telefono'] = f"Ya existe un pre-registro con el teléfono {telefono}."
            if is_ajax:
                return {"ok": False, "errores": errores}, 400
            flash(errores['telefono'], "error")
            return redirect(url_for("admin_nutricionistas"))
    
    # Verificar que no haya errores antes de actualizar
    if errores:
        if is_ajax:
            return {"ok": False, "errores": errores}, 400
        primer_error = list(errores.values())[0]
        flash(primer_error, "error")
        return redirect(url_for("admin_nutricionistas"))

    # Usuario - Solo actualizar si no hay errores
    if pwd:
        execute("UPDATE usuario SET email=%s, hash_pwd=%s, estado=%s, mfa=%s WHERE id=%s",
                (email, generate_password_hash(pwd), estado, mfa, uid))
    else:
        execute("UPDATE usuario SET email=%s, estado=%s, mfa=%s WHERE id=%s",
                (email, estado, mfa, uid))

    # Rol nutricionista
    ensure_role(uid, "nutricionista")

    # Perfil
    colegiatura  = (request.form.get("colegiatura") or "").strip() or None
    especialidad = (request.form.get("especialidad") or "").strip() or None
    nombres      = (request.form.get("nombres") or "").strip() or None
    apellidos    = (request.form.get("apellidos") or "").strip() or None
    sexo         = _norm_sexo(request.form.get("sexo"))
    telefono     = (request.form.get("telefono") or "").strip() or None
    activo       = (estado == "activo")

    existe = fetch_one("SELECT 1 FROM perfil_nutricionista WHERE usuario_id=%s", (uid,))
    if existe:
        execute("""
            UPDATE perfil_nutricionista
               SET colegiatura=%s, especialidad=%s,
                   nombres=%s, apellidos=%s, sexo=%s,
                   telefono=%s, activo=%s, actualizado_en=NOW()
             WHERE usuario_id=%s
        """, (colegiatura, especialidad, nombres, apellidos, sexo, telefono, activo, uid))
    else:
        execute("""
            INSERT INTO perfil_nutricionista
            (usuario_id, colegiatura, especialidad, nombres, apellidos, sexo, telefono, activo)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (uid, colegiatura, especialidad, nombres, apellidos, sexo, telefono, activo))

    flash("Nutricionista actualizado.", "success")
    return redirect(url_for("admin_nutricionistas"))


@app.route("/admin/nutricionistas/<int:usuario_id>/borrar", methods=["POST"])
@admin_only_required
def admin_nutri_borrar(usuario_id):
    # Borra el usuario; por FK se eliminará perfil_nutricionista y usuario_rol
    execute("DELETE FROM usuario WHERE id=%s", (usuario_id,))
    flash("Nutricionista eliminado.", "success")
    return redirect(url_for("admin_nutricionistas"))



@app.route("/admin/usuarios/<int:uid>/borrar", methods=["POST"])
@admin_only_required
def admin_usuario_borrar(uid):
    execute("DELETE FROM usuario WHERE id=%s", (uid,))
    flash("Usuario eliminado", "success")
    return redirect(url_for("admin_usuarios"))

# --------- ADMIN: ASIGNAR ROLES ---------

@app.route("/admin/usuarios/<int:uid>/roles", methods=["GET","POST"])
@admin_only_required
def admin_usuario_roles(uid):
    if request.method == "POST":
        # limpiar y volver a insertar selección
        execute("DELETE FROM usuario_rol WHERE usuario_id=%s", (uid,))
        roles_ids = request.form.getlist("roles")
        for rid in roles_ids:
            execute("INSERT INTO usuario_rol (usuario_id, rol_id) VALUES (%s,%s)", (uid, rid))
        flash("Roles actualizados", "success")
        return redirect(url_for("admin_usuarios"))

    usuario = fetch_one("SELECT id, email FROM usuario WHERE id=%s", (uid,))
    if not usuario:
        flash("Usuario no existe", "error")
        return redirect(url_for("admin_usuarios"))

    roles = fetch_all("SELECT id, nombre FROM rol ORDER BY nombre")
    asignados = fetch_all("SELECT rol_id FROM usuario_rol WHERE usuario_id=%s", (uid,))
    asignados = {r[0] for r in asignados}
    return render_template("admin/usuario_roles.html",
                           usuario=usuario, roles=roles, asignados=asignados)



# --------- ADMIN: PRE-REGISTRO (CRUD + token) ---------

@app.route("/admin/pre-registro", methods=["GET", "POST"])
@admin_required
def admin_preregistro():
    if request.method == "POST":
        dni       = (request.form.get("dni") or "").strip()
        nombres   = (request.form.get("nombres") or "").strip()
        apellidos = (request.form.get("apellidos") or "").strip()
        telefono  = (request.form.get("telefono") or "").strip() or None
        email     = (request.form.get("email") or "").strip().lower() or None

        # Verificar si es una petición AJAX
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        
        errores = {}
        
        # Validar DNI: solo números, 8 dígitos
        if not dni.isdigit():
            errores['dni'] = "El DNI solo puede contener números."
        elif len(dni) != 8:
            errores['dni'] = "El DNI debe tener exactamente 8 dígitos."
        else:
            # Verificar si ya existe un preregistro con este DNI
            existe_dni = fetch_one("SELECT dni FROM pre_registro WHERE dni = %s", (dni,))
            if existe_dni:
                errores['dni'] = f"Ya existe un pre-registro con el DNI {dni}."
        
        # Validar nombres: solo letras
        if nombres:
            import re
            if re.search(r'\d', nombres):
                errores['nombres'] = "Los nombres solo pueden contener letras."
            elif not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', nombres):
                errores['nombres'] = "Los nombres contienen caracteres inválidos."
        
        # Validar apellidos: solo letras
        if apellidos:
            import re
            if re.search(r'\d', apellidos):
                errores['apellidos'] = "Los apellidos solo pueden contener letras."
            elif not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', apellidos):
                errores['apellidos'] = "Los apellidos contienen caracteres inválidos."
        
        # Validar email si se proporciona - buscar en toda la base de datos
        if email:
            # Verificar en usuario (cualquier rol)
            existe_email_usuario = fetch_one("SELECT email FROM usuario WHERE email = %s", (email,))
            if existe_email_usuario:
                errores['email'] = f"Ya existe un usuario registrado con el email {email}."
            else:
                # Verificar en pre_registro
                existe_email_prereg = fetch_one("SELECT email FROM pre_registro WHERE email = %s", (email,))
                if existe_email_prereg:
                    errores['email'] = f"Ya existe un pre-registro con el email {email}."
        
        # Validar teléfono si se proporciona - buscar en toda la base de datos
        if telefono:
            # Validar formato: 9 dígitos
            import re
            telefono_limpio = re.sub(r'\D', '', telefono)
            if len(telefono_limpio) != 9:
                errores['telefono'] = "El teléfono debe tener exactamente 9 dígitos."
            else:
                # Normalizar teléfono a solo números
                telefono = telefono_limpio
                # Verificar en perfil_nutricionista
                existe_telefono_nutri = fetch_one("SELECT telefono FROM perfil_nutricionista WHERE telefono = %s", (telefono,))
                if existe_telefono_nutri:
                    errores['telefono'] = f"Ya existe un nutricionista registrado con el teléfono {telefono}."
                else:
                    # Verificar en paciente
                    existe_telefono_paciente = fetch_one("SELECT telefono FROM paciente WHERE telefono = %s", (telefono,))
                    if existe_telefono_paciente:
                        errores['telefono'] = f"Ya existe un paciente registrado con el teléfono {telefono}."
                    else:
                        # Verificar en pre_registro
                        existe_telefono_prereg = fetch_one("SELECT telefono FROM pre_registro WHERE telefono = %s", (telefono,))
                        if existe_telefono_prereg:
                            errores['telefono'] = f"Ya existe un pre-registro con el teléfono {telefono}."
        
        if errores:
            if is_ajax:
                return {"ok": False, "errores": errores}, 400
            # Para peticiones no AJAX, mostrar el primer error
            primer_error = list(errores.values())[0]
            flash(primer_error, "error")
        else:
            try:
                execute("""
                    INSERT INTO pre_registro (dni, nombres, apellidos, telefono, email, estado, creado_en, actualizado_en)
                    VALUES (%s, %s, %s, %s, %s, 'pendiente', NOW(), NOW())
                """, (dni, nombres, apellidos, telefono, email))
                if is_ajax:
                    return {"ok": True, "message": "Pre-registro guardado correctamente."}
                flash("Pre-registro guardado correctamente.", "success")
            except Exception as e:
                error_msg = str(e)
                errores = {}
                
                # Detectar errores de UniqueViolation
                if "uk_prereg_email" in error_msg or ("llave duplicada" in error_msg.lower() and "email" in error_msg.lower()):
                    errores['email'] = f"Ya existe un pre-registro con el email {email}."
                elif "uk_prereg_dni" in error_msg or ("llave duplicada" in error_msg.lower() and "dni" in error_msg.lower()):
                    errores['dni'] = f"Ya existe un pre-registro con el DNI {dni}."
                elif "llave duplicada" in error_msg.lower():
                    # Si no podemos determinar cuál campo, intentar ambos
                    if email:
                        errores['email'] = f"Ya existe un pre-registro con el email {email}."
                    if not errores:
                        errores['dni'] = f"Ya existe un pre-registro con el DNI {dni}."
                else:
                    errores['general'] = "Error al guardar el pre-registro."
                
                if is_ajax:
                    return {"ok": False, "errores": errores}, 400
                primer_error = list(errores.values())[0]
                flash(primer_error, "error")

    # Listado con paginación
    page = int(request.args.get('page', 1))
    per_page = 6
    
    # Contar total
    total = fetch_one("SELECT COUNT(*) FROM pre_registro")[0] or 0
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    # Ajustar página válida
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    offset = (page - 1) * per_page
    
    rows = fetch_all("""
        SELECT pr.dni, pr.nombres, pr.apellidos, pr.telefono, pr.email, pr.estado, pr.actualizado_en,
               CASE WHEN p.id IS NOT NULL THEN TRUE ELSE FALSE END as tiene_paciente
        FROM pre_registro pr
        LEFT JOIN paciente p ON p.dni = pr.dni
        ORDER BY pr.actualizado_en DESC NULLS LAST
        LIMIT %s OFFSET %s
    """, (per_page, offset)) or []

    filas = [{
        "dni": r[0],
        "nombres": r[1] or "",
        "apellidos": r[2] or "",
        "telefono": r[3] or "",
        "email": r[4] or "",
        "estado": r[5] or "",
        "actualizado": r[6].strftime("%Y-%m-%d %H:%M") if r[6] else "",
        "tiene_paciente": r[7]  # True si ya tiene paciente registrado
    } for r in rows]

    template_base = get_template_base()
    return render_template(
        f"{template_base}/preregistro.html",
        filas=filas,
        page=page,
        total_pages=total_pages,
        total=total,
        active_nav="preregistro",
        page_title="NutriSync · Pre-registro (DNI)",
        header_title="Pre-registro (DNI)"
    )





@app.route("/admin/pre-registro/<dni>/token", methods=["POST"])
@admin_required
def admin_preregistro_token(dni):
    # valida DNI
    if not (dni.isdigit() and len(dni) == 8):
        flash("DNI inválido para token.", "error")
        return redirect(url_for("admin_preregistro"))

    # Obtener datos del preregistro
    pr = fetch_one("""
        SELECT nombres, apellidos, telefono, email
        FROM pre_registro
        WHERE dni=%s
    """, (dni,))
    
    if not pr:
        flash("El DNI no está en pre-registro.", "error")
        return redirect(url_for("admin_preregistro"))
    
    nombres, apellidos, telefono, email = pr
    nombre_completo = f"{nombres or ''} {apellidos or ''}".strip()

    tok = str(uuid.uuid4())
    vence = datetime.now() + timedelta(days=2)
    link_activacion = build_activation_link(dni, tok)

    # usado es BOOLEAN → usa TRUE/FALSE, no 1/0
    execute("""
        INSERT INTO activacion_token (dni, token, vence_en, usado, creado_en, actualizado_en)
        VALUES (%s, %s, %s, FALSE, NOW(), NOW())
        ON CONFLICT (dni) DO UPDATE
           SET token = EXCLUDED.token,
               vence_en = EXCLUDED.vence_en,
               usado = FALSE,
               actualizado_en = NOW()
    """, (dni, tok, vence))

    # Intentar enviar email si hay email configurado
    mensaje_flash = f"Token generado para {dni}: {tok} (vence {vence:%Y-%m-%d %H:%M})"
    
    if email:
        exito, mensaje = enviar_token_activacion(
            dni=dni,
            token=tok,
            link_activacion=link_activacion,
            nombre=nombre_completo,
            email=email,
            telefono=telefono or ""
        )
        if exito:
            flash(f"{mensaje_flash}. ✅ Email enviado a {email}.", "success")
        else:
            # Mostrar el token y el error
            flash(f"{mensaje_flash}", "success")
            flash(f"⚠️ {mensaje}", "error")
            flash(f"📋 Token para enviar manualmente: {tok}", "info")
    else:
        flash(f"{mensaje_flash}. ⚠️ No hay email registrado, el token debe enviarse manualmente.", "warning")
    
    return redirect(url_for("admin_preregistro"))


@app.route("/admin/pre-registro/<dni>/borrar", methods=["POST"])
@admin_required
def admin_preregistro_borrar(dni):
    # Solo permite borrar si NO HAY paciente con ese DNI (por la FK)
    pac = fetch_one("SELECT 1 FROM paciente WHERE dni=%s", (dni,))
    if pac:
        flash("No puedes borrar: ya existe un paciente con ese DNI.", "error")
        return redirect(url_for("admin_preregistro"))

    execute("DELETE FROM pre_registro WHERE dni=%s", (dni,))
    flash("Pre-registro eliminado.", "success")
    return redirect(url_for("admin_preregistro"))
## Modales
@app.route("/admin/usuarios/<int:uid>/json")
@admin_only_required
def admin_usuario_json(uid):
    row = fetch_one("""
        SELECT id, email, estado, mfa
        FROM usuario
        WHERE id = %s
    """, (uid,))
    if not row:
        return {"ok": False, "error": "Usuario no existe"}, 404
    u = {"id": row[0], "email": row[1], "estado": row[2], "mfa": bool(row[3])}
    return {"ok": True, "user": u}

@app.route("/admin/usuarios/nuevo", methods=["POST"])
@admin_only_required
def admin_usuario_nuevo():
    if request.is_json:
        data = request.get_json(force=True)
        email  = (data.get("email") or "").strip().lower()
        estado = (data.get("estado") or "activo").strip()
        mfa    = bool(data.get("mfa", True))
        pwd    = data.get("password") or ""
    else:
        email  = (request.form.get("email") or "").strip().lower()
        estado = request.form.get("estado") or "activo"
        mfa    = request.form.get("mfa") == "on"
        pwd    = request.form.get("password") or ""

    if not email:
        if request.is_json:
            return {"ok": False, "error": "El email es obligatorio"}, 400
        flash("El email es obligatorio", "error")
        return redirect(url_for("admin_usuarios"))

    hash_pwd = generate_password_hash(pwd) if pwd else None
    execute(
        "INSERT INTO usuario (email, hash_pwd, estado, mfa) VALUES (%s,%s,%s,%s)",
        (email, hash_pwd, estado, mfa)
    )

    if request.is_json:
        return {"ok": True}

    flash("Usuario creado", "success")
    return redirect(url_for("admin_usuarios"))


@app.route("/admin/usuarios/<int:uid>/editar", methods=["POST"])
@admin_only_required
def admin_usuario_editar(uid):
    if request.is_json:
        data = request.get_json(force=True)
        email  = (data.get("email") or "").strip().lower()
        estado = (data.get("estado") or "activo").strip()
        mfa    = bool(data.get("mfa", True))
        pwd    = data.get("password") or ""
    else:
        email  = (request.form.get("email") or "").strip().lower()
        estado = request.form.get("estado") or "activo"
        mfa    = request.form.get("mfa") == "on"
        pwd    = request.form.get("password") or ""

    if not email:
        if request.is_json:
            return {"ok": False, "error": "El email es obligatorio"}, 400
        flash("El email es obligatorio", "error")
        return redirect(url_for("admin_usuarios"))

    if pwd:
        hash_pwd = generate_password_hash(pwd)
        execute(
            "UPDATE usuario SET email=%s, estado=%s, mfa=%s, hash_pwd=%s WHERE id=%s",
            (email, estado, mfa, hash_pwd, uid)
        )
    else:
        execute(
            "UPDATE usuario SET email=%s, estado=%s, mfa=%s WHERE id=%s",
            (email, estado, mfa, uid)
        )

    if request.is_json:
        return {"ok": True}

    flash("Usuario actualizado", "success")
    return redirect(url_for("admin_usuarios"))


# --------- ADMIN: ROLES (CRUD) ---------

@app.route("/admin/roles")
@admin_only_required
def admin_roles_list():
    rows = fetch_all("""
        SELECT r.id, r.nombre, r.descripcion,
               COALESCE(COUNT(ur.usuario_id), 0) AS usuarios
        FROM rol r
        LEFT JOIN usuario_rol ur ON ur.rol_id = r.id
        GROUP BY r.id
        ORDER BY r.nombre
    """) or []
    rows = [{"id": r[0], "nombre": r[1], "descripcion": r[2], "usuarios": r[3]} for r in rows]
    return render_template(
        "admin/roles_list.html",
        rows=rows,
        active_nav="roles",
        page_title="NutriSync · Roles",
        header_title="Roles"
    )

@app.route("/admin/roles/nuevo", methods=["POST"])
@admin_only_required
def admin_rol_nuevo():
    nombre = (request.form.get("nombre") or "").strip().lower()
    descripcion = (request.form.get("descripcion") or "").strip() or None

    # Verificar si es una petición AJAX
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if not nombre:
        if is_ajax:
            return {"ok": False, "error": "El nombre del rol es obligatorio."}, 400
        flash("El nombre del rol es obligatorio.", "error")
        return redirect(url_for("admin_roles_list"))

    # Validar que no contenga números
    if any(char.isdigit() for char in nombre):
        if is_ajax:
            return {"ok": False, "error": "El nombre del rol no puede contener números."}, 400
        flash("El nombre del rol no puede contener números.", "error")
        return redirect(url_for("admin_roles_list"))

    if descripcion and any(char.isdigit() for char in descripcion):
        if is_ajax:
            return {"ok": False, "error": "La descripción no puede contener números."}, 400
        flash("La descripción no puede contener números.", "error")
        return redirect(url_for("admin_roles_list"))

    # evita duplicados
    dup = fetch_one("SELECT 1 FROM rol WHERE LOWER(nombre)=%s", (nombre,))
    if dup:
        if is_ajax:
            return {"ok": False, "error": "Ya existe un rol con ese nombre."}, 400
        flash("Ya existe un rol con ese nombre.", "error")
        return redirect(url_for("admin_roles_list"))

    execute("INSERT INTO rol (nombre, descripcion) VALUES (%s, %s)", (nombre, descripcion))
    if is_ajax:
        return {"ok": True, "message": "Rol creado correctamente."}
    flash("Rol creado.", "success")
    return redirect(url_for("admin_roles_list"))

@app.route("/admin/roles/<int:rid>/editar", methods=["POST"])
@admin_only_required
def admin_rol_editar(rid):
    nombre = (request.form.get("nombre") or "").strip()
    descripcion = (request.form.get("descripcion") or "").strip() or None

    # Verificar si es una petición AJAX
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    row = fetch_one("SELECT nombre FROM rol WHERE id=%s", (rid,))
    if not row:
        if is_ajax:
            return {"ok": False, "error": "El rol no existe."}, 404
        flash("El rol no existe.", "error")
        return redirect(url_for("admin_roles_list"))

    nombre_actual = (row[0] or "").lower()

    # no permitir renombrar admin/paciente
    if nombre_actual in ("admin", "paciente"):
        execute("UPDATE rol SET descripcion=%s WHERE id=%s", (descripcion, rid))
        if is_ajax:
            return {"ok": True, "message": "Descripción actualizada (el nombre de este rol es fijo)."}
        flash("Descripción actualizada (el nombre de este rol es fijo).", "info")
        return redirect(url_for("admin_roles_list"))

    if not nombre:
        if is_ajax:
            return {"ok": False, "error": "El nombre del rol es obligatorio."}, 400
        flash("El nombre del rol es obligatorio.", "error")
        return redirect(url_for("admin_roles_list"))

    # Validar que no contenga números
    if any(char.isdigit() for char in nombre):
        if is_ajax:
            return {"ok": False, "error": "El nombre del rol no puede contener números."}, 400
        flash("El nombre del rol no puede contener números.", "error")
        return redirect(url_for("admin_roles_list"))

    if descripcion and any(char.isdigit() for char in descripcion):
        if is_ajax:
            return {"ok": False, "error": "La descripción no puede contener números."}, 400
        flash("La descripción no puede contener números.", "error")
        return redirect(url_for("admin_roles_list"))

    # check duplicado si cambió nombre
    if nombre.lower() != nombre_actual:
        dup = fetch_one("SELECT 1 FROM rol WHERE LOWER(nombre)=%s", (nombre.lower(),))
        if dup:
            if is_ajax:
                return {"ok": False, "error": "Ya existe otro rol con ese nombre."}, 400
            flash("Ya existe otro rol con ese nombre.", "error")
            return redirect(url_for("admin_roles_list"))

    execute("UPDATE rol SET nombre=%s, descripcion=%s WHERE id=%s", (nombre, descripcion, rid))
    if is_ajax:
        return {"ok": True, "message": "Rol actualizado correctamente."}
    flash("Rol actualizado.", "success")
    return redirect(url_for("admin_roles_list"))

@app.route("/admin/roles/<int:rid>/borrar", methods=["POST"])
@admin_only_required
def admin_rol_borrar(rid):
    row = fetch_one("SELECT nombre FROM rol WHERE id=%s", (rid,))
    if not row:
        flash("El rol no existe.", "error")
        return redirect(url_for("admin_roles_list"))

    nombre = (row[0] or "").lower()
    if nombre in ("admin", "paciente"):
        flash("No puedes borrar los roles reservados 'admin' y 'paciente'.", "error")
        return redirect(url_for("admin_roles_list"))

    usados = fetch_one("SELECT 1 FROM usuario_rol WHERE rol_id=%s LIMIT 1", (rid,))
    if usados:
        flash("No puedes borrar el rol porque tiene usuarios asignados.", "error")
        return redirect(url_for("admin_roles_list"))

    execute("DELETE FROM rol WHERE id=%s", (rid,))
    flash("Rol eliminado.", "success")
    return redirect(url_for("admin_roles_list"))


# ---------- ADMIN: CLÍNICO (CRUD por paciente) ----------
# --- helpers clínico ---


def _to_decimal(txt):
    txt = (txt or "").strip()
    if txt == "":
        return None
    try:
        return txt
    except InvalidOperation:
        return None

def _to_smallint(txt):
    txt = (txt or "").strip()
    if txt == "":
        return None
    try:
        return int(txt)
    except ValueError:
        return None

def _parse_json_field(raw: str):
    """
    Acepta:
      - vacío -> None
      - objeto/array JSON -> dict/list
    Si viene una cadena no vacía pero no es JSON válido, retorna (None, error_msg).
    """
    raw = (raw or "").strip()
    if raw == "":
        return None, None
    try:
        return json.loads(raw), None
    except Exception as e:
        return None, f"JSON inválido ({str(e)})."

def _parse_list_or_json(txt: str | None):
    """
    Acepta:
      - vacío -> None
      - JSON válido (objeto o arreglo) -> Python
      - Texto separado por comas/ saltos de línea/ punto y coma -> lista
    """
    if not txt or not txt.strip():
        return None
    t = txt.strip()
    # 1) si es JSON, úsalo
    try:
        return json.loads(t)
    except Exception:
        pass
    # 2) acepta 'Metformina, Insulina' o líneas
    parts = [p.strip() for p in re.split(r"[,\n;]+", t) if p.strip()]
    return parts or None


from datetime import date
import json

# ---------- ADMIN: DATOS CLÍNICOS (CRUD) ----------

def _parse_json_list(s: str | None) -> list[str]:
    """Devuelve lista limpia desde JSON (o vacío si malformado). Nunca lanza."""
    if not s:
        return []
    try:
        val = json.loads(s)
        if isinstance(val, list):
            # normaliza: solo strings no vacíos
            return [str(x).strip() for x in val if str(x).strip()]
        return []
    except Exception:
        return []

def _shorten(items: list[str], n: int = 2) -> tuple[str, str]:
    """Devuelve (corto, completo) para mostrar en tabla."""
    full = ", ".join(items) if items else ""
    if len(items) <= n:
        return full, full
    short = ", ".join(items[:n]) + f" +{len(items)-n}"
    return short, full

# ---------- ADMIN: DATOS CLÍNICOS (CRUD) ----------


@app.route("/admin/clinico")
@admin_required
def admin_clinico():
    """
    Lista todos los registros clínicos de los pacientes.
    Ahora solo contiene valores cuantitativos (sin meds_json / otros_json).
    """
    # Pacientes para el combo (DNI + nombre)
    pacientes = fetch_all("""
        SELECT p.id,
               p.dni,
               COALESCE(pr.nombres || ' ' || pr.apellidos, '') AS nombre
          FROM paciente p
          LEFT JOIN pre_registro pr ON pr.dni = p.dni
         ORDER BY p.id DESC
    """) or []
    pacientes = [{"id": r[0], "dni": r[1], "nombre": r[2]} for r in pacientes]

    # Registros clínicos
    rows = fetch_all("""
        SELECT c.id, c.fecha, c.hba1c, c.glucosa_ayunas, c.ldl, c.trigliceridos, c.pa_sis, c.pa_dia,
               p.id AS paciente_id,
               p.dni,
               COALESCE(pr.nombres || ' ' || pr.apellidos, '') AS nombre
          FROM clinico c
          JOIN paciente p ON p.id = c.paciente_id
          LEFT JOIN pre_registro pr ON pr.dni = p.dni
         ORDER BY c.fecha DESC, c.id DESC
    """) or []

    registros = [{
        "id": r[0],
        "fecha": r[1].strftime("%Y-%m-%d"),
        "hba1c": r[2],
        "glucosa_ayunas": r[3],
        "ldl": r[4],
        "trigliceridos": r[5],
        "pa_sis": r[6],
        "pa_dia": r[7],
        "paciente_id": r[8],
        "paciente": f"{r[9]} — {(r[10] or '(sin nombre)')}"
    } for r in rows]

    template_base = get_template_base()
    return render_template(
        f"{template_base}/clinico_list.html",
        rows=registros,
        pacientes=pacientes,
        hoy=date.today().strftime("%Y-%m-%d"),
        active_nav="clinico",
        page_title="NutriSync · Datos clínicos",
        header_title="Datos clínicos"
    )


@app.route("/admin/clinico/nuevo", methods=["POST"])
@admin_required
def admin_clinico_nuevo():
    """
    Inserta un nuevo registro clínico sin meds_json ni otros_json.
    """
    paciente_id = (request.form.get("paciente_id") or "").strip()
    fecha       = (request.form.get("fecha") or "").strip()

    if not paciente_id or not fecha:
        flash("Paciente y fecha son obligatorios.", "error")
        return redirect(url_for("admin_clinico"))

    def _num(name):
        v = (request.form.get(name) or "").strip()
        return float(v) if v else None

    hba1c          = _num("hba1c")
    glucosa_ayunas = _num("glucosa_ayunas")
    ldl            = _num("ldl")
    pa_sis         = request.form.get("pa_sis") or None
    pa_dia         = request.form.get("pa_dia") or None
    pa_sis = int(pa_sis) if pa_sis not in (None, "") else None
    pa_dia = int(pa_dia) if pa_dia not in (None, "") else None

    trigliceridos = request.form.get("trigliceridos") or None
    trigliceridos = float(trigliceridos) if trigliceridos not in (None, "") else None

    execute("""
        INSERT INTO clinico (paciente_id, fecha, hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (paciente_id, fecha, hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia))

    flash("Registro clínico creado correctamente.", "success")
    return redirect(url_for("admin_clinico"))


@app.route("/admin/clinico/<int:cid>/editar", methods=["POST"])
@admin_required
def admin_clinico_editar(cid):
    """
    Edita un registro clínico existente.
    """
    row = fetch_one("SELECT id FROM clinico WHERE id=%s", (cid,))
    if not row:
        flash("El registro clínico no existe.", "error")
        return redirect(url_for("admin_clinico"))

    paciente_id = (request.form.get("paciente_id") or "").strip()
    fecha       = (request.form.get("fecha") or "").strip()

    if not paciente_id or not fecha:
        flash("Paciente y fecha son obligatorios.", "error")
        return redirect(url_for("admin_clinico"))

    def _num(name):
        v = (request.form.get(name) or "").strip()
        return float(v) if v else None

    hba1c          = _num("hba1c")
    glucosa_ayunas = _num("glucosa_ayunas")
    ldl            = _num("ldl")
    pa_sis         = request.form.get("pa_sis") or None
    pa_dia         = request.form.get("pa_dia") or None
    pa_sis = int(pa_sis) if pa_sis not in (None, "") else None
    pa_dia = int(pa_dia) if pa_dia not in (None, "") else None

    trigliceridos = request.form.get("trigliceridos") or None
    trigliceridos = float(trigliceridos) if trigliceridos not in (None, "") else None

    execute("""
        UPDATE clinico
           SET paciente_id=%s,
               fecha=%s,
               hba1c=%s,
               glucosa_ayunas=%s,
               ldl=%s,
               trigliceridos=%s,
               pa_sis=%s,
               pa_dia=%s
         WHERE id=%s
    """, (paciente_id, fecha, hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia, cid))

    flash("Registro clínico actualizado correctamente.", "success")
    return redirect(url_for("admin_clinico"))


@app.route("/admin/clinico/<int:cid>/borrar", methods=["POST"])
@admin_required
def admin_clinico_borrar(cid):
    """
    Elimina un registro clínico.
    """
    execute("DELETE FROM clinico WHERE id=%s", (cid,))
    flash("Registro clínico eliminado.", "success")
    return redirect(url_for("admin_clinico"))



# ==== Helpers antropometría (parsers) ====
def _num_or_none(name: str) -> str | None:
    """Lee un campo numérico del form y devuelve cadena (Postgres castea a DECIMAL) o None."""
    v = (request.form.get(name) or "").strip()
    return v if v != "" else None

def _actividad_norm(txt: str | None) -> str | None:
    if not txt:
        return None
    t = txt.strip().lower()
    return t if t in ("baja", "moderada", "alta") else None


# ==== ADMIN: ANTROPOMETRÍA =====
@app.route("/admin/antropometria")
@admin_required
def admin_antropometria():
    # Pacientes para el combo
    pacientes = fetch_all("""
        SELECT p.id,
               p.dni,
               COALESCE(pr.nombres || ' ' || pr.apellidos, '') AS nombre
          FROM paciente p
          LEFT JOIN pre_registro pr ON pr.dni = p.dni
         ORDER BY p.id DESC
    """) or []
    pacientes = [{"id": r[0], "dni": r[1], "nombre": r[2]} for r in pacientes]

    rows = fetch_all("""
        SELECT a.id, a.paciente_id, a.fecha, a.peso, a.talla, a.cc, a.bf_pct, a.actividad,
               p.dni,
               COALESCE(pr.nombres || ' ' || pr.apellidos, '') AS nombre
          FROM antropometria a
          JOIN paciente p ON p.id = a.paciente_id
          LEFT JOIN pre_registro pr ON pr.dni = p.dni
         ORDER BY a.fecha DESC, a.id DESC
    """) or []

    out = []
    for r in rows:
        aid, pid, fecha, peso, talla, cc, bf, act, dni, nombre = r
        # calcula IMC si hay peso y talla
        imc = None
        try:
            if peso is not None and talla is not None and float(talla) > 0:
                imc = round(float(peso) / (float(talla) ** 2), 2)
        except Exception:
            imc = None

        out.append({
            "id": aid,
            "paciente_id": pid,
            "fecha": fecha.strftime("%Y-%m-%d"),
            "peso": float(peso) if peso is not None else None,
            "talla": float(talla) if talla is not None else None,
            "cc": float(cc) if cc is not None else None,
            "bf_pct": float(bf) if bf is not None else None,
            "actividad": act,
            "imc": imc,
            "paciente": f"{dni} — {(nombre or '(sin nombre)')}"
        })

    template_base = get_template_base()
    return render_template(
        f"{template_base}/antropometria_list.html",
        rows=out,
        pacientes=pacientes,
        hoy=date.today().strftime("%Y-%m-%d"),
        active_nav="antropometria",
        page_title="NutriSync · Antropometría",
        header_title="Antropometría"
    )


@app.route("/admin/antropometria/nuevo", methods=["POST"])
@admin_required
def admin_antropo_nuevo():
    paciente_id = (request.form.get("paciente_id") or "").strip()
    fecha       = (request.form.get("fecha") or "").strip()

    if not paciente_id or not fecha:
        flash("Paciente y fecha son obligatorios.", "error")
        return redirect(url_for("admin_antropometria"))

    peso   = _num_or_none("peso")     # DECIMAL(6,2)
    talla  = _num_or_none("talla")    # DECIMAL(5,2)
    cc     = _num_or_none("cc")       # DECIMAL(6,2)
    bf_pct = _num_or_none("bf_pct")   # DECIMAL(5,2)
    actividad = _actividad_norm(request.form.get("actividad"))

    execute("""
        INSERT INTO antropometria (paciente_id, fecha, peso, talla, cc, bf_pct, actividad)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (paciente_id, fecha, peso, talla, cc, bf_pct, actividad))

    flash("Registro de antropometría creado.", "success")
    return redirect(url_for("admin_antropometria"))


@app.route("/admin/antropometria/<int:aid>/editar", methods=["POST"])
@admin_required
def admin_antropo_editar(aid):
    row = fetch_one("SELECT id FROM antropometria WHERE id=%s", (aid,))
    if not row:
        flash("El registro no existe.", "error")
        return redirect(url_for("admin_antropometria"))

    paciente_id = (request.form.get("paciente_id") or "").strip()
    fecha       = (request.form.get("fecha") or "").strip()
    if not paciente_id or not fecha:
        flash("Paciente y fecha son obligatorios.", "error")
        return redirect(url_for("admin_antropometria"))

    peso   = _num_or_none("peso")
    talla  = _num_or_none("talla")
    cc     = _num_or_none("cc")
    bf_pct = _num_or_none("bf_pct")
    actividad = _actividad_norm(request.form.get("actividad"))

    execute("""
        UPDATE antropometria
           SET paciente_id=%s,
               fecha=%s,
               peso=%s,
               talla=%s,
               cc=%s,
               bf_pct=%s,
               actividad=%s
         WHERE id=%s
    """, (paciente_id, fecha, peso, talla, cc, bf_pct, actividad, aid))

    flash("Registro de antropometría actualizado.", "success")
    return redirect(url_for("admin_antropometria"))


@app.route("/admin/antropometria/<int:aid>/borrar", methods=["POST"])
@admin_required
def admin_antropo_borrar(aid):
    execute("DELETE FROM antropometria WHERE id=%s", (aid,))
    flash("Registro de antropometría eliminado.", "success")
    return redirect(url_for("admin_antropometria"))



# ========= ADMIN: TOKENS DE ACTIVACIÓN =========

from datetime import timedelta

def _now():
    return datetime.now()

def _vence_en_horas(horas: int) -> datetime:
    return _now() + timedelta(hours=horas)

@app.route("/admin/activaciones")
@admin_required
def admin_activaciones():
    """
    Listado de tokens. Soporta filtro ?q= (por DNI o email parcial).
    """
    q = (request.args.get("q") or "").strip()

    if q:
        rows = fetch_all("""
            SELECT a.dni, a.token,
                   TO_CHAR(a.vence_en,'YYYY-MM-DD HH24:MI') AS vence,
                   a.usado, a.creado_en,
                   COALESCE(pr.nombres,'') AS nombres,
                   COALESCE(pr.apellidos,'') AS apellidos,
                   COALESCE(pr.email,'') AS email
              FROM activacion_token a
              JOIN pre_registro pr ON pr.dni = a.dni
             WHERE a.dni ILIKE %s OR pr.email ILIKE %s
             ORDER BY a.creado_en DESC, a.dni, a.token
        """, (f"%{q}%", f"%{q}%")) or []
    else:
        rows = fetch_all("""
            SELECT a.dni, a.token,
                   TO_CHAR(a.vence_en,'YYYY-MM-DD HH24:MI') AS vence,
                   a.usado, a.creado_en,
                   COALESCE(pr.nombres,'') AS nombres,
                   COALESCE(pr.apellidos,'') AS apellidos,
                   COALESCE(pr.email,'') AS email
              FROM activacion_token a
              JOIN pre_registro pr ON pr.dni = a.dni
             ORDER BY a.creado_en DESC, a.dni, a.token
        """) or []

    tokens = []
    for r in rows:
        dni, token, vence, usado, creado_en, nom, ape, email = r
        link = build_activation_link(dni, token)
        tokens.append({
            "dni": dni,
            "token": token,
            "vence": vence,
            "usado": bool(usado),
            "creado": creado_en.strftime("%Y-%m-%d %H:%M"),
            "nombre": f"{nom} {ape}".strip(),
            "email": email or "",
            "link": link,
            "expirado": _now() > datetime.strptime(vence, "%Y-%m-%d %H:%M")
        })

    template_base = get_template_base()
    return render_template(
        f"{template_base}/activaciones.html",
        tokens=tokens,
        filtro=q,
        horas_default=TOKEN_HORAS_VALIDEZ,
        active_nav="activaciones",
        page_title="NutriSync · Tokens de activación",
        header_title="Tokens de activación"
    )


@app.route("/admin/activaciones/nuevo", methods=["POST"])
@admin_required
def admin_activaciones_nuevo():
    dni = (request.form.get("dni") or "").strip()
    horas_txt = (request.form.get("horas") or "").strip()
    horas = int(horas_txt) if horas_txt.isdigit() and int(horas_txt) > 0 else TOKEN_HORAS_VALIDEZ

    if not (dni.isdigit() and len(dni) == 8):
        flash("DNI inválido (8 dígitos).", "error")
        return redirect(url_for("admin_activaciones"))

    # Debe existir en pre_registro (por FK).
    pre = fetch_one("SELECT nombres, apellidos, telefono, email FROM pre_registro WHERE dni=%s", (dni,))
    if not pre:
        flash("Ese DNI no está en pre_registro.", "error")
        return redirect(url_for("admin_activaciones"))

    nombres, apellidos, telefono, email = pre
    nombre_completo = f"{nombres or ''} {apellidos or ''}".strip()

    tok = str(uuid.uuid4())
    vence = _vence_en_horas(horas)
    link_activacion = build_activation_link(dni, tok)

    # upsert por dni: sustituimos token activo para ese DNI
    execute("""
        INSERT INTO activacion_token (dni, token, vence_en, usado, creado_en, actualizado_en)
        VALUES (%s, %s, %s, FALSE, NOW(), NOW())
        ON CONFLICT (dni) DO UPDATE
           SET token = EXCLUDED.token,
               vence_en = EXCLUDED.vence_en,
               usado = FALSE,
               actualizado_en = NOW()
    """, (dni, tok, vence))

    # Intentar enviar email si hay email configurado
    mensaje_flash = f"Token generado para {dni}: {tok} (vence {vence:%Y-%m-%d %H:%M})"
    
    if email:
        exito, mensaje = enviar_token_activacion(
            dni=dni,
            token=tok,
            link_activacion=link_activacion,
            nombre=nombre_completo,
            email=email,
            telefono=telefono or ""
        )
        if exito:
            flash(f"{mensaje_flash}. ✅ Email enviado a {email}.", "success")
        else:
            # Mostrar el token y el error
            flash(f"{mensaje_flash}", "success")
            flash(f"⚠️ {mensaje}", "error")
            flash(f"📋 Token para enviar manualmente: {tok}", "info")
    else:
        flash(f"{mensaje_flash}. ⚠️ No hay email registrado, el token debe enviarse manualmente.", "warning")
    
    return redirect(url_for("admin_activaciones"))


@app.route("/admin/activaciones/<dni>/<token>/toggle", methods=["POST"])
@admin_required
def admin_activaciones_toggle(dni, token):
    """
    Marca usado <-> no usado para un token específico.
    """
    execute("""
        UPDATE activacion_token
           SET usado = NOT usado, actualizado_en = NOW()
         WHERE dni=%s AND token=%s
    """, (dni, token))
    flash("Estado 'usado' actualizado.", "success")
    return redirect(url_for("admin_activaciones"))


@app.route("/admin/activaciones/<dni>/<token>/borrar", methods=["POST"])
@admin_required
def admin_activaciones_borrar(dni, token):
    execute("DELETE FROM activacion_token WHERE dni=%s AND token=%s", (dni, token))
    flash("Token eliminado.", "success")
    return redirect(url_for("admin_activaciones"))


@app.route("/admin/activaciones/<dni>/regenerar", methods=["POST"])
@admin_required
def admin_activaciones_regenerar(dni):
    """
    Invalida el token actual (si existe) y crea uno nuevo con el mismo plazo (o el default).
    """
    horas_txt = (request.form.get("horas") or "").strip()
    horas = int(horas_txt) if horas_txt.isdigit() and int(horas_txt) > 0 else TOKEN_HORAS_VALIDEZ

    if not (dni.isdigit() and len(dni) == 8):
        flash("DNI inválido (8 dígitos).", "error")
        return redirect(url_for("admin_activaciones"))

    # Obtener datos del preregistro
    pre = fetch_one("SELECT nombres, apellidos, telefono, email FROM pre_registro WHERE dni=%s", (dni,))
    if not pre:
        flash("Ese DNI no está en pre_registro.", "error")
        return redirect(url_for("admin_activaciones"))

    nombres, apellidos, telefono, email = pre
    nombre_completo = f"{nombres or ''} {apellidos or ''}".strip()

    tok = str(uuid.uuid4())
    vence = _vence_en_horas(horas)
    link_activacion = build_activation_link(dni, tok)

    execute("""
        INSERT INTO activacion_token (dni, token, vence_en, usado, creado_en, actualizado_en)
        VALUES (%s, %s, %s, FALSE, NOW(), NOW())
        ON CONFLICT (dni) DO UPDATE
           SET token = EXCLUDED.token,
               vence_en = EXCLUDED.vence_en,
               usado = FALSE,
               actualizado_en = NOW()
    """, (dni, tok, vence))

    # Intentar enviar email si hay email configurado
    mensaje_flash = f"Token regenerado para {dni}: {tok} (vence {vence:%Y-%m-%d %H:%M})"
    
    if email:
        exito, mensaje = enviar_token_activacion(
            dni=dni,
            token=tok,
            link_activacion=link_activacion,
            nombre=nombre_completo,
            email=email,
            telefono=telefono or ""
        )
        if exito:
            flash(f"{mensaje_flash}. ✅ Email enviado a {email}.", "success")
        else:
            # Mostrar el token y el error
            flash(f"{mensaje_flash}", "success")
            flash(f"⚠️ {mensaje}", "error")
            flash(f"📋 Token para enviar manualmente: {tok}", "info")
    else:
        flash(f"{mensaje_flash}. ⚠️ No hay email registrado, el token debe enviarse manualmente.", "warning")
    
    return redirect(url_for("admin_activaciones"))



# ====== ADMIN: INGREDIENTES (CRUD) ======

# Grupos permitidos según la guía de intercambio de alimentos
ING_GRUPOS = ["GRUPO1_CEREALES", "GRUPO2_VERDURAS", "GRUPO3_FRUTAS", "GRUPO4_LACTEOS", "GRUPO5_CARNES", "GRUPO6_AZUCARES", "GRUPO7_GRASAS"]

def _norm_tags(raw: str | None):
    """
    Acepta JSON o texto separado por comas/líneas; devuelve list o None.
    """
    val = _parse_list_or_json(raw)
    if not val:
        return None
    # fuerza lista de strings
    if isinstance(val, dict):
        # si el usuario pega {"a":true} => conviértelo en ["a"]
        val = [k for k, v in val.items() if v]
    return [str(x).strip() for x in val if str(x).strip()] or None


@app.route("/admin/ingredientes")
@admin_required
def admin_ingredientes():
    rows = fetch_all("""
        SELECT id, nombre, grupo, kcal, cho, pro, fat, fibra,
               ig, sodio, costo, unidad_base, porcion_base, tags_json, activo
          FROM ingrediente
         ORDER BY nombre
    """) or []

    def _fmt(r):
        tags = r[13]
        # psycopg puede traer jsonb como list o str:
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except Exception:
                tags = None
        tags = tags or []
        tags_text = ", ".join([str(x) for x in tags]) if isinstance(tags, list) else ""
        return {
            "id": r[0],
            "nombre": r[1],
            "grupo": r[2],
            "kcal": r[3],
            "cho": r[4],
            "pro": r[5],
            "fat": r[6],
            "fibra": r[7],
            "ig": r[8],
            "sodio": r[9],
            "costo": r[10],
            "unidad_base": r[11],
            "porcion_base": r[12],
            "tags_full": tags_text,
            "tags_text": tags_text,
            "activo": bool(r[14]),
        }

    rows = [_fmt(r) for r in rows]

    template_base = get_template_base()
    return render_template(
        f"{template_base}/ingredientes_list.html",
        rows=rows,
        grupos=ING_GRUPOS,
        active_nav="ingredientes",
        page_title="NutriSync · Ingredientes",
        header_title="Ingredientes"
    )


@app.route("/api/ingredientes/nuevo", methods=["POST"])
@admin_required
def api_ing_nuevo():
    """Endpoint API para crear ingrediente desde el modal"""
    try:
        nombre = (request.form.get("nombre") or "").strip()
        grupo  = (request.form.get("grupo") or "GRUPO6_AZUCARES").strip().upper()

        if not nombre or grupo not in ING_GRUPOS:
            return {"ok": False, "error": "Nombre y grupo son obligatorios (grupo válido)."}

        # únicos y numéricos (opcionales)
        kcal   = _to_decimal(request.form.get("kcal"))
        cho    = _to_decimal(request.form.get("cho"))
        pro    = _to_decimal(request.form.get("pro"))
        fat    = _to_decimal(request.form.get("fat"))
        fibra  = _to_decimal(request.form.get("fibra"))
        ig     = request.form.get("ig") or None
        ig     = int(ig) if ig not in (None, "") else None
        sodio  = _to_decimal(request.form.get("sodio"))
        costo  = _to_decimal(request.form.get("costo"))
        unidad = (request.form.get("unidad_base") or "").strip() or None
        porcion= _to_decimal(request.form.get("porcion_base"))
        tags   = _norm_tags(request.form.get("tags_json"))
        activo = "activo" in request.form

        # evitar duplicado por nombre (tienes UK en DB)
        dup = fetch_one("SELECT 1 FROM ingrediente WHERE LOWER(nombre)=LOWER(%s)", (nombre,))
        if dup:
            return {"ok": False, "error": "Ya existe un ingrediente con ese nombre."}

        execute("""
            INSERT INTO ingrediente
            (nombre, grupo, kcal, cho, pro, fat, fibra, ig, sodio, costo,
             unidad_base, porcion_base, tags_json, activo)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (nombre, grupo, kcal, cho, pro, fat, fibra, ig, sodio, costo,
              unidad, porcion, json.dumps(tags) if tags else None, activo))

        return {"ok": True, "message": "Ingrediente creado correctamente."}
        
    except Exception as e:
        return {"ok": False, "error": f"Error interno: {str(e)}"}


@app.route("/admin/ingredientes/nuevo", methods=["POST"])
@admin_required
def admin_ing_nuevo():
    nombre = (request.form.get("nombre") or "").strip()
    grupo  = (request.form.get("grupo") or "GRUPO6_AZUCARES").strip().upper()

    if not nombre or grupo not in ING_GRUPOS:
        flash("Nombre y grupo son obligatorios (grupo válido).", "error")
        return redirect(url_for("admin_ingredientes"))

    # únicos y numéricos (opcionales)
    kcal   = _to_decimal(request.form.get("kcal"))
    cho    = _to_decimal(request.form.get("cho"))
    pro    = _to_decimal(request.form.get("pro"))
    fat    = _to_decimal(request.form.get("fat"))
    fibra  = _to_decimal(request.form.get("fibra"))
    ig     = request.form.get("ig") or None
    ig     = int(ig) if ig not in (None, "") else None
    sodio  = _to_decimal(request.form.get("sodio"))
    costo  = _to_decimal(request.form.get("costo"))
    unidad = (request.form.get("unidad_base") or "").strip() or None
    porcion= _to_decimal(request.form.get("porcion_base"))
    tags   = _norm_tags(request.form.get("tags_json"))
    activo = "activo" in request.form

    # evitar duplicado por nombre (tienes UK en DB)
    dup = fetch_one("SELECT 1 FROM ingrediente WHERE LOWER(nombre)=LOWER(%s)", (nombre,))
    if dup:
        flash("Ya existe un alimento con ese nombre.", "error")
        return redirect(url_for("admin_ingredientes"))

    execute("""
        INSERT INTO ingrediente
        (nombre, grupo, kcal, cho, pro, fat, fibra, ig, sodio, costo,
         unidad_base, porcion_base, tags_json, activo)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (nombre, grupo, kcal, cho, pro, fat, fibra, ig, sodio, costo,
          unidad, porcion, json.dumps(tags) if tags else None, activo))

    flash("Alimento creado.", "success")
    return redirect(url_for("admin_ingredientes"))


@app.route("/api/ingredientes/<int:iid>/editar", methods=["POST"])
@admin_required
def api_ing_editar(iid):
    """Endpoint API para editar ingrediente desde el modal de detalle"""
    try:
        row = fetch_one("SELECT id FROM ingrediente WHERE id=%s", (iid,))
        if not row:
            return {"ok": False, "error": "El alimento no existe."}

        nombre = (request.form.get("nombre") or "").strip()
        grupo  = (request.form.get("grupo") or "GRUPO6_AZUCARES").strip().upper()

        if not nombre or grupo not in ING_GRUPOS:
            return {"ok": False, "error": "Nombre y grupo son obligatorios (grupo válido)."}

        # si cambió nombre, valida duplicado
        dup = fetch_one("SELECT 1 FROM ingrediente WHERE LOWER(nombre)=LOWER(%s) AND id<>%s", (nombre, iid))
        if dup:
            return {"ok": False, "error": "Ya existe otro ingrediente con ese nombre."}

        kcal   = _to_decimal(request.form.get("kcal"))
        cho    = _to_decimal(request.form.get("cho"))
        pro    = _to_decimal(request.form.get("pro"))
        fat    = _to_decimal(request.form.get("fat"))
        fibra  = _to_decimal(request.form.get("fibra"))
        ig     = request.form.get("ig") or None
        ig     = int(ig) if ig not in (None, "") else None
        sodio  = _to_decimal(request.form.get("sodio"))
        costo  = _to_decimal(request.form.get("costo"))
        unidad = (request.form.get("unidad_base") or "").strip() or None
        porcion= _to_decimal(request.form.get("porcion_base"))
        tags   = _norm_tags(request.form.get("tags_json"))
        activo = "activo" in request.form

        execute("""
            UPDATE ingrediente
               SET nombre=%s, grupo=%s, kcal=%s, cho=%s, pro=%s, fat=%s, fibra=%s,
                   ig=%s, sodio=%s, costo=%s, unidad_base=%s, porcion_base=%s,
                   tags_json=%s, activo=%s
             WHERE id=%s
        """, (nombre, grupo, kcal, cho, pro, fat, fibra,
              ig, sodio, costo, unidad, porcion,
              json.dumps(tags) if tags else None, activo, iid))

        return {"ok": True, "message": "Ingrediente actualizado correctamente."}
        
    except Exception as e:
        return {"ok": False, "error": f"Error interno: {str(e)}"}


@app.route("/admin/ingredientes/<int:iid>/editar", methods=["POST"])
@admin_required
def admin_ing_editar(iid):
    row = fetch_one("SELECT id FROM ingrediente WHERE id=%s", (iid,))
    if not row:
        flash("El alimento no existe.", "error")
        return redirect(url_for("admin_ingredientes"))

    nombre = (request.form.get("nombre") or "").strip()
    grupo  = (request.form.get("grupo") or "GRUPO6_AZUCARES").strip().upper()

    if not nombre or grupo not in ING_GRUPOS:
        flash("Nombre y grupo son obligatorios (grupo válido).", "error")
        return redirect(url_for("admin_ingredientes"))

    # si cambió nombre, valida duplicado
    dup = fetch_one("SELECT 1 FROM ingrediente WHERE LOWER(nombre)=LOWER(%s) AND id<>%s", (nombre, iid))
    if dup:
        flash("Ya existe otro alimento con ese nombre.", "error")
        return redirect(url_for("admin_ingredientes"))

    kcal   = _to_decimal(request.form.get("kcal"))
    cho    = _to_decimal(request.form.get("cho"))
    pro    = _to_decimal(request.form.get("pro"))
    fat    = _to_decimal(request.form.get("fat"))
    fibra  = _to_decimal(request.form.get("fibra"))
    ig     = request.form.get("ig") or None
    ig     = int(ig) if ig not in (None, "") else None
    sodio  = _to_decimal(request.form.get("sodio"))
    costo  = _to_decimal(request.form.get("costo"))
    unidad = (request.form.get("unidad_base") or "").strip() or None
    porcion= _to_decimal(request.form.get("porcion_base"))
    tags   = _norm_tags(request.form.get("tags_json"))
    activo = "activo" in request.form

    execute("""
        UPDATE ingrediente
           SET nombre=%s, grupo=%s, kcal=%s, cho=%s, pro=%s, fat=%s, fibra=%s,
               ig=%s, sodio=%s, costo=%s, unidad_base=%s, porcion_base=%s,
               tags_json=%s, activo=%s
         WHERE id=%s
    """, (nombre, grupo, kcal, cho, pro, fat, fibra,
          ig, sodio, costo, unidad, porcion,
          json.dumps(tags) if tags else None, activo, iid))

    flash("Alimento actualizado.", "success")
    return redirect(url_for("admin_ingredientes"))


@app.route("/admin/ingredientes/<int:iid>/toggle", methods=["POST"])
@admin_required
def admin_ing_toggle(iid):
    execute("UPDATE ingrediente SET activo = NOT activo WHERE id=%s", (iid,))
    flash("Estado de alimento actualizado.", "success")
    return redirect(url_for("admin_ingredientes"))


@app.route("/admin/ingredientes/<int:iid>/borrar", methods=["POST"])
@admin_required
def admin_ing_borrar(iid):
    # Verificar si el ingrediente está siendo usado en plan_alimento
    uso = fetch_one("""
        SELECT COUNT(*) FROM plan_alimento WHERE ingrediente_id = %s
    """, (iid,))
    
    if uso and uso[0] > 0:
        flash(f"No se puede eliminar el alimento porque está siendo usado en {uso[0]} plan(es) de alimentación.", "error")
        return redirect(url_for("admin_ingredientes"))
    
    # Verificar si existe el ingrediente
    ingrediente = fetch_one("SELECT nombre FROM ingrediente WHERE id = %s", (iid,))
    if not ingrediente:
        flash("El alimento no existe.", "error")
        return redirect(url_for("admin_ingredientes"))
    
    try:
        execute("DELETE FROM ingrediente WHERE id=%s", (iid,))
        flash("Alimento eliminado correctamente.", "success")
    except Exception as e:
        # Capturar cualquier otro error de clave foránea (por si hay otras referencias)
        flash(f"No se puede eliminar el alimento: está siendo usado en el sistema.", "error")
    
    return redirect(url_for("admin_ingredientes"))




# ========= ADMIN: PLANES =========

def _short_json(txt: str | None, limit: int = 48) -> str:
    if not txt:
        return ""
    s = (txt or "").strip().replace("\n", " ")
    return s if len(s) <= limit else s[:limit-3] + "..."

def _get_ingredientes_combo():
    rows = fetch_all("""
        SELECT id, nombre, unidad_base, porcion_base
        FROM ingrediente
        WHERE activo = TRUE
        ORDER BY nombre
    """) or []
    return [
        {
            "id": r[0],
            "nombre": r[1],
            "unidad_base": r[2],
            "porcion_base": float(r[3]) if r[3] is not None else None,
        }
        for r in rows
    ]

def _get_pacientes_combo():
    rows = fetch_all("""
        SELECT p.id,
               p.dni,
               COALESCE(pr.nombres || ' ' || pr.apellidos, '') AS nombre
          FROM paciente p
          LEFT JOIN pre_registro pr ON pr.dni = p.dni
         ORDER BY p.id DESC
    """) or []
    # rows: [(id, dni, nombre), ...]
    return [
        {"id": r[0], "dni": r[1], "nombre": r[2]}
        for r in rows
    ]  # list[dict]


def _get_ingredientes_combo():
    rows = fetch_all("""
        SELECT id, nombre, unidad_base, porcion_base
        FROM ingrediente
        WHERE activo = TRUE
        ORDER BY nombre
    """) or []

    # rows = [(id, nombre, unidad_base, porcion_base), ...]
    return [
        {
            "id": r[0],
            "nombre": r[1],
            "unidad_base": r[2],
            "porcion_base": float(r[3]) if r[3] is not None else None,  # opcional: castear Decimal
        }
        for r in rows
    ]


@app.route("/admin/planes")
@admin_required
def admin_planes():
    # Listado planes con información completa del paciente - agrupados por paciente
    rows = fetch_all("""
        SELECT pl.id, pl.paciente_id,
               TO_CHAR(pl.fecha_ini,'YYYY-MM-DD') AS fi,
               TO_CHAR(pl.fecha_fin,'YYYY-MM-DD') AS ff,
               pl.estado, pl.metas_json,
               p.dni,
               COALESCE(pr.nombres || ' ' || pr.apellidos, 'Sin nombre') AS nombre,
               pr.nombres,
               pr.apellidos,
               p.fecha_nac,
               EXTRACT(YEAR FROM AGE(p.fecha_nac)) AS edad
          FROM plan pl
          JOIN paciente p ON p.id = pl.paciente_id
          LEFT JOIN pre_registro pr ON pr.dni = p.dni
         ORDER BY p.dni, pl.fecha_ini DESC, pl.id DESC
    """) or []
    
    # Agrupar planes por paciente
    pacientes_dict = {}
    for r in rows:
        paciente_id = r[1]
        
        # Si es la primera vez que vemos este paciente, crear entrada
        if paciente_id not in pacientes_dict:
            # Calcular edad si hay fecha de nacimiento
            edad_str = None
            if r[10]:  # fecha_nac
                try:
                    edad = int(r[11]) if r[11] else None
                    if edad is not None:
                        edad_str = str(edad)
                except:
                    pass
            
            # Formatear nombre completo
            nombre_completo = r[7] or "Sin nombre"
            if r[8] and r[9]:  # nombres y apellidos separados
                nombre_completo = f"{r[8]} {r[9]}"
            elif r[8]:
                nombre_completo = r[8]
            elif r[9]:
                nombre_completo = r[9]
            
            pacientes_dict[paciente_id] = {
                "paciente_id": paciente_id,
                "paciente_nombre": nombre_completo,
                "paciente_dni": r[6],
                "paciente_edad": edad_str,
                "planes": []
            }
        
        # Agregar plan a la lista del paciente
        plan_data = {
            "id": r[0],
            "fecha_ini": r[2],
            "fecha_fin": r[3],
            "estado": r[4],
            "metas_json": r[5] if isinstance(r[5], str) else (None if r[5] is None else json.dumps(r[5])),
            "metas_json_short": _short_json(r[5] if isinstance(r[5], str) else json.dumps(r[5]) if r[5] is not None else "", 40),
        }
        pacientes_dict[paciente_id]["planes"].append(plan_data)
    
    # Convertir a lista ordenada por nombre de paciente
    pacientes_agrupados = sorted(pacientes_dict.values(), key=lambda x: x["paciente_nombre"])
    
    # Mantener compatibilidad: también pasar planes planos para el template si es necesario
    planes = []
    for paciente in pacientes_agrupados:
        for plan in paciente["planes"]:
            planes.append({
                **plan,
                "paciente_id": paciente["paciente_id"],
                "paciente_nombre": paciente["paciente_nombre"],
                "paciente_dni": paciente["paciente_dni"],
                "paciente_edad": paciente["paciente_edad"],
            })

    template_base = get_template_base()
    return render_template(
        f"{template_base}/planes.html",
        planes=planes,  # Mantener para compatibilidad
        pacientes_agrupados=pacientes_agrupados,  # Nueva estructura agrupada
        pacientes=_get_pacientes_combo(),
        ingredientes=_get_ingredientes_combo(),
        plan_sel=None,
        detalles=[],
        active_nav="planes",
        page_title="NutriSync · Planes",
        header_title="Planes"
    )

@app.route("/admin/aprendizaje/verificar/<int:plan_id>")
@admin_required
def admin_aprendizaje_verificar(plan_id):
    """Verifica si un plan tiene baseline registrado para aprendizaje"""
    try:
        from Core.bd_conexion import fetch_one, fetch_all
        import psycopg
        
        # Primero verificar si la tabla existe
        try:
            tabla_existe = fetch_one("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'plan_resultado'
                )
            """)
            
            if not tabla_existe or not tabla_existe[0]:
                return jsonify({
                    "ok": False,
                    "baseline_registrado": False,
                    "error": "tabla_no_existe",
                    "mensaje": "La tabla 'plan_resultado' no existe. Ejecuta: psql -U postgres -d proyecto_tesis -f SQL/aprendizaje_continuo.sql"
                })
        except Exception as e:
            return jsonify({
                "ok": False,
                "baseline_registrado": False,
                "error": "error_verificando_tabla",
                "mensaje": f"Error verificando tabla: {str(e)}"
            })
        
        # Verificar baseline
        resultado = fetch_one("""
            SELECT id, paciente_id, fecha_inicio, estado,
                   hba1c_inicial, glucosa_inicial, peso_inicial, imc_inicial,
                   fecha_fin, hba1c_final, glucosa_final, peso_final,
                   cumplimiento_pct, satisfaccion, creado_en
            FROM plan_resultado
            WHERE plan_id = %s
            ORDER BY creado_en DESC
            LIMIT 1
        """, (plan_id,))
        
        if resultado:
            # Calcular resultado_exitoso basado en mejoras (si hay datos finales)
            resultado_exitoso = None
            if resultado[8] and resultado[4] and resultado[9]:  # fecha_fin, hba1c_inicial, hba1c_final
                # Si hay mejora en HbA1c (disminución) o peso (disminución si es objetivo)
                mejora_hba1c = float(resultado[4]) - float(resultado[9]) if resultado[9] else None
                if mejora_hba1c is not None:
                    resultado_exitoso = mejora_hba1c > 0  # True si mejoró (disminuyó HbA1c)
            
            return jsonify({
                "ok": True,
                "baseline_registrado": True,
                "datos": {
                    "resultado_id": resultado[0],
                    "paciente_id": resultado[1],
                    "fecha_inicio": str(resultado[2]),
                    "estado": resultado[3],
                    "hba1c_inicial": float(resultado[4]) if resultado[4] else None,
                    "glucosa_inicial": float(resultado[5]) if resultado[5] else None,
                    "peso_inicial": float(resultado[6]) if resultado[6] else None,
                    "imc_inicial": float(resultado[7]) if resultado[7] else None,
                    "fecha_fin": str(resultado[8]) if resultado[8] else None,
                    "hba1c_final": float(resultado[9]) if resultado[9] else None,
                    "glucosa_final": float(resultado[10]) if resultado[10] else None,
                    "peso_final": float(resultado[11]) if resultado[11] else None,
                    "cumplimiento_pct": float(resultado[12]) if resultado[12] else None,
                    "satisfaccion": int(resultado[13]) if resultado[13] else None,
                    "resultado_exitoso": resultado_exitoso,
                    "creado_en": str(resultado[14])
                }
            })
        else:
            return jsonify({
                "ok": True,
                "baseline_registrado": False,
                "mensaje": "No hay baseline registrado para este plan"
            })
    except psycopg.errors.UndefinedTable as e:
        return jsonify({
            "ok": False,
            "baseline_registrado": False,
            "error": "tabla_no_existe",
            "mensaje": f"La tabla 'plan_resultado' no existe. Ejecuta: psql -U postgres -d proyecto_tesis -f SQL/aprendizaje_continuo.sql"
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "tipo": type(e).__name__}), 500

@app.route("/admin/aprendizaje/estadisticas")
@admin_required
def admin_aprendizaje_estadisticas():
    """Muestra estadísticas del aprendizaje continuo"""
    try:
        from Core.bd_conexion import fetch_one, fetch_all
        from aprendizaje.aprendizaje_continuo import obtener_aprendizaje
        
        aprendizaje = obtener_aprendizaje()
        
        # Contar resultados
        total_resultados = fetch_one("SELECT COUNT(*) FROM plan_resultado")[0] or 0
        completados = fetch_one("SELECT COUNT(*) FROM plan_resultado WHERE estado='completado'")[0] or 0
        pendientes = fetch_one("SELECT COUNT(*) FROM plan_resultado WHERE estado='pendiente'")[0] or 0
        
        # Contar patrones
        total_patrones = fetch_one("SELECT COUNT(*) FROM aprendizaje_patron")[0] or 0
        ingredientes_exitosos = fetch_one("""
            SELECT COUNT(*) FROM aprendizaje_patron 
            WHERE tipo_patron = 'ingrediente_exitoso'
        """)[0] or 0
        
        # Top ingredientes
        top_ingredientes = fetch_all("""
            SELECT elemento_nombre, confianza, veces_observado, veces_exitoso
            FROM aprendizaje_patron
            WHERE tipo_patron = 'ingrediente_exitoso'
            ORDER BY confianza DESC, veces_observado DESC
            LIMIT 5
        """) or []
        
        return jsonify({
            "ok": True,
            "habilitado": aprendizaje.habilitado,
            "resultados": {
                "total": total_resultados,
                "completados": completados,
                "pendientes": pendientes
            },
            "patrones": {
                "total": total_patrones,
                "ingredientes_exitosos": ingredientes_exitosos,
                "top_ingredientes": [
                    {
                        "nombre": ing[0],
                        "confianza": float(ing[1]),
                        "veces_observado": ing[2],
                        "veces_exitoso": ing[3]
                    }
                    for ing in top_ingredientes
                ]
            }
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/admin/planes/<int:pid>")
@admin_required
def admin_plan_ver(pid):
    # cabecera
    pl = fetch_one("""
        SELECT pl.id, pl.paciente_id,
               TO_CHAR(pl.fecha_ini,'YYYY-MM-DD') AS fi,
               TO_CHAR(pl.fecha_fin,'YYYY-MM-DD') AS ff,
               pl.estado, pl.metas_json,
               p.dni,
               COALESCE(pr.nombres || ' ' || pr.apellidos, '') AS nombre
          FROM plan pl
          JOIN paciente p ON p.id = pl.paciente_id
          LEFT JOIN pre_registro pr ON pr.dni = p.dni
         WHERE pl.id = %s
    """, (pid,))
    if not pl:
        flash("El plan no existe.", "error")
        return redirect(url_for("admin_planes"))

    # Parsear metas_json si es string, mantener como dict si ya lo es
    metas_json_parsed = None
    if pl[5]:
        if isinstance(pl[5], str):
            try:
                metas_json_parsed = json.loads(pl[5])
            except:
                metas_json_parsed = {}
        else:
            metas_json_parsed = pl[5]
    
    plan_sel = {
        "id": pl[0],
        "paciente_id": pl[1],
        "fecha_ini": pl[2],
        "fecha_fin": pl[3],
        "estado": pl[4],
        "metas_json": pl[5] if isinstance(pl[5], str) else (json.dumps(pl[5]) if pl[5] is not None else ""),
        "metas_json_parsed": metas_json_parsed,  # Versión parseada para usar en el template
        "paciente": f"{pl[6]} — {(pl[7] or '(sin nombre)')}",
        "paciente_dni": pl[6],
        "paciente_nombre": pl[7] or "Sin nombre",
    }
    
    # Obtener datos del paciente para el resumen
    paciente_id = pl[1]
    
    # Datos básicos del paciente
    p_data = fetch_one("""
        SELECT p.sexo, TO_CHAR(p.fecha_nac,'YYYY-MM-DD') AS fecha_nac,
               p.telefono, u.email AS usuario_email,
               COALESCE(pr.nombres,'') AS nombres, COALESCE(pr.apellidos,'') AS apellidos
          FROM paciente p
          LEFT JOIN usuario u ON u.id = p.usuario_id
          LEFT JOIN pre_registro pr ON pr.dni = p.dni
         WHERE p.id=%s
    """, (paciente_id,))
    
    # Última antropometría
    antropo = fetch_one("""
        SELECT peso, talla, cc, bf_pct, actividad, TO_CHAR(fecha,'YYYY-MM-DD') AS fecha_medicion
          FROM antropometria
         WHERE paciente_id=%s
         ORDER BY fecha DESC LIMIT 1
    """, (paciente_id,))
    
    # Últimos datos clínicos
    clinico = fetch_one("""
        SELECT hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia, TO_CHAR(fecha,'YYYY-MM-DD') AS fecha_medicion
          FROM clinico
         WHERE paciente_id=%s
         ORDER BY fecha DESC LIMIT 1
    """, (paciente_id,))
    
    # Calcular IMC si hay peso y talla
    imc = None
    if antropo and antropo[0] and antropo[1]:
        try:
            imc = round(float(antropo[0]) / (float(antropo[1]) ** 2), 2)
        except:
            pass
    
    # Calcular edad si hay fecha de nacimiento
    edad = None
    if p_data and p_data[1]:
        try:
            from datetime import date
            fecha_nac = date.fromisoformat(p_data[1])
            edad = (date.today() - fecha_nac).days // 365
        except:
            pass
    
    # Preparar datos del paciente para el template
    paciente_resumen = {
        "dni": pl[6],
        "nombre": pl[7] or "Sin nombre",
        "nombres": p_data[4] if p_data else "",
        "apellidos": p_data[5] if p_data else "",
        "sexo": p_data[0] if p_data else None,
        "fecha_nac": p_data[1] if p_data else None,
        "edad": edad,
        "telefono": p_data[2] if p_data else None,
        "email": p_data[3] if p_data else None,
        "antropometria": {
            "peso": antropo[0] if antropo else None,
            "talla": antropo[1] if antropo else None,
            "cc": antropo[2] if antropo else None,
            "bf_pct": antropo[3] if antropo else None,
            "actividad": antropo[4] if antropo else None,
            "fecha_medicion": antropo[5] if antropo else None,
            "imc": imc
        },
        "clinico": {
            "hba1c": clinico[0] if clinico else None,
            "glucosa_ayunas": clinico[1] if clinico else None,
            "ldl": clinico[2] if clinico else None,
            "trigliceridos": clinico[3] if clinico else None,
            "pa_sis": clinico[4] if clinico else None,
            "pa_dia": clinico[5] if clinico else None,
            "fecha_medicion": clinico[6] if clinico else None
        }
    }

    # detalles + alimentos - organizados por día y tiempo
    drows = fetch_all("""
        SELECT d.id,
               TO_CHAR(d.dia,'YYYY-MM-DD') AS dia,
               d.tiempo
          FROM plan_detalle d
         WHERE d.plan_id = %s
         ORDER BY d.dia, 
                  CASE d.tiempo 
                      WHEN 'des' THEN 1
                      WHEN 'mm' THEN 2
                      WHEN 'alm' THEN 3
                      WHEN 'mt' THEN 4
                      WHEN 'cena' THEN 5
                      ELSE 6
                  END,
                  d.id
    """, (pid,)) or []

    # Organizar por día
    plan_por_dia = {}
    detalles_dict = {}  # Para mantener referencia a los detalles por ID
    
    for d in drows:
        detalle_id = d[0]
        dia = d[1]
        tiempo = d[2]
        
        if dia not in plan_por_dia:
            plan_por_dia[dia] = {}
        
        arows = fetch_all("""
            SELECT a.id, a.ingrediente_id, i.nombre, i.grupo,
                   a.cantidad, a.unidad,
                   a.kcal, a.cho, a.pro, a.fat, a.fibra, a.cg, i.ig
              FROM plan_alimento a
              JOIN ingrediente i ON i.id = a.ingrediente_id
             WHERE a.plan_detalle_id = %s
             ORDER BY a.id
        """, (detalle_id,)) or []
        
        alimentos = [{
            "id": x[0], "ingrediente_id": x[1], "ingrediente": x[2], "grupo": x[3],
            "cantidad": x[4], "unidad": x[5],
            "kcal": x[6], "cho": x[7], "pro": x[8], "fat": x[9], "fibra": x[10], "cg": x[11], "ig": x[12],
        } for x in arows]
        
        plan_por_dia[dia][tiempo] = {
            "detalle_id": detalle_id,
            "alimentos": alimentos
        }
        detalles_dict[detalle_id] = {"id": detalle_id, "dia": dia, "tiempo": tiempo, "alimentos": alimentos}
    
    # Mantener formato antiguo para compatibilidad
    detalles = []
    for d in drows:
        detalles.append(detalles_dict.get(d[0], {"id": d[0], "dia": d[1], "tiempo": d[2], "alimentos": []}))

    return render_template(
        "admin/planes.html",
        planes=[],                      # ocultamos la tabla principal si estás dentro del plan
        plan_sel=plan_sel,
        detalles=detalles,
        plan_por_dia=plan_por_dia,     # Nuevo formato organizado por día
        pacientes=_get_pacientes_combo(),
        ingredientes=_get_ingredientes_combo(),
        paciente_resumen=paciente_resumen,  # Datos del paciente para el resumen
        active_nav="planes",
        page_title=f"NutriSync · Plan #{pid}",
        header_title="Plan"
    )

# ---- CRUD Plan
@app.route("/admin/planes/nuevo", methods=["POST"])
@admin_required
def admin_plan_nuevo():
    pac_id   = (request.form.get("paciente_id") or "").strip()
    fi       = (request.form.get("fecha_ini") or "").strip()
    ff       = (request.form.get("fecha_fin") or "").strip()
    estado   = (request.form.get("estado") or "borrador").strip()
    metas    = (request.form.get("metas_json") or "").strip()

    metas_json = None
    if metas:
        try:
            metas_json = json.loads(metas)
        except Exception:
            flash("Metas JSON inválidas (se guardó vacío).", "info")

    if not pac_id or not fi or not ff:
        flash("Paciente e intervalo de fechas son obligatorios.", "error")
        return redirect(url_for("admin_planes"))

    pid = fetch_one("""
        INSERT INTO plan (paciente_id, metas_json, fecha_ini, fecha_fin, estado)
        VALUES (%s,%s,%s,%s,%s) RETURNING id
    """, (pac_id, json.dumps(metas_json) if metas_json is not None else None, fi, ff, estado))[0]

    flash("Plan creado.", "success")
    return redirect(url_for("admin_plan_ver", pid=pid))

@app.route("/admin/planes/<int:pid>/editar", methods=["POST"])
@admin_required
def admin_plan_editar(pid):
    pac_id   = (request.form.get("paciente_id") or "").strip()
    fi       = (request.form.get("fecha_ini") or "").strip()
    ff       = (request.form.get("fecha_fin") or "").strip()
    estado   = (request.form.get("estado") or "borrador").strip()
    metas    = (request.form.get("metas_json") or "").strip()

    metas_json = None
    if metas:
        try:
            metas_json = json.loads(metas)
        except Exception:
            flash("Metas JSON inválidas (se guardó vacío).", "info")

    execute("""
        UPDATE plan
           SET paciente_id=%s,
               metas_json=%s,
               fecha_ini=%s,
               fecha_fin=%s,
               estado=%s,
               actualizado_en=NOW()
         WHERE id=%s
    """, (pac_id, json.dumps(metas_json) if metas_json is not None else None, fi, ff, estado, pid))

    flash("Plan actualizado.", "success")
    return redirect(url_for("admin_plan_ver", pid=pid))

@app.route("/admin/planes/<int:pid>/guardar", methods=["POST"])
@admin_required
def admin_plan_guardar(pid):
    """Guarda el plan como borrador"""
    execute("""
        UPDATE plan
           SET estado='borrador',
               actualizado_en=NOW()
         WHERE id=%s
    """, (pid,))
    flash("Plan guardado como borrador.", "success")
    return redirect(url_for("admin_plan_ver", pid=pid))

@app.route("/admin/planes/<int:pid>/publicar", methods=["POST"])
@admin_required
def admin_plan_publicar(pid):
    """Publica el plan (cambia estado a activo)"""
    execute("""
        UPDATE plan
           SET estado='activo',
               actualizado_en=NOW()
         WHERE id=%s
    """, (pid,))
    flash("Plan publicado exitosamente.", "success")
    return redirect(url_for("admin_plan_ver", pid=pid))

@app.route("/admin/planes/<int:pid>/borrar", methods=["POST"])
@admin_required
def admin_plan_borrar(pid):
    execute("DELETE FROM plan WHERE id=%s", (pid,))
    flash("Plan eliminado.", "success")
    return redirect(url_for("admin_planes"))

# ---- CRUD Detalle (día/tiempo)
@app.route("/admin/planes/<int:pid>/detalle/nuevo", methods=["POST"])
@admin_required
def admin_plan_detalle_nuevo(pid):
    dia    = (request.form.get("dia") or "").strip()
    tiempo = (request.form.get("tiempo") or "").strip()
    if not dia or not tiempo:
        flash("Día y tiempo son obligatorios.", "error")
        return redirect(url_for("admin_plan_ver", pid=pid))

    execute("""
        INSERT INTO plan_detalle (plan_id, dia, tiempo)
        VALUES (%s,%s,%s)
    """, (pid, dia, tiempo))
    flash("Tiempo agregado.", "success")
    return redirect(url_for("admin_plan_ver", pid=pid))

@app.route("/admin/plan-detalle/<int:did>/editar", methods=["POST"])
@admin_required
def admin_plan_detalle_editar(did):
    row = fetch_one("SELECT plan_id FROM plan_detalle WHERE id=%s", (did,))
    if not row:
        flash("El slot no existe.", "error")
        return redirect(url_for("admin_planes"))
    pid = row[0]
    dia    = (request.form.get("dia") or "").strip()
    tiempo = (request.form.get("tiempo") or "").strip()
    execute("""
        UPDATE plan_detalle SET dia=%s, tiempo=%s WHERE id=%s
    """, (dia, tiempo, did))
    flash("Tiempo actualizado.", "success")
    return redirect(url_for("admin_plan_ver", pid=pid))

@app.route("/admin/plan-detalle/<int:did>/borrar", methods=["POST"])
@admin_required
def admin_plan_detalle_borrar(did):
    row = fetch_one("SELECT plan_id FROM plan_detalle WHERE id=%s", (did,))
    if not row:
        flash("El slot no existe.", "error")
        return redirect(url_for("admin_planes"))
    pid = row[0]
    execute("DELETE FROM plan_detalle WHERE id=%s", (did,))
    flash("Tiempo eliminado.", "success")
    return redirect(url_for("admin_plan_ver", pid=pid))

# ---- CRUD Alimento
@app.route("/admin/plan-alimento/<int:did>/nuevo", methods=["POST"])
@admin_required
def admin_plan_alimento_nuevo(did):
    row = fetch_one("SELECT plan_id FROM plan_detalle WHERE id=%s", (did,))
    if not row:
        flash("El slot no existe.", "error")
        return redirect(url_for("admin_planes"))
    pid = row[0]

    ing   = (request.form.get("ingrediente_id") or "").strip()
    cant  = (request.form.get("cantidad") or "").strip()
    uni   = (request.form.get("unidad") or "g").strip()

    def _num(name):
        v = (request.form.get(name) or "").strip()
        return float(v) if v else None

    kcal=_num("kcal"); cho=_num("cho"); pro=_num("pro"); fat=_num("fat"); fibra=_num("fibra"); cg=_num("cg")

    if not ing or not cant:
        flash("Ingrediente y cantidad son obligatorios.", "error")
        return redirect(url_for("admin_plan_ver", pid=pid))

    # Si no se proporcionaron valores nutricionales, calcularlos desde el ingrediente
    if kcal is None or cho is None or pro is None or fat is None:
        ing_data = fetch_one("""
            SELECT kcal, cho, pro, fat, fibra, ig, unidad_base, porcion_base
            FROM ingrediente
            WHERE id=%s
        """, (ing,))
        
        if ing_data:
            # Obtener valores por 100g del ingrediente
            kcal_100g = float(ing_data[0] or 0)
            cho_100g = float(ing_data[1] or 0)
            pro_100g = float(ing_data[2] or 0)
            fat_100g = float(ing_data[3] or 0)
            fibra_100g = float(ing_data[4] or 0)
            ig_val = float(ing_data[5] or 0) if ing_data[5] else None
            
            # Convertir cantidad a gramos si es necesario
            cantidad_g = float(cant)
            if uni and uni.lower() != 'g':
                # Si la unidad no es gramos, asumir que la cantidad ya está en la unidad base
                # Por ahora, usar la cantidad directamente (se puede mejorar con conversiones)
                pass
            
            # Calcular factor de conversión (cantidad / 100g)
            factor = cantidad_g / 100.0
            
            # Calcular valores nutricionales
            if kcal is None:
                kcal = round(kcal_100g * factor, 2)
            if cho is None:
                cho = round(cho_100g * factor, 2)
            if pro is None:
                pro = round(pro_100g * factor, 2)
            if fat is None:
                fat = round(fat_100g * factor, 2)
            if fibra is None:
                fibra = round(fibra_100g * factor, 2)
            
            # Calcular CG (carbohidratos glucémicos) si hay IG
            if cg is None and cho and ig_val:
                cg = round(cho * (ig_val / 100.0), 2)
            elif cg is None:
                cg = cho  # Si no hay IG, usar CHO como aproximación

    execute("""
        INSERT INTO plan_alimento (plan_detalle_id, ingrediente_id, cantidad, unidad,
                                   kcal, cho, pro, fat, fibra, cg)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (did, ing, cant, uni, kcal, cho, pro, fat, fibra, cg))

    flash("Alimento agregado.", "success")
    return redirect(url_for("admin_plan_ver", pid=pid))

@app.route("/admin/plan-alimento/<int:aid>/editar", methods=["POST"])
@admin_required
def admin_plan_alimento_editar(aid):
    row = fetch_one("""
        SELECT a.plan_detalle_id, d.plan_id
          FROM plan_alimento a
          JOIN plan_detalle d ON d.id = a.plan_detalle_id
         WHERE a.id=%s
    """, (aid,))
    if not row:
        flash("El alimento no existe.", "error")
        return redirect(url_for("admin_planes"))
    did, pid = row

    ing   = (request.form.get("ingrediente_id") or "").strip()
    cant  = (request.form.get("cantidad") or "").strip()
    uni   = (request.form.get("unidad") or "g").strip()
    def _num(name):
        v = (request.form.get(name) or "").strip()
        return float(v) if v else None
    kcal=_num("kcal"); cho=_num("cho"); pro=_num("pro"); fat=_num("fat"); fibra=_num("fibra"); cg=_num("cg")

    execute("""
        UPDATE plan_alimento
           SET ingrediente_id=%s, cantidad=%s, unidad=%s,
               kcal=%s, cho=%s, pro=%s, fat=%s, fibra=%s, cg=%s
         WHERE id=%s
    """, (ing, cant, uni, kcal, cho, pro, fat, fibra, cg, aid))

    flash("Alimento actualizado.", "success")
    return redirect(url_for("admin_plan_ver", pid=pid))

@app.route("/admin/plan-alimento/<int:aid>/borrar", methods=["POST"])
@admin_required
def admin_plan_alimento_borrar(aid):
    row = fetch_one("""
        SELECT d.plan_id
          FROM plan_alimento a
          JOIN plan_detalle d ON d.id = a.plan_detalle_id
         WHERE a.id=%s
    """, (aid,))
    if not row:
        flash("El alimento no existe.", "error")
        return redirect(url_for("admin_planes"))
    pid = row[0]
    execute("DELETE FROM plan_alimento WHERE id=%s", (aid,))
    flash("Alimento eliminado.", "success")
    return redirect(url_for("admin_plan_ver", pid=pid))

@app.route("/admin/plan-alimento/<int:aid>/intercambiar", methods=["POST"])
@admin_required
def admin_plan_alimento_intercambiar(aid):
    """Intercambiar un ingrediente por otro manteniendo la cantidad"""
    nuevo_ingrediente_id = request.form.get("ingrediente_id", "").strip()
    if not nuevo_ingrediente_id:
        flash("Debe seleccionar un ingrediente.", "error")
        return redirect(url_for("admin_planes"))
    
    try:
        nuevo_ingrediente_id = int(nuevo_ingrediente_id)
    except:
        flash("ID de ingrediente inválido.", "error")
        return redirect(url_for("admin_planes"))
    
    # Obtener el alimento actual
    alimento_actual = fetch_one("""
        SELECT a.plan_detalle_id, a.cantidad, a.unidad, d.plan_id
          FROM plan_alimento a
          JOIN plan_detalle d ON d.id = a.plan_detalle_id
         WHERE a.id=%s
    """, (aid,))
    
    if not alimento_actual:
        flash("El alimento no existe.", "error")
        return redirect(url_for("admin_planes"))
    
    did, cantidad, unidad, pid = alimento_actual
    
    # Obtener datos del nuevo ingrediente
    nuevo_ing = fetch_one("""
        SELECT kcal, cho, pro, fat, fibra, ig
          FROM ingrediente
         WHERE id=%s AND activo=TRUE
    """, (nuevo_ingrediente_id,))
    
    if not nuevo_ing:
        flash("El ingrediente seleccionado no existe o está inactivo.", "error")
        return redirect(url_for("admin_plan_ver", pid=pid))
    
    # Calcular valores nutricionales proporcionales
    # Si el ingrediente tiene porcion_base, calcular proporción
    ing_base = fetch_one("""
        SELECT porcion_base, kcal, cho, pro, fat, fibra, ig
          FROM ingrediente
         WHERE id=%s
    """, (nuevo_ingrediente_id,))
    
    if ing_base and ing_base[0]:  # porcion_base
        porcion_base = float(ing_base[0])
        factor = float(cantidad) / porcion_base if porcion_base > 0 else 1.0
        
        nueva_kcal = float(ing_base[1]) * factor if ing_base[1] else None
        nuevo_cho = float(ing_base[2]) * factor if ing_base[2] else None
        nuevo_pro = float(ing_base[3]) * factor if ing_base[3] else None
        nuevo_fat = float(ing_base[4]) * factor if ing_base[4] else None
        nueva_fibra = float(ing_base[5]) * factor if ing_base[5] else None
        # cg en plan_alimento se calcula como cho * (ig/100) si ig existe, sino se usa cho
        ig_val = float(ing_base[6]) if ing_base[6] else None
        if ig_val and nuevo_cho:
            nuevo_cg = nuevo_cho * (ig_val / 100.0)
        else:
            nuevo_cg = nuevo_cho  # Si no hay IG, usar CHO como aproximación
    else:
        nueva_kcal = float(nuevo_ing[0]) if nuevo_ing[0] else None
        nuevo_cho = float(nuevo_ing[1]) if nuevo_ing[1] else None
        nuevo_pro = float(nuevo_ing[2]) if nuevo_ing[2] else None
        nuevo_fat = float(nuevo_ing[3]) if nuevo_ing[3] else None
        nueva_fibra = float(nuevo_ing[4]) if nuevo_ing[4] else None
        # cg en plan_alimento se calcula como cho * (ig/100) si ig existe
        ig_val = float(nuevo_ing[5]) if nuevo_ing[5] else None
        if ig_val and nuevo_cho:
            nuevo_cg = nuevo_cho * (ig_val / 100.0)
        else:
            nuevo_cg = nuevo_cho  # Si no hay IG, usar CHO como aproximación
    
    # Actualizar el alimento
    execute("""
        UPDATE plan_alimento
           SET ingrediente_id=%s,
               kcal=%s, cho=%s, pro=%s, fat=%s, fibra=%s, cg=%s,
               actualizado_en=CURRENT_TIMESTAMP
         WHERE id=%s
    """, (nuevo_ingrediente_id, nueva_kcal, nuevo_cho, nuevo_pro, nuevo_fat, nueva_fibra, nuevo_cg, aid))
    
    flash("Ingrediente intercambiado correctamente.", "success")
    return redirect(url_for("admin_plan_ver", pid=pid))

@app.route("/admin/plan-alimento/<int:aid>/mover", methods=["POST"])
@admin_required
def admin_plan_alimento_mover(aid):
    """Mover un alimento a otro plan_detalle (otra celda)"""
    nuevo_detalle_id = request.form.get("plan_detalle_id", "").strip()
    dia = request.form.get("dia", "").strip()
    tiempo = request.form.get("tiempo", "").strip()
    
    # Verificar que el alimento existe
    alimento = fetch_one("""
        SELECT d.plan_id
          FROM plan_alimento a
          JOIN plan_detalle d ON d.id = a.plan_detalle_id
         WHERE a.id=%s
    """, (aid,))
    
    if not alimento:
        flash("El alimento no existe.", "error")
        return redirect(url_for("admin_planes"))
    
    pid = alimento[0]
    
    # Si no hay plan_detalle_id pero hay dia y tiempo, crear el plan_detalle primero
    if not nuevo_detalle_id and dia and tiempo:
        # Verificar si ya existe un plan_detalle para ese día y tiempo
        detalle_existente = fetch_one("""
            SELECT id FROM plan_detalle 
            WHERE plan_id=%s AND dia=%s AND tiempo=%s
        """, (pid, dia, tiempo))
        
        if detalle_existente:
            nuevo_detalle_id = detalle_existente[0]
        else:
            # Crear el plan_detalle
            execute("""
                INSERT INTO plan_detalle (plan_id, dia, tiempo)
                VALUES (%s, %s, %s)
            """, (pid, dia, tiempo))
            nuevo_detalle_id = fetch_one("SELECT id FROM plan_detalle WHERE plan_id=%s AND dia=%s AND tiempo=%s", (pid, dia, tiempo))[0]
    
    if not nuevo_detalle_id:
        flash("Debe especificar el destino.", "error")
        return redirect(url_for("admin_plan_ver", pid=pid))
    
    try:
        nuevo_detalle_id = int(nuevo_detalle_id)
    except:
        flash("ID de detalle inválido.", "error")
        return redirect(url_for("admin_plan_ver", pid=pid))
    
    # Verificar que el nuevo detalle existe y pertenece al mismo plan
    nuevo_detalle = fetch_one("""
        SELECT plan_id FROM plan_detalle WHERE id=%s
    """, (nuevo_detalle_id,))
    
    if not nuevo_detalle:
        flash("El destino no existe.", "error")
        return redirect(url_for("admin_plan_ver", pid=pid))
    
    if nuevo_detalle[0] != pid:
        flash("No se puede mover a otro plan.", "error")
        return redirect(url_for("admin_plan_ver", pid=pid))
    
    # Mover el alimento
    execute("""
        UPDATE plan_alimento
           SET plan_detalle_id=%s,
               actualizado_en=CURRENT_TIMESTAMP
         WHERE id=%s
    """, (nuevo_detalle_id, aid))
    
    flash("Alimento movido correctamente.", "success")
    return redirect(url_for("admin_plan_ver", pid=pid))


@app.route("/admin/config")
@admin_required
def admin_config():
    return _placeholder("Configuración clínica")


# ---------- Motor de Recomendación Nutricional ----------

# Endpoints de recomendación movidos a generar-plan

@app.route("/api/debug/ingredientes/<int:paciente_id>")
@admin_required
def api_debug_ingredientes(paciente_id):
    """Endpoint de debug para ver ingredientes disponibles"""
    try:
        motor = MotorRecomendacion()
        debug_info = motor.debug_ingredientes_disponibles(paciente_id)
        return debug_info
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/api/test/exclusion", methods=["POST"])
def api_test_exclusion():
    """Endpoint de prueba para exclusión de grupos sin autenticación"""
    try:
        data = request.get_json()
        print(f"TEST EXCLUSION: Datos recibidos: {data}")
        
        motor = MotorRecomendacion()
        
        # Generar recomendación estándar con filtros
        resultado = motor.generar_recomendacion_estandar(
            dias=data.get('configuracion', {}).get('dias_plan', 7),
            configuracion=data.get('configuracion', {}),
            ingredientes=data.get('ingredientes', {})
        )
        
        return resultado, 200
        
    except Exception as e:
        print(f"ERROR en api_test_exclusion: {str(e)}")
        print(f"TRACEBACK: {traceback.format_exc()}")
        return {"error": f"No se pudo generar la recomendación: {str(e)}"}, 500

@app.route("/api/test/motor/<int:paciente_id>")
def api_test_motor(paciente_id):
    """Endpoint de prueba para el motor sin autenticación"""
    try:
        print(f"TEST: Iniciando prueba del motor para paciente {paciente_id}")
        
        motor = MotorRecomendacion()
        print(f"TEST: Motor creado exitosamente")
        
        # Probar paso a paso
        perfil = motor.obtener_perfil_paciente(paciente_id)
        print(f"TEST: Perfil obtenido - ID: {perfil.paciente_id}, Edad: {perfil.edad}")
        
        metas = motor.calcular_metas_nutricionales(perfil)
        print(f"TEST: Metas calculadas - Calorías: {metas.calorias_diarias}")
        
        ingredientes = motor.obtener_ingredientes_recomendados(perfil, metas)
        print(f"TEST: Ingredientes obtenidos: {len(ingredientes)}")
        
        grupos = motor._agrupar_ingredientes(ingredientes)
        print(f"TEST: Grupos: {list(grupos.keys())}")
        
        # Generar recomendación completa
        recomendacion = motor.generar_recomendacion_semanal(paciente_id, 7)
        print(f"TEST: Recomendación generada exitosamente")
        
        return {
            "ok": True,
            "test": {
                "perfil_ok": True,
                "metas_ok": True,
                "ingredientes_count": len(ingredientes),
                "grupos_count": len(grupos),
                "recomendacion_keys": list(recomendacion.keys()) if isinstance(recomendacion, dict) else "No es dict"
            },
            "recomendacion": recomendacion
        }
        
    except Exception as e:
        print(f"TEST ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "ok": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }, 500

def _determinar_control_glucemico(probabilidad_ajustada, probabilidad_ml, perfil):
    """
    Determina el control glucémico basado en probabilidades ML o valores clínicos.
    Prioriza probabilidad_ajustada > probabilidad_ml > valores clínicos.
    """
    # Usar probabilidad ajustada si está disponible
    prob_final = probabilidad_ajustada
    
    # Si no hay probabilidad ajustada, usar probabilidad ML
    if prob_final is None:
        prob_final = probabilidad_ml
    
    # Si hay probabilidad ML, usarla para clasificar
    if prob_final is not None:
        if prob_final > 0.6:
            return 'MALO'
        elif prob_final > 0.4:
            return 'MODERADO'
        else:
            return 'BUENO'
    
    # Si no hay probabilidades ML, usar valores clínicos como fallback
    # HbA1c >= 7.0 o glucosa >= 140 → MALO
    if perfil.hba1c and perfil.hba1c >= 7.0:
        return 'MALO'
    if perfil.glucosa_ayunas and perfil.glucosa_ayunas >= 140:
        return 'MALO'
    
    # HbA1c 6.5-6.9 o glucosa 126-139 → MODERADO
    if perfil.hba1c and perfil.hba1c >= 6.5:
        return 'MODERADO'
    if perfil.glucosa_ayunas and perfil.glucosa_ayunas >= 126:
        return 'MODERADO'
    
    # Por defecto, BUENO
    return 'BUENO'

@app.route("/api/recomendacion/configuracion/<int:paciente_id>", methods=["GET"])
@login_required
def api_recomendacion_configuracion(paciente_id):
    """API endpoint para obtener configuración recomendada con ajuste ML"""
    try:
        from Core.motor_recomendacion import MotorRecomendacion
        
        motor = MotorRecomendacion()
        
        # Obtener perfil del paciente
        perfil = motor.obtener_perfil_paciente(paciente_id)
        
        # Calcular configuración base (sin ajuste ML aún)
        configuracion_base = {
            'kcal_objetivo': None,
            'cho_pct': None,
            'pro_pct': None,
            'fat_pct': None
        }
        
        # Calcular calorías basales
        if perfil.peso and perfil.talla:
            # Fórmula de Harris-Benedict
            if perfil.sexo == 'M':
                tmb = 88.362 + (13.397 * perfil.peso) + (4.799 * perfil.talla * 100) - (5.677 * perfil.edad)
            else:
                tmb = 447.593 + (9.247 * perfil.peso) + (3.098 * perfil.talla * 100) - (4.330 * perfil.edad)
            
            factores_actividad = {
                'baja': 1.2,
                'moderada': 1.375,
                'alta': 1.55
            }
            factor = factores_actividad.get(perfil.actividad, 1.2)
            calorias_mantenimiento = int(tmb * factor)
            
            # Aplicar déficit calórico para pérdida de peso si hay obesidad
            imc = perfil.imc
            if imc >= 35:
                # Obesidad grado II/III: déficit del 25%
                configuracion_base['kcal_objetivo'] = int(calorias_mantenimiento * 0.75)
            elif imc >= 30:
                # Obesidad grado I: déficit del 20%
                configuracion_base['kcal_objetivo'] = int(calorias_mantenimiento * 0.80)
            else:
                configuracion_base['kcal_objetivo'] = calorias_mantenimiento
        
        # Calcular macronutrientes base
        imc = perfil.imc
        hba1c = perfil.hba1c or 7.0
        glucosa = perfil.glucosa_ayunas or 0
        
        # Determinar si hay obesidad y diabetes mal controlada
        tiene_obesidad_severa = imc >= 35
        tiene_obesidad = imc >= 30
        diabetes_mal_controlada = hba1c >= 6.9 or glucosa >= 140
        
        cho_base = 50
        pro_base = 18
        fat_base = 32
        
        # Ajustar según obesidad + control glucémico
        if tiene_obesidad_severa and diabetes_mal_controlada:
            # Obesidad severa + diabetes mal controlada: CHO 25-30%
            cho_base = 30
            pro_base = 20
            fat_base = 50
        elif tiene_obesidad and diabetes_mal_controlada:
            # Obesidad + diabetes mal controlada: CHO 30-35%
            cho_base = 35
            pro_base = 20
            fat_base = 45
        elif hba1c > 8:
            cho_base = 35
            pro_base = 22
            fat_base = 43
        elif hba1c > 7:
            cho_base = 40
            pro_base = 22
            fat_base = 38
        elif hba1c > 6.5:
            cho_base = 45
            pro_base = 20
            fat_base = 35
        
        configuracion_base['cho_pct'] = cho_base
        configuracion_base['pro_pct'] = pro_base
        configuracion_base['fat_pct'] = fat_base
        
        # Calcular metas nutricionales CON ajuste ML (esto aplica el ajuste)
        configuracion_con_ml = {
            'kcal_objetivo': configuracion_base['kcal_objetivo'],
            'cho_pct': configuracion_base['cho_pct'],
            'pro_pct': configuracion_base['pro_pct'],
            'fat_pct': configuracion_base['fat_pct']
        }
        
        # Calcular metas nutricionales (esto aplica el ajuste ML internamente)
        metas = motor.calcular_metas_nutricionales(perfil, configuracion_con_ml)
        
        # Obtener probabilidad ML ajustada
        probabilidad_ml = getattr(motor, '_ultima_probabilidad_ml', None)
        probabilidad_ajustada = getattr(motor, '_ultima_probabilidad_ajustada', probabilidad_ml)
        
        # Configuración final (ya ajustada por ML)
        # Obtener valores por defecto para ig_max y max_repeticiones
        # Estos valores se pueden ajustar según el perfil del paciente
        ig_max = 70  # Valor por defecto para índice glucémico máximo
        max_repeticiones = 3  # Valor por defecto para repeticiones máximas por semana
        
        # Ajustar según control glucémico
        if probabilidad_ajustada and probabilidad_ajustada > 0.6:
            # Control malo: índice glucémico más bajo
            ig_max = 55
            max_repeticiones = 2
        elif probabilidad_ajustada and probabilidad_ajustada > 0.4:
            # Control moderado
            ig_max = 65
            max_repeticiones = 3
        else:
            # Control bueno
            ig_max = 70
            max_repeticiones = 3
        
        configuracion_final = {
            'kcal_objetivo': metas.calorias_diarias,
            'cho_pct': metas.carbohidratos_porcentaje,
            'pro_pct': metas.proteinas_porcentaje,
            'fat_pct': metas.grasas_porcentaje,
            'ig_max': ig_max,
            'max_repeticiones': max_repeticiones
        }
        
        return {
            'ok': True,
            'configuracion_base': configuracion_base,  # Antes del ajuste ML
            'configuracion_final': configuracion_final,  # Después del ajuste ML
            'metas_nutricionales': {
                'calorias_diarias': metas.calorias_diarias,
                'carbohidratos_g': metas.carbohidratos_g,
                'carbohidratos_porcentaje': metas.carbohidratos_porcentaje,
                'proteinas_g': metas.proteinas_g,
                'proteinas_porcentaje': metas.proteinas_porcentaje,
                'grasas_g': metas.grasas_g,
                'grasas_porcentaje': metas.grasas_porcentaje,
                'fibra_g': metas.fibra_g
            },
            'ml': {
                'probabilidad_mal_control': probabilidad_ml,
                'probabilidad_ajustada': probabilidad_ajustada,
                'control_glucemico': _determinar_control_glucemico(probabilidad_ajustada, probabilidad_ml, perfil)
            }
        }, 200
        
    except Exception as e:
        print(f"ERROR en api_recomendacion_configuracion: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": f"No se pudo calcular la configuración: {str(e)}"}, 500

@app.route("/api/recomendacion/generar", methods=["POST"])
@login_required
def api_recomendacion_generar():
    """API endpoint para generar recomendación nutricional con configuración personalizada"""
    try:
        data = request.get_json()
        paciente_id = data.get('paciente_id')
        configuracion = data.get('configuracion', {})
        ingredientes = data.get('ingredientes', {})
        
        print(f"DEBUG: Generando recomendación para paciente {paciente_id}")
        print(f"DEBUG: Configuración: {configuracion}")
        print(f"DEBUG: Ingredientes: {ingredientes}")
        
        # Validar datos requeridos
        if not paciente_id:
            return {"error": "ID de paciente requerido"}, 400
            
        # Generar plan usando el motor de recomendación existente
        from Core.motor_recomendacion import MotorRecomendacion
        
        # Crear instancia del motor
        motor = MotorRecomendacion()
        
        # Generar plan semanal específico del paciente con la configuración y filtros recibidos
        resultado = motor.generar_plan_semanal_completo(
            paciente_id=paciente_id,
            dias=configuracion.get('dias_plan', 7),
            configuracion=configuracion,
            ingredientes=ingredientes
        )
        
        return resultado, 200
        
    except Exception as e:
        print(f"ERROR en api_recomendacion_generar: {str(e)}")
        print(f"TRACEBACK: {traceback.format_exc()}")
        return {"error": f"No se pudo generar la recomendación: {str(e)}"}, 500

@app.route("/api/recomendacion/<int:paciente_id>")
@login_required
def api_recomendacion_paciente(paciente_id):
    """API endpoint para obtener recomendación nutricional"""
    try:
        print(f"DEBUG: Iniciando recomendación para paciente {paciente_id}")
        
        # Verificar que el usuario tenga acceso al paciente
        user_id = session.get("user_id")
        user_roles = get_user_roles(user_id)
        
        if "admin" not in user_roles and "nutricionista" not in user_roles:
            # Si es paciente, solo puede ver su propia recomendación
            paciente_usuario = fetch_one("""
                SELECT usuario_id FROM paciente WHERE id = %s
            """, (paciente_id,))
            
            if not paciente_usuario or paciente_usuario[0] != user_id:
                return {"error": "Acceso denegado"}, 403
        
        print(f"DEBUG: Creando instancia del motor completo")
        motor = MotorRecomendacion()
        print(f"DEBUG: Motor completo creado exitosamente")
        
        # Obtener parámetros de la URL para días
        dias = request.args.get('dias', 7, type=int)
        print(f"DEBUG: Generando recomendación para {dias} días")
        
        # Obtener filtros de la URL
        filtros = {}
        if request.args.get('kcal'):
            filtros['kcal'] = int(request.args.get('kcal'))
        if request.args.get('cho_pct'):
            filtros['cho_pct'] = int(request.args.get('cho_pct'))
        if request.args.get('pro_pct'):
            filtros['pro_pct'] = int(request.args.get('pro_pct'))
        if request.args.get('fat_pct'):
            filtros['fat_pct'] = int(request.args.get('fat_pct'))
        if request.args.get('ig_max'):
            filtros['ig_max'] = int(request.args.get('ig_max'))
        if request.args.get('max_repeticiones'):
            filtros['max_repeticiones'] = int(request.args.get('max_repeticiones'))
        if request.args.get('grupos_excluir'):
            filtros['grupos_excluir'] = request.args.get('grupos_excluir').split(',')
        if request.args.get('patron_comidas'):
            filtros['patron_comidas'] = request.args.get('patron_comidas').split(',')
        print(f"DEBUG: request.args completo: {dict(request.args)}")
        print(f"DEBUG: request.args.get('dia_inicio'): {request.args.get('dia_inicio')}")
        
        if request.args.get('dia_inicio'):
            filtros['dia_inicio'] = int(request.args.get('dia_inicio'))
            print(f"DEBUG: ✅ dia_inicio recibido del frontend: {filtros['dia_inicio']}")
        else:
            print(f"DEBUG: ❌ No se recibió dia_inicio del frontend")
        
        print(f"DEBUG: Filtros aplicados: {filtros}")
        if 'dia_inicio' in filtros:
            print(f"DEBUG: dia_inicio en filtros: {filtros['dia_inicio']} (tipo: {type(filtros['dia_inicio'])})")
        else:
            print(f"DEBUG: ⚠️ dia_inicio NO está en filtros")
        
        # Siempre generar el plan completo, independientemente de los filtros
        print(f"DEBUG: Generando plan completo con filtros: {filtros}")
        
        # Generar recomendación semanal con variedad y filtros
        try:
            recomendacion = motor.generar_recomendacion_semanal(paciente_id, dias, filtros)
            print(f"DEBUG: Recomendación generada exitosamente")
            print(f"DEBUG: Claves de recomendación: {list(recomendacion.keys())}")
            print(f"DEBUG: plan_semanal existe: {'plan_semanal' in recomendacion}")
            if 'plan_semanal' in recomendacion:
                print(f"DEBUG: plan_semanal tipo: {type(recomendacion['plan_semanal'])}")
                print(f"DEBUG: plan_semanal claves: {list(recomendacion['plan_semanal'].keys()) if isinstance(recomendacion['plan_semanal'], dict) else 'No es dict'}")
            
            # Verificar si hay error en la recomendación
            if 'error' in recomendacion:
                print(f"ERROR en recomendación: {recomendacion['error']}")
                return {"error": recomendacion['error']}, 500
            
            # Convertir el formato para que sea compatible con el frontend
            response_data = {
                'paciente_id': recomendacion['paciente_id'],
                'fecha': recomendacion['fecha'],
                'perfil': recomendacion['perfil'],
                'metas_nutricionales': recomendacion['metas_nutricionales'],
                'plan_completo': recomendacion['plan_completo'],  # Usar el nombre correcto del motor
                'validaciones': recomendacion['validaciones'],
                'ingredientes_disponibles': recomendacion['ingredientes_disponibles'],
                'filtros_aplicados': recomendacion.get('filtros_aplicados', {}),
                'total_semanas': recomendacion.get('total_semanas', 1)
            }
            
            print(f"DEBUG: Response data claves: {list(response_data.keys())}")
            print(f"DEBUG: plan_completo en response: {'plan_completo' in response_data}")
            
            return response_data
        except Exception as e:
            print(f"ERROR generando recomendación completa: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": f"Error generando recomendación completa: {str(e)}"}, 500
        
    except Exception as e:
        print(f"ERROR en api_recomendacion_paciente: {str(e)}")
        import traceback
        print(f"TRACEBACK: {traceback.format_exc()}")
        return {"error": f"No se pudo generar la recomendación: {str(e)}"}, 500

# ========== RUTAS PARA PACIENTES ==========

def get_paciente_by_user_id(user_id):
    """Helper para obtener datos del paciente por user_id"""
    paciente_data = fetch_one("""
        SELECT p.id, p.dni, p.sexo, TO_CHAR(p.fecha_nac,'YYYY-MM-DD') AS fecha_nac,
               p.telefono, u.email AS usuario_email,
               COALESCE(pr.nombres,'') AS nombres, COALESCE(pr.apellidos,'') AS apellidos
        FROM paciente p
        LEFT JOIN usuario u ON u.id = p.usuario_id
        LEFT JOIN pre_registro pr ON pr.dni = p.dni
        WHERE p.usuario_id = %s
    """, (user_id,))
    return paciente_data

@app.route("/paciente")
@login_required
def paciente_dashboard():
    """Dashboard principal del paciente"""
    user_id = session.get("user_id")
    
    # Verificar rol paciente
    roles = get_user_roles(user_id)
    print(f"DEBUG paciente_dashboard: user_id={user_id}, roles={roles}")  # Debug
    
    if "paciente" not in roles:
        flash("Acceso restringido al rol Paciente", "error")
        if "admin" in roles:
            return redirect(url_for("admin_home"))
        return redirect(url_for("logout"))
    
    paciente_data = get_paciente_by_user_id(user_id)
    print(f"DEBUG paciente_dashboard: paciente_data={paciente_data}")  # Debug
    
    if not paciente_data:
        flash("No se encontró información del paciente asociada a tu cuenta. Contacta al administrador para asociar tu cuenta con un registro de paciente.", "error")
        return redirect(url_for("logout"))
    
    paciente_id = paciente_data[0]
    paciente_nombre = f"{paciente_data[6]} {paciente_data[7]}".strip() or "Paciente"
    
    # Última antropometría
    antropo = fetch_one("""
        SELECT peso, talla, cc, bf_pct, actividad, TO_CHAR(fecha,'YYYY-MM-DD') AS fecha_medicion
        FROM antropometria
        WHERE paciente_id=%s
        ORDER BY fecha DESC LIMIT 1
    """, (paciente_id,))
    
    # Calcular IMC
    imc = None
    if antropo and antropo[0] and antropo[1]:
        try:
            imc = round(float(antropo[0]) / (float(antropo[1]) ** 2), 2)
        except:
            pass
    
    ultima_antropo = {
        "peso": antropo[0] if antropo else None,
        "talla": antropo[1] if antropo else None,
        "cc": antropo[2] if antropo else None,
        "bf_pct": antropo[3] if antropo else None,
        "actividad": antropo[4] if antropo else None,
        "fecha_medicion": antropo[5] if antropo else None,
        "imc": imc
    }
    
    # Últimos datos clínicos
    clinico = fetch_one("""
        SELECT hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia, TO_CHAR(fecha,'YYYY-MM-DD') AS fecha_medicion
        FROM clinico
        WHERE paciente_id=%s
        ORDER BY fecha DESC LIMIT 1
    """, (paciente_id,))
    
    ultimo_clinico = {
        "hba1c": clinico[0] if clinico else None,
        "glucosa_ayunas": clinico[1] if clinico else None,
        "ldl": clinico[2] if clinico else None,
        "trigliceridos": clinico[3] if clinico else None,
        "pa_sis": clinico[4] if clinico else None,
        "pa_dia": clinico[5] if clinico else None,
        "fecha_medicion": clinico[6] if clinico else None
    }
    
    # Plan activo (último plan generado) con información del nutricionista
    plan = fetch_one("""
        SELECT pl.id, pl.fecha_ini, pl.fecha_fin, 
               (pl.fecha_fin - pl.fecha_ini + 1) as duracion_dias,
               pl.metas_json,
               pl.creado_por, pl.creado_en,
               u.email as nutricionista_email,
               pn.nombres as nutricionista_nombres,
               pn.apellidos as nutricionista_apellidos,
               pn.colegiatura as nutricionista_colegiatura
        FROM plan pl
        LEFT JOIN usuario u ON u.id = pl.creado_por
        LEFT JOIN perfil_nutricionista pn ON pn.usuario_id = pl.creado_por
        WHERE pl.paciente_id = %s
        ORDER BY pl.fecha_ini DESC
        LIMIT 1
    """, (paciente_id,))
    
    plan_activo = None
    if plan:
        # Parsear metas desde JSON
        metas_json = plan[4] if plan[4] else {}
        if isinstance(metas_json, str):
            try:
                metas_json = json.loads(metas_json)
            except:
                metas_json = {}
        
        # Información del nutricionista
        nutricionista_nombre = ""
        if plan[8] and plan[9]:  # nombres y apellidos
            nutricionista_nombre = f"{plan[8]} {plan[9]}"
        elif plan[8]:
            nutricionista_nombre = plan[8]
        elif plan[9]:
            nutricionista_nombre = plan[9]
        elif plan[7]:  # email como fallback
            nutricionista_nombre = plan[7]
        
        plan_activo = {
            "id": plan[0],
            "fecha_inicio": plan[1].strftime("%d/%m/%Y") if plan[1] else None,
            "fecha_fin": plan[2].strftime("%d/%m/%Y") if plan[2] else None,
            "duracion_dias": plan[3] if plan[3] else 0,
            "metas": {
                "calorias_diarias": metas_json.get("calorias_diarias", 0) if metas_json else 0,
                "carbohidratos_porcentaje": metas_json.get("carbohidratos_porcentaje", 0) if metas_json else 0,
                "proteinas_porcentaje": metas_json.get("proteinas_porcentaje", 0) if metas_json else 0,
                "grasas_porcentaje": metas_json.get("grasas_porcentaje", 0) if metas_json else 0
            },
            "nutricionista": {
                "nombre": nutricionista_nombre or "Nutricionista",
                "colegiatura": plan[10] or "",
                "fecha_creacion": plan[6].strftime("%d/%m/%Y %H:%M") if plan[6] else None
            } if plan[5] else None  # creado_por
        }
    
    return render_template("paciente/dashboard.html",
                         paciente_nombre=paciente_nombre,
                         ultima_antropo=ultima_antropo,
                         ultimo_clinico=ultimo_clinico,
                         plan_activo=plan_activo)

@app.route("/paciente/mi-plan")
@login_required
def paciente_mi_plan():
    """Vista del plan nutricional del paciente"""
    user_id = session.get("user_id")
    
    # Verificar rol paciente
    roles = get_user_roles(user_id)
    if "paciente" not in roles:
        flash("Acceso restringido al rol Paciente", "error")
        if "admin" in roles:
            return redirect(url_for("admin_home"))
        return redirect(url_for("logout"))
    
    paciente_data = get_paciente_by_user_id(user_id)
    
    if not paciente_data:
        flash("No se encontró información del paciente asociada a tu cuenta", "error")
        return redirect(url_for("logout"))
    
    paciente_id = paciente_data[0]
    
    # Obtener el plan activo (último plan) con información del nutricionista
    plan = fetch_one("""
        SELECT pl.id, pl.fecha_ini, pl.fecha_fin, pl.metas_json,
               pl.creado_por, pl.creado_en,
               u.email as nutricionista_email,
               pn.nombres as nutricionista_nombres,
               pn.apellidos as nutricionista_apellidos,
               pn.colegiatura as nutricionista_colegiatura,
               pn.especialidad as nutricionista_especialidad
        FROM plan pl
        LEFT JOIN usuario u ON u.id = pl.creado_por
        LEFT JOIN perfil_nutricionista pn ON pn.usuario_id = pl.creado_por
        WHERE pl.paciente_id = %s
        ORDER BY pl.fecha_ini DESC
        LIMIT 1
    """, (paciente_id,))
    
    plan_completo = None
    metas_nutricionales = None
    nutricionista_info = None
    
    if plan:
        plan_id = plan[0]
        
        # Parsear metas
        metas_json = plan[3] if plan[3] else {}
        if isinstance(metas_json, str):
            try:
                metas_json = json.loads(metas_json)
            except:
                metas_json = {}
        metas_nutricionales = metas_json
        
        # Información del nutricionista que creó el plan
        nutricionista_info = None
        if plan[4]:  # creado_por
            nutricionista_nombre = ""
            if plan[7] and plan[8]:  # nombres y apellidos
                nutricionista_nombre = f"{plan[7]} {plan[8]}"
            elif plan[7]:
                nutricionista_nombre = plan[7]
            elif plan[8]:
                nutricionista_nombre = plan[8]
            elif plan[6]:  # email como fallback
                nutricionista_nombre = plan[6]
            
            nutricionista_info = {
                "nombre": nutricionista_nombre or "Nutricionista",
                "email": plan[6] or "",
                "colegiatura": plan[9] or "",
                "especialidad": plan[10] or "",
                "fecha_creacion": plan[5].strftime("%d/%m/%Y %H:%M") if plan[5] else None,
                "fecha_creacion_raw": plan[5] if plan[5] else None
            }
        
        # Obtener detalles del plan (comidas por día)
        detalles = fetch_all("""
            SELECT d.id, TO_CHAR(d.dia,'YYYY-MM-DD') AS dia, d.tiempo
            FROM plan_detalle d
            WHERE d.plan_id = %s
            ORDER BY d.dia, 
                     CASE d.tiempo 
                         WHEN 'des' THEN 1
                         WHEN 'mm' THEN 2
                         WHEN 'alm' THEN 3
                         WHEN 'mt' THEN 4
                         WHEN 'cena' THEN 5
                     END
        """, (plan_id,)) or []
        
        # Obtener alimentos de cada detalle
        plan_por_dia = {}
        for detalle in detalles:
            detalle_id = detalle[0]
            dia = detalle[1]
            tiempo = detalle[2]
            
            if dia not in plan_por_dia:
                plan_por_dia[dia] = {}
            
            alimentos = fetch_all("""
                SELECT i.nombre, i.grupo, pa.cantidad, pa.unidad, 
                       pa.kcal, pa.cho, pa.pro, pa.fat, pa.fibra
                FROM plan_alimento pa
                JOIN ingrediente i ON i.id = pa.ingrediente_id
                WHERE pa.plan_detalle_id = %s
                ORDER BY pa.id
            """, (detalle_id,)) or []
            
            # Mapear tiempos a nombres
            tiempo_nombres = {
                'des': 'Desayuno',
                'mm': 'Media Mañana',
                'alm': 'Almuerzo',
                'mt': 'Media Tarde',
                'cena': 'Cena'
            }
            
            horarios = {
                'des': '07:00',
                'mm': '10:00',
                'alm': '12:00',
                'mt': '15:00',
                'cena': '19:00'
            }
            
            plan_por_dia[dia][tiempo] = {
                'nombre': tiempo_nombres.get(tiempo, tiempo),
                'horario': horarios.get(tiempo, ''),
                'alimentos': [
                    {
                        'nombre': a[0],
                        'grupo': a[1],
                        'cantidad': f"{a[2]:g}" if a[2] else '',  # Formato sin decimales innecesarios
                        'unidad': a[3] if a[3] else 'g',
                        'kcal': a[4] or 0,
                        'cho': a[5] or 0,
                        'pro': a[6] or 0,
                        'fat': a[7] or 0,
                        'fibra': a[8] or 0
                    }
                    for a in alimentos
                ]
            }
        
        plan_completo = {
            'id': plan_id,
            'fecha_ini': plan[1].strftime("%Y-%m-%d") if plan[1] else None,
            'fecha_fin': plan[2].strftime("%Y-%m-%d") if plan[2] else None,
            'dias': plan_por_dia
        }
    
    # Si no hay plan guardado, NO generar automáticamente
    # El paciente debe tener un plan asignado por su nutricionista
    # if not plan_completo:
    #     # Ya no generamos automáticamente - el paciente debe tener un plan asignado
    #     pass
    
    return render_template("paciente/mi_plan.html",
                         plan_completo=plan_completo,
                         metas_nutricionales=metas_nutricionales,
                         paciente_data=paciente_data,
                         nutricionista_info=nutricionista_info if plan else None)

@app.route("/paciente/mi-perfil")
@login_required
def paciente_mi_perfil():
    """Vista del perfil del paciente"""
    user_id = session.get("user_id")
    
    # Verificar rol paciente
    roles = get_user_roles(user_id)
    if "paciente" not in roles:
        flash("Acceso restringido al rol Paciente", "error")
        if "admin" in roles:
            return redirect(url_for("admin_home"))
        return redirect(url_for("logout"))
    
    paciente_data = get_paciente_by_user_id(user_id)
    
    if not paciente_data:
        flash("No se encontró información del paciente asociada a tu cuenta", "error")
        return redirect(url_for("logout"))
    
    paciente_id = paciente_data[0]
    
    # Obtener datos completos
    antropo = fetch_one("""
        SELECT peso, talla, cc, bf_pct, actividad, TO_CHAR(fecha,'YYYY-MM-DD') AS fecha_medicion
        FROM antropometria
        WHERE paciente_id=%s
        ORDER BY fecha DESC LIMIT 1
    """, (paciente_id,))
    
    clinico = fetch_one("""
        SELECT hba1c, glucosa_ayunas, ldl, trigliceridos, pa_sis, pa_dia, TO_CHAR(fecha,'YYYY-MM-DD') AS fecha_medicion
        FROM clinico
        WHERE paciente_id=%s
        ORDER BY fecha DESC LIMIT 1
    """, (paciente_id,))
    
    # Calcular IMC y edad
    imc = None
    if antropo and antropo[0] and antropo[1]:
        try:
            imc = round(float(antropo[0]) / (float(antropo[1]) ** 2), 2)
        except:
            pass
    
    edad = None
    if paciente_data[3]:
        try:
            from datetime import date
            fecha_nac = date.fromisoformat(paciente_data[3])
            edad = (date.today() - fecha_nac).days // 365
        except:
            pass
    
    # Medicamentos
    medicamentos = fetch_all("""
        SELECT nombre, dosis, frecuencia
        FROM paciente_medicamento
        WHERE paciente_id = %s AND activo = true
        ORDER BY nombre
    """, (paciente_id,))
    
    # Alergias
    alergias = fetch_all("""
        SELECT i.nombre, pa.descripcion
        FROM paciente_alergia pa
        LEFT JOIN ingrediente i ON i.id = pa.ingrediente_id
        WHERE pa.paciente_id = %s
        ORDER BY i.nombre
    """, (paciente_id,))
    
    return render_template("paciente/mi_perfil.html",
                         paciente_data=paciente_data,
                         antropo=antropo,
                         clinico=clinico,
                         imc=imc,
                         edad=edad,
                         medicamentos=medicamentos,
                         alergias=alergias)

@app.route("/paciente/mi-progreso")
@login_required
def paciente_mi_progreso():
    """Vista de progreso y seguimiento del paciente"""
    user_id = session.get("user_id")
    
    # Verificar rol paciente
    roles = get_user_roles(user_id)
    if "paciente" not in roles:
        flash("Acceso restringido al rol Paciente", "error")
        if "admin" in roles:
            return redirect(url_for("admin_home"))
        return redirect(url_for("logout"))
    
    paciente_data = get_paciente_by_user_id(user_id)
    
    if not paciente_data:
        flash("No se encontró información del paciente asociada a tu cuenta", "error")
        return redirect(url_for("logout"))
    
    paciente_id = paciente_data[0]
    
    # Obtener historial de antropometría (últimos 12 meses) - usar subconsulta para evitar duplicados por fecha
    # Tomamos el registro más reciente (mayor id) para cada fecha
    historial_antropo = fetch_all("""
        SELECT a.peso, a.talla, a.cc, a.bf_pct, TO_CHAR(a.fecha,'YYYY-MM-DD') AS fecha
        FROM antropometria a
        INNER JOIN (
            SELECT fecha, MAX(id) as max_id
            FROM antropometria
            WHERE paciente_id = %s
            AND fecha >= CURRENT_DATE - INTERVAL '12 months'
            GROUP BY fecha
        ) b ON a.fecha = b.fecha AND a.id = b.max_id
        WHERE a.paciente_id = %s
        ORDER BY a.fecha DESC
    """, (paciente_id, paciente_id))
    
    # Obtener historial clínico (últimos 12 meses) - usar subconsulta para evitar duplicados por fecha
    # Tomamos el registro más reciente (mayor id) para cada fecha
    historial_clinico = fetch_all("""
        SELECT c.hba1c, c.glucosa_ayunas, c.ldl, c.trigliceridos, TO_CHAR(c.fecha,'YYYY-MM-DD') AS fecha
        FROM clinico c
        INNER JOIN (
            SELECT fecha, MAX(id) as max_id
            FROM clinico
            WHERE paciente_id = %s
            AND fecha >= CURRENT_DATE - INTERVAL '12 months'
            GROUP BY fecha
        ) d ON c.fecha = d.fecha AND c.id = d.max_id
        WHERE c.paciente_id = %s
        ORDER BY c.fecha DESC
    """, (paciente_id, paciente_id))
    
    # Filtrar duplicados por fecha como medida de seguridad adicional
    # (por si acaso la consulta SQL no los eliminó completamente)
    fechas_vistas_antropo = set()
    historial_antropo_filtrado = []
    for registro in historial_antropo:
        fecha = registro[4]  # La fecha está en el índice 4
        if fecha not in fechas_vistas_antropo:
            fechas_vistas_antropo.add(fecha)
            historial_antropo_filtrado.append(registro)
    
    fechas_vistas_clinico = set()
    historial_clinico_filtrado = []
    for registro in historial_clinico:
        fecha = registro[4]  # La fecha está en el índice 4
        if fecha not in fechas_vistas_clinico:
            fechas_vistas_clinico.add(fecha)
            historial_clinico_filtrado.append(registro)
    
    return render_template("paciente/mi_progreso.html",
                         paciente_data=paciente_data,
                         historial_antropo=historial_antropo_filtrado,
                         historial_clinico=historial_clinico_filtrado)

@app.route("/paciente/historial")
@login_required
def paciente_historial():
    """Vista del historial de planes nutricionales"""
    user_id = session.get("user_id")
    
    # Verificar rol paciente
    roles = get_user_roles(user_id)
    if "paciente" not in roles:
        flash("Acceso restringido al rol Paciente", "error")
        if "admin" in roles:
            return redirect(url_for("admin_home"))
        return redirect(url_for("logout"))
    
    paciente_data = get_paciente_by_user_id(user_id)
    
    if not paciente_data:
        flash("No se encontró información del paciente asociada a tu cuenta", "error")
        return redirect(url_for("logout"))
    
    paciente_id = paciente_data[0]
    
    # Obtener todos los planes del paciente
    planes = fetch_all("""
        SELECT id, fecha_ini, fecha_fin, 
               (fecha_fin - fecha_ini + 1) as duracion_dias,
               creado_en, metas_json
        FROM plan
        WHERE paciente_id = %s
        ORDER BY fecha_ini DESC
    """, (paciente_id,))
    
    planes_con_metas = []
    for plan in planes:
        # Parsear metas desde JSON
        metas_json = plan[5] if plan[5] else {}
        if isinstance(metas_json, str):
            try:
                metas_json = json.loads(metas_json)
            except:
                metas_json = {}
        
        planes_con_metas.append({
            "id": plan[0],
            "fecha_inicio": plan[1].strftime("%d/%m/%Y") if plan[1] else None,
            "fecha_fin": plan[2].strftime("%d/%m/%Y") if plan[2] else None,
            "duracion_dias": plan[3] if plan[3] else 0,
            "creado_en": plan[4].strftime("%d/%m/%Y %H:%M") if plan[4] else None,
            "metas": {
                "calorias_diarias": metas_json.get("calorias_diarias", 0) if metas_json else 0,
                "carbohidratos_porcentaje": metas_json.get("carbohidratos_porcentaje", 0) if metas_json else 0,
                "proteinas_porcentaje": metas_json.get("proteinas_porcentaje", 0) if metas_json else 0,
                "grasas_porcentaje": metas_json.get("grasas_porcentaje", 0) if metas_json else 0
            } if metas_json else None
        })
    
    return render_template("paciente/historial.html",
                         paciente_data=paciente_data,
                         planes=planes_con_metas)

@app.route("/paciente/mi-recomendacion")
@login_required
def paciente_mi_recomendacion():
    """Vista para que el paciente vea su recomendación nutricional (legacy - redirige a mi-plan)"""
    user_id = session.get("user_id")
    roles = get_user_roles(user_id)
    if "paciente" not in roles:
        flash("Acceso restringido al rol Paciente", "error")
        if "admin" in roles:
            return redirect(url_for("admin_home"))
        return redirect(url_for("logout"))
    return redirect(url_for("paciente_mi_plan"))

@app.route("/admin/recomendacion/estadisticas")
@admin_required
def admin_recomendacion_estadisticas():
    """Estadísticas del motor de recomendación"""
    
    # Estadísticas generales
    total_pacientes = fetch_one("SELECT COUNT(*) FROM paciente")[0]
    total_planes = fetch_one("SELECT COUNT(*) FROM plan WHERE version_modelo = 'motor_recomendacion_v1'")[0]
    
    # Pacientes con datos clínicos recientes
    pacientes_con_datos = fetch_one("""
        SELECT COUNT(DISTINCT c.paciente_id)
        FROM clinico c
        WHERE c.fecha >= CURRENT_DATE - INTERVAL '30 days'
    """)[0]
    
    # Ingredientes más utilizados
    ingredientes_populares = fetch_all("""
        SELECT i.nombre, COUNT(pa.id) as uso_count
        FROM ingrediente i
        JOIN plan_alimento pa ON pa.ingrediente_id = i.id
        JOIN plan_detalle pd ON pd.id = pa.plan_detalle_id
        JOIN plan p ON p.id = pd.plan_id
        WHERE p.version_modelo = 'motor_recomendacion_v1'
        GROUP BY i.id, i.nombre
        ORDER BY uso_count DESC
        LIMIT 10
    """)
    
    estadisticas = {
        'total_pacientes': total_pacientes,
        'total_planes_generados': total_planes,
        'pacientes_con_datos_recientes': pacientes_con_datos,
        'ingredientes_populares': ingredientes_populares
    }
    
    return render_template("admin/recomendacion_estadisticas.html", 
                         estadisticas=estadisticas)


# ---------- Punto de entrada ----------
if __name__ == "__main__":
    debug = os.getenv("FLASK_ENV", "development") == "development"
    app.run(debug=debug)
