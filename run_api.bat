@echo off
title Generator Dock API Server
color 0A

echo ====================================
echo  Generator Dock API Server
echo ====================================
echo.
echo Starting FastAPI server on port 8000...
echo API Docs: http://localhost:8000/docs
echo.
echo [로그 창] 이 창에서 모든 로그를 확인할 수 있습니다.
echo [종료] Ctrl+C를 눌러 서버를 종료할 수 있습니다.
echo ====================================
echo.

REM 가상환경 활성화 (있다면)
if exist venv\Scripts\activate.bat (
    echo [INFO] 가상환경 활성화 중...
    call venv\Scripts\activate.bat
)

REM FastAPI 서버 실행 (상세 로그 + 컬러 출력)
echo [INFO] FastAPI 서버 시작...
echo.
python -u api.py

pause

