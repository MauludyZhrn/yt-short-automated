@echo off
title Menghentikan Shorts AutoBot
color 0C

echo ==========================================
echo   Mematikan server Shorts AutoBot...
echo ==========================================
echo.

:: Mematikan semua proses Python secara paksa
taskkill /F /IM python.exe /T

echo.
echo ==========================================
echo   Bot berhasil dihentikan!
echo ==========================================
timeout /t 3 >nul