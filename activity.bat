@echo off
chcp 65001 >nul
REM Запуск симулятора активности

REM Переход в директорию скрипта
cd /d "%~dp0"

REM Проверяем, установлен ли пакет
python -c "import activity_simulator" 2>nul
if %errorlevel% neq 0 (
    echo Пакет activity_simulator не установлен, устанавливаем...
    pip install -e . --no-warn-script-location
    if %errorlevel% neq 0 (
        echo Ошибка при установке пакета!
        pause
        exit /b 1
    )
)

REM Запускаем симулятор
start python -m activity_simulator
