@echo off
echo Starting Knowledge Engine Visualizer...

REM Default values
set API_URL=http://127.0.0.1:6969
set PORT=3000

REM Parse command line arguments
:parse_args
if "%1"=="--api" (
    set API_URL=%2
    shift
    shift
    goto parse_args
)
if "%1"=="--port" (
    set PORT=%2
    shift
    shift
    goto parse_args
)
if "%1"=="--help" (
    echo Usage: run_visualizer.bat [--api API_URL] [--port PORT]
    echo.
    echo Options:
    echo   --api API_URL    Knowledge Engine API URL (default: http://127.0.0.1:6969)
    echo   --port PORT      Port to run the frontend on (default: 3000)
    echo   --help           Show this help message
    goto :eof
)
if not "%1"=="" (
    shift
    goto parse_args
)

echo API Backend: %API_URL%
echo Frontend Port: %PORT%
echo.

REM Run the visualizer
python src/knowledge_engine/visualization/serve_frontend.py --api %API_URL% --port %PORT% 