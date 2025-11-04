@echo off
echo ====================================
echo  Generator Dock API Server
echo ====================================
echo.
echo Starting FastAPI server on port 8000...
echo API Docs: http://localhost:8000/docs
echo.

REM 가상환경 활성화 (있다면)
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM FastAPI 서버 실행
uvicorn api:app --reload --port 8000

pause

