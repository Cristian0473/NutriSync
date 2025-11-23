@echo off
chcp 65001 >nul
echo ======================================================================
echo 🎯 PIPELINE COMPLETO DE MACHINE LEARNING
echo ======================================================================
echo.

cd /d "%~dp0"

echo 📂 Directorio actual:
cd
echo.

echo 🚀 Iniciando preparación de datos...
echo.

echo [1/6] Preparando datos para Modelo 1...
python preparar_datos_modelo1_respuesta_glucemica.py
if errorlevel 1 (
    echo ❌ Error en preparación Modelo 1
    pause
    exit /b 1
)

echo.
echo [2/6] Preparando datos para Modelo 2...
python preparar_datos_modelo2_seleccion_alimentos.py
if errorlevel 1 (
    echo ❌ Error en preparación Modelo 2
    pause
    exit /b 1
)

echo.
echo [3/6] Preparando datos para Modelo 3...
python preparar_datos_modelo3_combinaciones.py
if errorlevel 1 (
    echo ❌ Error en preparación Modelo 3
    pause
    exit /b 1
)

echo.
echo [4/6] Entrenando Modelo 1...
python entrenar_modelo1_respuesta_glucemica.py
if errorlevel 1 (
    echo ❌ Error en entrenamiento Modelo 1
    pause
    exit /b 1
)

echo.
echo [5/6] Entrenando Modelo 2...
python entrenar_modelo2_seleccion_alimentos.py
if errorlevel 1 (
    echo ❌ Error en entrenamiento Modelo 2
    pause
    exit /b 1
)

echo.
echo [6/6] Entrenando Modelo 3...
python entrenar_modelo3_combinaciones.py
if errorlevel 1 (
    echo ❌ Error en entrenamiento Modelo 3
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo ✅ PIPELINE COMPLETADO EXITOSAMENTE
echo ======================================================================
pause

