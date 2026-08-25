@echo off
setlocal

cd /d "%~dp0.."

call docker compose up -d --build
if errorlevel 1 exit /b %errorlevel%

call docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.microservices.yml up -d --build
if errorlevel 1 exit /b %errorlevel%

powershell -ExecutionPolicy Bypass -File "%~dp0ensure-local-hosts.ps1"
if errorlevel 1 exit /b %errorlevel%

powershell -ExecutionPolicy Bypass -File "%~dp0wait-for-services.ps1"
if errorlevel 1 exit /b %errorlevel%

powershell -ExecutionPolicy Bypass -File "%~dp0Check-Microservices.ps1"
exit /b %errorlevel%
