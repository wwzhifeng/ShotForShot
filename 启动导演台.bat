@echo off
rem Pure ASCII on purpose: cmd.exe mis-parses multibyte characters in .bat files.
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"
set "PY=%ROOT%runtime\python\python.exe"
if not exist "%PY%" (
  echo [ERROR] Missing runtime\python\python.exe - please extract the full package again.
  pause
  exit /b 1
)
set "PYTHONDONTWRITEBYTECODE=1"
set "NO_PROXY=localhost,127.0.0.1,::1"
set "HTTP_PROXY="
set "HTTPS_PROXY="
set "ALL_PROXY="
"%PY%" -I -X utf8 -c "import os,runpy,sys;r=sys.argv[1];d=chr(0x7a0b)+chr(0x5e8f);sys.argv=[os.path.join(r,d,'launcher.py')];runpy.run_path(sys.argv[0],run_name='__main__')" "%ROOT%."
if errorlevel 1 pause
endlocal
