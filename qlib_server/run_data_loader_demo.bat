@echo off
echo 正在启动Qlib多模态数据加载器验证工具...

REM 检查Python环境
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 错误: 未找到Python，请确保Python已安装并添加到PATH中
    pause
    exit /b 1
)

REM 检查并创建虚拟环境
if not exist venv (
    echo 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 安装依赖
echo 安装必要的依赖...
pip install pandas numpy matplotlib streamlit pillow

REM 运行Streamlit应用
echo 启动Streamlit应用...
streamlit run visualization\data_loader_demo.py

REM 如果应用关闭，保持窗口打开
pause
