@echo off
setlocal

echo.
echo ==^> Generando backup local de AGITServices
echo.

powershell -NoProfile -Command "New-Item -ItemType Directory -Force -Path 'D:\DockerContainers\backups' | Out-Null; Compress-Archive -Path 'D:\DockerContainers\Webs\AGITServices\*' -DestinationPath 'D:\DockerContainers\backups\agitservices-backup.zip' -Force"

if errorlevel 1 (
  echo.
  echo El backup ha terminado con errores.
  pause
  exit /b 1
)

echo.
echo Backup generado en D:\DockerContainers\backups\agitservices-backup.zip
pause
exit /b 0
