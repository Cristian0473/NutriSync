# 📚 Librerías Utilizadas y Justificación

## 📋 Índice

1. [Introducción](#introducción)
2. [Librerías de Backend (Python)](#librerías-de-backend-python)
3. [Librerías de Machine Learning](#librerías-de-machine-learning)
4. [Librerías de Base de Datos](#librerías-de-base-de-datos)
5. [Librerías de Frontend](#librerías-de-frontend)
6. [Resumen y Justificación](#resumen-y-justificación)

---

## 🎯 Introducción

Este documento detalla todas las librerías utilizadas en el sistema, explicando **qué hace cada una** y **por qué fue elegida** para este proyecto.

### **Archivo de Dependencias**

Las dependencias están definidas en `requirements.txt`:

```txt
Flask==3.0.2
Werkzeug==3.0.1
python-dotenv==1.0.1
gunicorn==21.2.0
psycopg[binary]>=3.2.0
psycopg-pool>=3.2.0
pandas>=2.0.0
numpy>=1.24.0
xgboost>=2.0.0
scikit-learn>=1.3.0
```

---

## 🐍 Librerías de Backend (Python)

### **1. Flask (3.0.2)**

**¿Qué es?**  
Framework web ligero para Python que permite crear aplicaciones web rápidamente.

**¿Por qué la usamos?**
- ✅ **Simplicidad**: Framework minimalista, fácil de aprender y usar
- ✅ **Flexibilidad**: Permite estructurar la aplicación como queramos
- ✅ **Rutas y Endpoints**: Fácil definición de rutas HTTP (GET, POST)
- ✅ **Templates**: Integración nativa con Jinja2 para renderizar HTML
- ✅ **Sesiones**: Manejo integrado de sesiones de usuario
- ✅ **Extensibilidad**: Fácil de extender con extensiones

**Uso en el sistema**:
- Definición de todas las rutas (`@app.route`)
- Manejo de autenticación y sesiones
- Renderizado de templates HTML
- APIs REST para comunicación frontend-backend

**Ejemplo**:
```python
@app.route("/admin/pacientes")
@admin_required
def admin_pacientes():
    return render_template("admin/pacientes_list.html")
```

---

### **2. Werkzeug (3.0.1)**

**¿Qué es?**  
Biblioteca de utilidades WSGI (Web Server Gateway Interface) que Flask usa internamente.

**¿Por qué la usamos?**
- ✅ **Dependencia de Flask**: Viene incluida con Flask
- ✅ **Utilidades de seguridad**: `generate_password_hash()`, `check_password_hash()`
- ✅ **Manejo de URLs**: Funciones para construir URLs
- ✅ **Utilidades HTTP**: Manejo de requests y responses

**Uso en el sistema**:
- Hash de contraseñas (`werkzeug.security`)
- Validación de datos de formularios
- Manejo de archivos subidos

**Ejemplo**:
```python
from werkzeug.security import generate_password_hash, check_password_hash

# Hash de contraseña
hash_pwd = generate_password_hash("contraseña123")

# Verificar contraseña
if check_password_hash(hash_pwd, "contraseña123"):
    # Contraseña correcta
```

---

### **3. python-dotenv (1.0.1)**

**¿Qué es?**  
Librería para cargar variables de entorno desde archivos `.env`.

**¿Por qué la usamos?**
- ✅ **Configuración segura**: No hardcodear credenciales en el código
- ✅ **Separación de entornos**: Diferentes configuraciones para local y producción
- ✅ **Facilidad de uso**: Carga automática de variables desde `.env`
- ✅ **Mejores prácticas**: Estándar en desarrollo Python

**Uso en el sistema**:
- Cargar `DATABASE_URL` para conexión a PostgreSQL
- Cargar `FLASK_SECRET` para sesiones
- Cargar credenciales SMTP para envío de emails
- Configuración de variables de entorno en Render

**Ejemplo**:
```python
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
```

---

### **4. Gunicorn (21.2.0)**

**¿Qué es?**  
Servidor WSGI HTTP para Python, diseñado para producción.

**¿Por qué la usamos?**
- ✅ **Producción**: Servidor robusto para entornos de producción
- ✅ **Múltiples workers**: Permite manejar múltiples requests simultáneamente
- ✅ **Recomendado para Flask**: Servidor estándar para Flask en producción
- ✅ **Render.com**: Compatible con plataformas de hosting como Render

**Uso en el sistema**:
- Servidor de producción en Render
- Manejo de múltiples requests concurrentes
- Configurado en `Procfile` para despliegue

**Ejemplo** (`Procfile`):
```
web: gunicorn main:app
```

---

## 🤖 Librerías de Machine Learning

### **5. XGBoost (>=2.0.0)**

**¿Qué es?**  
Algoritmo de Machine Learning de tipo "gradient boosting" optimizado para rendimiento y precisión.

**¿Por qué la usamos?**
- ✅ **Mejor rendimiento**: AUC-ROC de 0.861 (vs 0.811 y 0.719 de otros algoritmos)
- ✅ **Bien calibrado**: Detecta bien ambas clases (buen y mal control glucémico)
- ✅ **Regularización integrada**: Previene sobreajuste automáticamente
- ✅ **Manejo de clases desbalanceadas**: Ideal para datos clínicos
- ✅ **Optimización eficiente**: Algoritmo muy rápido
- ✅ **Robusto para datos tabulares**: Perfecto para datos clínicos estructurados

**Uso en el sistema**:
- **Modelo 1**: XGBoost Regressor para predecir respuesta glucémica
- **Modelo 2**: XGBoost Classifier para seleccionar alimentos adecuados
- **Modelo 3**: XGBoost como parte del Ensemble para optimizar combinaciones

**Ejemplo**:
```python
import xgboost as xgb

# Entrenamiento (en scripts de entrenamiento)
modelo = xgb.XGBRegressor()
modelo.fit(X_train, y_train)

# Predicción (en motor_recomendacion.py)
prediccion = modelo.predict(X_test)
```

**Justificación técnica**:
- Después de comparar con Logistic Regression y Random Forest, XGBoost obtuvo las mejores métricas
- Accuracy: 0.786 (vs 0.261 y 0.329)
- AUC-ROC: 0.861 (vs 0.811 y 0.719)
- F1-Score: 0.522 (vs 0.289 y 0.310)

---

### **6. scikit-learn (>=1.3.0)**

**¿Qué es?**  
Biblioteca de Machine Learning para Python con herramientas de preprocesamiento, modelado y evaluación.

**¿Por qué la usamos?**
- ✅ **Preprocesamiento**: `StandardScaler`, `SimpleImputer` para preparar datos
- ✅ **Evaluación**: Métricas de evaluación (accuracy, precision, recall, F1, AUC-ROC)
- ✅ **Utilidades**: Funciones auxiliares para ML
- ✅ **Estándar de la industria**: Librería más usada en ML con Python

**Uso en el sistema**:
- Preprocesamiento de datos antes de entrenar modelos
- Escalado de features (normalización)
- Imputación de valores faltantes
- Evaluación de modelos durante entrenamiento

**Ejemplo**:
```python
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

# Escalar features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Imputar valores faltantes
imputer = SimpleImputer(strategy='mean')
X_imputed = imputer.fit_transform(X)
```

---

### **7. pandas (>=2.0.0)**

**¿Qué es?**  
Biblioteca para manipulación y análisis de datos estructurados (DataFrames).

**¿Por qué la usamos?**
- ✅ **Estructura de datos**: DataFrames para manejar datos tabulares
- ✅ **Preparación de features**: Fácil manipulación de datos para ML
- ✅ **Compatibilidad con ML**: Integración perfecta con scikit-learn y XGBoost
- ✅ **Manejo de datos faltantes**: Funciones para manejar NaN
- ✅ **Estándar en ML**: Librería esencial para Machine Learning

**Uso en el sistema**:
- Preparar features del paciente para modelos ML
- Crear DataFrames con datos estructurados
- Manejar datos faltantes antes de preprocesar
- Compatibilidad con modelos ML que esperan DataFrames

**Ejemplo**:
```python
import pandas as pd

# Crear DataFrame con features
features = {
    'age': [50],
    'bmi': [28.5],
    'a1c': [7.2]
}
df = pd.DataFrame(features)

# Usar con modelo ML
prediccion = modelo.predict(df)
```

---

### **8. numpy (>=1.24.0)**

**¿Qué es?**  
Biblioteca fundamental para computación científica en Python, con arrays multidimensionales y funciones matemáticas.

**¿Por qué la usamos?**
- ✅ **Dependencia de ML**: Requerida por pandas, scikit-learn y XGBoost
- ✅ **Operaciones matemáticas**: Cálculos eficientes con arrays
- ✅ **Compatibilidad**: Base para todas las librerías de ML
- ✅ **Rendimiento**: Operaciones optimizadas en C

**Uso en el sistema**:
- Operaciones matemáticas en cálculos nutricionales
- Arrays para datos numéricos
- Compatibilidad con modelos ML
- Cálculos de IMC, metabolismo basal, etc.

**Ejemplo**:
```python
import numpy as np

# Calcular IMC
imc = peso / (talla ** 2)

# Manejar NaN
valor = np.nan if dato is None else dato
```

---

## 🗄️ Librerías de Base de Datos

### **9. psycopg[binary] (>=3.2.0)**

**¿Qué es?**  
Adaptador de PostgreSQL para Python (versión 3, la más moderna).

**¿Por qué la usamos?**
- ✅ **PostgreSQL nativo**: Adaptador oficial y más eficiente para PostgreSQL
- ✅ **Versión 3**: Versión moderna con mejor rendimiento que psycopg2
- ✅ **Pool de conexiones**: Soporte nativo para pools de conexiones
- ✅ **SSL/TLS**: Soporte completo para conexiones seguras
- ✅ **Async support**: Soporte para operaciones asíncronas (futuro)

**Uso en el sistema**:
- Todas las conexiones a la base de datos PostgreSQL
- Ejecución de consultas SQL
- Transacciones y commits
- Manejo de errores de conexión

**Ejemplo**:
```python
from psycopg_pool import ConnectionPool

pool = ConnectionPool(conninfo=DATABASE_URL)
with pool.connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM paciente WHERE id=%s", (id,))
        resultado = cur.fetchone()
```

---

### **10. psycopg-pool (>=3.2.0)**

**¿Qué es?**  
Librería para manejar pools de conexiones con psycopg3.

**¿Por qué la usamos?**
- ✅ **Eficiencia**: Reutiliza conexiones en lugar de crear nuevas cada vez
- ✅ **Rendimiento**: Reduce latencia en consultas frecuentes
- ✅ **Gestión automática**: Maneja apertura/cierre de conexiones automáticamente
- ✅ **Configuración flexible**: Permite configurar tamaño del pool, timeouts, etc.

**Uso en el sistema**:
- Pool de conexiones en `Core/bd_conexion.py`
- Reutilización de conexiones para múltiples consultas
- Manejo automático de reconexiones en caso de errores

**Ejemplo**:
```python
from psycopg_pool import ConnectionPool

pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=1,
    max_size=5,
    max_idle=300,
    max_lifetime=3600
)
```

---

## 🌐 Librerías de Frontend

### **11. Chart.js (CDN)**

**¿Qué es?**  
Librería JavaScript para crear gráficos interactivos.

**¿Por qué la usamos?**
- ✅ **Visualización de datos**: Gráficos de evolución de pacientes
- ✅ **Fácil de usar**: API simple y documentación excelente
- ✅ **Interactividad**: Gráficos interactivos con hover y zoom
- ✅ **Responsive**: Se adapta a diferentes tamaños de pantalla
- ✅ **CDN**: No requiere instalación, se carga desde CDN

**Uso en el sistema**:
- Gráficos de evolución de antropometría en dashboard de pacientes
- Gráficos de evolución de datos clínicos
- Visualización de tendencias temporales

**Ejemplo**:
```javascript
// En templates/paciente/mi_progreso.html
new Chart(ctx, {
    type: 'line',
    data: {
        labels: fechas,
        datasets: [{
            label: 'Peso (kg)',
            data: pesos
        }]
    }
});
```

---

### **12. Font Awesome (CDN)**

**¿Qué es?**  
Librería de iconos vectoriales.

**¿Por qué la usamos?**
- ✅ **Iconos profesionales**: Gran variedad de iconos médicos y de interfaz
- ✅ **Fácil de usar**: Solo agregar clases CSS
- ✅ **Escalable**: Iconos vectoriales que se ven bien en cualquier tamaño
- ✅ **CDN**: No requiere instalación

**Uso en el sistema**:
- Iconos en toda la interfaz (dashboard, menús, botones)
- Iconos médicos (estetoscopio, pastillas, etc.)
- Iconos de acción (editar, eliminar, guardar, etc.)

**Ejemplo**:
```html
<i class="fas fa-user-md"></i> Nutricionista
<i class="fas fa-chart-line"></i> Dashboard
```

---

### **13. Toastify (CDN)**

**¿Qué es?**  
Librería JavaScript para mostrar notificaciones toast elegantes.

**¿Por qué la usamos?**
- ✅ **Notificaciones elegantes**: Alertas visuales no intrusivas
- ✅ **Fácil de usar**: API simple
- ✅ **Personalizable**: Colores, posiciones, duración
- ✅ **CDN**: No requiere instalación

**Uso en el sistema**:
- Notificaciones de éxito/error en operaciones
- Alertas de validación en formularios
- Mensajes informativos al usuario

**Ejemplo**:
```javascript
Toastify({
    text: "Plan guardado correctamente",
    duration: 3000,
    gravity: "top",
    position: "right",
    backgroundColor: "#10b981"
}).showToast();
```

---

## 📦 Librerías Estándar de Python

### **Librerías incluidas en Python (no requieren instalación)**

#### **pickle**
- **Uso**: Serialización/deserialización de modelos ML
- **Por qué**: Formato estándar para guardar modelos entrenados

#### **json**
- **Uso**: Manejo de datos JSON (APIs, almacenamiento)
- **Por qué**: Formato estándar para intercambio de datos

#### **datetime**
- **Uso**: Manejo de fechas y tiempos
- **Por qué**: Cálculos de edad, fechas de planes, vencimientos

#### **urllib.parse**
- **Uso**: Parsing de URLs (para DATABASE_URL)
- **Por qué**: Manejo de parámetros SSL en URLs de conexión

#### **smtplib**
- **Uso**: Envío de emails (SMTP)
- **Por qué**: Envío de tokens de activación por email

---

## 📊 Resumen y Justificación

### **Tabla Resumen de Librerías**

| Librería | Versión | Propósito | Justificación |
|----------|---------|-----------|----------------|
| **Flask** | 3.0.2 | Framework web | Simplicidad, flexibilidad, estándar para Python |
| **Werkzeug** | 3.0.1 | Utilidades WSGI | Seguridad (hash passwords), incluida con Flask |
| **python-dotenv** | 1.0.1 | Variables de entorno | Configuración segura, separación de entornos |
| **Gunicorn** | 21.2.0 | Servidor WSGI | Producción, múltiples workers, estándar Flask |
| **XGBoost** | >=2.0.0 | Machine Learning | Mejor rendimiento (AUC-ROC: 0.861) |
| **scikit-learn** | >=1.3.0 | ML utilities | Preprocesamiento, evaluación, estándar ML |
| **pandas** | >=2.0.0 | Manipulación de datos | DataFrames, compatibilidad ML, estándar |
| **numpy** | >=1.24.0 | Computación numérica | Base para ML, operaciones matemáticas |
| **psycopg[binary]** | >=3.2.0 | PostgreSQL adapter | Nativo, eficiente, versión moderna |
| **psycopg-pool** | >=3.2.0 | Connection pooling | Eficiencia, reutilización de conexiones |

### **Justificación por Categoría**

#### **Backend Web**
- **Flask**: Elegido por simplicidad y flexibilidad sobre Django (más pesado)
- **Gunicorn**: Estándar de la industria para Flask en producción

#### **Machine Learning**
- **XGBoost**: Elegido después de comparación con otros algoritmos (mejor AUC-ROC: 0.861)
- **scikit-learn**: Estándar de la industria, esencial para preprocesamiento
- **pandas/numpy**: Base fundamental para cualquier proyecto de ML

#### **Base de Datos**
- **psycopg3**: Versión moderna y eficiente, mejor que psycopg2
- **Pool de conexiones**: Necesario para aplicaciones web con múltiples usuarios

#### **Configuración**
- **python-dotenv**: Mejores prácticas de desarrollo, seguridad

---

## 🎯 Conclusión

Todas las librerías fueron elegidas con criterios específicos:

1. ✅ **Rendimiento**: XGBoost, psycopg3 para mejor eficiencia
2. ✅ **Estándares de la industria**: Flask, scikit-learn, pandas
3. ✅ **Seguridad**: Werkzeug para hash de passwords, python-dotenv para configuración
4. ✅ **Producción**: Gunicorn para servidor robusto
5. ✅ **Compatibilidad**: Librerías que trabajan bien juntas

El sistema utiliza **librerías modernas, eficientes y bien mantenidas** que son estándar en la industria para desarrollo web con Python y Machine Learning.

