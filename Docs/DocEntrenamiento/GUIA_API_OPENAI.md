# 🔑 Guía para Configurar la API de OpenAI (GPT)

Esta guía te ayudará a configurar la API de OpenAI para mejorar las combinaciones de alimentos en los planes nutricionales.

## 📋 Pasos para Configurar

### 1. **Obtener tu API Key de OpenAI**

1. Ve a: https://platform.openai.com/
2. Crea una cuenta o inicia sesión
3. Ve a: https://platform.openai.com/api-keys
4. Haz clic en "Create new secret key"
5. **Copia la clave** (solo se muestra una vez, guárdala bien)
6. La clave se verá así: `sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 2. **Configurar la API Key (Método más simple - RECOMENDADO)**

**Opción A: Usar archivo .env (MÁS FÁCIL)**

1. Abre el archivo `.env` en la raíz del proyecto
2. Busca la línea: `OPENAI_API_KEY=sk-proj-tu-clave-aqui`
3. Reemplaza `sk-proj-tu-clave-aqui` con tu clave real de OpenAI
4. Guarda el archivo
5. **¡Listo!** No necesitas reiniciar nada, el sistema la cargará automáticamente

**Opción B: Variable de Entorno (Alternativa)**

#### En Windows (PowerShell):
```powershell
# Temporal (solo para esta sesión)
$env:OPENAI_API_KEY = "sk-proj-tu-clave-aqui"

# Permanente (para todas las sesiones)
[System.Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'sk-proj-tu-clave-aqui', 'User')
```

#### En Windows (CMD):
```cmd
# Temporal
set OPENAI_API_KEY=sk-proj-tu-clave-aqui

# Permanente (ejecutar como administrador)
setx OPENAI_API_KEY "sk-proj-tu-clave-aqui"
```

#### En Linux/Mac:
```bash
# Temporal
export OPENAI_API_KEY="sk-proj-tu-clave-aqui"

# Permanente (agregar al archivo ~/.bashrc o ~/.zshrc)
echo 'export OPENAI_API_KEY="sk-proj-tu-clave-aqui"' >> ~/.bashrc
source ~/.bashrc
```

### 3. **Instalar la Librería de OpenAI**

Abre una terminal en la carpeta del proyecto y ejecuta:

```bash
pip install openai
```

### 4. **Verificar que Funciona**

El sistema intentará usar la API automáticamente. Si está configurada correctamente, verás en la consola:

```
✅ Motor de IA inicializado correctamente
```

Si no está configurada, verás:

```
⚠️  OPENAI_API_KEY no configurada. Configura la variable de entorno o pasa api_key
```

## 💰 Costos de la API

- **Modelo usado:** `gpt-4o-mini` (el más económico)
- **Costo aproximado:** 
  - ~$0.15 por cada 1 millón de tokens de entrada
  - ~$0.60 por cada 1 millón de tokens de salida
- **Uso estimado:** 
  - Cada optimización de plan: ~500-1000 tokens
  - Costo por plan: ~$0.0001 - $0.0005 (muy económico)
  - 1000 planes optimizados: ~$0.10 - $0.50

**Recomendación:** Configura un límite de gasto en tu cuenta de OpenAI para evitar sorpresas.

## 🔧 Configuración Alternativa (Sin Variable de Entorno)

Si prefieres no usar variables de entorno, puedes modificar `main.py` para pasar la clave directamente:

```python
# En main.py, buscar donde se inicializa MotorRecomendacion
# y agregar:
motor_ia = MotorIARecomendaciones(api_key="sk-proj-tu-clave-aqui")
```

**⚠️ IMPORTANTE:** No subas tu clave API a Git. Si lo haces, revócala inmediatamente en OpenAI.

## ✅ Verificación

Una vez configurado, cuando generes un plan, el sistema:
1. Intentará usar la API de GPT para mejorar combinaciones
2. Si no está disponible, funcionará normalmente sin IA
3. Verás mensajes en la consola indicando si se está usando IA

## 🆘 Solución de Problemas

**Error: "OpenAI no está instalado"**
```bash
pip install openai
```

**Error: "OPENAI_API_KEY no configurada"**
- Verifica que la variable de entorno esté configurada
- Reinicia la terminal/IDE después de configurarla
- Verifica que la clave sea correcta

**Error: "Invalid API Key"**
- Verifica que copiaste la clave completa
- Asegúrate de que no tenga espacios al inicio/final
- Verifica que la clave no haya expirado en OpenAI

## 📝 Notas

- La API se usa solo para **mejorar combinaciones de alimentos**, no es obligatoria
- El sistema funciona perfectamente sin la API, solo con reglas básicas
- La API ayuda a hacer las combinaciones más apetitosas y culturalmente apropiadas

