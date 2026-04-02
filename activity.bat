@echo off
REM ����� ����⭮� ���ᨨ activity-simulator

REM ��४��砥��� � ��४��� �ਯ�
cd /d "%~dp0"

REM �஢��塞, ��⠭����� �� �����
python -c "import activity_simulator" 2>nul
if %errorlevel% neq 0 (
    echo ����� activity_simulator �� ������, ��⠭��������...
    pip install -e . --no-warn-script-location
    if %errorlevel% neq 0 (
        echo �訡�� �� ��⠭���� �����!
        pause
        exit /b 1
    )
)

REM ����᪠�� ᨬ����
start python -m activity_simulator
