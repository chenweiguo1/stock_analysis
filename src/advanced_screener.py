"""
高级股票筛选器
实现复杂的多条件筛选功能
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
from src.data_fetcher import StockDataFetcher
from src.technical_analysis import TechnicalIndicators


class AdvancedStockScreener:
    """高级股票筛选器"""
    
    def __init__(self):
        self.fetcher = StockDataFetcher()
        self.results = []
    
    def screen_stocks(self,
                     min_price_to_ma120_ratio: float = 0.95,
                     max_price_to_ma120_ratio: float = 1.05,
                     min_daily_change: float = 2.5,
                     max_daily_change: float = 5.0,
                     check_limit_up_days: int = 20,
                     min_market_cap: float = 40,  # 亿
                     max_market_cap: float = 300,  # 亿
                     min_turnover: float = 5.0,
                     max_turnover: float = 10.0,
                     exclude_kcb: bool = True,  # 排除科创板
                     exclude_st: bool = True,  # 排除ST
                     max_stocks: int = 50) -> pd.DataFrame:
        """
        多条件筛选股票
        
        Args:
            min_price_to_ma120_ratio: 股价/MA120最小比例
            max_price_to_ma120_ratio: 股价/MA120最大比例
            min_daily_change: 当日最小涨幅(%)
            max_daily_change: 当日最大涨幅(%)
            check_limit_up_days: 检查涨停的天数范围
            min_market_cap: 最小流通市值(亿)
            max_market_cap: 最大流通市值(亿)
            min_turnover: 最小换手率(%)
            max_turnover: 最大换手率(%)
            exclude_kcb: 是否排除科创板(688开头)
            exclude_st: 是否排除ST股票
            max_stocks: 最多分析的股票数量
            
        Returns:
            DataFrame: 符合条件的股票列表
        """
        print("=" * 60)
        print("开始高级股票筛选...")
        print("=" * 60)
        
        # 获取股票列表
        print("\n正在获取股票列表...")
        stock_list = self.fetcher.get_stock_list()
        
        if stock_list.empty:
            print("无法获取股票列表")
            return pd.DataFrame()
        
        print(f"获取到 {len(stock_list)} 只股票")
        
        # 第一步:基础筛选(快速过滤)
        print("\n第一步:基础条件筛选...")
        filtered_stocks = stock_list.copy()
        
        # 排除科创板(688开头)
        if exclude_kcb:
            filtered_stocks = filtered_stocks[~filtered_stocks['代码'].str.startswith('688')]
            print(f"  排除科创板后: {len(filtered_stocks)} 只")
        
        # 排除ST股票
        if exclude_st:
            filtered_stocks = filtered_stocks[~filtered_stocks['名称'].str.contains('ST', na=False)]
            print(f"  排除ST股票后: {len(filtered_stocks)} 只")
        
        # 当日涨幅筛选
        filtered_stocks = filtered_stocks[
            (filtered_stocks['涨跌幅'] >= min_daily_change) & 
            (filtered_stocks['涨跌幅'] <= max_daily_change)
        ]
        print(f"  当日涨幅{min_daily_change}%-{max_daily_change}%: {len(filtered_stocks)} 只")
        
        # 换手率筛选
        filtered_stocks = filtered_stocks[
            (filtered_stocks['换手率'] >= min_turnover) & 
            (filtered_stocks['换手率'] <= max_turnover)
        ]
        print(f"  换手率{min_turnover}%-{max_turnover}%: {len(filtered_stocks)} 只")
        
        # 流通市值筛选(总市值近似替代,单位:亿)
        filtered_stocks = filtered_stocks[
            (filtered_stocks['总市值'] >= min_market_cap * 1e8) & 
            (filtered_stocks['总市值'] <= max_market_cap * 1e8)
        ]
        print(f"  流通市值{min_market_cap}-{max_market_cap}亿: {len(filtered_stocks)} 只")
        
        if filtered_stocks.empty:
            print("\n没有股票通过基础筛选")
            return pd.DataFrame()
        
        # 限制分析数量
        if len(filtered_stocks) > max_stocks:
            print(f"\n股票数量较多,仅分析前 {max_stocks} 只")
            filtered_stocks = filtered_stocks.head(max_stocks)
        
        # 第二步:历史数据筛选(需要获取历史数据)
        print(f"\n第二步:历史数据筛选(共{len(filtered_stocks)}只)...")
        
        qualified_stocks = []
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
        
        for idx, row in filtered_stocks.iterrows():
            symbol = row['代码']
            name = row['名称']
            
            try:
                print(f"  正在分析 {symbol} {name}...", end="")
                
                # 获取历史数据
                df = self.fetcher.get_stock_hist(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if df.empty or len(df) < 120:
                    print(" 数据不足")
                    continue
                
                # 计算MA120
                df['MA120'] = df['收盘'].rolling(window=120).mean()
                
                # 获取最新数据
                latest = df.iloc[-1]
                
                # 检查股价是否在MA120附近
                if pd.isna(latest['MA120']):
                    print(" MA120数据不足")
                    continue
                
                price_to_ma120 = latest['收盘'] / latest['MA120']
                
                if not (min_price_to_ma120_ratio <= price_to_ma120 <= max_price_to_ma120_ratio):
                    print(f" 股价/MA120={price_to_ma120:.3f} 不符合")
                    continue
                
                # 检查最近N天内是否有涨停(涨幅>9.5%)
                recent_days = df.tail(check_limit_up_days)
                has_limit_up = (recent_days['涨跌幅'] >= 9.5).any()
                
                if not has_limit_up:
                    print(" 近期无涨停")
                    continue
                
                # 找到涨停的日期
                limit_up_dates = recent_days[recent_days['涨跌幅'] >= 9.5]['日期'].tolist()
                
                # 通过所有条件
                qualified_stocks.append({
                    '代码': symbol,
                    '名称': name,
                    '最新价': latest['收盘'],
                    '当日涨幅': row['涨跌幅'],
                    'MA120': latest['MA120'],
                    '价格/MA120': price_to_ma120,
                    '换手率': row['换手率'],
                    '总市值(亿)': row['总市值'] / 1e8,
                    '涨停日期': limit_up_dates[-1].strftime('%Y-%m-%d'),
                    '涨停次数': len(limit_up_dates)
                })
                
                print(" ✓ 符合条件!")
                
                # 避免请求过快
                time.sleep(0.3)
                
            except Exception as e:
                print(f" 错误: {e}")
                continue
        
        # 整理结果
        if not qualified_stocks:
            print("\n没有股票符合所有条件")
            return pd.DataFrame()
        
        result_df = pd.DataFrame(qualified_stocks)
        
        # 按涨幅排序
        result_df = result_df.sort_values('当日涨幅', ascending=False)
        
        print("\n" + "=" * 60)
        print(f"筛选完成!共找到 {len(result_df)} 只符合条件的股票")
        print("=" * 60)
        
        self.results = result_df
        return result_df
    
    def save_results(self, filename: str = None):
        """
        保存筛选结果到CSV文件
        
        Args:
            filename: 文件名,默认使用日期命名
        """
        if self.results.empty:
            print("没有结果可保存")
            return
        
        if filename is None:
            filename = f"data/screened_stocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        self.results.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存到: {filename}")
    
    def print_results(self):
        """打印筛选结果"""
        if self.results.empty:
            print("没有筛选结果")
            return
        
        print("\n" + "=" * 80)
        print("筛选结果详情:")
        print("=" * 80)
        
        # 设置显示选项
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.unicode.east_asian_width', True)
        
        # 格式化显示
        display_df = self.results.copy()
        display_df['最新价'] = display_df['最新价'].apply(lambda x: f"{x:.2f}")
        display_df['当日涨幅'] = display_df['当日涨幅'].apply(lambda x: f"{x:.2f}%")
        display_df['MA120'] = display_df['MA120'].apply(lambda x: f"{x:.2f}")
        display_df['价格/MA120'] = display_df['价格/MA120'].apply(lambda x: f"{x:.3f}")
        display_df['换手率'] = display_df['换手率'].apply(lambda x: f"{x:.2f}%")
        display_df['总市值(亿)'] = display_df['总市值(亿)'].apply(lambda x: f"{x:.2f}")
        
        print(display_df.to_string(index=False))
        print("=" * 80)
    
    def get_detailed_analysis(self, symbol: str):
        """
        获取某只股票的详细分析
        
        Args:
            symbol: 股票代码
        """
        print(f"\n详细分析: {symbol}")
        print("-" * 60)
        
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
        
        # 获取历史数据
        df = self.fetcher.get_stock_hist(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if df.empty:
            print("无法获取数据")
            return
        
        # 计算技术指标
        df = TechnicalIndicators.calculate_all_indicators(df)
        
        # 计算MA120
        df['MA120'] = df['收盘'].rolling(window=120).mean()
        
        # 显示最近数据
        print("\n最近10天行情:")
        columns = ['日期', '收盘', '涨跌幅', 'MA5', 'MA20', 'MA120', 'RSI14', 'K', 'D', 'J']
        
        # 检查哪些列存在
        available_columns = [col for col in columns if col in df.columns]
        print(df[available_columns].tail(10).to_string(index=False))
        
        # 统计涨停信息
        limit_ups = df[df['涨跌幅'] >= 9.5].tail(5)
        if not limit_ups.empty:
            print(f"\n最近涨停记录(共{len(limit_ups)}次):")
            print(limit_ups[['日期', '收盘', '涨跌幅', '成交量']].to_string(index=False))


def run_custom_screen():
    """运行自定义筛选"""
    screener = AdvancedStockScreener()
    
    # 筛选条件
    result = screener.screen_stocks(
        min_price_to_ma120_ratio=0.95,  # 股价在MA120的95%-105%之间
        max_price_to_ma120_ratio=1.05,
        min_daily_change=2.5,            # 当日涨幅2.5%-5%
        max_daily_change=5.0,
        check_limit_up_days=20,          # 最近20天内有涨停
        min_market_cap=40,               # 流通市值40-300亿
        max_market_cap=300,
        min_turnover=5.0,                # 换手率5%-10%
        max_turnover=10.0,
        exclude_kcb=True,                # 排除科创板
        exclude_st=True,                 # 排除ST
        max_stocks=100                   # 最多分析100只
    )
    
    if not result.empty:
        # 打印结果
        screener.print_results()
        
        # 保存结果
        screener.save_results()
        
        # 询问是否查看详细分析
        print("\n" + "=" * 60)
        choice = input("是否查看某只股票的详细分析? (输入股票代码,或按回车跳过): ").strip()
        if choice:
            screener.get_detailed_analysis(choice)


if __name__ == "__main__":
    run_custom_screen()
