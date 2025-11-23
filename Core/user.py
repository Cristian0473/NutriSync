from werkzeug.security import generate_password_hash
from Core.bd_conexion import execute, fetch_one

# Crear usuario admin
email = "admin@nutrisync.com"
pwd = generate_password_hash("Admin123")

# Insertar usuario y recuperar id
uid = fetch_one("""
    INSERT INTO usuario (email, hash_pwd, estado, mfa)
    VALUES (%s, %s, 'activo', FALSE)
    RETURNING id
""", (email, pwd))[0]

# Buscar id del rol admin
rid = fetch_one("SELECT id FROM rol WHERE nombre='admin'")[0]

# Asignar rol
execute("INSERT INTO usuario_rol (usuario_id, rol_id) VALUES (%s,%s)", (uid, rid))

print("✅ Usuario admin creado correctamente:", email)
