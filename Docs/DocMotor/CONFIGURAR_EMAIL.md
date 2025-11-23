# 📧 Configuración de Envío de Emails

Este documento explica cómo configurar el envío automático de tokens de activación por email.

## ✅ Estado Actual

El sistema ahora **envía automáticamente** los tokens de activación por email cuando:
- Se genera un token desde "Pre-registro"
- Se genera un token desde "Tokens de activación"
- Se regenera un token

## 🔧 Configuración (GRATIS con Gmail)

### Opción 1: Gmail (Recomendado - Gratis)

**⚠️ IMPORTANTE:** Gmail NO acepta tu contraseña normal. Debes usar una "Contraseña de aplicación".

#### Paso 1: Habilitar verificación en 2 pasos (si no la tienes)
1. Ve a: https://myaccount.google.com/security
2. Activa "Verificación en 2 pasos" (es obligatoria para usar contraseñas de aplicación)

#### Paso 2: Crear contraseña de aplicación
1. Ve a: https://myaccount.google.com/apppasswords
2. Inicia sesión con tu cuenta de Gmail
3. Si no ves la opción, asegúrate de tener verificación en 2 pasos activada
4. Selecciona:
   - **Aplicación:** "Correo"
   - **Dispositivo:** "Otro (nombre personalizado)" → escribe "NutriSync"
5. Haz clic en "Generar"
6. **Copia la contraseña de 16 caracteres** (se verá así: `abcd efgh ijkl mnop`)
   - ⚠️ **IMPORTANTE:** Quita los espacios o déjalos, ambos funcionan

#### Paso 3: Configurar variables en `.env`
Crea o edita el archivo `.env` en la raíz del proyecto y agrega:

```env
# Configuración SMTP para Gmail
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

**Nota:** Puedes dejar los espacios en la contraseña o quitarlos, ambos funcionan.

### Opción 2: Otros proveedores SMTP

**Outlook/Hotmail:**
```env
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=tu-email@outlook.com
SMTP_PASSWORD=tu-contraseña
SMTP_FROM_EMAIL=tu-email@outlook.com
SMTP_FROM_NAME=NutriSync
```

**Otros servidores SMTP:**
```env
SMTP_HOST=smtp.tu-servidor.com
SMTP_PORT=587
SMTP_USER=tu-usuario
SMTP_PASSWORD=tu-contraseña
SMTP_FROM_EMAIL=tu-email@dominio.com
SMTP_FROM_NAME=NutriSync
```

## 📱 ¿Y SMS?

Para enviar SMS necesitarías una API de pago como:
- **Twilio** (desde $0.0075 por SMS)
- **AWS SNS** (desde $0.00645 por SMS)
- **MessageBird** (desde $0.05 por SMS)

**Recomendación:** Usa email (gratis) para tokens. SMS solo si es estrictamente necesario.

## 🚀 Funcionamiento

1. **Si hay email configurado:**
   - El token se envía automáticamente al email del paciente
   - El email incluye el token y un enlace directo para activar
   - Se muestra un mensaje de éxito

2. **Si NO hay email configurado:**
   - Se muestra el token en pantalla
   - Se muestra una advertencia de que debe enviarse manualmente
   - El sistema funciona igual, solo sin envío automático

3. **Si el email falla:**
   - Se muestra el token en pantalla
   - Se muestra un mensaje de error con detalles
   - El token se guarda correctamente, solo falló el envío

## ⚠️ Notas Importantes

- **Gmail:** Requiere "Contraseña de aplicación", no uses tu contraseña normal
- **Seguridad:** Nunca subas el archivo `.env` a repositorios públicos
- **Límites:** Gmail permite hasta 500 emails/día en cuentas gratuitas
- **Pruebas:** Prueba primero con tu propio email antes de usar en producción

## 🧪 Probar el Envío

1. Configura las variables en `.env`
2. Reinicia el servidor Flask
3. Genera un token para un preregistro que tenga email
4. Revisa la bandeja de entrada (y spam) del email registrado

