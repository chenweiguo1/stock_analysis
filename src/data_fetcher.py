"""
A股数据获取模块
使用 AKShare 获取A股实时和历史数据

优化:
1. 自动重试机制 - 网络请求失败时自动重试
2. 超时处理 - 设置更长的超时时间
3. 缓存机制 - 减少重复请求
4. 请求配置 - 优化HTTP请求参数
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List
import time
from functools import wraps
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def configure_requests():
    """
    配置 requests 默认参数
    - 增加超时时间
    - 配置重试策略
    - 设置连接池
    """
    # 配置重试策略
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    # 创建适配器
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=10
    )
    
    # 创建会话并挂载适配器
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # 设置默认超时（AKShare 内部使用 requests）
    # 通过 monkey patch 设置默认超时
    old_request = requests.Session.request
    
    def new_request(self, method, url, **kwargs):
        # 设置默认超时为 30 秒
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30
        return old_request(self, method, url, **kwargs)
    
    requests.Session.request = new_request
    
    return session


# 初始化时配置 requests
_session = configure_requests()


def retry_request(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    重试装饰器 - 网络请求失败时自动重试
    
    Args:
        max_retries: 最大重试次数
        delay: 初始重试间隔（秒）
        backoff: 退避系数（每次重试间隔乘以此系数）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        print(f"  请求失败 (尝试 {attempt + 1}/{max_retries}): {type(e).__name__}")
                        print(f"  {current_delay:.1f}秒后重试...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        print(f"  请求失败 (已重试{max_retries}次): {e}")
            
            # 返回 None 或空 DataFrame，而不是抛出异常
            return None
        return wrapper
    return decorator


class StockDataFetcher:
    """A股数据获取器"""
    
    def __init__(self):
        """初始化数据获取器"""
        self.cache = {}
        self._stock_list_cache = None
        self._stock_list_cache_time = None
        self._cache_ttl = 60  # 缓存有效期（秒）
    
    def _normalize_stock_data(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        """
        统一不同数据源的字段名
        
        Args:
            df: 原始数据
            source: 数据源 ('em' 东方财富, 'sina' 新浪)
            
        Returns:
            DataFrame: 统一字段名后的数据
        """
        if df is None or df.empty:
            return df
        
        # 新浪接口字段映射 -> 东方财富字段
        sina_mapping = {
            'symbol': '代码',
            'code': '代码', 
            'name': '名称',
            'trade': '最新价',
            'price': '最新价',
            'pricechange': '涨跌额',
            'changepercent': '涨跌幅',
            'buy': '买入',
            'sell': '卖出',
            'settlement': '昨收',
            'open': '今开',
            'high': '最高',
            'low': '最低',
            'volume': '成交量',
            'amount': '成交额',
            'ticktime': '时间',
            'per': '市盈率-动态',
            'pb': '市净率',
            'mktcap': '总市值',
            'nmc': '流通市值',
            'turnoverratio': '换手率',
        }
        
        if source == 'sina':
            # 重命名列
            df = df.rename(columns=sina_mapping)
            
            # 处理代码格式（新浪可能带 sh/sz 前缀）
            if '代码' in df.columns:
                df['代码'] = df['代码'].astype(str).str.replace(r'^(sh|sz)', '', regex=True)
        
        return df
    
    def _fetch_stock_list_raw(self) -> pd.DataFrame:
        """
        获取原始股票列表
        优先使用东方财富接口，失败时尝试新浪接口
        """
        # 尝试东方财富接口
        for attempt in range(3):
            try:
                print(f"  尝试东方财富接口 ({attempt + 1}/3)...")
                df = ak.stock_zh_a_spot_em()
                if df is not None and not df.empty:
                    print(f"  成功获取 {len(df)} 只股票")
                    return self._normalize_stock_data(df, 'em')
            except Exception as e:
                print(f"  东方财富接口失败: {type(e).__name__}")
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        
        # 尝试新浪接口作为备用
        print("  尝试新浪备用接口...")
        try:
            df = ak.stock_zh_a_spot()
            if df is not None and not df.empty:
                print(f"  新浪接口成功，获取 {len(df)} 只股票")
                return self._normalize_stock_data(df, 'sina')
        except Exception as e:
            print(f"  新浪接口也失败: {e}")
        
        return None
    
    def get_stock_list(self, use_cache: bool = True) -> pd.DataFrame:
        """
        获取A股股票列表
        
        Args:
            use_cache: 是否使用缓存（60秒内有效）
        
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
        # 检查缓存是否有效
        if use_cache and self._stock_list_cache is not None:
            if self._stock_list_cache_time:
                elapsed = (datetime.now() - self._stock_list_cache_time).total_seconds()
                if elapsed < self._cache_ttl:
                    print(f"  使用缓存数据 (有效期还剩 {self._cache_ttl - elapsed:.0f}秒)")
                    return self._stock_list_cache
        
        try:
            # 获取沪深A股列表（带重试）
            stock_list = self._fetch_stock_list_raw()
            
            if stock_list is None or stock_list.empty:
                print("获取股票列表失败: 返回数据为空")
                return pd.DataFrame()
            
            # 选择需要的列（包含更多字段以支持策略分析）
            columns_needed = ['代码', '名称', '最新价', '涨跌幅', '换手率', 
                            '市盈率-动态', '总市值', '流通市值', '成交量',
                            '今开', '最高', '最低', '振幅', '量比']
            
            # 只选择存在的列
            available_columns = [c for c in columns_needed if c in stock_list.columns]
            result = stock_list[available_columns]
            
            # 更新缓存
            self._stock_list_cache = result
            self._stock_list_cache_time = datetime.now()
            
            return result
            
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return pd.DataFrame()
    
    @retry_request(max_retries=3, delay=0.5, backoff=1.5)
    def _fetch_stock_hist_raw(self, symbol: str, period: str, 
                               start_date: str, end_date: str, adjust: str) -> pd.DataFrame:
        """获取原始历史数据（带重试）"""
        return ak.stock_zh_a_hist(
            symbol=symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust
        )
    
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
            df = self._fetch_stock_hist_raw(symbol, period, start_date, end_date, adjust)
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.sort_values('日期')
            df.reset_index(drop=True, inplace=True)
            
            return df
        except Exception as e:
            # 静默处理，避免打印过多错误
            return pd.DataFrame()
    
    def get_stock_realtime(self, symbol: str, use_cache: bool = True) -> dict:
        """
        获取股票实时行情 - 优化版
        
        优先使用缓存的股票列表数据，避免重复网络请求
        
        Args:
            symbol: 股票代码
            use_cache: 是否使用缓存数据
            
        Returns:
            dict: 实时行情数据
        """
        try:
            # 优先使用缓存数据
            if use_cache and self._stock_list_cache is not None:
                if self._stock_list_cache_time:
                    elapsed = (datetime.now() - self._stock_list_cache_time).total_seconds()
                    if elapsed < self._cache_ttl:
                        # 从缓存中查找
                        stock_data = self._stock_list_cache[
                            self._stock_list_cache['代码'] == symbol
                        ]
                        if not stock_data.empty:
                            return stock_data.iloc[0].to_dict()
            
            # 缓存不可用，获取新数据（带重试）
            df = self._fetch_stock_list_raw()
            
            if df is None or df.empty:
                return {}
            
            stock_data = df[df['代码'] == symbol]
            
            if stock_data.empty:
                return {}
            
            return stock_data.iloc[0].to_dict()
            
        except Exception as e:
            # 静默处理，避免打印过多错误信息
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
