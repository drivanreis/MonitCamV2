@echo off
rem Simple runner for Windows CMD: create venv, install deps, and run main.py

rem Detecta um comando Python utilizavel (tenta: py, python, python3)
set "SYSTEM_PY="
echo Detectando interpretador Python...

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set "SYSTEM_PY=py -3"
  %SYSTEM_PY% -c "import sys" >nul 2>nul
  if %ERRORLEVEL% neq 0 set "SYSTEM_PY="
)

if not defined SYSTEM_PY (
  echo Tentando 'python'...
  where python >nul 2>nul
  if %ERRORLEVEL%==0 (
    set "SYSTEM_PY=python"
    %SYSTEM_PY% -c "import sys" >nul 2>nul
    if %ERRORLEVEL% neq 0 set "SYSTEM_PY="
  )
)

if not defined SYSTEM_PY (
  echo Tentando 'python3'...
  where python3 >nul 2>nul
  if %ERRORLEVEL%==0 (
    set "SYSTEM_PY=python3"
    %SYSTEM_PY% -c "import sys" >nul 2>nul
    if %ERRORLEVEL% neq 0 set "SYSTEM_PY="
  )
)

if not defined SYSTEM_PY (
  echo Erro: nenhum interpretador Python valido encontrado. Instale Python 3.x e reexecute.
  exit /b 1
)

echo Encontrado interpretador: %SYSTEM_PY%
if exist ".venv" (
  echo .venv existente -> ativando sem recriar...
  set "VENV_PY=.venv\Scripts\python.exe"
  if exist "%VENV_PY%" (
    set "PY=%VENV_PY%"
  ) else (
    echo ATENCAO: .venv existe, mas %VENV_PY% nao encontrado. Usando %SYSTEM_PY%.
    set "PY=%SYSTEM_PY%"
  )
) else (
  echo Criando virtual environment .venv usando %SYSTEM_PY% ...
  %SYSTEM_PY% -m venv .venv
  set "VENV_PY=.venv\Scripts\python.exe"
  if exist "%VENV_PY%" (
    set "PY=%VENV_PY%"
  )
  if not defined PY (
    set "PY=%SYSTEM_PY%"
  )
  echo Usando interpretador: %PY%
  echo Installing dependencies...
  %PY% -m pip install --upgrade pip >nul
  %PY% -m pip install -r requirements.txt
)

echo Usando interpretador: %PY%
echo Running MonitCam (Ctrl+C to stop)...
%PY% main.py
