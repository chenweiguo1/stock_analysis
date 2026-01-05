# A股分析工具 - 安装指南

## 快速安装 🚀

### 推荐方式:使用国内镜像源最小化安装

```bash
# 方式1: 使用安装脚本(推荐)
chmod +x install.sh
./install.sh

# 方式2: 手动安装核心依赖
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple akshare pandas numpy

# 方式3: 使用最小化依赖文件
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements-minimal.txt
```

## 常见问题解决 ❓

### 1. 安装速度慢/超时

**原因**: 默认使用国外PyPI源,网络较慢

**解决方案**: 使用国内镜像源

```bash
# 临时使用清华源
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple akshare pandas numpy

# 或设置为默认源(一劳永逸)
pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

常用国内镜像源:
- 清华: https://pypi.tuna.tsinghua.edu.cn/simple
- 阿里云: https://mirrors.aliyun.com/pypi/simple/
- 腾讯云: https://mirrors.cloud.tencent.com/pypi/simple

### 2. pandas安装失败

**原因**: pandas 2.0+需要编译,较慢

**解决方案**: 降低版本或使用预编译包

```bash
# 方式1: 使用较低版本
pip3 install pandas==1.5.3

# 方式2: 使用conda安装(如果有)
conda install pandas
```

### 3. ta-lib安装失败

**原因**: ta-lib需要C编译器

**解决方案**: 跳过ta-lib,使用pandas-ta替代

```bash
# ta-lib是可选的,项目已实现所有需要的技术指标
# 不安装ta-lib不影响使用
```

## 验证安装 ✅

```bash
# 测试是否安装成功
python3 -c "import akshare; import pandas; import numpy; print('安装成功!')"
```

## 分阶段安装

### 阶段1: 核心功能(必需)
```bash
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple akshare pandas numpy
```
可运行: 数据获取、技术分析、策略回测、股票筛选

### 阶段2: 可视化(可选)
```bash
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple matplotlib plotly mplfinance
```
可运行: K线图、指标可视化

### 阶段3: 高级功能(可选)
```bash
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple backtrader pandas-ta tqdm
```
可运行: 专业回测、更多技术指标

## 使用虚拟环境(推荐) 🔧

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements-minimal.txt

# 退出虚拟环境
deactivate
```

## macOS特别说明 🍎

```bash
# 如果使用系统Python,建议用pip3
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple akshare pandas numpy

# 或使用homebrew安装的Python
brew install python
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple akshare pandas numpy
```

## 立即开始 🎯

安装完核心依赖后:

```bash
# 运行股票筛选器
python3 run_screener.py

# 或运行主程序
python3 main.py
```

---

**遇到问题?**

1. 确保Python版本 >= 3.8
2. 使用国内镜像源
3. 优先安装最小化依赖
4. 使用虚拟环境避免冲突
