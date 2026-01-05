"""
双均线交叉策略
经典的趋势跟踪策略,利用短期和长期均线的交叉来产生买卖信号
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


class DualMovingAverageStrategy:
    """双均线策略"""
    
    def __init__(self, short_period: int = 5, long_period: int = 20):
        """
        初始化策略
        
        Args:
            short_period: 短期均线周期
            long_period: 长期均线周期
        """
        self.short_period = short_period
        self.long_period = long_period
        self.positions = []
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            df: 包含价格数据的DataFrame
            
        Returns:
            DataFrame: 添加了交易信号的数据
        """
        result = df.copy()
        
        # 计算均线
        result['MA_Short'] = result['收盘'].rolling(window=self.short_period).mean()
        result['MA_Long'] = result['收盘'].rolling(window=self.long_period).mean()
        
        # 生成信号
        result['Signal'] = 0
        result.loc[result['MA_Short'] > result['MA_Long'], 'Signal'] = 1  # 买入信号
        result.loc[result['MA_Short'] < result['MA_Long'], 'Signal'] = -1  # 卖出信号
        
        # 找出交叉点
        result['Position'] = result['Signal'].diff()
        
        return result
    
    def backtest(self, df: pd.DataFrame, initial_capital: float = 100000) -> Dict:
        """
        回测策略
        
        Args:
            df: 包含价格数据的DataFrame
            initial_capital: 初始资金
            
        Returns:
            dict: 回测结果
        """
        signals = self.generate_signals(df)
        
        # 初始化
        capital = initial_capital
        shares = 0
        trade_log = []
        
        for i in range(len(signals)):
            if signals['Position'].iloc[i] == 2:  # 买入信号
                if capital > 0:
                    price = signals['收盘'].iloc[i]
                    shares = capital / price
                    capital = 0
                    trade_log.append({
                        'date': signals['日期'].iloc[i],
                        'action': 'BUY',
                        'price': price,
                        'shares': shares
                    })
            
            elif signals['Position'].iloc[i] == -2:  # 卖出信号
                if shares > 0:
                    price = signals['收盘'].iloc[i]
                    capital = shares * price
                    profit = capital - initial_capital
                    trade_log.append({
                        'date': signals['日期'].iloc[i],
                        'action': 'SELL',
                        'price': price,
                        'shares': shares,
                        'profit': profit
                    })
                    shares = 0
        
        # 计算最终收益
        final_value = capital if shares == 0 else shares * signals['收盘'].iloc[-1]
        total_return = (final_value - initial_capital) / initial_capital * 100
        
        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'trade_log': trade_log,
            'signals': signals
        }
