@echo off
chcp 65001 >nul
title Diagnostico - FOLGAS ATENDIMENTO
cd /d "%~dp0"
echo ==========================================
echo  DIAGNOSTICO DO SISTEMA
echo ==========================================
echo.
echo Pasta atual:
echo %cd%
echo.
echo Procurando Python:
where python
echo.
echo Versao do Python:
python --version
echo.
echo Versao do Pip:
python -m pip --version
echo.
echo Testando Streamlit:
python -m streamlit --version
echo.
echo Arquivos da pasta:
dir
echo.
echo Se alguma linha acima mostrou ERRO, tire foto desta tela e envie.
pause
