# envio_email.py
# Módulo para envío de emails usando SMTP (Gmail u otros)

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# Configuración SMTP desde variables de entorno
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER)
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "NutriSync")

def enviar_email(destinatario: str, asunto: str, cuerpo_html: str, cuerpo_texto: str = None) -> tuple[bool, str]:
    """
    Envía un email usando SMTP.
    
    Args:
        destinatario: Email del destinatario
        asunto: Asunto del email
        cuerpo_html: Cuerpo del email en HTML
        cuerpo_texto: Cuerpo del email en texto plano (opcional)
    
    Returns:
        (éxito: bool, mensaje: str)
    """
    # Si no hay configuración SMTP, retornar error
    if not SMTP_USER or not SMTP_PASSWORD:
        return False, "SMTP no configurado. Agrega SMTP_USER y SMTP_PASSWORD en .env (ver CONFIGURAR_EMAIL.md)"
    
    if not destinatario:
        return False, "No se proporcionó destinatario"
    
    try:
        # Crear mensaje
        msg = MIMEMultipart('alternative')
        msg['Subject'] = asunto
        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg['To'] = destinatario
        
        # Agregar cuerpo
        if cuerpo_texto:
            part_texto = MIMEText(cuerpo_texto, 'plain', 'utf-8')
            msg.attach(part_texto)
        
        part_html = MIMEText(cuerpo_html, 'html', 'utf-8')
        msg.attach(part_html)
        
        # Conectar y enviar
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        return True, "Email enviado correctamente"
    
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"Error de autenticación SMTP.\n"
        error_msg += f"Para Gmail: Usa una 'Contraseña de aplicación' (no tu contraseña normal).\n"
        error_msg += f"Obténla en: https://myaccount.google.com/apppasswords\n"
        error_msg += f"Verifica que SMTP_USER y SMTP_PASSWORD estén correctos en .env"
        return False, error_msg
    except smtplib.SMTPException as e:
        return False, f"Error SMTP: {str(e)}"
    except Exception as e:
        return False, f"Error al enviar email: {str(e)}"


def enviar_token_activacion(dni: str, token: str, link_activacion: str, 
                            nombre: str = "", email: str = "", telefono: str = "") -> tuple[bool, str]:
    """
    Envía el token de activación por email.
    
    Args:
        dni: DNI del paciente
        token: Token de activación
        link_activacion: URL completa para activar
        nombre: Nombre del paciente (opcional)
        email: Email del paciente (requerido)
        telefono: Teléfono del paciente (opcional)
    
    Returns:
        (éxito: bool, mensaje: str)
    """
    if not email:
        return False, "No se proporcionó email para enviar el token"
    
    nombre_display = nombre if nombre else f"DNI {dni}"
    
    # Cuerpo HTML del email
    cuerpo_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
            .token-box {{ background: white; border: 2px solid #667eea; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center; }}
            .token {{ font-size: 24px; font-weight: bold; color: #667eea; letter-spacing: 2px; font-family: monospace; }}
            .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🎉 Bienvenido a NutriSync</h2>
            </div>
            <div class="content">
                <p>Hola <strong>{nombre_display}</strong>,</p>
                
                <p>Tu cuenta ha sido pre-registrada en NutriSync. Para activar tu cuenta, necesitas el siguiente token de activación:</p>
                
                <div class="token-box">
                    <p style="margin: 0 0 10px 0; color: #6b7280;">Tu token de activación:</p>
                    <div class="token">{token}</div>
                </div>
                
                <p style="text-align: center;">
                    <a href="{link_activacion}" class="button">Activar mi cuenta</a>
                </p>
                
                <p>O copia y pega este enlace en tu navegador:</p>
                <p style="word-break: break-all; color: #667eea;">{link_activacion}</p>
                
                <p><strong>⚠️ Importante:</strong></p>
                <ul>
                    <li>Este token expira en 48 horas</li>
                    <li>Úsalo solo una vez</li>
                    <li>No compartas este token con nadie</li>
                </ul>
                
                <div class="footer">
                    <p>Si no solicitaste este registro, puedes ignorar este email.</p>
                    <p>© NutriSync - Sistema de Gestión Nutricional</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Cuerpo texto plano
    cuerpo_texto = f"""
Bienvenido a NutriSync

Hola {nombre_display},

Tu cuenta ha sido pre-registrada en NutriSync. Para activar tu cuenta, necesitas el siguiente token de activación:

Token: {token}

Enlace de activación: {link_activacion}

IMPORTANTE:
- Este token expira en 48 horas
- Úsalo solo una vez
- No compartas este token con nadie

Si no solicitaste este registro, puedes ignorar este email.

© NutriSync - Sistema de Gestión Nutricional
    """
    
    asunto = "🎉 Activa tu cuenta en NutriSync"
    
    return enviar_email(email, asunto, cuerpo_html, cuerpo_texto)

