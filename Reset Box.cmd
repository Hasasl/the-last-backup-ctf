@echo off
echo Reset options: -Status  -Linux  -Portal  -Verifier [-Team id]  -Scores  -Players  -All  -FullWipe  -Backup  -DryRun
echo Example: "Reset Box.cmd" -All
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0local\reset.ps1" %*
pause
