# bd_conexion.py
# Conexión a PostgreSQL con psycopg3 + pool y helpers simples.

import os
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

# Puedes usar una sola URL (DATABASE_URL) o las variables separadas.
DB_URL = os.getenv("DATABASE_URL")

if DB_URL:
    # Parsear la URL para asegurar configuración SSL correcta
    parsed = urllib.parse.urlparse(DB_URL)
    query_params = urllib.parse.parse_qs(parsed.query)
    
    # Si no tiene sslmode, agregarlo según el entorno
    # En Render (producción) necesitamos SSL, en local puede ser disable
    if 'sslmode' not in query_params:
        # Detectar si estamos en Render (tiene .onrender.com en el host o variable RENDER)
        hostname = parsed.hostname or ""
        if '.onrender.com' in hostname or os.getenv("RENDER") or os.getenv("RENDER_EXTERNAL_HOSTNAME"):
            # En Render, usar require para SSL (obligatorio)
            query_params['sslmode'] = ['require']
        else:
            # En local, puede ser prefer (intenta SSL pero no falla si no está disponible)
            query_params['sslmode'] = ['prefer']
    
    # Reconstruir la URL con los parámetros SSL
    new_query = urllib.parse.urlencode(query_params, doseq=True)
    CONNINFO = urllib.parse.urlunparse((
        parsed.scheme, parsed.netloc, parsed.path,
        parsed.params, new_query, parsed.fragment
    ))
else:
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    name = os.getenv("PGDATABASE", "proyecto_tesis")
    user = os.getenv("PGUSER", "postgres")
    pwd  = os.getenv("PGPASSWORD", "")
    
    # Detectar si estamos en Render
    if '.onrender.com' in host or os.getenv("RENDER"):
        sslmode = "require"
    else:
        sslmode = "prefer"
    
    CONNINFO = f"host={host} port={port} dbname={name} user={user} password={pwd} sslmode={sslmode}"

POOL_MIN = int(os.getenv("POOL_MIN", "1"))
POOL_MAX = int(os.getenv("POOL_MAX", "5"))

# Configurar el pool con reconexión automática y manejo de errores SSL
try:
    pool = ConnectionPool(
        conninfo=CONNINFO,
        min_size=POOL_MIN,
        max_size=POOL_MAX,
        open=True,
        # Configuraciones para manejar desconexiones y SSL
        max_idle=300,  # Cerrar conexiones inactivas después de 5 minutos
        max_lifetime=3600,  # Máximo tiempo de vida de una conexión: 1 hora
    )
except TypeError:
    # Si algunos parámetros no son compatibles, usar configuración básica
    pool = ConnectionPool(
        conninfo=CONNINFO,
        min_size=POOL_MIN,
        max_size=POOL_MAX,
        open=True
    )


def fetch_one(sql: str, params: tuple | None = None):
    """Devuelve una tupla (row) o None."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params or ())
                    return cur.fetchone()
        except Exception as e:
            if attempt < max_retries - 1 and ("SSL" in str(e) or "connection" in str(e).lower()):
                # Reintentar en caso de error SSL o de conexión
                import time
                time.sleep(0.5 * (attempt + 1))  # Backoff exponencial
                continue
            raise


def fetch_all(sql: str, params: tuple | None = None):
    """Devuelve lista de tuplas."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params or ())
                    return cur.fetchall()
        except Exception as e:
            if attempt < max_retries - 1 and ("SSL" in str(e) or "connection" in str(e).lower()):
                # Reintentar en caso de error SSL o de conexión
                import time
                time.sleep(0.5 * (attempt + 1))  # Backoff exponencial
                continue
            raise


def execute(sql: str, params: tuple | None = None):
    """Ejecuta INSERT/UPDATE/DELETE y hace commit."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params or ())
                    conn.commit()
                    return
        except Exception as e:
            if attempt < max_retries - 1 and ("SSL" in str(e) or "connection" in str(e).lower()):
                # Reintentar en caso de error SSL o de conexión
                import time
                time.sleep(0.5 * (attempt + 1))  # Backoff exponencial
                continue
            raise
