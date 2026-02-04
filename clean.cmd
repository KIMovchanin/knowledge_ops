@echo off
setlocal

powershell -ExecutionPolicy Bypass -File "%~dp0clean.ps1"
if errorlevel 1 (
  echo.
  echo Failed to run clean.ps1. If PowerShell is blocked, run this in PowerShell:
  echo   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  echo.
  exit /b 1
)
