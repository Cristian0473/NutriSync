# bd_conexion.py
# Conexión a PostgreSQL con psycopg3 + pool y helpers simples.

import os
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv

load_dotenv()

# Puedes usar una sola URL (DATABASE_URL) o las variables separadas.
DB_URL = os.getenv("DATABASE_URL")

if DB_URL:
    # Ej.: postgresql://user:pass@host:5432/dbname?sslmode=disable
    CONNINFO = DB_URL
else:
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    name = os.getenv("PGDATABASE", "proyecto_tesis")
    user = os.getenv("PGUSER", "postgres")
    pwd  = os.getenv("PGPASSWORD", "")

    # En local normalmente NO necesitas sslmode=require.
    CONNINFO = f"host={host} port={port} dbname={name} user={user} password={pwd}"

POOL_MIN = int(os.getenv("POOL_MIN", "1"))
POOL_MAX = int(os.getenv("POOL_MAX", "5"))

pool = ConnectionPool(conninfo=CONNINFO, min_size=POOL_MIN, max_size=POOL_MAX, open=True)


def fetch_one(sql: str, params: tuple | None = None):
    """Devuelve una tupla (row) o None."""
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()


def fetch_all(sql: str, params: tuple | None = None):
    """Devuelve lista de tuplas."""
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()


def execute(sql: str, params: tuple | None = None):
    """Ejecuta INSERT/UPDATE/DELETE y hace commit."""
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            conn.commit()
