@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Nandha Admission System - Launcher

echo ============================================================
echo   Nandha Engineering College - Admission Assistance System
echo   Backend + Frontend + Telegram Bot (+ optional ngrok app link)
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found on PATH.
  echo         Install Python 3.10+ and enable "Add Python to PATH".
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js/npm was not found on PATH.
  echo         Install Node.js 18+ from https://nodejs.org and retry.
  pause
  exit /b 1
)

REM ---------- Backend: .env, venv, dependencies ----------
pushd backend
if not exist ".env" (
  if exist ".env.example" copy /y ".env.example" ".env" >nul
)
if not exist "venv\Scripts\python.exe" (
  echo [setup] Creating Python virtual environment ...
  python -m venv venv
)
echo [setup] Installing backend dependencies ...
"venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Backend dependency installation failed.
  popd
  pause
  exit /b 1
)
popd

REM ---------- Frontend dependencies ----------
pushd frontend
if not exist "node_modules" (
  echo [setup] Installing frontend dependencies ^(first run, please wait^) ...
  call npm install
  if errorlevel 1 (
    echo [ERROR] Frontend dependency installation failed.
    popd
    pause
    exit /b 1
  )
)
popd

REM ---------- ngrok public link (whole app, optional / best effort) ----------
set "NGROK_URL="
where ngrok >nul 2>nul && goto :has_ngrok
echo [ngrok] ngrok not found on this PC - using LAN IP for QR codes.
goto :reset_url

:has_ngrok
echo [ngrok] Opening a public tunnel for the web app ^(and its /api backend^) ...
start "Ngrok (Public App Tunnel)" cmd /k "ngrok http 5173"
echo [ngrok] Waiting for the tunnel to come up ...
timeout /t 8 /nobreak >nul
for /f "delims=" %%u in ('powershell -NoProfile -Command "(try { (Invoke-RestMethod http://127.0.0.1:4040/api/tunnels).tunnels[0].public_url } catch {})"') do set "NGROK_URL=%%u"
if not defined NGROK_URL (
  echo [ngrok] Tunnel not ready yet - using LAN IP for QR codes.
) else (
  echo [ngrok] Public app link ready.
)
:reset_url
REM Point the reception QR codes at the public URL when a tunnel exists,
REM otherwise clear PUBLIC_BASE_URL so QR codes use the LAN IP (no stale URL).
if defined NGROK_URL powershell -NoProfile -Command "$u='%NGROK_URL%'; $p=Join-Path (Get-Location) 'backend\.env'; $c=@(Get-Content -LiteralPath $p); $hit=$false; for($i=0;$i -lt $c.Count;$i++){ if($c[$i] -match '^PUBLIC_BASE_URL='){ $c[$i]='PUBLIC_BASE_URL='+$u; $hit=$true } }; if($hit){ [IO.File]::WriteAllLines($p,$c,(New-Object Text.UTF8Encoding($false))) } else { [IO.File]::AppendAllText($p,[Environment]::NewLine+'PUBLIC_BASE_URL='+$u,(New-Object Text.UTF8Encoding($false))) }"
if not defined NGROK_URL powershell -NoProfile -Command "$p=Join-Path (Get-Location) 'backend\.env'; if(Test-Path -LiteralPath $p){ $c=@(Get-Content -LiteralPath $p); for($i=0;$i -lt $c.Count;$i++){ if($c[$i] -match '^PUBLIC_BASE_URL='){ $c[$i]='PUBLIC_BASE_URL='; [IO.File]::WriteAllLines($p,$c,(New-Object Text.UTF8Encoding($false))) } } }"

:servers
echo.
echo Launching servers in separate windows ...
pushd backend
start "Nandha Backend (API :8000)" cmd /k ""venv\Scripts\python.exe" run.py"
popd
pushd frontend
start "Nandha Frontend (App :5173)" cmd /k "npm run dev"
popd

echo.
echo Waiting for the servers to come up ...
timeout /t 9 /nobreak >nul
if defined NGROK_URL (
  start "" "%NGROK_URL%"
) else (
  start "" http://localhost:5173
)

echo.
echo ============================================================
echo   Web app      : http://localhost:5173
echo   Backend API  : http://localhost:8000   (docs at /docs)
if defined NGROK_URL (
  echo   PUBLIC APP   : %NGROK_URL%
  echo                 WhatsApp webhook : %NGROK_URL%/api/whatsapp/webhook
)
echo   Telegram bot : @Academic_Nandhabot
echo   Logins       : admin/admin123  ^|  reception/reception123
echo.
echo   To STOP: close the "Nandha ..." and "Ngrok ..." windows.
echo ============================================================
pause
endlocal