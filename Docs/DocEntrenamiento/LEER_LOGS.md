# 📝 Cómo Capturar los Logs Completos

## Opción 1: Script Automático (Recomendado)

1. **Ejecuta el script capturador:**
   ```bash
   python capturar_logs_flask.py
   ```

2. **Abre tu navegador** y regenera un plan nutricional

3. **Los logs se guardarán automáticamente** en `logs_sistema.md`

4. **Cuando termines**, presiona `Ctrl+C` para detener

5. **Comparte el archivo** `logs_sistema.md` completo

## Opción 2: Redirección Manual

Si prefieres hacerlo manualmente:

```bash
python main.py > logs_sistema.txt 2>&1
```

Luego regenera un plan desde la interfaz web.

Para detener: `Ctrl+C`

## Opción 3: Copiar desde Terminal

1. Ejecuta Flask normalmente: `python main.py`
2. Regenera un plan
3. Copia todo el contenido de la terminal
4. Pégalo en un archivo `.txt` o `.md`
5. Compártelo

## ¿Qué buscar en los logs?

Busca estos mensajes para verificar que los modelos se están usando:

- ✅ `Modelo de respuesta glucémica cargado`
- ✅ `Modelo de selección de alimentos cargado`
- ✅ `Modelo de optimización de combinaciones cargado`
- 🤖 `Aplicando modelos ML para filtrar y rankear alimentos...`
- ✅ `X alimentos evaluados y rankeados por ML`
- 🤖 `Modelo 3 - Score combinación: X.XXX`

Si no aparecen estos mensajes, puede haber un problema con la carga de los modelos.

