@echo off
REM 面部识别签到系统启动脚本 (Windows)

echo ==========================================
echo    面部识别自动签到系统
echo ==========================================
echo.

REM 检查Python
echo 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)
echo ✓ Python已安装
echo.

REM 检查虚拟环境
if not exist "venv" (
    echo 创建虚拟环境...
    python -m venv venv
    echo ✓ 虚拟环境创建成功
)

REM 激活虚拟环境
echo 激活虚拟环境...
call venv\Scripts\activate.bat
echo ✓ 虚拟环境已激活
echo.

REM 安装依赖
if not exist ".dependencies_installed" (
    echo 安装依赖包（首次运行可能需要较长时间）...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    
    if errorlevel 0 (
        echo. > .dependencies_installed
        echo ✓ 依赖包安装成功
    ) else (
        echo ❌ 依赖包安装失败，请检查错误信息
        pause
        exit /b 1
    )
) else (
    echo ✓ 依赖包已安装
)
echo.

REM 初始化数据库
if not exist "attendance.db" (
    echo 初始化数据库...
    python init_db.py
    echo ✓ 数据库初始化成功
) else (
    echo ✓ 数据库已存在
)
echo.

REM 创建必要的目录
if not exist "uploads" mkdir uploads
echo ✓ 上传目录已准备
echo.

REM 启动应用
echo ==========================================
echo 启动应用...
echo ==========================================
echo.
echo 访问地址: http://localhost:5000
echo 按 Ctrl+C 停止服务器
echo.

python app.py
pause
