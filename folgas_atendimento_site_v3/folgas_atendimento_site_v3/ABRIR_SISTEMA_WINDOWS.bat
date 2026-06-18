@echo off
chcp 65001 >nul
title FOLGAS ATENDIMENTO - Abrir Sistema
cd /d "%~dp0"

echo ==========================================
echo  FOLGAS ATENDIMENTO - INICIANDO SISTEMA
echo ==========================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set PY_CMD=py
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set PY_CMD=python
    ) else (
        echo ERRO: Python nao encontrado no computador.
        echo.
        echo Instale o Python pelo site python.org e marque a opcao:
        echo "Add Python to PATH"
        echo.
        pause
        exit /b 1
    )
)

echo Python encontrado. Instalando/atualizando dependencias...
echo.
%PY_CMD% -m pip install --upgrade pip
%PY_CMD% -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ERRO ao instalar dependencias.
    echo Confira sua internet e se o Python foi instalado corretamente.
    pause
    exit /b 1
)

echo.
echo Abrindo o site no navegador...
echo Quando terminar, feche esta janela para encerrar o sistema.
echo.
%PY_CMD% -m streamlit run app.py

echo.
pause
