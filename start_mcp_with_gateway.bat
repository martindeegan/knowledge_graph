@echo off
REM Start Knowledge Engine MCP Server with SuperGateway in parallel
echo Starting Knowledge Engine MCP Server and SuperGateway...

REM Set environment variables
set DANGEROUSLY_OMIT_AUTH=true
set PYTHONUNBUFFERED=1

REM Change to the correct directory
cd /d "C:\Users\mddee\knowledge_engine"

REM Start the MCP server in background on port 6969
echo Starting MCP Server on port 6969...
start /B "MCP Server" uv run ke-server --port 6969 --workspace knowledge_engine

REM Wait a moment for the server to start
timeout /t 3 /nobreak >nul

REM Start SuperGateway
echo Starting SuperGateway...
npx supergateway

REM If we reach here, SuperGateway has exited
echo SuperGateway has stopped. Cleaning up...

REM Kill the MCP server when SuperGateway exits
taskkill /F /IM "python.exe" /T >nul 2>&1
taskkill /F /IM "ke-server.exe" /T >nul 2>&1

echo All processes stopped.
pause 