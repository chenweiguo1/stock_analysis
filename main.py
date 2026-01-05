"""
A股分析工具 - 主程序
演示如何使用各个模块进行股票分析
"""
import sys
sys.path.append('src')
sys.path.append('strategies')

from data_fetcher import StockDataFetcher
from technical_analysis import TechnicalIndicators
from dual_ma_strategy import DualMovingAverageStrategy
from macd_strategy import MACDStrategy
from kdj_strategy import KDJStrategy
from advanced_screener import AdvancedStockScreener
from similar_stocks import SimilarStockFinder
import pandas as pd
from datetime import datetime, timedelta


def example_1_get_stock_data():
    """示例1: 获取股票数据"""
    print("=" * 50)
    print("示例1: 获取股票数据")
    print("=" * 50)
    
    fetcher = StockDataFetcher()
    
    # 获取贵州茅台(600519)最近1年的数据
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    
    df = fetcher.get_stock_hist(
        symbol="600519",
        start_date=start_date,
        end_date=end_date
    )
    
    print(f"\n获取到 {len(df)} 条数据")
    print("\n前5条数据:")
    print(df.head())
    print("\n最近5条数据:")
    print(df.tail())
    
    return df


def example_2_technical_analysis(df):
    """示例2: 技术指标分析"""
    print("\n" + "=" * 50)
    print("示例2: 技术指标分析")
    print("=" * 50)
    
    # 计算所有技术指标
    df_with_indicators = TechnicalIndicators.calculate_all_indicators(df)
    
    # 显示最近的数据和指标
    print("\n最近5天的技术指标:")
    columns_to_show = ['日期', '收盘', 'MA5', 'MA20', 'MACD', 'RSI14', 'K', 'D', 'J']
    print(df_with_indicators[columns_to_show].tail())
    
    # 寻找金叉和死叉
    df_with_signals = TechnicalIndicators.find_golden_cross(df_with_indicators)
    df_with_signals = TechnicalIndicators.find_death_cross(df_with_signals)
    
    # 显示最近的交叉信号
    golden_crosses = df_with_signals[df_with_signals['Golden_Cross'] == True]
    death_crosses = df_with_signals[df_with_signals['Death_Cross'] == True]
    
    print(f"\n最近的金叉信号 (共{len(golden_crosses)}次):")
    if len(golden_crosses) > 0:
        print(golden_crosses[['日期', '收盘', 'MA5', 'MA20']].tail(3))
    
    print(f"\n最近的死叉信号 (共{len(death_crosses)}次):")
    if len(death_crosses) > 0:
        print(death_crosses[['日期', '收盘', 'MA5', 'MA20']].tail(3))
    
    return df_with_indicators


def example_3_backtest_strategies(df):
    """示例3: 策略回测"""
    print("\n" + "=" * 50)
    print("示例3: 量化策略回测")
    print("=" * 50)
    
    initial_capital = 100000
    
    # 1. 双均线策略
    print("\n1. 双均线策略 (MA5 & MA20)")
    print("-" * 40)
    dual_ma = DualMovingAverageStrategy(short_period=5, long_period=20)
    result1 = dual_ma.backtest(df, initial_capital)
    
    print(f"初始资金: ¥{result1['initial_capital']:,.2f}")
    print(f"最终资金: ¥{result1['final_value']:,.2f}")
    print(f"总收益率: {result1['total_return']:.2f}%")
    print(f"交易次数: {len(result1['trade_log'])}")
    
    if len(result1['trade_log']) > 0:
        print("\n最近3次交易:")
        for trade in result1['trade_log'][-3:]:
            print(f"  {trade['date'].strftime('%Y-%m-%d')} - {trade['action']} @ ¥{trade['price']:.2f}")
    
    # 2. MACD策略
    print("\n2. MACD策略")
    print("-" * 40)
    macd = MACDStrategy()
    result2 = macd.backtest(df, initial_capital)
    
    print(f"初始资金: ¥{result2['initial_capital']:,.2f}")
    print(f"最终资金: ¥{result2['final_value']:,.2f}")
    print(f"总收益率: {result2['total_return']:.2f}%")
    print(f"交易次数: {len(result2['trade_log'])}")
    
    # 3. KDJ策略
    print("\n3. KDJ策略")
    print("-" * 40)
    kdj = KDJStrategy()
    result3 = kdj.backtest(df, initial_capital)
    
    print(f"初始资金: ¥{result3['initial_capital']:,.2f}")
    print(f"最终资金: ¥{result3['final_value']:,.2f}")
    print(f"总收益率: {result3['total_return']:.2f}%")
    print(f"交易次数: {len(result3['trade_log'])}")
    
    # 策略对比
    print("\n" + "=" * 50)
    print("策略收益对比:")
    print("-" * 40)
    strategies_comparison = pd.DataFrame({
        '策略': ['双均线', 'MACD', 'KDJ'],
        '收益率(%)': [
            result1['total_return'],
            result2['total_return'],
            result3['total_return']
        ],
        '交易次数': [
            len(result1['trade_log']),
            len(result2['trade_log']),
            len(result3['trade_log'])
        ]
    })
    strategies_comparison = strategies_comparison.sort_values('收益率(%)', ascending=False)
    print(strategies_comparison.to_string(index=False))


def example_4_stock_screener():
    """示例4: 股票筛选器"""
    print("\n" + "=" * 50)
    print("示例4: 股票筛选 - 寻找金叉机会")
    print("=" * 50)
    
    fetcher = StockDataFetcher()
    
    # 获取部分股票列表(示例只取前20只)
    print("\n正在获取股票列表...")
    stock_list = fetcher.get_stock_list()
    
    if stock_list.empty:
        print("无法获取股票列表")
        return
    
    # 只分析前10只股票作为演示
    sample_stocks = stock_list.head(10)
    
    golden_cross_stocks = []
    
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
    
    print(f"\n正在分析 {len(sample_stocks)} 只股票...")
    
    for idx, row in sample_stocks.iterrows():
        symbol = row['代码']
        name = row['名称']
        
        try:
            df = fetcher.get_stock_hist(symbol, start_date, end_date)
            if df.empty or len(df) < 20:
                continue
            
            # 计算均线
            df = TechnicalIndicators.calculate_ma(df, periods=[5, 20])
            
            # 检查最近是否有金叉
            df = TechnicalIndicators.find_golden_cross(df)
            recent_golden_cross = df[df['Golden_Cross'] == True].tail(1)
            
            if not recent_golden_cross.empty:
                days_ago = (datetime.now() - recent_golden_cross['日期'].iloc[0]).days
                if days_ago <= 5:  # 5天内的金叉
                    golden_cross_stocks.append({
                        '代码': symbol,
                        '名称': name,
                        '金叉日期': recent_golden_cross['日期'].iloc[0],
                        '当前价': row['最新价'],
                        '涨跌幅': row['涨跌幅']
                    })
            
        except Exception as e:
            continue
    
    if golden_cross_stocks:
        print(f"\n发现 {len(golden_cross_stocks)} 只近期金叉股票:")
        print(pd.DataFrame(golden_cross_stocks).to_string(index=False))
    else:
        print("\n未发现近期金叉的股票(分析样本较小)")


def example_5_advanced_screener():
    """示例5: 高级股票筛选"""
    print("\n" + "=" * 50)
    print("示例5: 高级多条件筛选")
    print("=" * 50)
    
    screener = AdvancedStockScreener()
    
    print("\n筛选条件:")
    print("  - 股价在MA120附近(95%-105%)")
    print("  - 当日涨幅: 2.5%-5%")
    print("  - 最近20天内有涨停")
    print("  - 流通市值: 40-300亿")
    print("  - 换手率: 5%-10%")
    print("  - 排除科创板和ST股票")
    
    result = screener.screen_stocks(
        min_price_to_ma120_ratio=0.95,
        max_price_to_ma120_ratio=1.05,
        min_daily_change=2.5,
        max_daily_change=5.0,
        check_limit_up_days=20,
        min_market_cap=40,
        max_market_cap=300,
        min_turnover=5.0,
        max_turnover=10.0,
        exclude_kcb=True,
        exclude_st=True,
        max_stocks=500
    )
    
    if not result.empty:
        screener.print_results()
        screener.save_results()
        
        # 询问是否查看详细分析
        print("\n" + "=" * 60)
        choice = input("是否查看某只股票的详细分析? (输入股票代码,或按回车跳过): ").strip()
        if choice:
            screener.get_detailed_analysis(choice)


def example_6_similar_stocks():
    """示例6: 相似股票推荐"""
    print("\n" + "=" * 50)
    print("示例6: 相似股票推荐")
    print("=" * 50)
    
    finder = SimilarStockFinder()
    
    # 输入目标股票
    target = input("\n请输入目标股票代码(如 600519 贵州茅台): ").strip()
    
    if not target:
        print("未输入股票代码")
        return
    
    # 查找相似股票
    print(f"\n正在寻找与 {target} 相似的股票...")
    result = finder.find_similar_stocks(
        target_symbol=target,
        top_n=10,
        min_score=65.0
    )
    
    if not result.empty:
        print("\n" + "=" * 80)
        print("相似股票列表:")
        print("=" * 80)
        
        # 格式化显示
        display_df = result.copy()
        display_df['相似度'] = display_df['相似度'].apply(lambda x: f"{x:.1f}")
        display_df['最新价'] = display_df['最新价'].apply(lambda x: f"{x:.2f}")
        display_df['涨跌幅'] = display_df['涨跌幅'].apply(lambda x: f"{x:.2f}%")
        display_df['换手率'] = display_df['换手率'].apply(lambda x: f"{x:.2f}%")
        display_df['RSI'] = display_df['RSI'].apply(lambda x: f"{x:.1f}")
        display_df['趋势'] = display_df['趋势'].apply(lambda x: f"{x:.2f}")
        
        print(display_df.to_string(index=False))
        
        # 询问是否对比
        print("\n" + "=" * 80)
        compare = input("是否详细对比目标股票与某只相似股票? (输入股票代码,或按回车跳过): ").strip()
        if compare:
            finder.compare_stocks(target, compare)


def main():
    """主函数"""
    print("\n" + "=" * 50)
    print("A股分析工具")
    print("=" * 50)
    
    print("\n请选择示例:")
    print("1. 获取股票数据")
    print("2. 技术指标分析")
    print("3. 策略回测")
    print("4. 股票筛选(简单金叉)")
    print("5. 高级多条件筛选 ⭐")
    print("6. 相似股票推荐 🔥")
    print("7. 运行所有示例")
    print("0. 退出")
    
    choice = input("\n请输入选择 (0-7): ").strip()
    
    if choice == "0":
        print("退出程序")
        return
    
    # 获取数据(示例1-3和7需要)
    if choice in ["1", "2", "3", "7"]:
        df = example_1_get_stock_data()
        
        if choice == "1":
            return
        
        if choice in ["2", "7"]:
            df_with_indicators = example_2_technical_analysis(df)
            
            if choice == "2":
                return
        
        if choice in ["3", "7"]:
            example_3_backtest_strategies(df)
            
            if choice == "3":
                return
    
    if choice == "4":
        example_4_stock_screener()
    
    elif choice == "5":
        example_5_advanced_screener()
    
    elif choice == "6":
        example_6_similar_stocks()
    
    elif choice == "7":
        example_4_stock_screener()
        example_5_advanced_screener()
        example_6_similar_stocks()
        example_4_stock_screener()
        example_5_advanced_screener()


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════╗
    ║      A股量化分析工具                    ║
    ║      Stock Analysis Tool               ║
    ╚════════════════════════════════════════╝
    
    使用的工具和库:
    - AKShare: 免费获取A股数据
    - Pandas: 数据处理
    - NumPy: 数值计算
    
    实现的策略:
    1. 双均线策略 (趋势跟踪)
    2. MACD策略 (动量策略)
    3. KDJ策略 (超买超卖)
    
    技术指标:
    - MA/EMA (移动平均线)
    - MACD (指数平滑异同移动平均线)
    - RSI (相对强弱指标)
    - KDJ (随机指标)
    - BOLL (布林带)
    - ATR (平均真实波幅)
    """)
    
    main()
