@echo off
REM ============================================
REM  Script para compilar FinanzasApp a .exe
REM  Requiere: Python + PyInstaller
REM ============================================

python -m PyInstaller --onefile --windowed --name FinanzasApp ^
    --add-data "assets/logo.png;assets" ^
    --add-data "assets/logo.ico;assets" ^
    --icon "assets/logo.ico" ^
    --hidden-import "cryptography" ^
    --hidden-import "cryptography.fernet" ^
    --hidden-import "cryptography.hazmat.primitives.kdf.pbkdf2" ^
    --hidden-import "cryptography.hazmat.primitives.hashes" ^
    --distpath "dist" --workpath "build" --specpath "." ^
    src/main.py

if %errorlevel% equ 0 (
    echo.
    echo [OK] Ejecutable generado en: dist\FinanzasApp.exe
    echo.
) else (
    echo.
    echo [ERROR] Fallo la compilacion.
    echo.
)
