# A股量化分析工具

这是一个基于Python的A股分析工具,提供数据获取、技术分析和量化策略回测功能。

## 功能特点

### 1. 数据获取 (data_fetcher.py)
- 使用 **AKShare** 获取实时和历史A股数据
- 支持股票列表、历史行情、实时行情
- 支持指数数据、概念板块成分股
- 批量获取多只股票数据

### 2. 技术指标分析 (technical_analysis.py)
实现了常用的技术分析指标:
- **均线系统**: MA、EMA
- **动量指标**: MACD、RSI、KDJ
- **波动指标**: 布林带(BOLL)、ATR
- **成交量指标**: 成交量均线
- **信号识别**: 金叉、死叉

### 3. 高级股票筛选器 ⭐ (advanced_screener.py)
多条件精准筛选:
- 股价相对MA120位置筛选
- 涨幅区间筛选
- 历史涨停检测
- 流通市值筛选
- 换手率区间筛选
- 排除科创板/ST股票
- 批量分析并生成报告

### 4. 相似股票推荐系统 🔥 (similar_stocks.py)
智能推荐相似股票:
- 多维度相似度计算
- 趋势相似度分析(MA走势)
- 动量相似度(MACD, RSI)
- 波动率匹配
- 成交量特征对比
- 资金流向相似度
- 股票详细对比功能

### 5. 量化策略 (strategies/)
实现了多个经典量化策略:

#### 双均线策略 (dual_ma_strategy.py)
- 短期均线上穿长期均线 → 买入
- 短期均线下穿长期均线 → 卖出
- 适合趋势性行情

#### MACD策略 (macd_strategy.py)
- MACD金叉 → 买入
- MACD死叉 → 卖出
- 适合捕捉中短期趋势

#### KDJ策略 (kdj_strategy.py)
- J值超卖区上穿 → 买入
- J值超买区下穿 → 卖出
- KDJ金叉死叉辅助判断

## 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖:
- `akshare`: A股数据获取
- `pandas`: 数据处理
- `numpy`: 数值计算
- `matplotlib`: 数据可视化
- `pandas-ta`: 技术指标(可选)

## 使用方法

### 快速开始 - 高级筛选器 ⭐

```bash
# 直接运行高级筛选器
python run_screener.py
```

筛选条件:
- ✅ 股价在MA120附近(95%-105%)
- ✅ 当日涨幅2.5%-5%
- ✅ 最近20天内有涨停
- ✅ 流通市值40-300亿
- ✅ 换手率5%-10%
- ✅ 排除科创板和ST股票

### 运行主程序

```bash
python main.py
```

### 使用示例

#### 1. 获取股票数据

```python
from src.data_fetcher import StockDataFetcher

fetcher = StockDataFetcher()

# 获取贵州茅台历史数据
df = fetcher.get_stock_hist(
    symbol="600519",
    start_date="20240101",
    end_date="20241231"
)
```

#### 2. 计算技术指标

```python
from src.technical_analysis import TechnicalIndicators

# 计算所有技术指标
df_with_indicators = TechnicalIndicators.calculate_all_indicators(df)

# 或单独计算某个指标
df = TechnicalIndicators.calculate_macd(df)
df = TechnicalIndicators.calculate_kdj(df)
```

#### 3. 策略回测

```python
from strategies.dual_ma_strategy import DualMovingAverageStrategy

# 创建策略
strategy = DualMovingAverageStrategy(short_period=5, long_period=20)

# 回测
result = strategy.backtest(df, initial_capital=100000)

print(f"总收益率: {result['total_return']:.2f}%")
print(f"交易次数: {len(result['trade_log'])}")
```

#### 4. 高级股票筛选

```python
from src.advanced_screener import AdvancedStockScreener

screener = AdvancedStockScreener()

# 多条件筛选
result = screener.screen_stocks(
    min_price_to_ma120_ratio=0.95,  # 股价在MA120附近
    max_price_to_ma120_ratio=1.05,
    min_daily_change=2.5,            # 当日涨幅2.5%-5%
    max_daily_change=5.0,
    check_limit_up_days=20,          # 最近20天内有涨停
    min_market_cap=40,               # 流通市值40-300亿
    max_market_cap=300,
    min_turnover=5.0,                # 换手率5%-10%
    max_turnover=10.0,
    exclude_kcb=True,                # 排除科创板
    exclude_st=True                  # 排除ST
)

# 显示和保存结果
screener.print_results()
screener.save_results()
```

## 项目结构

```
stock_analysis/
├── README.md                      # 项目说明
├── requirements.txt               # 依赖包
├── main.py                        # 主程序(所有功能演示)
├── run_screener.py               # 快速运行高级筛选器 ⭐
├── data/                          # 数据目录
├── src/                           # 源代码
│   ├── data_fetcher.py           # 数据获取模块
│   ├── technical_analysis.py     # 技术分析模块
│   └── advanced_screener.py      # 高级筛选器 ⭐
└── strategies/                    # 策略目录
    ├── dual_ma_strategy.py       # 双均线策略
    ├── macd_strategy.py          # MACD策略
    └── kdj_strategy.py           # KDJ策略
```

## 工具推荐

### 数据源
1. **AKShare** (推荐⭐⭐⭐⭐⭐)
   - 完全免费,无需注册
   - 数据全面,更新及时
   - API简单易用
   - 支持A股、港股、美股等多个市场

2. **TuShare** (备选)
   - 需要积分或付费
   - 数据更稳定
   - 适合专业用户

### 技术分析库
1. **pandas-ta** (推荐)
   - 130+ 技术指标
   - 与pandas完美集成

2. **TA-Lib** (经典)
   - 金融市场标准库
   - 需要编译安装

### 回测框架
1. **Backtrader** (推荐)
   - 功能强大
   - 支持复杂策略

2. **vnpy**
   - 国产框架
   - 支持实盘交易

## 策略说明

### 双均线策略
- **优点**: 简单易懂,趋势明确时表现好
- **缺点**: 震荡市容易产生虚假信号
- **适用**: 趋势性强的股票

### MACD策略
- **优点**: 能捕捉中短期趋势,信号相对可靠
- **缺点**: 滞后性,可能错过启动点
- **适用**: 波段操作

### KDJ策略
- **优点**: 对短期波动敏感,适合短线
- **缺点**: 容易钝化,需结合其他指标
- **适用**: 活跃股票的短线交易

## 注意事项

1. **数据获取**: AKShare免费但有访问频率限制,建议添加延时
2. **回测局限**: 历史回测不代表未来收益,注意过拟合
3. **交易成本**: 实际交易需考虑手续费、滑点等成本
4. **风险控制**: 建议添加止损、仓位管理等风险控制机制

## 扩展建议

1. **增加更多策略**:
   - 布林带突破策略
   - RSI反转策略
   - 量价配合策略

2. **优化功能**:
   - 添加数据可视化(K线图)
   - 实现组合策略
   - 添加风险管理模块
   - 支持实时监控和预警

3. **性能优化**:
   - 数据缓存
   - 并行计算
   - 数据库存储

## 免责声明

本工具仅供学习和研究使用,不构成任何投资建议。
股市有风险,投资需谨慎。

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request!

---

**开始使用:**

```bash
# 安装依赖
pip install -r requirements.txt

# 运行示例
python main.py
```

祝您使用愉快! 📈
