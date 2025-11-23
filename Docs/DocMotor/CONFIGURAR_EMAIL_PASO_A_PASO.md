# 📧 Configuración de Email - Guía Paso a Paso

## ⚠️ Error Actual
Estás viendo este error porque el archivo `.env` no está configurado o las credenciales son incorrectas.

## ✅ Solución Rápida (5 minutos)

### Paso 1: Crear Contraseña de Aplicación en Gmail

1. **Activa Verificación en 2 Pasos** (si no la tienes):
   - Ve a: https://myaccount.google.com/security
   - Busca "Verificación en 2 pasos" y actívala
   - ⚠️ **ES OBLIGATORIO** para usar contraseñas de aplicación

2. **Crea la Contraseña de Aplicación**:
   - Ve a: https://myaccount.google.com/apppasswords
   - Si no ves la opción, vuelve al paso 1 y activa verificación en 2 pasos
   - Selecciona:
     - **Aplicación:** "Correo"
     - **Dispositivo:** "Otro (nombre personalizado)"
     - Escribe: `NutriSync`
   - Haz clic en **"Generar"**
   - **Copia la contraseña de 16 caracteres** (ejemplo: `abcd efgh ijkl mnop`)
     - Puedes copiarla con o sin espacios, ambos funcionan

### Paso 2: Editar el archivo `.env`

1. Abre el archivo `.env` que está en la raíz del proyecto (misma carpeta que `main.py`)

2. Reemplaza estas líneas con tus datos reales:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email-real@gmail.com
SMTP_PASSWORD=la-contraseña-de-16-caracteres-que-copiaste
SMTP_FROM_EMAIL=tu-email-real@gmail.com
SMTP_FROM_NAME=NutriSync
```

**Ejemplo real:**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=nutrisync@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop
SMTP_FROM_EMAIL=nutrisync@gmail.com
SMTP_FROM_NAME=NutriSync
```

**⚠️ IMPORTANTE:**
- `SMTP_USER` debe ser tu email de Gmail completo
- `SMTP_PASSWORD` debe ser la contraseña de aplicación (16 caracteres), NO tu contraseña normal
- `SMTP_FROM_EMAIL` debe ser el mismo que `SMTP_USER`

### Paso 3: Reiniciar el Servidor

1. **Cierra completamente** el servidor Flask (presiona `Ctrl+C` en la terminal)
2. **Vuelve a iniciarlo**:
   ```bash
   python iniciar_servidor.py
   ```
   O si usas otro comando:
   ```bash
   python main.py
   ```

### Paso 4: Probar

1. Genera un token de activación desde el panel de administración
2. Deberías ver: `✅ Email enviado a [email]`
3. Revisa la bandeja de entrada (y spam) del email del paciente

## 🔍 Verificar que Funciona

Si quieres verificar que las variables se están cargando correctamente, puedes agregar temporalmente esto en `main.py` (al inicio, después de los imports):

```python
import os
from dotenv import load_dotenv
load_dotenv()

print("=" * 50)
print("VERIFICACIÓN DE CONFIGURACIÓN SMTP:")
print("=" * 50)
print("SMTP_HOST:", os.getenv("SMTP_HOST", "NO CONFIGURADO"))
print("SMTP_PORT:", os.getenv("SMTP_PORT", "NO CONFIGURADO"))
print("SMTP_USER:", os.getenv("SMTP_USER", "NO CONFIGURADO"))
print("SMTP_PASSWORD:", "✅ Configurado" if os.getenv("SMTP_PASSWORD") else "❌ NO CONFIGURADO")
print("SMTP_FROM_EMAIL:", os.getenv("SMTP_FROM_EMAIL", "NO CONFIGURADO"))
print("=" * 50)
```

Luego reinicia el servidor y revisa la salida en la consola.

## ❓ Problemas Comunes

### "No veo la opción de contraseñas de aplicación"
**Solución:** Debes activar primero "Verificación en 2 pasos" en https://myaccount.google.com/security

### "Sigo viendo el error de autenticación"
**Solución:** 
1. Verifica que copiaste bien la contraseña (sin espacios extra al inicio/final)
2. Verifica que el email en `SMTP_USER` es correcto
3. Asegúrate de haber reiniciado el servidor después de cambiar `.env`
4. Verifica que el archivo `.env` está en la raíz del proyecto (misma carpeta que `main.py`)

### "El email no llega"
**Solución:**
1. Revisa la carpeta de spam/correo no deseado
2. Verifica que el email del destinatario es correcto
3. Revisa los logs del servidor para ver si hay errores

### "Quiero usar otro email (no Gmail)"
**Solución:** Ver `CONFIGURAR_EMAIL.md` para configurar Outlook u otros proveedores

## 📝 Nota Importante

El token **siempre se genera correctamente**, incluso si falla el envío del email. El sistema te mostrará el token para que lo envíes manualmente si es necesario.

## 🎯 Resumen

1. ✅ Activa verificación en 2 pasos en Gmail
2. ✅ Crea contraseña de aplicación en https://myaccount.google.com/apppasswords
3. ✅ Edita `.env` con tus credenciales
4. ✅ Reinicia el servidor Flask
5. ✅ Prueba generando un token

¡Listo! 🚀

