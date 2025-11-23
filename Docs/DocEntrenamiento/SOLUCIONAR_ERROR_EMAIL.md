# 🔧 Solución: Error de Autenticación SMTP

## ❌ Error que estás viendo:
```
⚠️ No se pudo enviar email: Error de autenticación SMTP. Verifica usuario y contraseña.
```

## ✅ Solución Paso a Paso

### Paso 1: Verificar que tienes un archivo `.env`

El archivo `.env` debe estar en la raíz del proyecto (misma carpeta que `main.py`).

Si no existe, créalo.

### Paso 2: Configurar Gmail (Recomendado)

#### 2.1. Habilitar verificación en 2 pasos (OBLIGATORIO)
1. Ve a: https://myaccount.google.com/security
2. Activa **"Verificación en 2 pasos"** si no la tienes activada
   - ⚠️ **ES OBLIGATORIO** para usar contraseñas de aplicación

#### 2.2. Crear contraseña de aplicación
1. Ve a: https://myaccount.google.com/apppasswords
2. Si no ves la opción, significa que NO tienes verificación en 2 pasos activada
3. Selecciona:
   - **Aplicación:** "Correo"
   - **Dispositivo:** "Otro (nombre personalizado)"
   - Escribe: `NutriSync`
4. Haz clic en **"Generar"**
5. **Copia la contraseña de 16 caracteres** (ejemplo: `abcd efgh ijkl mnop`)

#### 2.3. Agregar al archivo `.env`

Abre o crea el archivo `.env` y agrega estas líneas:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
SMTP_FROM_EMAIL=tu-email@gmail.com
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
- Usa la **contraseña de aplicación** (16 caracteres), NO tu contraseña normal de Gmail
- Puedes dejar los espacios o quitarlos, ambos funcionan
- El `SMTP_USER` debe ser el mismo email de Gmail

### Paso 3: Reiniciar el servidor Flask

**Cierra completamente** el servidor Flask (Ctrl+C) y vuelve a iniciarlo:

```bash
python iniciar_servidor.py
```

O si usas otro comando:
```bash
python main.py
```

### Paso 4: Probar de nuevo

1. Genera un token de activación
2. Deberías ver: `✅ Email enviado a [email]`
3. Revisa la bandeja de entrada (y spam) del email

## 🔍 Verificar que está configurado

Si quieres verificar que las variables se están cargando correctamente, puedes agregar temporalmente esto en `main.py`:

```python
import os
from dotenv import load_dotenv
load_dotenv()

print("SMTP_USER:", os.getenv("SMTP_USER"))
print("SMTP_PASSWORD configurado:", "Sí" if os.getenv("SMTP_PASSWORD") else "No")
```

## ❓ Problemas Comunes

### "No veo la opción de contraseñas de aplicación"
→ **Solución:** Activa primero "Verificación en 2 pasos" en https://myaccount.google.com/security

### "Sigo viendo el error de autenticación"
→ **Solución:** 
1. Verifica que copiaste bien la contraseña (sin espacios extra)
2. Verifica que el email en `SMTP_USER` es correcto
3. Asegúrate de haber reiniciado el servidor después de cambiar `.env`

### "El email no llega"
→ **Solución:**
1. Revisa la carpeta de spam
2. Verifica que el email del destinatario es correcto
3. Revisa los logs del servidor para ver si hay errores

### "Quiero usar otro email (no Gmail)"
→ **Solución:** Ver `CONFIGURAR_EMAIL.md` para configurar Outlook u otros proveedores

## 📝 Nota

El token **siempre se genera correctamente**, incluso si falla el envío del email. El sistema te mostrará el token para que lo envíes manualmente si es necesario.

