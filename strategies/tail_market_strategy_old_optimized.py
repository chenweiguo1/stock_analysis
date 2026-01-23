"""
尾盘选股策略 - 优化版 V2
专注于捕捉尾盘拉升机会的选股系统

性能优化:
1. 并行处理 - 使用多线程并行分析多只股票
2. 减少网络请求 - 从stock_list获取实时数据，避免重复请求
3. 减少延迟 - 降低sleep时间，只在必要时延迟
4. 提前过滤 - 在获取历史数据前做更多基础筛选
5. 错误重试 - 网络请求失败自动重试
6. 增强评分 - 更全面的分时强度和成交量评估
7. 日志记录 - 便于调试和追踪
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
import logging
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.data_fetcher import StockDataFetcher
from src.technical_analysis import TechnicalIndicators


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def retry_on_failure(max_retries: int = 3, delay: float = 0.3):
    """
    重试装饰器 - 网络请求失败时自动重试
    
    Args:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
            # 所有重试都失败，返回 None 而不是抛出异常
            return None
        return wrapper
    return decorator


class TailMarketStrategyOptimized:
    """尾盘选股策略 - 优化版 V2"""
    
    def __init__(self, max_workers: int = 10, enable_logging: bool = False):
        """
        初始化
        
        Args:
            max_workers: 并行处理的线程数
            enable_logging: 是否启用详细日志
        """
        self.fetcher = StockDataFetcher()
        self.results = []
        self.max_workers = max_workers
        self.stock_list_cache = None  # 缓存股票列表数据
        self.logger = logging.getLogger(__name__)
        
        # 根据参数设置日志级别
        if not enable_logging:
            self.logger.setLevel(logging.WARNING)
    
    def check_volume_pattern(self, df: pd.DataFrame, days: int = 5) -> Dict:
        """
        检查成交量是否呈阶梯式抬高(持续放量) - 增强版
        
        Args:
            df: 历史数据
            days: 检查的天数
            
        Returns:
            dict: {'passed': bool, 'score': int, 'description': str}
        """
        result = {'passed': False, 'score': 0, 'description': ''}
        
        if len(df) < max(days, 20):
            result['description'] = '数据不足'
            return result
        
        recent_volumes = df['成交量'].tail(days).values
        avg_volume_20d = df['成交量'].tail(20).mean()  # 20日均量作为基准
        avg_volume_5d = df['成交量'].tail(5).mean()    # 5日均量
        
        # 1. 线性回归斜率检查 - 趋势判断
        x = np.arange(len(recent_volumes))
        slope = np.polyfit(x, recent_volumes, 1)[0]
        
        if slope <= 0:
            result['description'] = '成交量趋势下降'
            return result
        
        # 2. 检查放量天数和幅度
        volume_increases = 0
        significant_increases = 0  # 显著放量（超过前一天10%）
        
        for i in range(1, len(recent_volumes)):
            if recent_volumes[i] > recent_volumes[i-1]:
                volume_increases += 1
                if recent_volumes[i] > recent_volumes[i-1] * 1.1:
                    significant_increases += 1
        
        # 3. 最近一天成交量与均量比较
        latest_volume = recent_volumes[-1]
        volume_vs_20d = latest_volume / avg_volume_20d if avg_volume_20d > 0 else 0
        volume_vs_5d = latest_volume / avg_volume_5d if avg_volume_5d > 0 else 0
        
        # 评分逻辑
        score = 0
        descriptions = []
        
        # 放量天数评分 (满分30)
        if volume_increases >= 4:
            score += 30
            descriptions.append(f"连续放量{volume_increases}天✓✓")
        elif volume_increases >= 3:
            score += 20
            descriptions.append(f"放量{volume_increases}天✓")
        elif volume_increases >= 2:
            score += 10
        
        # 显著放量评分 (满分20)
        if significant_increases >= 2:
            score += 20
            descriptions.append(f"显著放量{significant_increases}天✓")
        elif significant_increases >= 1:
            score += 10
        
        # 与20日均量比较 (满分30)
        if volume_vs_20d >= 2.0:
            score += 30
            descriptions.append(f"量比20日均{volume_vs_20d:.1f}倍✓✓")
        elif volume_vs_20d >= 1.5:
            score += 20
            descriptions.append(f"量比20日均{volume_vs_20d:.1f}倍✓")
        elif volume_vs_20d >= 1.2:
            score += 10
        
        # 与5日均量比较 (满分20)
        if volume_vs_5d >= 1.3:
            score += 20
        elif volume_vs_5d >= 1.1:
            score += 10
        
        # 判断是否通过
        # 条件: 至少3天放量 且 (有显著放量 或 高于20日均量1.2倍)
        passed = volume_increases >= 3 and (significant_increases >= 1 or volume_vs_20d >= 1.2)
        
        result = {
            'passed': passed,
            'score': score,
            'description': '; '.join(descriptions) if descriptions else '成交量一般',
            'volume_vs_20d': volume_vs_20d,
            'volume_vs_5d': volume_vs_5d,
            'volume_increases': volume_increases
        }
        
        return result
    
    def check_ma_alignment(self, latest_data: pd.Series) -> Dict:
        """
        检查均线多头排列 - 增强版
        
        Args:
            latest_data: 最新一天的数据
            
        Returns:
            dict: {'passed': bool, 'score': int, 'type': str, 'description': str}
        """
        result = {'passed': False, 'score': 0, 'type': 'none', 'description': ''}
        required_mas = ['MA5', 'MA10', 'MA20', 'MA60']
        
        # 检查是否有所有均线数据
        for ma in required_mas:
            if ma not in latest_data or pd.isna(latest_data[ma]):
                result['description'] = f'缺少{ma}数据'
                return result
        
        price = latest_data['收盘']
        ma5 = latest_data['MA5']
        ma10 = latest_data['MA10']
        ma20 = latest_data['MA20']
        ma60 = latest_data['MA60']
        
        score = 0
        descriptions = []
        
        # 完美多头排列: 价格 > MA5 > MA10 > MA20 > MA60
        if price > ma5 > ma10 > ma20 > ma60:
            score = 100
            result['type'] = 'perfect'
            descriptions.append("完美多头排列✓✓")
        # 准多头排列: MA5 > MA10 > MA20 > MA60，价格在MA5附近
        elif ma5 > ma10 > ma20 > ma60 and price >= ma10:
            score = 70
            result['type'] = 'quasi'
            descriptions.append("准多头排列✓")
        # 短期多头: MA5 > MA10 > MA20，价格在MA5上方
        elif price > ma5 > ma10 > ma20:
            score = 50
            result['type'] = 'short_term'
            descriptions.append("短期多头✓")
        # 价格站上所有均线
        elif price > ma5 and price > ma10 and price > ma20 and price > ma60:
            score = 30
            result['type'] = 'above_all'
            descriptions.append("站上全部均线")
        else:
            result['description'] = '均线未形成多头'
            return result
        
        # 计算均线发散程度 (发散度越大趋势越强)
        ma_spread = (ma5 - ma60) / ma60 * 100 if ma60 > 0 else 0
        if ma_spread > 10:
            score += 10
            descriptions.append(f"均线发散{ma_spread:.1f}%")
        
        # 价格相对MA5的位置
        price_vs_ma5 = (price - ma5) / ma5 * 100 if ma5 > 0 else 0
        if 0 < price_vs_ma5 < 3:
            score += 10
            descriptions.append("价格贴近MA5")
        
        result['passed'] = score >= 50  # 至少准多头排列
        result['score'] = min(score, 100)
        result['description'] = '; '.join(descriptions)
        result['ma_spread'] = ma_spread
        
        return result
    
    def calculate_volume_ratio(self, df: pd.DataFrame, symbol: str = None, 
                               stock_row: pd.Series = None) -> Dict:
        """
        计算量比 - 优化版
        量比 = 当日成交量 / 最近5日平均成交量
        
        优先使用 stock_row 中的数据，避免额外网络请求
        
        Args:
            df: 历史数据
            symbol: 股票代码
            stock_row: 股票列表中的行数据（包含实时成交量）
            
        Returns:
            dict: {'ratio': float, 'score': int, 'description': str}
        """
        result = {'ratio': 0, 'score': 0, 'description': ''}
        
        if len(df) < 6:
            result['description'] = '历史数据不足'
            return result
        
        # 优先从 stock_row 获取当日成交量，避免额外网络请求
        current_volume = None
        
        if stock_row is not None and '成交量' in stock_row:
            current_volume = stock_row['成交量']
        
        # 如果 stock_row 没有数据，使用历史数据的最后一天
        if current_volume is None or current_volume == 0:
            current_volume = df['成交量'].iloc[-1]
        
        # 计算最近5日平均成交量（不包括今天）
        avg_volume_5d = df['成交量'].iloc[-6:-1].mean()
        
        if avg_volume_5d == 0:
            result['description'] = '5日均量为0'
            return result
        
        # 计算量比
        volume_ratio = current_volume / avg_volume_5d
        
        # 评分逻辑
        score = 0
        descriptions = []
        
        if volume_ratio >= 3.0:
            score = 50
            descriptions.append(f"量比{volume_ratio:.2f}极度放量✓✓")
        elif volume_ratio >= 2.0:
            score = 40
            descriptions.append(f"量比{volume_ratio:.2f}明显放量✓✓")
        elif volume_ratio >= 1.5:
            score = 30
            descriptions.append(f"量比{volume_ratio:.2f}温和放量✓")
        elif volume_ratio >= 1.2:
            score = 20
            descriptions.append(f"量比{volume_ratio:.2f}小幅放量")
        elif volume_ratio >= 1.0:
            score = 10
            descriptions.append(f"量比{volume_ratio:.2f}持平")
        else:
            descriptions.append(f"量比{volume_ratio:.2f}缩量")
        
        result = {
            'ratio': volume_ratio,
            'score': score,
            'description': '; '.join(descriptions),
            'current_volume': current_volume,
            'avg_volume_5d': avg_volume_5d
        }
        
        return result
    
    def check_intraday_strength(self, symbol: str, stock_row: pd.Series) -> Dict:
        """
        检查分时图强度 - 增强版
        从stock_list中获取数据，避免额外网络请求
        
        评分维度:
        1. 价格位置 (满分40) - 当前价在日内高低点的位置
        2. 振幅分析 (满分20) - 振幅小说明走势稳健
        3. 开盘表现 (满分20) - 相对开盘价的涨幅
        4. 尾盘特征 (满分20) - 是否接近最高价
        
        Args:
            symbol: 股票代码
            stock_row: 股票列表中的行数据
            
        Returns:
            dict: 包含 strength, description, price_position 等
        """
        try:
            # 从stock_row获取数据，避免额外请求
            change_pct = stock_row.get('涨跌幅', 0)
            current_price = stock_row.get('最新价', 0)
            
            if current_price <= 0:
                return {'strength': 0, 'description': '价格数据异常'}
            
            # 获取价格数据
            open_price = stock_row.get('今开', current_price)
            high_price = stock_row.get('最高', current_price)
            low_price = stock_row.get('最低', current_price)
            
            # 处理缺失数据
            if pd.isna(open_price) or open_price <= 0:
                open_price = current_price / (1 + change_pct / 100) if change_pct != 0 else current_price
            if pd.isna(high_price) or high_price <= 0:
                high_price = current_price
            if pd.isna(low_price) or low_price <= 0:
                low_price = current_price
            
            # 计算关键指标
            # 1. 价格位置 (当前价在日内高低点的相对位置)
            if high_price > low_price:
                price_position = (current_price - low_price) / (high_price - low_price)
            else:
                price_position = 0.5
            
            # 2. 振幅
            amplitude = (high_price - low_price) / low_price * 100 if low_price > 0 else 0
            
            # 3. 相对开盘涨幅
            open_change = (current_price - open_price) / open_price * 100 if open_price > 0 else 0
            
            # 4. 距离最高价的差距
            gap_to_high = (high_price - current_price) / high_price * 100 if high_price > 0 else 0
            
            # 分时强度评分
            strength = 0
            descriptions = []
            
            # 评分1: 价格位置 (满分40)
            if price_position >= 0.95:
                strength += 40
                descriptions.append("价格接近最高✓✓")
            elif price_position >= 0.85:
                strength += 35
                descriptions.append(f"价格位置极高{price_position*100:.0f}%✓✓")
            elif price_position >= 0.7:
                strength += 25
                descriptions.append(f"价格位置高{price_position*100:.0f}%✓")
            elif price_position >= 0.5:
                strength += 15
                descriptions.append(f"价格位置中{price_position*100:.0f}%")
            else:
                descriptions.append(f"价格位置低{price_position*100:.0f}%")
            
            # 评分2: 振幅分析 (满分20) - 振幅小说明走势稳健
            if amplitude < 2.5:
                strength += 20
                descriptions.append(f"振幅小{amplitude:.1f}%走势稳✓")
            elif amplitude < 4:
                strength += 15
                descriptions.append(f"振幅适中{amplitude:.1f}%")
            elif amplitude < 6:
                strength += 10
            else:
                descriptions.append(f"振幅大{amplitude:.1f}%")
            
            # 评分3: 开盘表现 (满分20)
            if open_change >= 3:
                strength += 20
                descriptions.append("开盘后持续走强✓✓")
            elif open_change >= 1.5:
                strength += 15
                descriptions.append("开盘后走强✓")
            elif open_change >= 0:
                strength += 10
            elif open_change >= -1:
                strength += 5
            
            # 评分4: 尾盘特征 (满分20)
            if gap_to_high < 0.3:  # 距离最高价不到0.3%
                strength += 20
                descriptions.append("尾盘创新高✓✓")
            elif gap_to_high < 1:
                strength += 15
                descriptions.append("接近最高价✓")
            elif gap_to_high < 2:
                strength += 10
            
            return {
                'strength': strength,
                'description': '; '.join(descriptions),
                'price_position': price_position,
                'change_pct': change_pct,
                'amplitude': amplitude,
                'open_change': open_change,
                'gap_to_high': gap_to_high
            }
            
        except Exception as e:
            self.logger.debug(f"分析 {symbol} 分时强度失败: {e}")
            return {'strength': 0, 'description': f'分析失败', 'price_position': 0}
    
    @retry_on_failure(max_retries=3, delay=0.3)
    def _fetch_stock_hist(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取历史数据 - 带重试机制"""
        return self.fetcher.get_stock_hist(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
    
    def analyze_single_stock(self, symbol: str, name: str, stock_row: pd.Series, 
                            min_volume_ratio: float, start_date: str, end_date: str) -> Optional[Dict]:
        """
        分析单只股票 - 用于并行处理（增强版）
        
        综合评分体系 (满分200分):
        - 分时强度: 最高100分
        - 均线形态: 最高100分 (根据type加权)
        - 成交量形态: 最高100分
        - 量比加分: 最高50分
        
        Args:
            symbol: 股票代码
            name: 股票名称
            stock_row: 股票列表中的行数据
            min_volume_ratio: 最小量比
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            dict: 符合条件的股票信息，或None
        """
        try:
            # 获取历史数据（带重试）
            df = self._fetch_stock_hist(symbol, start_date, end_date)
            
            if df is None or df.empty or len(df) < 60:
                self.logger.debug(f"{symbol} {name}: 历史数据不足")
                return None
            
            # 计算技术指标
            df = TechnicalIndicators.calculate_ma(df, periods=[5, 10, 20, 60])
            
            latest = df.iloc[-1]
            
            # 检查均线多头排列（增强版）
            ma_result = self.check_ma_alignment(latest)
            if not ma_result['passed']:
                self.logger.debug(f"{symbol} {name}: {ma_result['description']}")
                return None
            
            # 计算量比（优化版，使用stock_row数据）
            volume_result = self.calculate_volume_ratio(df, symbol=symbol, stock_row=stock_row)
            if volume_result['ratio'] < min_volume_ratio:
                self.logger.debug(f"{symbol} {name}: 量比{volume_result['ratio']:.2f}不足")
                return None
            
            # 检查成交量阶梯式放量（增强版）
            volume_pattern = self.check_volume_pattern(df, days=5)
            if not volume_pattern['passed']:
                self.logger.debug(f"{symbol} {name}: {volume_pattern['description']}")
                return None
            
            # 检查分时强度（增强版）
            intraday = self.check_intraday_strength(symbol, stock_row)
            
            # 综合评分计算
            # 基础分 = 分时强度 (已经是0-100)
            score = intraday['strength']
            
            # 均线形态加分 (根据类型)
            ma_bonus = {
                'perfect': 30,    # 完美多头
                'quasi': 20,      # 准多头
                'short_term': 10, # 短期多头
                'above_all': 5    # 站上均线
            }
            score += ma_bonus.get(ma_result['type'], 0)
            
            # 成交量形态加分 (按比例)
            score += volume_pattern['score'] * 0.3  # 最高30分
            
            # 量比加分
            if volume_result['ratio'] >= 2.0:
                score += 20
            elif volume_result['ratio'] >= 1.5:
                score += 15
            elif volume_result['ratio'] >= 1.2:
                score += 10
            
            # 构建特征描述
            features = []
            if intraday.get('description'):
                features.append(intraday['description'])
            if ma_result.get('description'):
                features.append(ma_result['description'])
            if volume_pattern.get('description'):
                features.append(volume_pattern['description'])
            
            # 获取流通市值（优先使用流通市值字段）
            market_cap = stock_row.get('流通市值', stock_row.get('总市值', 0)) / 1e8
            
            return {
                '代码': symbol,
                '名称': name,
                '最新价': stock_row['最新价'],
                '涨跌幅': stock_row['涨跌幅'],
                '换手率': stock_row['换手率'],
                '量比': volume_result['ratio'],
                '流通市值(亿)': market_cap,
                'MA5': latest['MA5'],
                'MA10': latest['MA10'],
                'MA20': latest['MA20'],
                'MA60': latest['MA60'],
                '价格位置': intraday.get('price_position', 0),
                '振幅': intraday.get('amplitude', 0),
                '均线形态': ma_result['type'],
                '综合评分': round(score, 1),
                '特征': '; '.join(features)
            }
            
        except Exception as e:
            self.logger.debug(f"分析 {symbol} {name} 失败: {e}")
            return None
    
    def screen_tail_market_stocks(self,
                                  min_change: float = 1.3,
                                  max_change: float = 5.0,
                                  min_volume_ratio: float = 1.0,
                                  min_turnover: float = 5.0,
                                  max_turnover: float = 10.0,
                                  min_market_cap: float = 50,
                                  max_market_cap: float = 200,
                                  max_stocks: int = 200,
                                  exclude_cyb: bool = False) -> pd.DataFrame:
        """
        尾盘选股策略筛选 - 优化版 V2（并行处理）
        
        Args:
            min_change: 最小涨幅(%)
            max_change: 最大涨幅(%)
            min_volume_ratio: 最小量比
            min_turnover: 最小换手率(%)
            max_turnover: 最大换手率(%)
            min_market_cap: 最小流通市值(亿)
            max_market_cap: 最大流通市值(亿)
            max_stocks: 最多分析的股票数量
            exclude_cyb: 是否排除创业板
            
        Returns:
            DataFrame: 符合条件的股票列表
        """
        print("=" * 70)
        print("尾盘选股策略 - 优化版 V2 (并行处理 + 增强评分)")
        print("=" * 70)
        
        # 获取股票列表
        print("\n正在获取股票列表...")
        stock_list = self.fetcher.get_stock_list()
        self.stock_list_cache = stock_list  # 缓存
        
        if stock_list.empty:
            print("无法获取股票列表")
            return pd.DataFrame()
        
        print(f"获取到 {len(stock_list)} 只股票")
        
        # 第一步: 基础筛选
        print("\n第一步: 基础条件筛选...")
        filtered = stock_list.copy()
        
        # 排除科创板
        filtered = filtered[~filtered['代码'].str.startswith('688')]
        print(f"  排除科创板: {len(filtered)} 只")
        
        # 可选排除创业板
        if exclude_cyb:
            filtered = filtered[~filtered['代码'].str.startswith('300')]
            print(f"  排除创业板: {len(filtered)} 只")
        
        # 排除ST
        filtered = filtered[~filtered['名称'].str.contains('ST', na=False)]
        print(f"  排除ST: {len(filtered)} 只")
        
        # 排除北交所
        filtered = filtered[~filtered['代码'].str.startswith('8')]
        filtered = filtered[~filtered['代码'].str.startswith('4')]
        print(f"  排除北交所: {len(filtered)} 只")
        
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
        
        # 市值筛选（优先使用流通市值）
        market_cap_col = '流通市值' if '流通市值' in filtered.columns else '总市值'
        filtered = filtered[
            (filtered[market_cap_col] >= min_market_cap * 1e8) & 
            (filtered[market_cap_col] <= max_market_cap * 1e8)
        ]
        print(f"  市值{min_market_cap}-{max_market_cap}亿: {len(filtered)} 只")
        
        if filtered.empty:
            print("\n没有股票通过基础筛选")
            return pd.DataFrame()
        
        # 按涨幅排序，优先分析涨幅适中的
        filtered = filtered.sort_values('涨跌幅', ascending=False)
        
        # 限制数量
        if len(filtered) > max_stocks:
            print(f"\n股票数量较多, 仅分析前 {max_stocks} 只")
            filtered = filtered.head(max_stocks)
        
        # 第二步: 并行深度分析
        print(f"\n第二步: 并行深度技术分析 (共{len(filtered)}只, {self.max_workers}线程)...")
        
        qualified_stocks = []
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=120)).strftime("%Y%m%d")  # 增加到120天确保MA60有效
        
        # 准备任务列表
        tasks = []
        for idx, (_, row) in enumerate(filtered.iterrows()):
            symbol = row['代码']
            name = row['名称']
            tasks.append((idx, symbol, name, row))
        
        # 并行处理
        completed = 0
        failed = 0
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(
                    self.analyze_single_stock,
                    symbol, name, row, min_volume_ratio, start_date, end_date
                ): (idx, symbol, name) 
                for idx, symbol, name, row in tasks
            }
            
            # 收集结果
            for future in as_completed(future_to_task):
                completed += 1
                idx, symbol, name = future_to_task[future]
                
                # 显示进度
                if completed % 10 == 0 or completed == len(tasks):
                    elapsed = time.time() - start_time
                    speed = completed / elapsed if elapsed > 0 else 0
                    remaining = (len(tasks) - completed) / speed if speed > 0 else 0
                    print(f"  进度: {completed}/{len(tasks)} ({completed/len(tasks)*100:.1f}%) "
                          f"速度: {speed:.1f}只/秒 预计剩余: {remaining:.0f}秒", end='\r')
                
                try:
                    result = future.result()
                    if result:
                        qualified_stocks.append(result)
                        print(f"\n  [{completed}/{len(tasks)}] ✓ {symbol} {name} "
                              f"评分{result['综合评分']} 均线:{result['均线形态']}")
                except Exception as e:
                    failed += 1
                    self.logger.debug(f"处理 {symbol} 失败: {e}")
        
        elapsed_total = time.time() - start_time
        print(f"\n  完成! 耗时{elapsed_total:.1f}秒, 分析{completed}只, "
              f"符合{len(qualified_stocks)}只, 失败{failed}只")
        
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
    
    def print_results(self, top_n: int = None):
        """
        打印筛选结果
        
        Args:
            top_n: 只显示前N个结果，None表示全部显示
        """
        if self.results.empty:
            print("没有筛选结果")
            return
        
        print("\n" + "=" * 100)
        print("尾盘选股结果详情:")
        print("=" * 100)
        
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.unicode.east_asian_width', True)
        
        # 格式化显示
        display_df = self.results.copy()
        if top_n:
            display_df = display_df.head(top_n)
        
        display_df['最新价'] = display_df['最新价'].apply(lambda x: f"{x:.2f}")
        display_df['涨跌幅'] = display_df['涨跌幅'].apply(lambda x: f"{x:.2f}%")
        display_df['换手率'] = display_df['换手率'].apply(lambda x: f"{x:.2f}%")
        display_df['量比'] = display_df['量比'].apply(lambda x: f"{x:.2f}")
        display_df['流通市值(亿)'] = display_df['流通市值(亿)'].apply(lambda x: f"{x:.1f}")
        display_df['价格位置'] = display_df['价格位置'].apply(lambda x: f"{x*100:.0f}%")
        display_df['振幅'] = display_df['振幅'].apply(lambda x: f"{x:.1f}%") if '振幅' in display_df.columns else '-'
        
        # 均线形态中文映射
        ma_type_map = {
            'perfect': '完美多头',
            'quasi': '准多头',
            'short_term': '短期多头',
            'above_all': '站上均线'
        }
        if '均线形态' in display_df.columns:
            display_df['均线形态'] = display_df['均线形态'].map(ma_type_map).fillna('-')
        
        # 只显示关键列
        key_columns = ['代码', '名称', '最新价', '涨跌幅', '换手率', '量比', 
                      '综合评分', '均线形态', '价格位置', '振幅']
        
        # 确保所有列都存在
        key_columns = [c for c in key_columns if c in display_df.columns]
        
        print(display_df[key_columns].to_string(index=False))
        print("=" * 100)
        
        # 打印特征详情
        if len(display_df) <= 10:
            print("\n特征详情:")
            print("-" * 100)
            for _, row in display_df.iterrows():
                print(f"  {row['代码']} {row['名称']}: {row.get('特征', '-')}")
            print("-" * 100)
    
    def save_results(self, filename: str = None):
        """保存结果到CSV"""
        if self.results.empty:
            print("没有结果可保存")
            return
        
        if filename is None:
            filename = f"data/tail_market_optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        self.results.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存到: {filename}")


def run_tail_market_screener_old_optimized(
    max_workers: int = 10,
    min_change: float = 1.3,
    max_change: float = 5.0,
    min_volume_ratio: float = 1.0,
    min_turnover: float = 5.0,
    max_turnover: float = 10.0,
    min_market_cap: float = 50,
    max_market_cap: float = 200,
    exclude_cyb: bool = False,
    enable_logging: bool = False
):
    """
    运行尾盘选股策略 - 优化版 V2
    
    Args:
        max_workers: 并行处理的线程数，建议5-15
        min_change: 最小涨幅(%)
        max_change: 最大涨幅(%)
        min_volume_ratio: 最小量比
        min_turnover: 最小换手率(%)
        max_turnover: 最大换手率(%)
        min_market_cap: 最小流通市值(亿)
        max_market_cap: 最大流通市值(亿)
        exclude_cyb: 是否排除创业板
        enable_logging: 是否启用详细日志
    """
    strategy = TailMarketStrategyOptimized(
        max_workers=max_workers, 
        enable_logging=enable_logging
    )
    
    # 执行筛选
    result = strategy.screen_tail_market_stocks(
        min_change=min_change,
        max_change=max_change,
        min_volume_ratio=min_volume_ratio,
        min_turnover=min_turnover,
        max_turnover=max_turnover,
        min_market_cap=min_market_cap,
        max_market_cap=max_market_cap,
        max_stocks=200,
        exclude_cyb=exclude_cyb
    )
    
    if not result.empty:
        strategy.print_results()
        strategy.save_results()
        
        print("\n" + "=" * 70)
        print("策略说明 (优化版 V2):")
        print(f"  ✓ 涨幅: {min_change}%-{max_change}%")
        print(f"  ✓ 量比: >{min_volume_ratio}")
        print(f"  ✓ 换手率: {min_turnover}%-{max_turnover}%")
        print(f"  ✓ 流通市值: {min_market_cap}-{max_market_cap}亿")
        print("  ✓ 成交量: 阶梯式抬高 (增强检测)")
        print("  ✓ 均线: 多头排列 (完美/准多头/短期)")
        print("  ✓ 分时: 价格位置+振幅+开盘表现+尾盘特征")
        print("  ✓ 性能: 并行处理 + 错误重试 + 减少请求")
        print("=" * 70)
        
        # 返回策略对象以便进一步分析
        return strategy
    
    return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='尾盘选股策略 - 优化版 V2')
    parser.add_argument('--workers', type=int, default=10, 
                       help='并行线程数 (默认10，建议5-15)')
    parser.add_argument('--min-change', type=float, default=1.3,
                       help='最小涨幅%% (默认1.3)')
    parser.add_argument('--max-change', type=float, default=5.0,
                       help='最大涨幅%% (默认5.0)')
    parser.add_argument('--min-volume-ratio', type=float, default=1.0,
                       help='最小量比 (默认1.0)')
    parser.add_argument('--min-turnover', type=float, default=5.0,
                       help='最小换手率%% (默认5.0)')
    parser.add_argument('--max-turnover', type=float, default=10.0,
                       help='最大换手率%% (默认10.0)')
    parser.add_argument('--min-cap', type=float, default=50,
                       help='最小市值(亿) (默认50)')
    parser.add_argument('--max-cap', type=float, default=200,
                       help='最大市值(亿) (默认200)')
    parser.add_argument('--exclude-cyb', action='store_true',
                       help='排除创业板')
    parser.add_argument('--debug', action='store_true',
                       help='启用调试日志')
    
    args = parser.parse_args()
    
    run_tail_market_screener_old_optimized(
        max_workers=args.workers,
        min_change=args.min_change,
        max_change=args.max_change,
        min_volume_ratio=args.min_volume_ratio,
        min_turnover=args.min_turnover,
        max_turnover=args.max_turnover,
        min_market_cap=args.min_cap,
        max_market_cap=args.max_cap,
        exclude_cyb=args.exclude_cyb,
        enable_logging=args.debug
    )
