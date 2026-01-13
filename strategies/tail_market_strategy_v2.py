"""
尾盘选股策略 V2 (支持历史回测)
可指定日期进行历史筛选，验证策略有效性

核心选股逻辑:
1. 技术面(核心): 收盘>MA5, 最低≥MA5(未破线), MA5向上
2. 资金面: 涨幅3-7%, 换手5-15%
3. 趋势面: 5日涨幅10%-15%, 20日涨幅15%-25%, 昨日小幅调整
4. 防追高: 收盘偏离MA5≤3%, 涨幅上限控制

使用方法:
1. 实时筛选: run_tail_market_screener_v2()
2. 历史回测: run_tail_market_screener_v2(target_date="20260106")
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


class TailMarketScreenerV2:
    """尾盘选股器 V2 (支持历史回测)"""
    
    def __init__(self):
        self.fetcher = StockDataFetcher()
        self.hot_sectors = []
        self.results = []
        self.target_date = None  # 目标日期
        
    def set_target_date(self, date_str: str = None):
        """
        设置目标日期
        
        Args:
            date_str: 日期字符串，格式YYYYMMDD，如"20260106"
                      如果为None则使用当前日期
        """
        if date_str:
            self.target_date = datetime.strptime(date_str, "%Y%m%d")
            print(f"\n📅 目标日期: {self.target_date.strftime('%Y-%m-%d')}")
        else:
            self.target_date = datetime.now()
            print(f"\n📅 使用当前日期: {self.target_date.strftime('%Y-%m-%d')}")
        
    def get_hot_sectors(self) -> pd.DataFrame:
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
    
    def check_ma5_condition(self, df: pd.DataFrame, max_close_vs_ma5: float = 3.0) -> Dict:
        """
        检查MA5条件(核心)
        
        Args:
            df: 历史数据
            max_close_vs_ma5: 收盘偏离MA5的最大值(%)，超过此值认为追高风险大
        """
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
        
        close_vs_ma5 = (close - ma5) / ma5 * 100
        
        # 核心三条件
        cond1 = close > ma5  # 收盘>MA5
        cond2 = low >= ma5 * 0.998  # 最低≥MA5(允许0.2%误差)
        cond3 = ma5 > yesterday['MA5'] if pd.notna(yesterday['MA5']) else True  # MA5向上
        # 新增：收盘偏离MA5不能过高(防止追高)
        cond4 = close_vs_ma5 <= max_close_vs_ma5
        
        passed = cond1 and cond2 and cond3 and cond4
        
        return {
            'pass': passed,
            'close': close,
            'low': low,
            'ma5': ma5,
            'ma10': today.get('MA10', 0),
            'ma20': today.get('MA20', 0),
            'close_vs_ma5': close_vs_ma5,
            'low_vs_ma5': (low - ma5) / ma5 * 100,
            'ma5_trend': (ma5 - yesterday['MA5']) / yesterday['MA5'] * 100 if pd.notna(yesterday['MA5']) else 0,
            'cond1': cond1,
            'cond2': cond2,
            'cond3': cond3,
            'cond4': cond4,
            'reason': f"收盘{'✓' if cond1 else '✗'} 最低{'✓' if cond2 else '✗'} MA5{'✓' if cond3 else '✗'} 偏离{'✓' if cond4 else '✗'}({close_vs_ma5:.1f}%)"
        }
    
    def check_trend_condition(self, df: pd.DataFrame, 
                               min_gain_5d: float = 10.0, max_gain_5d: float = 15.0,
                               min_gain_20d: float = 15.0, max_gain_20d: float = 25.0) -> Dict:
        """
        检查趋势条件
        
        Args:
            df: 历史数据
            min_gain_5d: 5日最小涨幅(%)
            max_gain_5d: 5日最大涨幅(%)，超过此值认为短期涨幅透支
            min_gain_20d: 20日最小涨幅(%)
            max_gain_20d: 20日最大涨幅(%)，超过此值认为中期涨幅透支
        """
        if len(df) < 20:
            return {'pass': False, 'reason': '数据不足'}
        
        recent_5 = df.tail(5)
        gain_5d = recent_5['涨跌幅'].sum()
        
        recent_20 = df.tail(20)
        gain_20d = recent_20['涨跌幅'].sum()
        
        yesterday_change = df.iloc[-2]['涨跌幅'] if len(df) >= 2 else 0
        
        cond1 = gain_5d >= min_gain_5d  # 5日涨幅达标
        cond2 = gain_5d <= max_gain_5d  # 5日涨幅不能过高(防止追高)
        cond3 = gain_20d >= min_gain_20d  # 20日涨幅达标
        cond4 = gain_20d <= max_gain_20d  # 20日涨幅不能过高(防止追高)
        cond5 = -3 <= yesterday_change <= 1  # 昨日小幅调整
        
        passed = cond1 and cond2 and cond3 and cond4 and cond5
        
        return {
            'pass': passed,
            'gain_5d': gain_5d,
            'gain_20d': gain_20d,
            'yesterday_change': yesterday_change,
            'cond1': cond1,
            'cond2': cond2,
            'cond3': cond3,
            'cond4': cond4,
            'cond5': cond5,
            'reason': f"5日{gain_5d:.1f}%({'✓' if cond1 and cond2 else '✗'}) 20日{gain_20d:.1f}%({'✓' if cond3 and cond4 else '✗'}) 昨日{yesterday_change:.2f}%"
        }
    
    def get_next_day_performance(self, symbol: str, target_date: datetime) -> Dict:
        """
        获取次日表现(用于验证策略)
        
        Args:
            symbol: 股票代码
            target_date: 选股日期
            
        Returns:
            dict: 次日表现数据
        """
        try:
            # 获取选股日期后两天的数据
            start_date = target_date.strftime("%Y%m%d")
            end_date = (target_date + timedelta(days=10)).strftime("%Y%m%d")
            
            df = self.fetcher.get_stock_hist(symbol, start_date, end_date)
            
            if df.empty or len(df) < 2:
                return {'available': False, 'reason': '次日数据不足'}
            
            # 找到目标日期后的第一个交易日
            df['日期'] = pd.to_datetime(df['日期'])
            target_date_only = target_date.date()
            
            # 获取目标日期及之后的数据
            future_data = df[df['日期'].dt.date > target_date_only]
            
            if future_data.empty:
                return {'available': False, 'reason': '无次日数据'}
            
            next_day = future_data.iloc[0]
            
            return {
                'available': True,
                'next_date': next_day['日期'].strftime('%Y-%m-%d'),
                'next_open': next_day['开盘'],
                'next_close': next_day['收盘'],
                'next_high': next_day['最高'],
                'next_low': next_day['最低'],
                'next_change': next_day['涨跌幅'],
                'next_turnover': next_day.get('换手率', 0)
            }
            
        except Exception as e:
            return {'available': False, 'reason': str(e)}
    
    def screen_stocks(self,
                     target_date: str = None,
                     min_change: float = 3.0,
                     max_change: float = 7.0,
                     min_turnover: float = 5.0,
                     max_turnover: float = 15.0,
                     min_market_cap: float = 40,  # 亿
                     max_market_cap: float = 300,  # 亿
                     max_close_vs_ma5: float = 3.0,  # 收盘偏离MA5上限
                     min_gain_5d: float = 10.0,  # 5日最小涨幅
                     max_gain_5d: float = 15.0,  # 5日最大涨幅(防止追高)
                     min_gain_20d: float = 15.0,  # 20日最小涨幅
                     max_gain_20d: float = 25.0,  # 20日最大涨幅(防止追高)
                     max_stocks_to_analyze: int = 100,
                     check_next_day: bool = False) -> pd.DataFrame:
        """
        尾盘选股主函数 (支持历史回测)
        
        Args:
            target_date: 目标日期，格式YYYYMMDD，如"20260106"。None表示当前日期
            check_next_day: 是否检查次日表现(回测模式)
            其他参数同原版本
        """
        print("=" * 70)
        print("🔥 尾盘选股器 V2 - 支持历史回测")
        print("=" * 70)
        
        # 设置目标日期
        self.set_target_date(target_date)
        
        end_date = self.target_date.strftime("%Y%m%d")
        start_date = (self.target_date - timedelta(days=60)).strftime("%Y%m%d")
        
        print(f"数据范围: {start_date} ~ {end_date}")
        
        # 第0步: 识别热门板块
        stock_list = self.get_hot_sectors()
        
        if stock_list.empty:
            print("无法获取股票列表")
            return pd.DataFrame()
        
        # 第1步: 基础筛选(与原版本顺序一致)
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
        
        # 限制分析数量(按涨幅排序取前N只,与原版本一致)
        if len(filtered) > max_stocks_to_analyze:
            print(f"\n  候选股票较多,取涨幅靠前的{max_stocks_to_analyze}只")
            filtered = filtered.sort_values('涨跌幅', ascending=False).head(max_stocks_to_analyze)
        
        print(f"\n  ✅ 通过基础筛选: {len(filtered)} 只")
        
        # 第2步: 技术面筛选(MA5核心)
        print("\n【第2步】技术面筛选(MA5核心)...")
        print("-" * 60)
        
        qualified = []
        
        for idx, row in filtered.iterrows():
            symbol = row['代码']
            name = row['名称']
            
            print(f"  [{idx+1}/{len(filtered)}] {symbol} {name}...", end="", flush=True)
            
            try:
                # 获取历史数据(截止到目标日期)
                df = self.fetcher.get_stock_hist(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if df.empty or len(df) < 20:
                    print(" ✗ 数据不足")
                    continue
                
                # 检查MA5条件
                ma5_result = self.check_ma5_condition(df, max_close_vs_ma5=max_close_vs_ma5)
                
                if not ma5_result['pass']:
                    print(f" ✗ MA5不符: {ma5_result['reason']}")
                    continue
                
                # 检查趋势条件
                trend_result = self.check_trend_condition(
                    df, 
                    min_gain_5d=min_gain_5d, 
                    max_gain_5d=max_gain_5d,
                    min_gain_20d=min_gain_20d, 
                    max_gain_20d=max_gain_20d
                )
                
                if not trend_result['pass']:
                    print(f" ✗ 趋势不符: {trend_result['reason']}")
                    continue
                
                # 通过所有条件!
                print(f" ✓✓ 符合!", end="")
                
                result_item = {
                    '代码': symbol,
                    '名称': name,
                    '选股日期': self.target_date.strftime('%Y-%m-%d'),
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
                }
                
                # 检查次日表现(回测模式)
                if check_next_day:
                    next_day = self.get_next_day_performance(symbol, self.target_date)
                    if next_day['available']:
                        result_item['次日日期'] = next_day['next_date']
                        result_item['次日涨跌'] = next_day['next_change']
                        result_item['次日开盘'] = next_day['next_open']
                        result_item['次日收盘'] = next_day['next_close']
                        print(f" → 次日{next_day['next_change']:+.2f}%")
                    else:
                        result_item['次日日期'] = '无数据'
                        result_item['次日涨跌'] = None
                        print(f" → 次日无数据")
                else:
                    print("")
                
                qualified.append(result_item)
                
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
        columns_to_show = ['代码', '名称', '选股日期', '最新价', '涨跌幅', '换手率', 
                          '收盘偏离MA5', '5日涨幅', '20日涨幅']
        
        # 如果有次日数据，添加到显示列
        if '次日涨跌' in display_df_formatted.columns:
            display_df_formatted['次日涨跌'] = display_df_formatted['次日涨跌'].apply(
                lambda x: f"{x:+.2f}%" if pd.notna(x) else "无数据"
            )
            columns_to_show.append('次日涨跌')
        
        print(display_df_formatted[columns_to_show].to_string(index=False))
        print("=" * 100)
        
        # 显示关键统计
        print(f"\n📈 统计信息:")
        print(f"  平均涨幅: {display_df['涨跌幅'].mean():.2f}%")
        print(f"  平均换手: {display_df['换手率'].mean():.2f}%")
        print(f"  平均5日涨幅: {display_df['5日涨幅'].mean():.2f}%")
        print(f"  平均20日涨幅: {display_df['20日涨幅'].mean():.2f}%")
        
        # 如果有次日数据，显示次日统计
        if '次日涨跌' in display_df.columns:
            valid_next_day = display_df['次日涨跌'].dropna()
            if len(valid_next_day) > 0:
                print(f"\n📊 次日表现统计:")
                print(f"  有效样本: {len(valid_next_day)} 只")
                print(f"  平均次日涨跌: {valid_next_day.mean():+.2f}%")
                print(f"  上涨数量: {(valid_next_day > 0).sum()} 只 ({(valid_next_day > 0).sum()/len(valid_next_day)*100:.1f}%)")
                print(f"  下跌数量: {(valid_next_day < 0).sum()} 只 ({(valid_next_day < 0).sum()/len(valid_next_day)*100:.1f}%)")
                print(f"  最大涨幅: {valid_next_day.max():+.2f}%")
                print(f"  最大跌幅: {valid_next_day.min():+.2f}%")
    
    def save_results(self, filename: str = None):
        """保存筛选结果"""
        if self.results.empty:
            print("没有结果可保存")
            return
        
        if filename is None:
            date_str = self.target_date.strftime('%Y%m%d') if self.target_date else datetime.now().strftime('%Y%m%d')
            filename = f"data/tail_market_v2_{date_str}_{datetime.now().strftime('%H%M%S')}.csv"
        
        self.results.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n💾 结果已保存到: {filename}")


def run_tail_market_screener_v2(target_date: str = None, check_next_day: bool = False):
    """
    运行尾盘选股器V2
    
    Args:
        target_date: 目标日期，格式YYYYMMDD，如"20260106"。None表示当前日期
        check_next_day: 是否检查次日表现(回测模式)
    
    Examples:
        # 实时筛选
        run_tail_market_screener_v2()
        
        # 历史回测(指定日期并检查次日表现)
        run_tail_market_screener_v2(target_date="20260106", check_next_day=True)
    """
    screener = TailMarketScreenerV2()
    
    # 执行筛选(已优化参数,防止追高)
    result = screener.screen_stocks(
        target_date=target_date,
        min_change=3.0,
        max_change=7.0,
        min_turnover=5.0,
        max_turnover=15.0,
        min_market_cap=40,
        max_market_cap=300,
        max_close_vs_ma5=3.0,   # 收盘偏离MA5不超过3%(防止追高)
        min_gain_5d=10.0,       # 5日涨幅至少10%
        max_gain_5d=15.0,       # 5日涨幅不超过15%(防止短期透支)
        min_gain_20d=15.0,      # 20日涨幅至少15%
        max_gain_20d=25.0,      # 20日涨幅不超过25%(防止中期透支)
        max_stocks_to_analyze=300,
        check_next_day=check_next_day
    )
    
    if not result.empty:
        # 打印结果
        screener.print_results(top_n=20)
        
        # 保存结果
        screener.save_results()
        
        print("\n" + "=" * 70)
        print("💡 策略说明(V2-防止追高+支持回测):")
        print("  ✓ 核心: 收盘>MA5, 最低≥MA5(未破线), MA5向上")
        print("  ✓ 涨幅: 3%-7% (适中)")
        print("  ✓ 换手率: 5%-15% (活跃)")
        print("  ✓ 趋势: 5日涨幅10%-15%, 20日涨幅15%-25% (限制上限)")
        print("  ✓ 偏离: 收盘偏离MA5≤3% (防止追高)")
        print("  ✓ 昨日: 小幅调整(-3%~+1%)")
        print("  ✓ 市值: 40-300亿")
        if check_next_day:
            print("  ✓ 模式: 历史回测(含次日验证)")
        print("=" * 70)
    
    return screener


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='尾盘选股器V2 - 支持历史回测')
    parser.add_argument('--date', type=str, default=None, 
                        help='目标日期，格式YYYYMMDD，如20260106')
    parser.add_argument('--backtest', action='store_true',
                        help='回测模式，检查次日表现')
    
    args = parser.parse_args()
    
    run_tail_market_screener_v2(target_date=args.date, check_next_day=args.backtest)

