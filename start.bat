@echo off
cd /d "C:\Users\张家程\shelf-manager"

echo ============================================
echo   实验室货架管理系统
echo ============================================
echo.
echo 启动 ngrok 隧道...
start "ngrok" "C:\ngrok\ngrok.exe" http 8501 --log=stdout

echo 启动 Streamlit...
streamlit run app.py --server.port 8501 --server.headless true

pause
