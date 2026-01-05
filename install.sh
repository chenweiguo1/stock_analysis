#!/bin/bash

# A股分析工具 - 快速安装脚本

echo "======================================"
echo "A股分析工具 - 依赖安装"
echo "======================================"
echo ""

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "当前Python版本: $python_version"
echo ""

# 使用国内镜像源加速安装
echo "使用清华大学镜像源加速安装..."
echo ""

# 方式1: 最小化安装(推荐,快速)
echo "【方式1】最小化安装(推荐)"
echo "只安装核心依赖: akshare, pandas, numpy"
echo ""
read -p "是否选择最小化安装? (y/n): " choice

if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
    echo ""
    echo "开始安装核心依赖..."
    pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple akshare pandas numpy
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ 安装成功!"
        echo ""
        echo "现在可以运行:"
        echo "  python3 run_screener.py  # 股票筛选"
        echo "  python3 main.py          # 完整功能"
    else
        echo ""
        echo "❌ 安装失败,请检查网络连接"
    fi
else
    echo ""
    echo "【方式2】完整安装"
    echo "安装所有依赖(包括可视化、回测框架等)"
    echo ""
    read -p "确认完整安装? (y/n): " full_choice
    
    if [ "$full_choice" = "y" ] || [ "$full_choice" = "Y" ]; then
        echo ""
        echo "开始完整安装..."
        pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ 完整安装成功!"
        else
            echo ""
            echo "❌ 安装失败,建议使用最小化安装"
            echo "或手动安装: pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple akshare pandas numpy"
        fi
    fi
fi

echo ""
echo "======================================"
