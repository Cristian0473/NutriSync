# 🚀 Guía de Deployment - Sistema de Recomendación Nutricional

## Opción Recomendada: Render.com (Gratis)

### Paso 1: Preparar el Repositorio en GitHub

1. **Crear repositorio en GitHub:**
   - Ve a https://github.com/new
   - Crea un repositorio nuevo (ej: `sistema-tesis-nutricional`)
   - **NO marques** "Add README" ni "Add .gitignore" (ya tienes archivos)

2. **Subir tu código a GitHub:**
   ```bash
   # En la carpeta de tu proyecto
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/TU-USUARIO/sistema-tesis-nutricional.git
   git push -u origin main
   ```

3. **Crear archivo `.gitignore`** (si no existe):
   ```
   __pycache__/
   *.pyc
   *.pyo
   *.pyd
   .env
   .venv
   venv/
   env/
   *.log
   .DS_Store
   ApartadoInteligente/ModeloML/*.pkl
   logs_sistema.md
   ```

### Paso 2: Exportar Base de Datos desde pgAdmin

1. **Abrir pgAdmin** y conectar a tu base de datos local

2. **Exportar la base de datos:**
   - Click derecho en tu base de datos → **Backup...**
   - **Filename:** `backup_tesis.sql` (o el nombre que prefieras)
   - **Format:** `Plain` o `Custom`
   - **Encoding:** `UTF8`
   - Click en **Backup**

3. **Guardar el archivo** `backup_tesis.sql` en tu computadora (lo necesitarás después)

### Paso 3: Crear Servicio Web en Render

1. **Crear cuenta en Render:**
   - Ve a https://render.com
   - Regístrate con GitHub (recomendado) o email

2. **Crear nuevo Web Service:**
   - Click en **"New +"** → **"Web Service"**
   - Conecta tu repositorio de GitHub
   - Selecciona el repositorio que creaste

3. **Configurar el servicio:**
   - **Name:** `sistema-tesis-nutricional` (o el nombre que prefieras)
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn main:app`
   - **Plan:** `Free` (gratis)

4. **Agregar variables de entorno:**
   En la sección **"Environment Variables"**, agrega:
   ```
   FLASK_SECRET=tu-clave-secreta-muy-larga-y-aleatoria-aqui
   FLASK_ENV=production
   ```
   (Genera una clave secreta aleatoria, puede ser cualquier string largo)

### Paso 4: Crear Base de Datos PostgreSQL en Render

1. **Crear PostgreSQL:**
   - Click en **"New +"** → **"PostgreSQL"**
   - **Name:** `sistema-tesis-db`
   - **Database:** `proyecto_tesis` (o el nombre que uses)
   - **User:** Se genera automáticamente
   - **Plan:** `Free` (gratis, 90 días de prueba, luego $7/mes)

2. **Copiar DATABASE_URL:**
   - Una vez creada, ve a la base de datos
   - En la sección **"Connections"**, copia la **"Internal Database URL"**
   - Se ve así: `postgresql://usuario:password@host:5432/dbname`

3. **Agregar DATABASE_URL al Web Service:**
   - Ve a tu Web Service
   - En **"Environment Variables"**, agrega:
     ```
     DATABASE_URL=postgresql://usuario:password@host:5432/dbname
     ```
     (Pega la URL que copiaste)

### Paso 5: Importar Base de Datos a Render

**Opción A: Usando pgAdmin (Recomendado)**

1. **Obtener credenciales de Render:**
   - Ve a tu base de datos PostgreSQL en Render
   - En **"Connections"**, verás:
     - **Host:** `dpg-xxxxx-a.oregon-postgres.render.com`
     - **Port:** `5432`
     - **Database:** `proyecto_tesis`
     - **User:** `usuario`
     - **Password:** (click en "Show" para verla)

2. **Conectar desde pgAdmin:**
   - Abre pgAdmin
   - Click derecho en **"Servers"** → **"Create"** → **"Server"**
   - **General tab:**
     - Name: `Render PostgreSQL`
   - **Connection tab:**
     - Host: `dpg-xxxxx-a.oregon-postgres.render.com`
     - Port: `5432`
     - Database: `proyecto_tesis`
     - Username: `usuario`
     - Password: `[la contraseña de Render]`
   - Click **"Save"**

3. **Restaurar backup:**
   - Click derecho en la base de datos `proyecto_tesis` en Render
   - **Restore...**
   - **Filename:** Selecciona tu archivo `backup_tesis.sql`
   - **Format:** `Plain` o `Custom` (según cómo lo exportaste)
   - Click en **Restore**

**Opción B: Usando psql desde terminal (Alternativa)**

```bash
# Instalar psql si no lo tienes (Windows: descargar PostgreSQL)
# Luego ejecutar:
psql "postgresql://usuario:password@host:5432/dbname" < backup_tesis.sql
```

### Paso 6: Configurar Email (Opcional)

Si necesitas que funcione el envío de emails:

1. En tu Web Service en Render, agrega estas variables de entorno:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=tu-email@gmail.com
   SMTP_PASSWORD=tu-contraseña-de-aplicacion
   SMTP_FROM_EMAIL=tu-email@gmail.com
   SMTP_FROM_NAME=NutriSync
   ```

### Paso 7: Desplegar

1. **Render despliega automáticamente** cuando haces push a GitHub
2. O puedes hacer click en **"Manual Deploy"** → **"Deploy latest commit"**
3. Espera a que termine el build (5-10 minutos la primera vez)
4. Tu aplicación estará disponible en: `https://sistema-tesis-nutricional.onrender.com`

### Paso 8: Verificar que Funciona

1. Abre el link de tu aplicación
2. Deberías ver la página de login
3. Prueba iniciar sesión con tus credenciales

---

## Alternativa: Railway.app (También Gratis)

Railway es otra opción similar a Render:

1. **Crear cuenta:** https://railway.app (con GitHub)
2. **New Project** → **Deploy from GitHub repo**
3. **Add PostgreSQL** (se crea automáticamente)
4. **Variables de entorno:**
   - Railway detecta automáticamente `DATABASE_URL` de PostgreSQL
   - Solo necesitas agregar `FLASK_SECRET`
5. **Importar base de datos:** Similar a Render, usando pgAdmin o psql

---

## Notas Importantes

### Archivos que NO se suben a GitHub:
- `.env` (debe estar en `.gitignore`)
- Archivos `.pkl` de modelos ML (si son muy grandes)
- `logs_sistema.md`

### Variables de Entorno Necesarias:
```
DATABASE_URL=postgresql://...
FLASK_SECRET=tu-clave-secreta
FLASK_ENV=production
SMTP_HOST=... (opcional)
SMTP_PORT=... (opcional)
SMTP_USER=... (opcional)
SMTP_PASSWORD=... (opcional)
SMTP_FROM_EMAIL=... (opcional)
SMTP_FROM_NAME=... (opcional)
```

### Si tienes modelos ML grandes:
Si tus archivos `.pkl` son muy grandes (>100MB), considera:
1. Subirlos a un servicio de almacenamiento (AWS S3, Google Cloud Storage)
2. O usar Git LFS (Large File Storage)
3. O cargarlos manualmente después del deployment

### Límites del Plan Gratis de Render:
- **Web Service:** Se "duerme" después de 15 minutos de inactividad (se despierta automáticamente al usarlo)
- **PostgreSQL:** 90 días gratis, luego $7/mes
- **Build time:** Limitado pero suficiente para proyectos pequeños

---

## Solución de Problemas

### Error: "Module not found"
- Verifica que `requirements.txt` tenga todas las dependencias
- Revisa los logs de build en Render

### Error: "Database connection failed"
- Verifica que `DATABASE_URL` esté correctamente configurada
- Asegúrate de usar la "Internal Database URL" (no la externa)

### Error: "Application error"
- Revisa los logs en Render (sección "Logs")
- Verifica que `gunicorn` esté instalado (debe estar en `requirements.txt`)

### La aplicación se "duerme"
- Es normal en el plan gratis
- Se despierta automáticamente cuando alguien accede (puede tardar 30-60 segundos)

---

## Actualizar el Sistema

Cada vez que quieras actualizar:

1. Haz cambios en tu código local
2. Commit y push a GitHub:
   ```bash
   git add .
   git commit -m "Descripción de cambios"
   git push
   ```
3. Render detecta el cambio y despliega automáticamente
4. Espera 5-10 minutos para que termine el deployment

---

¡Listo! Tu sistema estará disponible en un link público. 🎉

