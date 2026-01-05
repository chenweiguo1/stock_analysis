"""
相似股票推荐系统
根据技术指标、趋势、资金流等多维度找到相似的股票
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import time
from src.data_fetcher import StockDataFetcher
from src.technical_analysis import TechnicalIndicators


class SimilarStockFinder:
    """相似股票查找器"""
    
    def __init__(self):
        self.fetcher = StockDataFetcher()
        
    def calculate_similarity_score(self, 
                                   target_features: Dict,
                                   candidate_features: Dict,
                                   weights: Dict = None) -> float:
        """
        计算两只股票的相似度分数
        
        Args:
            target_features: 目标股票的特征
            candidate_features: 候选股票的特征
            weights: 各特征的权重
            
        Returns:
            float: 相似度分数(0-100,越高越相似)
        """
        if weights is None:
            weights = {
                'trend': 0.3,      # 趋势相似度权重
                'momentum': 0.25,   # 动量相似度权重
                'volatility': 0.15, # 波动率相似度权重
                'volume': 0.15,     # 成交量相似度权重
                'valuation': 0.15   # 估值相似度权重
            }
        
        total_score = 0
        
        # 1. 趋势相似度(MA趋势方向)
        if 'ma_trend' in target_features and 'ma_trend' in candidate_features:
            ma_diff = abs(target_features['ma_trend'] - candidate_features['ma_trend'])
            trend_score = max(0, 100 - ma_diff * 10)
            total_score += trend_score * weights['trend']
        
        # 2. 动量相似度(MACD, RSI)
        momentum_score = 0
        momentum_count = 0
        
        if 'macd' in target_features and 'macd' in candidate_features:
            macd_diff = abs(target_features['macd'] - candidate_features['macd'])
            momentum_score += max(0, 100 - macd_diff * 50)
            momentum_count += 1
        
        if 'rsi' in target_features and 'rsi' in candidate_features:
            rsi_diff = abs(target_features['rsi'] - candidate_features['rsi'])
            momentum_score += max(0, 100 - rsi_diff)
            momentum_count += 1
        
        if momentum_count > 0:
            total_score += (momentum_score / momentum_count) * weights['momentum']
        
        # 3. 波动率相似度
        if 'volatility' in target_features and 'volatility' in candidate_features:
            vol_ratio = min(target_features['volatility'], candidate_features['volatility']) / \
                       max(target_features['volatility'], candidate_features['volatility'])
            volatility_score = vol_ratio * 100
            total_score += volatility_score * weights['volatility']
        
        # 4. 成交量相似度(换手率)
        if 'turnover' in target_features and 'turnover' in candidate_features:
            turnover_ratio = min(target_features['turnover'], candidate_features['turnover']) / \
                            max(target_features['turnover'], candidate_features['turnover'])
            volume_score = turnover_ratio * 100
            total_score += volume_score * weights['volume']
        
        # 5. 估值相似度(市盈率)
        if 'pe' in target_features and 'pe' in candidate_features:
            if target_features['pe'] > 0 and candidate_features['pe'] > 0:
                pe_ratio = min(target_features['pe'], candidate_features['pe']) / \
                          max(target_features['pe'], candidate_features['pe'])
                valuation_score = pe_ratio * 100
                total_score += valuation_score * weights['valuation']
        
        return total_score
    
    def extract_stock_features(self, 
                              symbol: str,
                              days: int = 60) -> Optional[Dict]:
        """
        提取股票的特征向量
        
        Args:
            symbol: 股票代码
            days: 分析的天数
            
        Returns:
            dict: 股票特征字典
        """
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days + 120)).strftime("%Y%m%d")
            
            # 获取历史数据
            df = self.fetcher.get_stock_hist(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if df.empty or len(df) < 30:
                return None
            
            # 计算技术指标
            df = TechnicalIndicators.calculate_all_indicators(df)
            
            # 只取最近N天
            df = df.tail(days)
            
            # 获取实时数据
            realtime = self.fetcher.get_stock_realtime(symbol)
            
            # 提取特征
            features = {}
            
            # 1. 趋势特征
            if 'MA5' in df.columns and 'MA20' in df.columns and 'MA60' in df.columns:
                latest = df.iloc[-1]
                # MA排列(多头排列为正值,空头排列为负值)
                ma5_slope = (df['MA5'].iloc[-1] - df['MA5'].iloc[-5]) / df['MA5'].iloc[-5] * 100 if len(df) >= 5 else 0
                ma20_slope = (df['MA20'].iloc[-1] - df['MA20'].iloc[-10]) / df['MA20'].iloc[-10] * 100 if len(df) >= 10 else 0
                features['ma_trend'] = (ma5_slope + ma20_slope) / 2
            
            # 2. 动量特征
            if 'MACD' in df.columns:
                features['macd'] = df['MACD'].iloc[-1]
            
            if 'RSI14' in df.columns:
                features['rsi'] = df['RSI14'].iloc[-1]
            
            # 3. 波动率特征(最近N天的标准差)
            if len(df) >= 20:
                price_returns = df['收盘'].pct_change().tail(20)
                features['volatility'] = price_returns.std() * 100
            
            # 4. 成交量特征
            if realtime and '换手率' in realtime:
                features['turnover'] = realtime['换手率']
            else:
                features['turnover'] = df['换手率'].mean() if '换手率' in df.columns else 0
            
            # 5. 估值特征
            if realtime and '市盈率-动态' in realtime:
                features['pe'] = realtime['市盈率-动态']
            
            # 6. 资金流特征(涨跌幅和换手率的综合)
            if len(df) >= 5:
                recent_change = df['涨跌幅'].tail(5).sum()
                recent_turnover = df['换手率'].tail(5).mean() if '换手率' in df.columns else 0
                features['capital_flow'] = recent_change * recent_turnover
            
            # 7. 价格位置(相对于近期高低点)
            if len(df) >= 20:
                high_20 = df['最高'].tail(20).max()
                low_20 = df['最低'].tail(20).min()
                current = df['收盘'].iloc[-1]
                features['price_position'] = (current - low_20) / (high_20 - low_20) * 100 if high_20 != low_20 else 50
            
            return features
            
        except Exception as e:
            print(f"提取 {symbol} 特征失败: {e}")
            return None
    
    def find_similar_stocks(self,
                           target_symbol: str,
                           candidate_symbols: List[str] = None,
                           top_n: int = 10,
                           min_score: float = 60.0,
                           exclude_same_sector: bool = False) -> pd.DataFrame:
        """
        查找相似股票
        
        Args:
            target_symbol: 目标股票代码
            candidate_symbols: 候选股票列表(如果为None则从全市场筛选)
            top_n: 返回前N只最相似的股票
            min_score: 最小相似度分数
            exclude_same_sector: 是否排除同板块股票
            
        Returns:
            DataFrame: 相似股票列表及相似度分数
        """
        print("=" * 60)
        print(f"正在查找与 {target_symbol} 相似的股票...")
        print("=" * 60)
        
        # 获取目标股票特征
        print(f"\n1. 分析目标股票 {target_symbol}...")
        target_features = self.extract_stock_features(target_symbol)
        
        if target_features is None:
            print(f"无法获取 {target_symbol} 的数据")
            return pd.DataFrame()
        
        print(f"   目标股票特征:")
        print(f"   - 趋势强度: {target_features.get('ma_trend', 0):.2f}%")
        print(f"   - RSI: {target_features.get('rsi', 0):.2f}")
        print(f"   - 波动率: {target_features.get('volatility', 0):.2f}%")
        print(f"   - 换手率: {target_features.get('turnover', 0):.2f}%")
        
        # 如果没有提供候选列表,从市场中筛选
        if candidate_symbols is None:
            print("\n2. 获取候选股票列表...")
            stock_list = self.fetcher.get_stock_list()
            
            if stock_list.empty:
                print("无法获取股票列表")
                return pd.DataFrame()
            
            # 基础过滤
            stock_list = stock_list[~stock_list['代码'].str.startswith('688')]  # 排除科创板
            stock_list = stock_list[~stock_list['名称'].str.contains('ST', na=False)]  # 排除ST
            stock_list = stock_list[stock_list['代码'] != target_symbol]  # 排除目标股票
            
            # 限制数量(避免分析太多)
            candidate_symbols = stock_list['代码'].head(100).tolist()
        
        print(f"\n3. 分析 {len(candidate_symbols)} 只候选股票...")
        
        similar_stocks = []
        
        for idx, symbol in enumerate(candidate_symbols):
            if (idx + 1) % 10 == 0:
                print(f"   进度: {idx + 1}/{len(candidate_symbols)}")
            
            try:
                # 获取候选股票特征
                candidate_features = self.extract_stock_features(symbol)
                
                if candidate_features is None:
                    continue
                
                # 计算相似度
                score = self.calculate_similarity_score(target_features, candidate_features)
                
                if score >= min_score:
                    # 获取基本信息
                    realtime = self.fetcher.get_stock_realtime(symbol)
                    
                    similar_stocks.append({
                        '代码': symbol,
                        '名称': realtime.get('名称', '') if realtime else '',
                        '相似度': score,
                        '最新价': realtime.get('最新价', 0) if realtime else 0,
                        '涨跌幅': realtime.get('涨跌幅', 0) if realtime else 0,
                        '换手率': realtime.get('换手率', 0) if realtime else 0,
                        'RSI': candidate_features.get('rsi', 0),
                        '趋势': candidate_features.get('ma_trend', 0),
                        '市盈率': candidate_features.get('pe', 0)
                    })
                
                time.sleep(0.2)  # 避免请求过快
                
            except Exception as e:
                continue
        
        if not similar_stocks:
            print("\n未找到相似的股票")
            return pd.DataFrame()
        
        # 整理结果
        result_df = pd.DataFrame(similar_stocks)
        result_df = result_df.sort_values('相似度', ascending=False).head(top_n)
        
        print("\n" + "=" * 60)
        print(f"找到 {len(result_df)} 只相似股票")
        print("=" * 60)
        
        return result_df
    
    def compare_stocks(self, symbol1: str, symbol2: str):
        """
        详细对比两只股票
        
        Args:
            symbol1: 股票1代码
            symbol2: 股票2代码
        """
        print("\n" + "=" * 60)
        print(f"股票对比: {symbol1} vs {symbol2}")
        print("=" * 60)
        
        features1 = self.extract_stock_features(symbol1)
        features2 = self.extract_stock_features(symbol2)
        
        if features1 is None or features2 is None:
            print("无法获取股票数据")
            return
        
        score = self.calculate_similarity_score(features1, features2)
        
        print(f"\n相似度分数: {score:.2f}\n")
        
        comparison = pd.DataFrame({
            '指标': ['趋势强度(%)', 'RSI', '波动率(%)', '换手率(%)', '市盈率'],
            symbol1: [
                features1.get('ma_trend', 0),
                features1.get('rsi', 0),
                features1.get('volatility', 0),
                features1.get('turnover', 0),
                features1.get('pe', 0)
            ],
            symbol2: [
                features2.get('ma_trend', 0),
                features2.get('rsi', 0),
                features2.get('volatility', 0),
                features2.get('turnover', 0),
                features2.get('pe', 0)
            ]
        })
        
        print(comparison.to_string(index=False))


def demo_find_similar():
    """演示相似股票查找"""
    finder = SimilarStockFinder()
    
    print("\n" + "=" * 60)
    print("相似股票推荐系统")
    print("=" * 60)
    
    # 输入目标股票
    target = input("\n请输入目标股票代码(如 600519): ").strip()
    
    if not target:
        print("未输入股票代码")
        return
    
    # 查找相似股票
    result = finder.find_similar_stocks(
        target_symbol=target,
        top_n=10,
        min_score=65.0
    )
    
    if not result.empty:
        print("\n" + "=" * 60)
        print("相似股票列表:")
        print("=" * 60)
        
        # 格式化显示
        display_df = result.copy()
        display_df['相似度'] = display_df['相似度'].apply(lambda x: f"{x:.1f}")
        display_df['最新价'] = display_df['最新价'].apply(lambda x: f"{x:.2f}")
        display_df['涨跌幅'] = display_df['涨跌幅'].apply(lambda x: f"{x:.2f}%")
        display_df['换手率'] = display_df['换手率'].apply(lambda x: f"{x:.2f}%")
        display_df['RSI'] = display_df['RSI'].apply(lambda x: f"{x:.1f}")
        display_df['趋势'] = display_df['趋势'].apply(lambda x: f"{x:.2f}")
        
        print(display_df.to_string(index=False))
        
        # 询问是否对比
        print("\n" + "=" * 60)
        compare = input("是否详细对比两只股票? (输入两个代码,用空格分隔,或按回车跳过): ").strip()
        if compare:
            codes = compare.split()
            if len(codes) == 2:
                finder.compare_stocks(codes[0], codes[1])


if __name__ == "__main__":
    demo_find_similar()
