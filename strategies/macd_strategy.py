"""
MACD策略
使用MACD指标的金叉死叉来产生交易信号
"""
import pandas as pd
import numpy as np
from typing import Dict


class MACDStrategy:
    """MACD策略"""
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        """
        初始化策略
        
        Args:
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
        """
        self.fast = fast
        self.slow = slow
        self.signal = signal
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            df: 包含价格数据的DataFrame
            
        Returns:
            DataFrame: 添加了交易信号的数据
        """
        result = df.copy()
        
        # 计算MACD
        ema_fast = result['收盘'].ewm(span=self.fast, adjust=False).mean()
        ema_slow = result['收盘'].ewm(span=self.slow, adjust=False).mean()
        
        result['MACD'] = ema_fast - ema_slow
        result['Signal_Line'] = result['MACD'].ewm(span=self.signal, adjust=False).mean()
        result['Histogram'] = result['MACD'] - result['Signal_Line']
        
        # 生成交易信号
        result['Trade_Signal'] = 0
        
        # 金叉买入
        result.loc[(result['MACD'] > result['Signal_Line']) & 
                   (result['MACD'].shift(1) <= result['Signal_Line'].shift(1)), 
                   'Trade_Signal'] = 1
        
        # 死叉卖出
        result.loc[(result['MACD'] < result['Signal_Line']) & 
                   (result['MACD'].shift(1) >= result['Signal_Line'].shift(1)), 
                   'Trade_Signal'] = -1
        
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
        
        capital = initial_capital
        shares = 0
        trade_log = []
        
        for i in range(len(signals)):
            if signals['Trade_Signal'].iloc[i] == 1 and capital > 0:  # 买入
                price = signals['收盘'].iloc[i]
                shares = capital / price
                capital = 0
                trade_log.append({
                    'date': signals['日期'].iloc[i],
                    'action': 'BUY',
                    'price': price,
                    'shares': shares
                })
            
            elif signals['Trade_Signal'].iloc[i] == -1 and shares > 0:  # 卖出
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
        
        final_value = capital if shares == 0 else shares * signals['收盘'].iloc[-1]
        total_return = (final_value - initial_capital) / initial_capital * 100
        
        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'trade_log': trade_log,
            'signals': signals
        }
