"""
A股数据获取模块
使用 AKShare 获取A股实时和历史数据
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List
import time


class StockDataFetcher:
    """A股数据获取器"""
    
    def __init__(self):
        """初始化数据获取器"""
        self.cache = {}
    
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取A股股票列表
        
        Returns:
            DataFrame: 包含股票代码、名称等信息
        
        接口全量返回类型：
            名称	类型	描述
            序号	int64	-
            代码	object	-
            名称	object	-
            最新价	float64	-
            涨跌幅	float64	注意单位: %
            涨跌额	float64	-
            成交量	float64	注意单位: 手
            成交额	float64	注意单位: 元
            振幅	float64	注意单位: %
            最高	float64	-
            最低	float64	-
            今开	float64	-
            昨收	float64	-
            量比	float64	-
            换手率	float64	注意单位: %
            市盈率-动态	float64	-
            市净率	float64	-
            总市值	float64	注意单位: 元
            流通市值	float64	注意单位: 元
            涨速	float64	-
            5分钟涨跌	float64	注意单位: %
            60日涨跌幅	float64	注意单位: %
            年初至今涨跌幅	float64	注意单位: %
        """
        try:
            # 获取沪深A股列表
            stock_list = ak.stock_zh_a_spot_em()
            return stock_list[['代码', '名称', '最新价', '涨跌幅', '换手率', '市盈率-动态', '总市值']]
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def get_stock_hist(self, 
                       symbol: str, 
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       period: str = "daily",
                       adjust: str = "qfq") -> pd.DataFrame:
        """
        获取股票历史数据
        
        Args:
            symbol: 股票代码 (如 "000001" 或 "600000")
            start_date: 开始日期 (格式: "20240101")
            end_date: 结束日期 (格式: "20241231")
            period: 周期 ("daily", "weekly", "monthly")
            adjust: 复权类型 ("qfq"前复权, "hfq"后复权, ""不复权)
        
        Returns:
            DataFrame: 历史行情数据
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            
            if not df.empty:
                df['日期'] = pd.to_datetime(df['日期'])
                df = df.sort_values('日期')
                df.reset_index(drop=True, inplace=True)
            
            return df
        except Exception as e:
            print(f"获取股票 {symbol} 历史数据失败: {e}")
            return pd.DataFrame()
    
    def get_stock_realtime(self, symbol: str) -> dict:
        """
        获取股票实时行情
        
        Args:
            symbol: 股票代码
            
        Returns:
            dict: 实时行情数据
        """
        try:
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == symbol]
            
            if stock_data.empty:
                return {}
            
            return stock_data.iloc[0].to_dict()
        except Exception as e:
            print(f"获取股票 {symbol} 实时数据失败: {e}")
            return {}
    
    def get_stock_info(self, symbol: str) -> dict:
        """
        获取股票基本信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            dict: 股票基本信息
        """
        try:
            # 获取个股信息
            info = ak.stock_individual_info_em(symbol=symbol)
            return info.set_index('item')['value'].to_dict()
        except Exception as e:
            print(f"获取股票 {symbol} 基本信息失败: {e}")
            return {}
    
    def get_market_index(self, 
                         symbol: str = "000001",
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取指数数据
        
        Args:
            symbol: 指数代码 ("000001"上证指数, "399001"深证成指, "399006"创业板指)
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame: 指数历史数据
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        
        try:
            df = ak.stock_zh_index_daily(symbol=f"sh{symbol}")
            df['date'] = pd.to_datetime(df['date'])
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
            return df
        except Exception as e:
            print(f"获取指数 {symbol} 数据失败: {e}")
            return pd.DataFrame()
    
    def batch_get_stocks(self, symbols: List[str], **kwargs) -> dict:
        """
        批量获取股票数据
        
        Args:
            symbols: 股票代码列表
            **kwargs: 传递给 get_stock_hist 的参数
            
        Returns:
            dict: {股票代码: DataFrame}
        """
        result = {}
        for symbol in symbols:
            print(f"正在获取 {symbol} 数据...")
            df = self.get_stock_hist(symbol, **kwargs)
            if not df.empty:
                result[symbol] = df
            time.sleep(0.5)  # 避免请求过快
        
        return result
    
    def get_concept_stocks(self, concept_name: str) -> pd.DataFrame:
        """
        获取概念板块成分股
        
        Args:
            concept_name: 概念名称
            
        Returns:
            DataFrame: 概念股列表
        """
        try:
            # 获取概念板块成分股
            df = ak.stock_board_concept_cons_em(symbol=concept_name)
            return df
        except Exception as e:
            print(f"获取概念 {concept_name} 成分股失败: {e}")
            return pd.DataFrame()
