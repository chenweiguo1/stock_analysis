"""
尾盘选股策略 (14:30专用版)
基于日盈电子(603286)案例分析实现

核心选股逻辑:
1. 技术面(核心): 收盘>MA5, 最低≥MA5(未破线), MA5向上
2. 资金面: 涨幅3-7%, 换手5-15%
3. 趋势面: 5日涨幅>10%, 20日涨幅>15%, 昨日小幅调整
4. 热点板块: 优先选择当前热门板块的股票

案例: 2026-01-06 日盈电子
- 价格: 71.37, +5.06%
- MA5: 67.67 (收盘>MA5✓, 最低67.78≥MA5✓, MA5向上✓)
- 趋势: 5日+15%, 20日+31%
- 板块: 汽车零部件/新能源汽车(热点)
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import time
import sys
sys.path.append('src')

from src.data_fetcher import StockDataFetcher
from src.technical_analysis import TechnicalIndicators


class TailMarketScreener:
    """尾盘选股器 (14:30版)"""
    
    def __init__(self):
        self.fetcher = StockDataFetcher()
        self.hot_sectors = []
        self.results = []
        
    def get_hot_sectors(self) -> List[Dict]:
        """获取当日热门板块"""
        print("\n【第0步】识别热门板块...")
        print("-" * 60)
        
        try:
            stock_list = self.fetcher.get_stock_list()
            hot_stocks = stock_list[stock_list['涨跌幅'] > 3].sort_values('涨跌幅', ascending=False)
            print(f"  今日涨幅>3%的股票: {len(hot_stocks)} 只")
            return stock_list
            
        except Exception as e:
            print(f"  获取板块数据失败: {e}")
            return self.fetcher.get_stock_list()
    
    def check_ma5_condition(self, df: pd.DataFrame) -> Dict:
        """检查MA5条件(核心)"""
        if len(df) < 5:
            return {'pass': False, 'reason': '数据不足'}
        
        df = TechnicalIndicators.calculate_ma(df, periods=[5, 10, 20])
        
        today = df.iloc[-1]
        yesterday = df.iloc[-2] if len(df) >= 2 else today
        
        close = today['收盘']
        low = today['最低']
        ma5 = today['MA5']
        
        if pd.isna(ma5):
            return {'pass': False, 'reason': 'MA5数据不足'}
        
        # 核心三条件
        cond1 = close > ma5  # 收盘>MA5
        cond2 = low >= ma5 * 0.998  # 最低≥MA5(允许0.2%误差)
        cond3 = ma5 > yesterday['MA5'] if pd.notna(yesterday['MA5']) else True  # MA5向上
        
        passed = cond1 and cond2 and cond3
        
        return {
            'pass': passed,
            'close': close,
            'low': low,
            'ma5': ma5,
            'ma10': today.get('MA10', 0),
            'ma20': today.get('MA20', 0),
            'close_vs_ma5': (close - ma5) / ma5 * 100,
            'low_vs_ma5': (low - ma5) / ma5 * 100,
            'ma5_trend': (ma5 - yesterday['MA5']) / yesterday['MA5'] * 100 if pd.notna(yesterday['MA5']) else 0,
            'cond1': cond1,
            'cond2': cond2,
            'cond3': cond3,
            'reason': f"收盘{'✓' if cond1 else '✗'} 最低{'✓' if cond2 else '✗'} MA5{'✓' if cond3 else '✗'}"
        }
    
    def check_trend_condition(self, df: pd.DataFrame) -> Dict:
        """检查趋势条件"""
        if len(df) < 20:
            return {'pass': False, 'reason': '数据不足'}
        
        recent_5 = df.tail(5)
        gain_5d = recent_5['涨跌幅'].sum()
        
        recent_20 = df.tail(20)
        gain_20d = recent_20['涨跌幅'].sum()
        
        yesterday_change = df.iloc[-2]['涨跌幅'] if len(df) >= 2 else 0
        
        cond1 = gain_5d > 10  # 5日涨幅>10%
        cond2 = gain_20d > 15  # 20日涨幅>15%
        cond3 = -3 <= yesterday_change <= 1  # 昨日小幅调整
        
        passed = cond1 and cond2 and cond3
        
        return {
            'pass': passed,
            'gain_5d': gain_5d,
            'gain_20d': gain_20d,
            'yesterday_change': yesterday_change,
            'cond1': cond1,
            'cond2': cond2,
            'cond3': cond3,
            'reason': f"5日{gain_5d:.1f}% 20日{gain_20d:.1f}% 昨日{yesterday_change:.2f}%"
        }
    
    def screen_stocks(self,
                     min_change: float = 3.0,
                     max_change: float = 7.0,
                     min_turnover: float = 5.0,
                     max_turnover: float = 15.0,
                     min_market_cap: float = 40,  # 亿
                     max_market_cap: float = 300,  # 亿
                     max_stocks_to_analyze: int = 100) -> pd.DataFrame:
        """尾盘选股主函数"""
        print("=" * 70)
        print("🔥 尾盘选股器 - 14:30专用")
        print("=" * 70)
        print(f"\n运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 第0步: 识别热门板块
        stock_list = self.get_hot_sectors()
        
        if stock_list.empty:
            print("无法获取股票列表")
            return pd.DataFrame()
        
        # 第1步: 基础筛选
        print("\n【第1步】基础条件筛选...")
        print("-" * 60)
        
        filtered = stock_list.copy()
        initial_count = len(filtered)
        
        # 排除科创板、北交所和ST
        filtered = filtered[~filtered['代码'].str.startswith('688')]
        filtered = filtered[~filtered['代码'].str.startswith('8')]
        filtered = filtered[~filtered['名称'].str.contains('ST', na=False)]
        print(f"  排除科创板/北交所/ST: {initial_count} → {len(filtered)}")
        
        # 涨幅筛选
        filtered = filtered[(filtered['涨跌幅'] >= min_change) & 
                           (filtered['涨跌幅'] <= max_change)]
        print(f"  涨幅{min_change}%-{max_change}%: → {len(filtered)}")
        
        # 换手率筛选
        filtered = filtered[(filtered['换手率'] >= min_turnover) & 
                           (filtered['换手率'] <= max_turnover)]
        print(f"  换手率{min_turnover}%-{max_turnover}%: → {len(filtered)}")
        
        # 市值筛选
        filtered = filtered[(filtered['总市值'] >= min_market_cap * 1e8) & 
                           (filtered['总市值'] <= max_market_cap * 1e8)]
        print(f"  市值{min_market_cap}-{max_market_cap}亿: → {len(filtered)}")
        
        if filtered.empty:
            print("\n❌ 没有股票通过基础筛选")
            return pd.DataFrame()
        
        # 限制分析数量
        if len(filtered) > max_stocks_to_analyze:
            print(f"\n  候选股票较多,取涨幅靠前的{max_stocks_to_analyze}只")
            filtered = filtered.sort_values('涨跌幅', ascending=False).head(max_stocks_to_analyze)
        
        print(f"\n  ✅ 通过基础筛选: {len(filtered)} 只")
        
        # 第2步: 技术面筛选(MA5核心条件)
        print("\n【第2步】技术面筛选(MA5核心)...")
        print("-" * 60)
        
        qualified = []
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
        
        for idx, row in filtered.iterrows():
            symbol = row['代码']
            name = row['名称']
            
            print(f"  [{idx+1}/{len(filtered)}] {symbol} {name}...", end="", flush=True)
            
            try:
                # 获取历史数据
                df = self.fetcher.get_stock_hist(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if df.empty or len(df) < 20:
                    print(" ✗ 数据不足")
                    continue
                
                # 检查MA5条件
                ma5_result = self.check_ma5_condition(df)
                
                if not ma5_result['pass']:
                    print(f" ✗ MA5不符: {ma5_result['reason']}")
                    continue
                
                # 检查趋势条件
                trend_result = self.check_trend_condition(df)
                
                if not trend_result['pass']:
                    print(f" ✗ 趋势不符: {trend_result['reason']}")
                    continue
                
                # 通过所有条件!
                print(f" ✓✓ 符合!")
                
                qualified.append({
                    '代码': symbol,
                    '名称': name,
                    '最新价': row['最新价'],
                    '涨跌幅': row['涨跌幅'],
                    '换手率': row['换手率'],
                    '总市值': row['总市值'] / 1e8,
                    'MA5': ma5_result['ma5'],
                    '收盘偏离MA5': ma5_result['close_vs_ma5'],
                    '最低偏离MA5': ma5_result['low_vs_ma5'],
                    'MA5斜率': ma5_result['ma5_trend'],
                    '5日涨幅': trend_result['gain_5d'],
                    '20日涨幅': trend_result['gain_20d'],
                    '昨日涨跌': trend_result['yesterday_change']
                })
                
                time.sleep(0.3)  # 避免请求过快
                
            except Exception as e:
                print(f" ✗ 错误: {str(e)[:30]}")
                continue
        
        # 整理结果
        if not qualified:
            print("\n❌ 没有股票通过完整筛选")
            return pd.DataFrame()
        
        result_df = pd.DataFrame(qualified)
        result_df = result_df.sort_values('涨跌幅', ascending=False)
        
        print("\n" + "=" * 70)
        print(f"✅ 筛选完成! 共找到 {len(result_df)} 只符合条件的股票")
        print("=" * 70)
        
        self.results = result_df
        return result_df
    
    def print_results(self, top_n: int = None):
        """打印筛选结果"""
        if self.results.empty:
            print("没有筛选结果")
            return
        
        display_df = self.results.copy()
        if top_n:
            display_df = display_df.head(top_n)
        
        print("\n" + "=" * 100)
        print("📊 尾盘选股结果详情")
        print("=" * 100)
        
        # 格式化显示
        display_df_formatted = display_df.copy()
        display_df_formatted['最新价'] = display_df_formatted['最新价'].apply(lambda x: f"{x:.2f}")
        display_df_formatted['涨跌幅'] = display_df_formatted['涨跌幅'].apply(lambda x: f"{x:+.2f}%")
        display_df_formatted['换手率'] = display_df_formatted['换手率'].apply(lambda x: f"{x:.2f}%")
        display_df_formatted['总市值'] = display_df_formatted['总市值'].apply(lambda x: f"{x:.2f}亿")
        display_df_formatted['MA5'] = display_df_formatted['MA5'].apply(lambda x: f"{x:.2f}")
        display_df_formatted['收盘偏离MA5'] = display_df_formatted['收盘偏离MA5'].apply(lambda x: f"{x:+.2f}%")
        display_df_formatted['5日涨幅'] = display_df_formatted['5日涨幅'].apply(lambda x: f"{x:+.2f}%")
        display_df_formatted['20日涨幅'] = display_df_formatted['20日涨幅'].apply(lambda x: f"{x:+.2f}%")
        
        # 选择显示列
        columns_to_show = ['代码', '名称', '最新价', '涨跌幅', '换手率', '总市值', 
                          'MA5', '收盘偏离MA5', '5日涨幅', '20日涨幅']
        
        print(display_df_formatted[columns_to_show].to_string(index=False))
        print("=" * 100)
        
        # 显示关键统计
        print(f"\n📈 统计信息:")
        print(f"  平均涨幅: {display_df['涨跌幅'].mean():.2f}%")
        print(f"  平均换手: {display_df['换手率'].mean():.2f}%")
        print(f"  平均5日涨幅: {display_df['5日涨幅'].mean():.2f}%")
        print(f"  平均20日涨幅: {display_df['20日涨幅'].mean():.2f}%")
    
    def save_results(self, filename: str = None):
        """保存筛选结果"""
        if self.results.empty:
            print("没有结果可保存")
            return
        
        if filename is None:
            filename = f"data/tail_market_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        self.results.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n💾 结果已保存到: {filename}")
    
    def get_stock_detail(self, symbol: str):
        """获取某只股票的详细分析"""
        print(f"\n{'=' * 70}")
        print(f"📊 {symbol} 详细分析")
        print("=" * 70)
        
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
        
        df = self.fetcher.get_stock_hist(symbol, start_date, end_date)
        
        if df.empty:
            print("无法获取数据")
            return
        
        # 计算指标
        df = TechnicalIndicators.calculate_ma(df, periods=[5, 10, 20, 60, 120])
        
        # 显示最近10天
        print("\n最近10天行情:")
        recent = df.tail(10)
        for idx, row in recent.iterrows():
            date = row['日期'].strftime('%Y-%m-%d')
            close = row['收盘']
            change = row['涨跌幅']
            turnover = row.get('换手率', 0)
            ma5 = row.get('MA5', 0)
            
            ma5_status = '✓' if close > ma5 and pd.notna(ma5) else '✗'
            
            print(f"  {date}: 收{close:.2f} {change:+.2f}% 换手{turnover:.2f}% MA5={ma5:.2f if pd.notna(ma5) else 0:.2f} ({ma5_status})")


def run_tail_market_screener():
    """运行尾盘选股器"""
    screener = TailMarketScreener()
    
    # 执行筛选
    result = screener.screen_stocks(
        min_change=3.0,
        max_change=7.0,
        min_turnover=5.0,
        max_turnover=15.0,
        min_market_cap=40,
        max_market_cap=300,
        max_stocks_to_analyze=200
    )
    
    if not result.empty:
        # 打印结果
        screener.print_results(top_n=20)
        
        # 保存结果
        screener.save_results()
        
        print("\n" + "=" * 70)
        print("💡 策略说明:")
        print("  ✓ 核心: 收盘>MA5, 最低≥MA5(未破线), MA5向上")
        print("  ✓ 涨幅: 3%-7% (适中)")
        print("  ✓ 换手率: 5%-15% (活跃)")
        print("  ✓ 趋势: 5日涨幅>10%, 20日涨幅>15%")
        print("  ✓ 昨日: 小幅调整(-3%~+1%)")
        print("  ✓ 市值: 40-300亿")
        print("=" * 70)


if __name__ == "__main__":
    run_tail_market_screener()
