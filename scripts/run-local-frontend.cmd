@echo off
setlocal
cd /d "%~dp0.."
if not exist ".server-logs" mkdir ".server-logs"
"C:\Program Files\nodejs\npm.cmd" run dev > ".server-logs\frontend.log" 2>&1
