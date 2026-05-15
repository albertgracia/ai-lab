@echo off
setlocal

echo.
echo ==^> Generando backup local de AGITHome
echo.

powershell -NoProfile -Command "New-Item -ItemType Directory -Force -Path 'D:\DockerContainers\backups' | Out-Null; Compress-Archive -Path 'D:\DockerContainers\Webs\AGITHome\*' -DestinationPath 'D:\DockerContainers\backups\agithome-backup.zip' -Force"

if errorlevel 1 (
  echo.
  echo El backup ha terminado con errores.
  pause
  exit /b 1
)

echo.
echo Backup generado en D:\DockerContainers\backups\agithome-backup.zip
pause
exit /b 0
