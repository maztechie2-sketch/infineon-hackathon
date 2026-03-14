@echo off
title BugSlayers GUI Backend
echo.
echo  ============================================
echo   BUGSLAYERS - Infineon Agentic Bug Detection
echo   GUI Backend starting on http://localhost:8000
echo  ============================================
echo.
echo  Make sure MCP server is running in another window!
echo  Make sure Ollama is running!
echo.
cd /d "C:\Users\Sana\Hackathons\infineon-hackathon\gui\backend"
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
pause
