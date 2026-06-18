@echo off
chcp 65001 >nul
title FOLGAS ATENDIMENTO - Sistema
cd /d "%~dp0"

echo ==========================================
echo  FOLGAS ATENDIMENTO - ABRINDO SISTEMA
echo ==========================================
echo.
echo Pasta atual: %cd%
echo.

REM Usa preferencialmente python direto, pois em alguns Windows o comando py nao abre o mesmo Python instalado.
where python >nul 2>nul
if %errorlevel%==0 (
    set PY_CMD=python
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set PY_CMD=py
    ) else (
        echo ERRO: Python nao encontrado.
        echo Instale o Python e marque Add Python to PATH.
        echo.
        pause
        exit /b 1
    )
)

echo Verificando Python...
%PY_CMD% --version
if %errorlevel% neq 0 (
    echo ERRO: Nao foi possivel executar o Python.
    pause
    exit /b 1
)

echo.
echo Instalando dependencias necessarias...
%PY_CMD% -m pip install --upgrade pip
%PY_CMD% -m pip install streamlit pandas openpyxl
if %errorlevel% neq 0 (
    echo.
    echo ERRO ao instalar dependencias.
    echo Se apareceu mensagem de internet ou permissao, copie a mensagem e envie para o ChatGPT.
    echo.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  O sistema vai abrir no navegador.
echo  Se nao abrir sozinho, copie este endereco:
echo.
echo  http://localhost:8501
echo ==========================================
echo.

REM Abre o navegador alguns segundos depois, enquanto o Streamlit sobe.
start "" cmd /c "timeout /t 6 >nul && start http://localhost:8501"

%PY_CMD% -m streamlit run app.py --server.port 8501 --server.address localhost --browser.gatherUsageStats false

echo.
echo O sistema foi encerrado ou ocorreu algum erro.
echo Se deu erro, envie uma foto desta janela.
pause
