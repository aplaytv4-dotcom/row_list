@echo off
setlocal

echo =============================
echo Компиляция AttendanceApp
echo =============================

where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo.
    echo PyInstaller не найден.
    echo Установите PyInstaller заранее.
    echo Например: python -m pip install pyinstaller
    pause
    exit /b 1
)

echo PyInstaller найден. Запуск сборки...
python -m PyInstaller attendance_app.spec
if errorlevel 1 (
    echo.
    echo Ошибка компиляции.
    pause
    exit /b 1
)

echo.
echo Компиляция завершена.
echo Быстрый вариант exe находится в dist\attendance_app\attendance_app.exe
pause
endlocal
