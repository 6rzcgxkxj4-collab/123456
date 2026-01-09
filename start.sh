#!/bin/bash

# 面部识别签到系统启动脚本

echo "=========================================="
echo "   面部识别自动签到系统"
echo "=========================================="
echo ""

# 检查Python版本
echo "检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3，请先安装Python 3.7+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✓ Python版本: $PYTHON_VERSION"
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
    echo "✓ 虚拟环境创建成功"
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate
echo "✓ 虚拟环境已激活"
echo ""

# 安装依赖
if [ ! -f ".dependencies_installed" ]; then
    echo "安装依赖包（首次运行可能需要较长时间）..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        touch .dependencies_installed
        echo "✓ 依赖包安装成功"
    else
        echo "❌ 依赖包安装失败，请检查错误信息"
        exit 1
    fi
else
    echo "✓ 依赖包已安装"
fi
echo ""

# 初始化数据库
if [ ! -f "attendance.db" ]; then
    echo "初始化数据库..."
    python init_db.py
    echo "✓ 数据库初始化成功"
else
    echo "✓ 数据库已存在"
fi
echo ""

# 创建必要的目录
mkdir -p uploads
echo "✓ 上传目录已准备"
echo ""

# 启动应用
echo "=========================================="
echo "启动应用..."
echo "=========================================="
echo ""
echo "访问地址: http://localhost:5000"
echo "按 Ctrl+C 停止服务器"
echo ""

python app.py
