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

rem -------------------------------------------------------------------------
:remove_venv
rem tenta remover .venv com retries; se falhar, permite ao usuario retentar ou abortar
set "RM_TRIES=0"
:remove_loop
set /A RM_TRIES+=1
echo Tentativa %RM_TRIES%: removendo .venv ...
rmdir /S /Q ".venv" >nul 2>nul
if %ERRORLEVEL%==0 goto :remove_done
echo rmdir falhou. Finalizando processos python e tentando PowerShell...
taskkill /IM python.exe /F >nul 2>nul
taskkill /IM python3.exe /F >nul 2>nul
powershell -Command "Remove-Item -Recurse -Force '.venv'" >nul 2>nul
if %ERRORLEVEL%==0 goto :remove_done
if %RM_TRIES% LSS 4 (
  echo Tentativa %RM_TRIES% falhou; aguardando 1s e tentando novamente...
  timeout /t 1 >nul
  goto :remove_loop
)
echo Nao foi possivel remover .venv apos %RM_TRIES% tentativas.
choice /c RT /n /m "R=Retentar  T=Terminar (abort) "
if %ERRORLEVEL%==1 (
  echo Usuario escolheu retentar...
  goto :remove_loop
) else (
  echo Abortando execucao. Remova .venv manualmente e reexecute.
  exit /b 1
)
:remove_done
echo .venv removido com sucesso.
goto :eof
rem -------------------------------------------------------------------------
