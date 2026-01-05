"""
KDJ策略
基于KDJ指标的超买超卖策略
"""
import pandas as pd
import numpy as np
from typing import Dict


class KDJStrategy:
    """KDJ策略"""
    
    def __init__(self, 
                 n: int = 9,
                 m1: int = 3,
                 m2: int = 3,
                 oversold: int = 20,
                 overbought: int = 80):
        """
        初始化策略
        
        Args:
            n: KDJ周期
            m1: K值平滑参数
            m2: D值平滑参数
            oversold: 超卖线
            overbought: 超买线
        """
        self.n = n
        self.m1 = m1
        self.m2 = m2
        self.oversold = oversold
        self.overbought = overbought
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            df: 包含价格数据的DataFrame
            
        Returns:
            DataFrame: 添加了交易信号的数据
        """
        result = df.copy()
        
        # 计算KDJ
        low_list = result['最低'].rolling(window=self.n, min_periods=1).min()
        high_list = result['最高'].rolling(window=self.n, min_periods=1).max()
        rsv = (result['收盘'] - low_list) / (high_list - low_list) * 100
        
        result['K'] = rsv.ewm(com=self.m1-1, adjust=False).mean()
        result['D'] = result['K'].ewm(com=self.m2-1, adjust=False).mean()
        result['J'] = 3 * result['K'] - 2 * result['D']
        
        # 生成交易信号
        result['Trade_Signal'] = 0
        
        # 超卖区买入: J值从下方上穿超卖线
        result.loc[(result['J'] > self.oversold) & 
                   (result['J'].shift(1) <= self.oversold), 
                   'Trade_Signal'] = 1
        
        # 超买区卖出: J值从上方下穿超买线
        result.loc[(result['J'] < self.overbought) & 
                   (result['J'].shift(1) >= self.overbought), 
                   'Trade_Signal'] = -1
        
        # KDJ金叉买入
        result.loc[(result['K'] > result['D']) & 
                   (result['K'].shift(1) <= result['D'].shift(1)) &
                   (result['K'] < 50), 
                   'Trade_Signal'] = 1
        
        # KDJ死叉卖出
        result.loc[(result['K'] < result['D']) & 
                   (result['K'].shift(1) >= result['D'].shift(1)) &
                   (result['K'] > 50), 
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
            if signals['Trade_Signal'].iloc[i] == 1 and capital > 0:
                price = signals['收盘'].iloc[i]
                shares = capital / price
                capital = 0
                trade_log.append({
                    'date': signals['日期'].iloc[i],
                    'action': 'BUY',
                    'price': price,
                    'shares': shares
                })
            
            elif signals['Trade_Signal'].iloc[i] == -1 and shares > 0:
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
