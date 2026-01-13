"""
尾盘选股策略 V3 - 综合稳定版 (优化版)
整合多指标评分系统，支持历史回溯和次日对比分析

优化说明 (基于2026-01-06回测结果):
- 高分组(≥80分)次日均+0.63%，胜率42.9% 表现最好
- 提高默认评分阈值至75分
- 增加量能评分，筛选放量突破股票
- 优化趋势条件，控制追高风险
- 增加更严格的风控条件

核心特点:
1. 综合评分系统 - MA5、MACD、RSI、KDJ、布林带、量能等多指标交叉验证
2. 稳定性优化 - 多维度筛选降低假信号
3. 历史回溯 - 支持指定任意历史日期进行选股
4. 次日对比 - 自动分析选中股票的次日表现和统计数据
5. 多日回测 - 支持连续多日回测验证策略有效性

使用方法:
1. 实时筛选: run_tail_market_v3()
2. 历史回测: run_tail_market_v3(target_date="20260106", check_next_day=True)
3. 多日回测: run_multi_day_backtest(start_date="20260101", end_date="20260107")
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import time
import sys
sys.path.append('src')

from src.data_fetcher import StockDataFetcher
from src.technical_analysis import TechnicalIndicators


class TailMarketScreenerV3:
    """尾盘选股器 V3 - 综合稳定版"""
    
    def __init__(self):
        self.fetcher = StockDataFetcher()
        self.results = pd.DataFrame()
        self.target_date = None
        self.backtest_results = []
        
    def set_target_date(self, date_str: str = None):
        """设置目标日期"""
        if date_str:
            self.target_date = datetime.strptime(date_str, "%Y%m%d")
        else:
            self.target_date = datetime.now()
        print(f"\n📅 目标日期: {self.target_date.strftime('%Y-%m-%d')}")
    
    # ==================== 核心评分系统 (优化版) ====================
    
    def calculate_ma_score(self, df: pd.DataFrame) -> Dict:
        """
        计算均线评分 (满分30分) - 优化版
        
        评分标准:
        - 收盘>MA5: +8分
        - 最低>=MA5*0.998: +8分
        - MA5向上: +6分
        - 收盘偏离MA5在0-2%: +8分 (收紧至2%，降低追高)
        - MA5>MA10>MA20(多头排列): 额外+2分
        """
        if len(df) < 20:
            return {'score': 0, 'pass': False, 'details': {}}
        
        df = TechnicalIndicators.calculate_ma(df, periods=[5, 10, 20, 60])
        
        today = df.iloc[-1]
        yesterday = df.iloc[-2] if len(df) >= 2 else today
        
        close = today['收盘']
        low = today['最低']
        ma5 = today['MA5']
        ma10 = today.get('MA10', np.nan)
        ma20 = today.get('MA20', np.nan)
        
        if pd.isna(ma5):
            return {'score': 0, 'pass': False, 'details': {}}
        
        score = 0
        details = {}
        
        # 1. 收盘>MA5 (+8分)
        cond1 = close > ma5
        if cond1:
            score += 8
        details['close_above_ma5'] = cond1
        
        # 2. 最低>=MA5*0.998 (+8分)
        cond2 = low >= ma5 * 0.998
        if cond2:
            score += 8
        details['low_above_ma5'] = cond2
        
        # 3. MA5向上 (+6分)
        cond3 = ma5 > yesterday['MA5'] if pd.notna(yesterday.get('MA5')) else False
        if cond3:
            score += 6
        details['ma5_rising'] = cond3
        
        # 4. 收盘偏离MA5在合理范围 (+8分) - 收紧至2%
        close_vs_ma5 = (close - ma5) / ma5 * 100
        if 0 <= close_vs_ma5 <= 2:
            score += 8  # 偏离0-2%最佳
        elif 2 < close_vs_ma5 <= 3:
            score += 4  # 偏离2-3%次之
        elif 3 < close_vs_ma5 <= 4:
            score += 1  # 偏离3-4%扣分
        # 偏离>4%不加分
        details['close_vs_ma5'] = close_vs_ma5
        
        # 5. 多头排列 (额外+2分)
        if pd.notna(ma10) and pd.notna(ma20):
            multi_head = ma5 > ma10 > ma20
            if multi_head:
                score += 2
            details['multi_head'] = multi_head
        
        # 必须通过的条件: 收盘>MA5 且 最低>=MA5*0.998 且 偏离<5%
        passed = cond1 and cond2 and close_vs_ma5 < 5
        
        details.update({
            'close': close,
            'low': low,
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'ma5_trend': (ma5 - yesterday['MA5']) / yesterday['MA5'] * 100 if pd.notna(yesterday.get('MA5')) else 0
        })
        
        return {'score': min(score, 30), 'max_score': 30, 'pass': passed, 'details': details}
    
    def calculate_macd_score(self, df: pd.DataFrame) -> Dict:
        """
        计算MACD评分 (满分20分)
        
        评分标准:
        - MACD > 0 (多头): +6分
        - MACD > Signal (金叉状态): +6分
        - Histogram > 0: +4分
        - Histogram连续2日放大: +4分
        """
        if len(df) < 30:
            return {'score': 0, 'pass': True, 'details': {}}
        
        df = TechnicalIndicators.calculate_macd(df)
        
        today = df.iloc[-1]
        yesterday = df.iloc[-2] if len(df) >= 2 else today
        day_before = df.iloc[-3] if len(df) >= 3 else yesterday
        
        macd = today['MACD']
        signal = today['Signal']
        histogram = today['Histogram']
        
        score = 0
        details = {}
        
        # 1. MACD > 0 (+6分)
        if macd > 0:
            score += 6
        details['macd_positive'] = macd > 0
        
        # 2. MACD > Signal (+6分)
        if macd > signal:
            score += 6
        details['macd_above_signal'] = macd > signal
        
        # 3. Histogram > 0 (+4分)
        if histogram > 0:
            score += 4
        details['histogram_positive'] = histogram > 0
        
        # 4. Histogram连续放大 (+4分)
        hist_expanding = (histogram > yesterday['Histogram'] > day_before['Histogram'])
        if hist_expanding and histogram > 0:
            score += 4
        details['histogram_expanding'] = hist_expanding
        
        details.update({
            'macd': macd,
            'signal': signal,
            'histogram': histogram
        })
        
        return {'score': score, 'max_score': 20, 'pass': True, 'details': details}
    
    def calculate_rsi_score(self, df: pd.DataFrame) -> Dict:
        """
        计算RSI评分 (满分15分) - 优化版
        
        评分标准:
        - RSI在50-65之间(强势但不超买): +15分
        - RSI在45-50或65-70之间: +10分
        - RSI在40-45之间(蓄势): +8分
        - RSI>70(超买风险): +3分
        - RSI<40或>80: 0分
        """
        if len(df) < 20:
            return {'score': 0, 'pass': True, 'details': {}}
        
        df = TechnicalIndicators.calculate_rsi(df, period=14)
        
        today = df.iloc[-1]
        rsi = today['RSI14']
        
        if pd.isna(rsi):
            return {'score': 0, 'pass': True, 'details': {}}
        
        score = 0
        details = {'rsi': rsi}
        
        # RSI评分 - 优化
        if 50 <= rsi <= 65:
            score = 15  # 最佳区间
            details['rsi_zone'] = '最佳强势区'
        elif 45 <= rsi < 50:
            score = 10  # 蓄势区
            details['rsi_zone'] = '蓄势区'
        elif 65 < rsi <= 70:
            score = 10  # 偏强
            details['rsi_zone'] = '偏强区'
        elif 40 <= rsi < 45:
            score = 8   # 弱势蓄力
            details['rsi_zone'] = '弱势蓄力'
        elif 70 < rsi <= 80:
            score = 3   # 超买风险
            details['rsi_zone'] = '超买风险'
        else:
            score = 0   # 极端
            details['rsi_zone'] = '极端区'
        
        # RSI>80视为风险信号
        passed = rsi <= 80
        
        return {'score': score, 'max_score': 15, 'pass': passed, 'details': details}
    
    def calculate_kdj_score(self, df: pd.DataFrame) -> Dict:
        """
        计算KDJ评分 (满分15分) - 优化版
        
        评分标准:
        - K值在40-70之间: +5分
        - J值在50-90之间: +5分
        - KDJ金叉(K>D): +3分
        - J值上升: +2分
        """
        if len(df) < 15:
            return {'score': 0, 'pass': True, 'details': {}}
        
        df = TechnicalIndicators.calculate_kdj(df)
        
        today = df.iloc[-1]
        yesterday = df.iloc[-2] if len(df) >= 2 else today
        k = today['K']
        d = today['D']
        j = today['J']
        
        if pd.isna(k) or pd.isna(d) or pd.isna(j):
            return {'score': 0, 'pass': True, 'details': {}}
        
        score = 0
        details = {'K': k, 'D': d, 'J': j}
        
        # K值在合理区间 (40-70)
        if 40 <= k <= 70:
            score += 5
        elif 70 < k <= 80:
            score += 3
        details['k_in_range'] = 40 <= k <= 70
        
        # J值在合理区间 (50-90)
        if 50 <= j <= 90:
            score += 5
        elif 40 <= j < 50 or 90 < j <= 100:
            score += 3
        details['j_in_range'] = 50 <= j <= 90
        
        # KDJ金叉状态 (K>D)
        golden = k > d
        if golden:
            score += 3
        details['kdj_golden'] = golden
        
        # J值上升
        j_rising = j > yesterday['J'] if pd.notna(yesterday.get('J')) else False
        if j_rising:
            score += 2
        details['j_rising'] = j_rising
        
        # J>100视为超买风险
        passed = j <= 110
        
        return {'score': score, 'max_score': 15, 'pass': passed, 'details': details}
    
    def calculate_boll_score(self, df: pd.DataFrame) -> Dict:
        """
        计算布林带评分 (满分10分) - 优化版
        
        评分标准:
        - 收盘在中轨与上轨之间(50%-80%位置): +10分
        - 收盘在80%-95%位置: +5分
        - 收盘>95%(触及上轨): +2分 (风险)
        - 收盘<50%: 0分
        """
        if len(df) < 25:
            return {'score': 0, 'pass': True, 'details': {}}
        
        df = TechnicalIndicators.calculate_boll(df)
        
        today = df.iloc[-1]
        close = today['收盘']
        upper = today['BOLL_UPPER']
        middle = today['BOLL_MIDDLE']
        lower = today['BOLL_LOWER']
        
        if pd.isna(upper) or pd.isna(middle) or pd.isna(lower):
            return {'score': 0, 'pass': True, 'details': {}}
        
        score = 0
        details = {
            'close': close,
            'upper': upper,
            'middle': middle,
            'lower': lower
        }
        
        # 计算收盘在布林带的位置
        boll_position = (close - lower) / (upper - lower) * 100 if (upper - lower) > 0 else 50
        details['boll_position'] = boll_position
        
        # 收盘位置评分 - 优化
        if 50 <= boll_position <= 80:
            score = 10  # 最佳位置
            details['boll_zone'] = '最佳区'
        elif 80 < boll_position <= 95:
            score = 5   # 偏高但可接受
            details['boll_zone'] = '偏高区'
        elif 95 < boll_position:
            score = 2   # 触及上轨，风险
            details['boll_zone'] = '超买区'
        elif 30 <= boll_position < 50:
            score = 4   # 中轨附近
            details['boll_zone'] = '中性区'
        else:
            score = 0
            details['boll_zone'] = '弱势区'
        
        return {'score': score, 'max_score': 10, 'pass': True, 'details': details}
    
    def calculate_volume_score(self, df: pd.DataFrame) -> Dict:
        """
        计算量能评分 (满分10分) - 新增
        
        评分标准:
        - 当日成交量>5日均量: +4分
        - 当日成交量>10日均量: +3分
        - 成交量温和放大(1-2倍): +3分
        - 成交量过大(>3倍): -2分 (风险)
        """
        if len(df) < 10:
            return {'score': 0, 'pass': True, 'details': {}}
        
        df = TechnicalIndicators.calculate_volume_ma(df, periods=[5, 10])
        
        today = df.iloc[-1]
        volume = today['成交量']
        vol_ma5 = today.get('VOL_MA5', np.nan)
        vol_ma10 = today.get('VOL_MA10', np.nan)
        
        if pd.isna(vol_ma5) or pd.isna(vol_ma10) or vol_ma5 == 0:
            return {'score': 0, 'pass': True, 'details': {}}
        
        score = 0
        details = {
            'volume': volume,
            'vol_ma5': vol_ma5,
            'vol_ma10': vol_ma10
        }
        
        vol_ratio = volume / vol_ma5
        details['vol_ratio'] = vol_ratio
        
        # 成交量>5日均量
        if volume > vol_ma5:
            score += 4
        details['above_vol_ma5'] = volume > vol_ma5
        
        # 成交量>10日均量
        if volume > vol_ma10:
            score += 3
        details['above_vol_ma10'] = volume > vol_ma10
        
        # 温和放量评分
        if 1.0 <= vol_ratio <= 2.0:
            score += 3  # 温和放量最佳
            details['vol_status'] = '温和放量'
        elif 2.0 < vol_ratio <= 3.0:
            score += 1  # 放量偏大
            details['vol_status'] = '明显放量'
        elif vol_ratio > 3.0:
            score -= 2  # 过度放量，风险
            details['vol_status'] = '过度放量'
        else:
            details['vol_status'] = '缩量'
        
        return {'score': max(0, score), 'max_score': 10, 'pass': True, 'details': details}
    
    def calculate_trend_score(self, df: pd.DataFrame) -> Dict:
        """
        计算趋势评分 (满分10分) - 优化版
        
        评分标准:
        - 5日涨幅3%-12%: +4分 (收紧上限)
        - 20日涨幅8%-20%: +4分 (收紧上限)
        - 昨日小幅调整(-2%~+0.5%): +2分
        """
        if len(df) < 20:
            return {'score': 0, 'pass': False, 'details': {}}
        
        recent_5 = df.tail(5)
        gain_5d = recent_5['涨跌幅'].sum()
        
        recent_20 = df.tail(20)
        gain_20d = recent_20['涨跌幅'].sum()
        
        yesterday_change = df.iloc[-2]['涨跌幅'] if len(df) >= 2 else 0
        
        score = 0
        details = {
            'gain_5d': gain_5d,
            'gain_20d': gain_20d,
            'yesterday_change': yesterday_change
        }
        
        # 5日涨幅评分 - 收紧
        if 3 <= gain_5d <= 12:
            score += 4  # 最佳
        elif 12 < gain_5d <= 15:
            score += 2  # 偏大
        elif 0 <= gain_5d < 3:
            score += 2  # 偏小
        details['gain_5d_ok'] = 3 <= gain_5d <= 12
        
        # 20日涨幅评分 - 收紧
        if 8 <= gain_20d <= 20:
            score += 4  # 最佳
        elif 20 < gain_20d <= 25:
            score += 2  # 偏大
        elif 0 <= gain_20d < 8:
            score += 2  # 偏小
        details['gain_20d_ok'] = 8 <= gain_20d <= 20
        
        # 昨日调整评分 - 更严格
        if -2 <= yesterday_change <= 0.5:
            score += 2  # 昨日小幅回调最佳
        elif -3 <= yesterday_change < -2 or 0.5 < yesterday_change <= 1:
            score += 1
        details['yesterday_ok'] = -2 <= yesterday_change <= 0.5
        
        # 必须通过条件：不能严重透支
        passed = gain_5d <= 20 and gain_20d <= 30
        
        return {'score': score, 'max_score': 10, 'pass': passed, 'details': details}
    
    def calculate_total_score(self, df: pd.DataFrame) -> Dict:
        """
        计算综合评分 (满分110分，转换为100分制)
        
        各项占比:
        - 均线评分: 30分
        - MACD评分: 20分
        - RSI评分: 15分
        - KDJ评分: 15分
        - 布林带评分: 10分
        - 量能评分: 10分 (新增)
        - 趋势评分: 10分
        """
        ma_result = self.calculate_ma_score(df)
        macd_result = self.calculate_macd_score(df)
        rsi_result = self.calculate_rsi_score(df)
        kdj_result = self.calculate_kdj_score(df)
        boll_result = self.calculate_boll_score(df)
        volume_result = self.calculate_volume_score(df)
        trend_result = self.calculate_trend_score(df)
        
        raw_score = (
            ma_result['score'] + 
            macd_result['score'] + 
            rsi_result['score'] + 
            kdj_result['score'] + 
            boll_result['score'] + 
            volume_result['score'] +
            trend_result['score']
        )
        
        # 转换为100分制
        total_score = raw_score / 110 * 100
        
        # 核心条件必须通过
        all_pass = (ma_result['pass'] and trend_result['pass'] and 
                   rsi_result['pass'] and kdj_result['pass'])
        
        return {
            'total_score': total_score,
            'raw_score': raw_score,
            'max_score': 100,
            'pass': all_pass,
            'ma': ma_result,
            'macd': macd_result,
            'rsi': rsi_result,
            'kdj': kdj_result,
            'boll': boll_result,
            'volume': volume_result,
            'trend': trend_result
        }
    
    # ==================== 次日表现分析 ====================
    
    def get_next_day_performance(self, symbol: str, target_date: datetime) -> Dict:
        """获取次日表现"""
        try:
            start_date = target_date.strftime("%Y%m%d")
            end_date = (target_date + timedelta(days=10)).strftime("%Y%m%d")
            
            df = self.fetcher.get_stock_hist(symbol, start_date, end_date)
            
            if df.empty or len(df) < 2:
                return {'available': False, 'reason': '次日数据不足'}
            
            df['日期'] = pd.to_datetime(df['日期'])
            target_date_only = target_date.date()
            
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
    
    # ==================== 主筛选函数 ====================
    
    def screen_stocks(self,
                     target_date: str = None,
                     min_change: float = 2.0,
                     max_change: float = 6.5,
                     min_turnover: float = 3.0,
                     max_turnover: float = 18.0,
                     min_market_cap: float = 30,
                     max_market_cap: float = 500,
                     min_score: float = 75,
                     max_stocks_to_analyze: int = 500,
                     check_next_day: bool = False) -> pd.DataFrame:
        """
        尾盘选股主函数 - 综合评分版 (优化)
        
        Args:
            target_date: 目标日期 YYYYMMDD格式，None为当天
            min_change: 最小涨幅%
            max_change: 最大涨幅% (收紧至6.5%)
            min_turnover: 最小换手率%
            max_turnover: 最大换手率%
            min_market_cap: 最小市值(亿)
            max_market_cap: 最大市值(亿)
            min_score: 最小综合评分(提高至75分)
            max_stocks_to_analyze: 最大分析数量
            check_next_day: 是否检查次日表现
        """
        print("=" * 80)
        print("🔥 尾盘选股器 V3 - 综合稳定版 (优化)")
        print("=" * 80)
        
        self.set_target_date(target_date)
        
        end_date = self.target_date.strftime("%Y%m%d")
        start_date = (self.target_date - timedelta(days=90)).strftime("%Y%m%d")
        
        # 获取股票列表
        print("\n【第1步】获取股票列表...")
        stock_list = self.fetcher.get_stock_list()
        
        if stock_list.empty:
            print("❌ 无法获取股票列表")
            return pd.DataFrame()
        
        print(f"  获取到 {len(stock_list)} 只股票")
        
        # 基础筛选
        print("\n【第2步】基础条件筛选...")
        filtered = stock_list.copy()
        
        # 排除科创板、北交所、ST
        filtered = filtered[~filtered['代码'].str.startswith('688')]
        filtered = filtered[~filtered['代码'].str.startswith('8')]
        filtered = filtered[~filtered['名称'].str.contains('ST', na=False)]
        print(f"  排除科创板/北交所/ST: → {len(filtered)}")
        
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
        
        # 限制分析数量
        if len(filtered) > max_stocks_to_analyze:
            filtered = filtered.sort_values('涨跌幅', ascending=False).head(max_stocks_to_analyze)
            print(f"  取涨幅前{max_stocks_to_analyze}只分析")
        
        # 技术面综合评分
        print(f"\n【第3步】综合评分筛选 (阈值: {min_score}分)...")
        print("-" * 60)
        
        qualified = []
        
        for idx, (_, row) in enumerate(filtered.iterrows()):
            symbol = row['代码']
            name = row['名称']
            
            print(f"  [{idx+1}/{len(filtered)}] {symbol} {name}...", end="", flush=True)
            
            try:
                df = self.fetcher.get_stock_hist(symbol, start_date, end_date)
                
                if df.empty or len(df) < 30:
                    print(" ✗ 数据不足")
                    continue
                
                # 计算综合评分
                score_result = self.calculate_total_score(df)
                
                if not score_result['pass']:
                    print(f" ✗ 核心条件不满足")
                    continue
                
                total_score = score_result['total_score']
                
                if total_score < min_score:
                    print(f" ✗ 评分{total_score:.0f}分<{min_score}分")
                    continue
                
                print(f" ✓ 评分{total_score:.0f}分", end="")
                
                # 构建结果
                ma_details = score_result['ma']['details']
                macd_details = score_result['macd']['details']
                rsi_details = score_result['rsi']['details']
                kdj_details = score_result['kdj']['details']
                volume_details = score_result['volume']['details']
                trend_details = score_result['trend']['details']
                
                result_item = {
                    '代码': symbol,
                    '名称': name,
                    '选股日期': self.target_date.strftime('%Y-%m-%d'),
                    '综合评分': total_score,
                    '最新价': row['最新价'],
                    '涨跌幅': row['涨跌幅'],
                    '换手率': row['换手率'],
                    '总市值': row['总市值'] / 1e8,
                    # 均线指标
                    'MA5': ma_details.get('ma5', 0),
                    '收盘偏离MA5': ma_details.get('close_vs_ma5', 0),
                    # 动量指标
                    'MACD': macd_details.get('macd', 0),
                    'RSI': rsi_details.get('rsi', 0),
                    'KDJ_J': kdj_details.get('J', 0),
                    # 量能
                    '量比': volume_details.get('vol_ratio', 0),
                    # 趋势
                    '5日涨幅': trend_details.get('gain_5d', 0),
                    '20日涨幅': trend_details.get('gain_20d', 0),
                    '昨日涨跌': trend_details.get('yesterday_change', 0),
                    # 分项评分
                    '均线分': score_result['ma']['score'],
                    'MACD分': score_result['macd']['score'],
                    'RSI分': score_result['rsi']['score'],
                    'KDJ分': score_result['kdj']['score'],
                    '布林分': score_result['boll']['score'],
                    '量能分': score_result['volume']['score'],
                    '趋势分': score_result['trend']['score']
                }
                
                # 检查次日表现
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
                        print(" → 无次日数据")
                else:
                    print("")
                
                qualified.append(result_item)
                time.sleep(0.2)
                
            except Exception as e:
                print(f" ✗ 错误: {str(e)[:30]}")
                continue
        
        if not qualified:
            print("\n❌ 没有股票通过综合评分筛选")
            return pd.DataFrame()
        
        result_df = pd.DataFrame(qualified)
        result_df = result_df.sort_values('综合评分', ascending=False)
        
        print("\n" + "=" * 80)
        print(f"✅ 筛选完成! 共找到 {len(result_df)} 只符合条件的股票")
        print("=" * 80)
        
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
        print("📊 尾盘选股结果 - 综合评分版 (优化)")
        print("=" * 100)
        
        # 格式化
        fmt_df = display_df.copy()
        fmt_df['综合评分'] = fmt_df['综合评分'].apply(lambda x: f"{x:.0f}")
        fmt_df['最新价'] = fmt_df['最新价'].apply(lambda x: f"{x:.2f}")
        fmt_df['涨跌幅'] = fmt_df['涨跌幅'].apply(lambda x: f"{x:+.2f}%")
        fmt_df['换手率'] = fmt_df['换手率'].apply(lambda x: f"{x:.2f}%")
        fmt_df['总市值'] = fmt_df['总市值'].apply(lambda x: f"{x:.0f}亿")
        fmt_df['收盘偏离MA5'] = fmt_df['收盘偏离MA5'].apply(lambda x: f"{x:+.2f}%")
        fmt_df['RSI'] = fmt_df['RSI'].apply(lambda x: f"{x:.1f}")
        fmt_df['量比'] = fmt_df['量比'].apply(lambda x: f"{x:.2f}")
        fmt_df['5日涨幅'] = fmt_df['5日涨幅'].apply(lambda x: f"{x:+.2f}%")
        fmt_df['20日涨幅'] = fmt_df['20日涨幅'].apply(lambda x: f"{x:+.2f}%")
        
        # 显示主要列
        cols = ['代码', '名称', '综合评分', '最新价', '涨跌幅', '换手率', 
                '收盘偏离MA5', 'RSI', '量比', '5日涨幅']
        
        if '次日涨跌' in fmt_df.columns:
            fmt_df['次日涨跌'] = fmt_df['次日涨跌'].apply(
                lambda x: f"{x:+.2f}%" if pd.notna(x) else "无数据"
            )
            cols.append('次日涨跌')
        
        print(fmt_df[cols].to_string(index=False))
        
        # 显示分项评分
        print("\n📈 分项评分:")
        score_cols = ['代码', '名称', '综合评分', '均线分', 'MACD分', 'RSI分', 'KDJ分', '布林分', '量能分', '趋势分']
        score_df = display_df[score_cols].copy()
        score_df['综合评分'] = score_df['综合评分'].apply(lambda x: f"{x:.0f}")
        print(score_df.to_string(index=False))
        
        # 统计信息
        print(f"\n📊 统计信息:")
        print(f"  平均评分: {display_df['综合评分'].mean():.1f}分")
        print(f"  平均涨幅: {display_df['涨跌幅'].mean():.2f}%")
        print(f"  平均换手: {display_df['换手率'].mean():.2f}%")
        
        # 次日统计
        if '次日涨跌' in display_df.columns:
            valid = display_df['次日涨跌'].dropna()
            if len(valid) > 0:
                print(f"\n📊 次日表现统计:")
                print(f"  有效样本: {len(valid)} 只")
                print(f"  平均次日涨跌: {valid.mean():+.2f}%")
                win_rate = (valid > 0).sum() / len(valid) * 100
                print(f"  胜率(次日上涨): {win_rate:.1f}% ({(valid > 0).sum()}/{len(valid)})")
                print(f"  最大涨幅: {valid.max():+.2f}%")
                print(f"  最大跌幅: {valid.min():+.2f}%")
                
                # 按评分分组统计
                print(f"\n📊 按评分分组统计:")
                high_score = display_df[display_df['综合评分'] >= 85]['次日涨跌'].dropna()
                mid_score = display_df[(display_df['综合评分'] >= 80) & (display_df['综合评分'] < 85)]['次日涨跌'].dropna()
                low_score = display_df[display_df['综合评分'] < 80]['次日涨跌'].dropna()
                
                if len(high_score) > 0:
                    print(f"  高分组(≥85分): {len(high_score)}只, 次日均{high_score.mean():+.2f}%, 胜率{(high_score>0).sum()/len(high_score)*100:.1f}%")
                if len(mid_score) > 0:
                    print(f"  中分组(80-84): {len(mid_score)}只, 次日均{mid_score.mean():+.2f}%, 胜率{(mid_score>0).sum()/len(mid_score)*100:.1f}%")
                if len(low_score) > 0:
                    print(f"  低分组(<80分): {len(low_score)}只, 次日均{low_score.mean():+.2f}%, 胜率{(low_score>0).sum()/len(low_score)*100:.1f}%")
    
    def save_results(self, filename: str = None):
        """保存结果"""
        if self.results.empty:
            return
        
        if filename is None:
            date_str = self.target_date.strftime('%Y%m%d')
            filename = f"data/tail_market_v3_{date_str}_{datetime.now().strftime('%H%M%S')}.csv"
        
        self.results.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n💾 结果已保存到: {filename}")
    
    # ==================== 多日回测 ====================
    
    def run_multi_day_backtest(self, 
                               start_date: str, 
                               end_date: str,
                               min_score: float = 75) -> pd.DataFrame:
        """
        多日回测 - 连续多天运行策略并统计表现
        
        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            min_score: 最小评分阈值
        """
        print("=" * 80)
        print("📊 多日回测分析 (优化版)")
        print("=" * 80)
        print(f"回测区间: {start_date} ~ {end_date}")
        print(f"评分阈值: {min_score}分")
        print("=" * 80)
        
        # 生成日期列表
        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")
        
        all_results = []
        date_stats = []
        
        current = start
        while current <= end:
            date_str = current.strftime("%Y%m%d")
            print(f"\n{'='*40}")
            print(f"📅 回测日期: {current.strftime('%Y-%m-%d')}")
            print(f"{'='*40}")
            
            try:
                result = self.screen_stocks(
                    target_date=date_str,
                    min_score=min_score,
                    check_next_day=True,
                    max_stocks_to_analyze=150
                )
                
                if not result.empty:
                    all_results.append(result)
                    
                    # 计算当日统计
                    valid_next = result['次日涨跌'].dropna()
                    if len(valid_next) > 0:
                        date_stats.append({
                            '日期': current.strftime('%Y-%m-%d'),
                            '选中数量': len(result),
                            '平均评分': result['综合评分'].mean(),
                            '次日平均涨跌': valid_next.mean(),
                            '胜率': (valid_next > 0).sum() / len(valid_next) * 100,
                            '最大涨幅': valid_next.max(),
                            '最大跌幅': valid_next.min()
                        })
                
            except Exception as e:
                print(f"  日期 {date_str} 处理失败: {e}")
            
            current += timedelta(days=1)
        
        # 汇总统计
        if date_stats:
            stats_df = pd.DataFrame(date_stats)
            
            print("\n" + "=" * 80)
            print("📊 多日回测汇总")
            print("=" * 80)
            
            # 格式化显示
            fmt_stats = stats_df.copy()
            fmt_stats['平均评分'] = fmt_stats['平均评分'].apply(lambda x: f"{x:.1f}")
            fmt_stats['次日平均涨跌'] = fmt_stats['次日平均涨跌'].apply(lambda x: f"{x:+.2f}%")
            fmt_stats['胜率'] = fmt_stats['胜率'].apply(lambda x: f"{x:.1f}%")
            fmt_stats['最大涨幅'] = fmt_stats['最大涨幅'].apply(lambda x: f"{x:+.2f}%")
            fmt_stats['最大跌幅'] = fmt_stats['最大跌幅'].apply(lambda x: f"{x:+.2f}%")
            
            print(fmt_stats.to_string(index=False))
            
            print(f"\n📈 整体统计:")
            print(f"  总交易日: {len(stats_df)} 天")
            print(f"  总选中股票: {stats_df['选中数量'].sum()} 只")
            print(f"  平均每日选中: {stats_df['选中数量'].mean():.1f} 只")
            print(f"  平均次日涨跌: {stats_df['次日平均涨跌'].mean():+.2f}%")
            print(f"  平均胜率: {stats_df['胜率'].mean():.1f}%")
            
            self.backtest_results = date_stats
            return stats_df
        
        return pd.DataFrame()


def run_tail_market_v3(target_date: str = None, 
                       check_next_day: bool = False,
                       min_score: float = 75):
    """
    运行尾盘选股V3 (优化版)
    
    Args:
        target_date: 目标日期 YYYYMMDD，None为当天
        check_next_day: 是否检查次日表现
        min_score: 最小综合评分 (默认75分)
    
    Examples:
        run_tail_market_v3()  # 实时筛选
        run_tail_market_v3(target_date="20260106", check_next_day=True)  # 历史回测
    """
    screener = TailMarketScreenerV3()
    
    result = screener.screen_stocks(
        target_date=target_date,
        min_change=2.0,
        max_change=6.5,
        min_turnover=3.0,
        max_turnover=18.0,
        min_market_cap=30,
        max_market_cap=500,
        min_score=min_score,
        max_stocks_to_analyze=500,
        check_next_day=check_next_day
    )
    
    if not result.empty:
        screener.print_results(top_n=20)
        screener.save_results()
        
        print("\n" + "=" * 80)
        print("💡 策略V3说明 - 综合评分版 (优化):")
        print("  ✓ 均线(30分): 收盘>MA5, 最低>=MA5, MA5向上, 偏离≤2%最佳")
        print("  ✓ MACD(20分): 多头, 金叉状态, 红柱连续放大")
        print("  ✓ RSI(15分): 50-65最佳, >70风险")
        print("  ✓ KDJ(15分): K值40-70, J值50-90最佳")
        print("  ✓ 布林(10分): 50%-80%位置最佳")
        print("  ✓ 量能(10分): 温和放量1-2倍最佳")
        print("  ✓ 趋势(10分): 5日涨幅3-12%, 20日涨幅8-20%")
        print(f"  ✓ 评分阈值: {min_score}分 (建议≥80分)")
        print("=" * 80)
    
    return screener


def run_multi_day_backtest(start_date: str, end_date: str, min_score: float = 75):
    """
    运行多日回测
    
    Args:
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        min_score: 最小评分
    
    Example:
        run_multi_day_backtest("20260101", "20260107")
    """
    screener = TailMarketScreenerV3()
    return screener.run_multi_day_backtest(start_date, end_date, min_score)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='尾盘选股V3 - 综合稳定版')
    parser.add_argument('--date', type=str, default=None, help='目标日期 YYYYMMDD')
    parser.add_argument('--backtest', action='store_true', help='回测模式(检查次日)')
    parser.add_argument('--score', type=float, default=75, help='最小评分阈值')
    parser.add_argument('--multi', action='store_true', help='多日回测模式')
    parser.add_argument('--start', type=str, help='多日回测开始日期')
    parser.add_argument('--end', type=str, help='多日回测结束日期')
    
    args = parser.parse_args()
    
    if args.multi and args.start and args.end:
        run_multi_day_backtest(args.start, args.end, args.score)
    else:
        run_tail_market_v3(
            target_date=args.date, 
            check_next_day=args.backtest,
            min_score=args.score
        )
