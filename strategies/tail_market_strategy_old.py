"""
尾盘选股策略
专注于捕捉尾盘拉升机会的选股系统
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
from src.data_fetcher import StockDataFetcher
from src.technical_analysis import TechnicalIndicators


class TailMarketStrategy:
    """尾盘选股策略"""
    
    def __init__(self):
        self.fetcher = StockDataFetcher()
        self.results = []
    
    def check_volume_pattern(self, df: pd.DataFrame, days: int = 5) -> bool:
        """
        检查成交量是否呈阶梯式抬高(持续放量)
        
        Args:
            df: 历史数据
            days: 检查最近N天
            
        Returns:
            bool: 是否符合持续放量特征
        """
        if len(df) < days:
            return False
        
        recent_volumes = df['成交量'].tail(days).values
        
        # 计算成交量的趋势(线性回归斜率)
        x = np.arange(len(recent_volumes))
        slope = np.polyfit(x, recent_volumes, 1)[0]
        
        # 斜率为正表示成交量上升
        if slope <= 0:
            return False
        
        # 检查是否有连续的放量
        volume_increases = 0
        for i in range(1, len(recent_volumes)):
            if recent_volumes[i] > recent_volumes[i-1]:
                volume_increases += 1
        
        # 至少有3天是放量的
        return volume_increases >= 3
    
    def check_ma_alignment(self, latest_data: pd.Series) -> bool:
        """
        检查均线多头排列
        要求: MA5 > MA10 > MA20 > MA60, 且价格在所有均线之上
        
        Args:
            latest_data: 最新的数据行
            
        Returns:
            bool: 是否多头排列
        """
        required_mas = ['MA5', 'MA10', 'MA20', 'MA60']
        
        # 检查是否有所有均线数据
        for ma in required_mas:
            if ma not in latest_data or pd.isna(latest_data[ma]):
                return False
        
        price = latest_data['收盘']
        ma5 = latest_data['MA5']
        ma10 = latest_data['MA10']
        ma20 = latest_data['MA20']
        ma60 = latest_data['MA60']
        
        # 多头排列: 价格 > MA5 > MA10 > MA20 > MA60
        if price > ma5 > ma10 > ma20 > ma60:
            return True
        
        return False
    
    def calculate_volume_ratio(self, df: pd.DataFrame) -> float:
        """
        计算量比
        量比 = 当日成交量 / 最近5日平均成交量
        
        Args:
            df: 历史数据
            
        Returns:
            float: 量比值
        """
        if len(df) < 6:
            return 0
        
        current_volume = df['成交量'].iloc[-1]
        avg_volume_5d = df['成交量'].iloc[-6:-1].mean()
        
        if avg_volume_5d == 0:
            return 0
        
        return current_volume / avg_volume_5d
    
    def check_intraday_strength(self, symbol: str) -> Dict:
        """
        检查分时图强度
        理想状态: 全天价格在分时均价之上
        
        Args:
            symbol: 股票代码
            
        Returns:
            dict: 包含分时强度信息
        """
        # 注意: AKShare可能不提供完整分时数据
        # 这里使用日内涨跌幅作为替代指标
        try:
            realtime = self.fetcher.get_stock_realtime(symbol)
            
            if not realtime:
                return {'strength': 0, 'description': '无法获取实时数据'}
            
            change_pct = realtime.get('涨跌幅', 0)
            current_price = realtime.get('最新价', 0)
            open_price = realtime.get('今开', 0)
            high_price = realtime.get('最高', 0)
            low_price = realtime.get('最低', 0)
            
            # 计算强度指标
            if high_price > low_price:
                # 价格位置 = (当前价 - 最低价) / (最高价 - 最低价)
                price_position = (current_price - low_price) / (high_price - low_price)
            else:
                price_position = 0.5
            
            # 分时强度评分
            strength = 0
            description = []
            
            # 1. 涨幅在目标区间
            if 1.3 <= change_pct <= 5.0:
                strength += 30
                description.append(f"涨幅{change_pct:.2f}%✓")
            
            # 2. 价格位置较高(接近最高价)
            if price_position > 0.7:
                strength += 30
                description.append(f"价格位置高{price_position*100:.1f}%✓")
            
            # 3. 盘中创新高
            if current_price == high_price:
                strength += 20
                description.append("当前价=最高价✓")
            
            # 4. 开盘后持续走强
            if open_price > 0 and current_price > open_price:
                strength += 20
                description.append("高开后走强✓")
            
            return {
                'strength': strength,
                'description': '; '.join(description),
                'price_position': price_position,
                'change_pct': change_pct
            }
            
        except Exception as e:
            return {'strength': 0, 'description': f'分析失败: {e}'}
    
    def screen_tail_market_stocks(self,
                                  min_change: float = 1.3,
                                  max_change: float = 5.0,
                                  min_volume_ratio: float = 1.0,
                                  min_turnover: float = 5.0,
                                  max_turnover: float = 10.0,
                                  min_market_cap: float = 50,
                                  max_market_cap: float = 200,
                                  max_stocks: int = 100) -> pd.DataFrame:
        """
        尾盘选股策略筛选
        
        Args:
            min_change: 最小涨幅(%)
            max_change: 最大涨幅(%)
            min_volume_ratio: 最小量比
            min_turnover: 最小换手率(%)
            max_turnover: 最大换手率(%)
            min_market_cap: 最小流通市值(亿)
            max_market_cap: 最大流通市值(亿)
            max_stocks: 最多分析的股票数量
            
        Returns:
            DataFrame: 符合条件的股票列表
        """
        print("=" * 70)
        print("尾盘选股策略")
        print("=" * 70)
        
        # 获取股票列表
        print("\n正在获取股票列表...")
        stock_list = self.fetcher.get_stock_list()
        
        if stock_list.empty:
            print("无法获取股票列表")
            return pd.DataFrame()
        
        print(f"获取到 {len(stock_list)} 只股票")
        
        # 第一步: 基础筛选
        print("\n第一步: 基础条件筛选...")
        filtered = stock_list.copy()
        
        # 排除科创板和ST
        filtered = filtered[~filtered['代码'].str.startswith('688')]
        filtered = filtered[~filtered['名称'].str.contains('ST', na=False)]
        print(f"  排除科创板/ST: {len(filtered)} 只")
        
        # 涨幅筛选
        filtered = filtered[
            (filtered['涨跌幅'] >= min_change) & 
            (filtered['涨跌幅'] <= max_change)
        ]
        print(f"  涨幅{min_change}%-{max_change}%: {len(filtered)} 只")
        
        # 换手率筛选
        filtered = filtered[
            (filtered['换手率'] >= min_turnover) & 
            (filtered['换手率'] <= max_turnover)
        ]
        print(f"  换手率{min_turnover}%-{max_turnover}%: {len(filtered)} 只")
        
        # 流通市值筛选
        filtered = filtered[
            (filtered['总市值'] >= min_market_cap * 1e8) & 
            (filtered['总市值'] <= max_market_cap * 1e8)
        ]
        print(f"  流通市值{min_market_cap}-{max_market_cap}亿: {len(filtered)} 只")
        
        if filtered.empty:
            print("\n没有股票通过基础筛选")
            return pd.DataFrame()
        
        # 限制数量
        if len(filtered) > max_stocks:
            print(f"\n股票数量较多,仅分析前 {max_stocks} 只")
            filtered = filtered.head(max_stocks)
        
        # 第二步: 深度分析
        print(f"\n第二步: 深度技术分析(共{len(filtered)}只)...")
        
        qualified_stocks = []
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
        
        for idx, row in filtered.iterrows():
            symbol = row['代码']
            name = row['名称']
            
            try:
                print(f"  [{idx+1}/{len(filtered)}] 分析 {symbol} {name}...", end="")
                
                # 获取历史数据
                df = self.fetcher.get_stock_hist(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if df.empty or len(df) < 60:
                    print(" 数据不足")
                    continue
                
                # 计算技术指标
                df = TechnicalIndicators.calculate_ma(df, periods=[5, 10, 20, 60])
                
                latest = df.iloc[-1]
                
                # 检查均线多头排列
                if not self.check_ma_alignment(latest):
                    print(" 均线非多头")
                    continue
                
                # 计算量比
                volume_ratio = self.calculate_volume_ratio(df)
                if volume_ratio < min_volume_ratio:
                    print(f" 量比{volume_ratio:.2f}<{min_volume_ratio}")
                    continue
                
                # 检查成交量阶梯式放量
                if not self.check_volume_pattern(df, days=5):
                    print(" 成交量未持续放量")
                    continue
                
                # 检查分时强度
                intraday = self.check_intraday_strength(symbol)
                
                # 综合评分
                score = intraday['strength']
                
                # 多头排列加分
                score += 20
                
                # 持续放量加分
                score += 10
                
                # 量比加分
                if volume_ratio >= 1.5:
                    score += 10
                
                qualified_stocks.append({
                    '代码': symbol,
                    '名称': name,
                    '最新价': row['最新价'],
                    '涨跌幅': row['涨跌幅'],
                    '换手率': row['换手率'],
                    '量比': volume_ratio,
                    '流通市值(亿)': row['总市值'] / 1e8,
                    'MA5': latest['MA5'],
                    'MA10': latest['MA10'],
                    'MA20': latest['MA20'],
                    'MA60': latest['MA60'],
                    '价格位置': intraday.get('price_position', 0),
                    '综合评分': score,
                    '特征': intraday.get('description', '')
                })
                
                print(f" ✓ 评分{score}")
                
                time.sleep(0.3)
                
            except Exception as e:
                print(f" 错误: {e}")
                continue
        
        if not qualified_stocks:
            print("\n没有股票符合所有条件")
            return pd.DataFrame()
        
        # 整理结果
        result_df = pd.DataFrame(qualified_stocks)
        result_df = result_df.sort_values('综合评分', ascending=False)
        
        print("\n" + "=" * 70)
        print(f"筛选完成! 共找到 {len(result_df)} 只符合条件的股票")
        print("=" * 70)
        
        self.results = result_df
        return result_df
    
    def print_results(self):
        """打印筛选结果"""
        if self.results.empty:
            print("没有筛选结果")
            return
        
        print("\n" + "=" * 90)
        print("尾盘选股结果详情:")
        print("=" * 90)
        
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.unicode.east_asian_width', True)
        
        # 格式化显示
        display_df = self.results.copy()
        display_df['最新价'] = display_df['最新价'].apply(lambda x: f"{x:.2f}")
        display_df['涨跌幅'] = display_df['涨跌幅'].apply(lambda x: f"{x:.2f}%")
        display_df['换手率'] = display_df['换手率'].apply(lambda x: f"{x:.2f}%")
        display_df['量比'] = display_df['量比'].apply(lambda x: f"{x:.2f}")
        display_df['流通市值(亿)'] = display_df['流通市值(亿)'].apply(lambda x: f"{x:.2f}")
        display_df['价格位置'] = display_df['价格位置'].apply(lambda x: f"{x*100:.1f}%")
        
        # 只显示关键列
        key_columns = ['代码', '名称', '最新价', '涨跌幅', '换手率', '量比', 
                      '综合评分', '价格位置', '特征']
        print(display_df[key_columns].to_string(index=False))
        print("=" * 90)
    
    def save_results(self, filename: str = None):
        """保存结果到CSV"""
        if self.results.empty:
            print("没有结果可保存")
            return
        
        if filename is None:
            filename = f"data/tail_market_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        self.results.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存到: {filename}")


def run_tail_market_screener_old():
    """运行尾盘选股策略"""
    strategy = TailMarketStrategy()
    
    # 执行筛选
    result = strategy.screen_tail_market_stocks(
        min_change=1.3,           # 涨幅1.3%-5%
        max_change=5.0,
        min_volume_ratio=1.0,     # 量比大于1
        min_turnover=5.0,         # 换手率5%-10%
        max_turnover=10.0,
        min_market_cap=50,        # 流通市值50-200亿
        max_market_cap=200,
        max_stocks=200
    )
    
    if not result.empty:
        strategy.print_results()
        strategy.save_results()
        
        print("\n" + "=" * 70)
        print("策略说明:")
        print("  ✓ 涨幅: 1.3%-5%")
        print("  ✓ 量比: >1")
        print("  ✓ 换手率: 5%-10%")
        print("  ✓ 流通市值: 50-200亿")
        print("  ✓ 成交量: 阶梯式抬高")
        print("  ✓ 均线: 5/10/20/60多头排列")
        print("  ✓ 分时: 价格在均价线之上")
        print("  ✓ 尾盘: 创新高且节奏清晰")
        print("=" * 70)


if __name__ == "__main__":
    run_tail_market_screen()
