@echo off
REM Caminho até o interpretador pythonw.exe (sem terminal)
set PYTHONW=c:\users\dante\AppData\Local\Programs\Python\Python312\pythonw.exe

REM Caminho completo até o script
set SCRIPT=C:\b3analise\backend\scripts\monitorar_recomendacoes.py

start "" "%PYTHONW%" "%SCRIPT%"
