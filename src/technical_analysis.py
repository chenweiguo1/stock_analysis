"""
技术指标分析模块
实现常用的技术分析指标
"""
import pandas as pd
import numpy as np
from typing import Tuple


class TechnicalIndicators:
    """技术指标计算器"""
    
    @staticmethod
    def calculate_ma(df: pd.DataFrame, 
                     price_col: str = '收盘',
                     periods: list = [5, 10, 20, 60, 120]) -> pd.DataFrame:
        """
        计算移动平均线 (MA)
        
        Args:
            df: 包含价格数据的DataFrame
            price_col: 价格列名
            periods: MA周期列表
            
        Returns:
            DataFrame: 添加了MA指标的数据
        """
        result = df.copy()
        for period in periods:
            result[f'MA{period}'] = result[price_col].rolling(window=period).mean()
        return result
    
    @staticmethod
    def calculate_ema(df: pd.DataFrame,
                      price_col: str = '收盘',
                      periods: list = [12, 26]) -> pd.DataFrame:
        """
        计算指数移动平均线 (EMA)
        
        Args:
            df: 包含价格数据的DataFrame
            price_col: 价格列名
            periods: EMA周期列表
            
        Returns:
            DataFrame: 添加了EMA指标的数据
        """
        result = df.copy()
        for period in periods:
            result[f'EMA{period}'] = result[price_col].ewm(span=period, adjust=False).mean()
        return result
    
    @staticmethod
    def calculate_macd(df: pd.DataFrame,
                       price_col: str = '收盘',
                       fast: int = 12,
                       slow: int = 26,
                       signal: int = 9) -> pd.DataFrame:
        """
        计算MACD指标
        
        Args:
            df: 包含价格数据的DataFrame
            price_col: 价格列名
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
            
        Returns:
            DataFrame: 添加了MACD指标的数据
        """
        result = df.copy()
        
        # 计算EMA
        ema_fast = result[price_col].ewm(span=fast, adjust=False).mean()
        ema_slow = result[price_col].ewm(span=slow, adjust=False).mean()
        
        # MACD线
        result['MACD'] = ema_fast - ema_slow
        
        # 信号线
        result['Signal'] = result['MACD'].ewm(span=signal, adjust=False).mean()
        
        # 柱状图
        result['Histogram'] = result['MACD'] - result['Signal']
        
        return result
    
    @staticmethod
    def calculate_rsi(df: pd.DataFrame,
                      price_col: str = '收盘',
                      period: int = 14) -> pd.DataFrame:
        """
        计算RSI指标
        
        Args:
            df: 包含价格数据的DataFrame
            price_col: 价格列名
            period: RSI周期
            
        Returns:
            DataFrame: 添加了RSI指标的数据
        """
        result = df.copy()
        
        # 计算价格变化
        delta = result[price_col].diff()
        
        # 分离涨跌
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # 计算RS和RSI
        rs = gain / loss
        result[f'RSI{period}'] = 100 - (100 / (1 + rs))
        
        return result
    
    @staticmethod
    def calculate_kdj(df: pd.DataFrame,
                      n: int = 9,
                      m1: int = 3,
                      m2: int = 3) -> pd.DataFrame:
        """
        计算KDJ指标
        
        Args:
            df: 包含价格数据的DataFrame
            n: 周期
            m1: K值平滑参数
            m2: D值平滑参数
            
        Returns:
            DataFrame: 添加了KDJ指标的数据
        """
        result = df.copy()
        
        # 计算RSV
        low_list = result['最低'].rolling(window=n, min_periods=1).min()
        high_list = result['最高'].rolling(window=n, min_periods=1).max()
        rsv = (result['收盘'] - low_list) / (high_list - low_list) * 100
        
        # 计算K、D、J
        result['K'] = rsv.ewm(com=m1-1, adjust=False).mean()
        result['D'] = result['K'].ewm(com=m2-1, adjust=False).mean()
        result['J'] = 3 * result['K'] - 2 * result['D']
        
        return result
    
    @staticmethod
    def calculate_boll(df: pd.DataFrame,
                       price_col: str = '收盘',
                       period: int = 20,
                       std_dev: float = 2.0) -> pd.DataFrame:
        """
        计算布林带指标
        
        Args:
            df: 包含价格数据的DataFrame
            price_col: 价格列名
            period: 周期
            std_dev: 标准差倍数
            
        Returns:
            DataFrame: 添加了布林带指标的数据
        """
        result = df.copy()
        
        # 中轨
        result['BOLL_MIDDLE'] = result[price_col].rolling(window=period).mean()
        
        # 标准差
        std = result[price_col].rolling(window=period).std()
        
        # 上轨和下轨
        result['BOLL_UPPER'] = result['BOLL_MIDDLE'] + (std_dev * std)
        result['BOLL_LOWER'] = result['BOLL_MIDDLE'] - (std_dev * std)
        
        return result
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        计算ATR(平均真实波幅)
        
        Args:
            df: 包含价格数据的DataFrame
            period: 周期
            
        Returns:
            DataFrame: 添加了ATR指标的数据
        """
        result = df.copy()
        
        high_low = result['最高'] - result['最低']
        high_close = np.abs(result['最高'] - result['收盘'].shift())
        low_close = np.abs(result['最低'] - result['收盘'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        result['ATR'] = tr.rolling(window=period).mean()
        
        return result
    
    @staticmethod
    def calculate_volume_ma(df: pd.DataFrame,
                           volume_col: str = '成交量',
                           periods: list = [5, 10, 20]) -> pd.DataFrame:
        """
        计算成交量均线
        
        Args:
            df: 包含成交量数据的DataFrame
            volume_col: 成交量列名
            periods: 周期列表
            
        Returns:
            DataFrame: 添加了成交量均线的数据
        """
        result = df.copy()
        for period in periods:
            result[f'VOL_MA{period}'] = result[volume_col].rolling(window=period).mean()
        return result
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有常用技术指标
        
        Args:
            df: 包含价格数据的DataFrame
            
        Returns:
            DataFrame: 添加了所有指标的数据
        """
        result = df.copy()
        
        # 均线
        result = TechnicalIndicators.calculate_ma(result)
        result = TechnicalIndicators.calculate_ema(result)
        
        # 动量指标
        result = TechnicalIndicators.calculate_macd(result)
        result = TechnicalIndicators.calculate_rsi(result)
        result = TechnicalIndicators.calculate_kdj(result)
        
        # 波动指标
        result = TechnicalIndicators.calculate_boll(result)
        result = TechnicalIndicators.calculate_atr(result)
        
        # 成交量指标
        result = TechnicalIndicators.calculate_volume_ma(result)
        
        return result
    
    @staticmethod
    def find_golden_cross(df: pd.DataFrame,
                         short_ma: str = 'MA5',
                         long_ma: str = 'MA20') -> pd.DataFrame:
        """
        寻找金叉信号
        
        Args:
            df: 包含均线数据的DataFrame
            short_ma: 短期均线列名
            long_ma: 长期均线列名
            
        Returns:
            DataFrame: 添加了金叉信号的数据
        """
        result = df.copy()
        
        # 金叉: 短期均线上穿长期均线
        result['Golden_Cross'] = (
            (result[short_ma] > result[long_ma]) & 
            (result[short_ma].shift(1) <= result[long_ma].shift(1))
        )
        
        return result
    
    @staticmethod
    def find_death_cross(df: pd.DataFrame,
                        short_ma: str = 'MA5',
                        long_ma: str = 'MA20') -> pd.DataFrame:
        """
        寻找死叉信号
        
        Args:
            df: 包含均线数据的DataFrame
            short_ma: 短期均线列名
            long_ma: 长期均线列名
            
        Returns:
            DataFrame: 添加了死叉信号的数据
        """
        result = df.copy()
        
        # 死叉: 短期均线下穿长期均线
        result['Death_Cross'] = (
            (result[short_ma] < result[long_ma]) & 
            (result[short_ma].shift(1) >= result[long_ma].shift(1))
        )
        
        return result
