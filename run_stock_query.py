"""
股票信息查询工具
查询指定股票的实时行情、历史数据、技术指标等

使用方法:
    python run_stock_query.py 000001              # 查询实时信息
    python run_stock_query.py 000001 --hist       # 查询历史K线
    python run_stock_query.py 000001 --hist --days 30   # 最近30天
    python run_stock_query.py 000001 --detail     # 详细信息
    python run_stock_query.py 000001 --all        # 全部信息
"""
import sys
import argparse
import pandas as pd
from datetime import datetime, timedelta

sys.path.append('src')
from data_fetcher import StockDataFetcher
from technical_analysis import TechnicalIndicators


class StockQuery:
    """股票信息查询器"""
    
    def __init__(self):
        self.fetcher = StockDataFetcher()
        self._stock_list_cache = None
    
    def _get_stock_list(self) -> pd.DataFrame:
        """获取并缓存股票列表"""
        if self._stock_list_cache is None:
            self._stock_list_cache = self.fetcher.get_stock_list()
        return self._stock_list_cache
    
    def search_stock(self, keyword: str) -> pd.DataFrame:
        """
        搜索股票（支持代码或名称）
        
        Args:
            keyword: 股票代码或名称关键词
            
        Returns:
            DataFrame: 匹配的股票列表
        """
        stock_list = self._get_stock_list()
        
        if stock_list.empty:
            return pd.DataFrame()
        
        # 精确匹配代码
        exact_code = stock_list[stock_list['代码'] == keyword]
        if not exact_code.empty:
            return exact_code
        
        # 精确匹配名称
        exact_name = stock_list[stock_list['名称'] == keyword]
        if not exact_name.empty:
            return exact_name
        
        # 模糊匹配名称
        fuzzy_name = stock_list[stock_list['名称'].str.contains(keyword, na=False)]
        if not fuzzy_name.empty:
            return fuzzy_name
        
        # 模糊匹配代码
        fuzzy_code = stock_list[stock_list['代码'].str.contains(keyword, na=False)]
        return fuzzy_code
    
    def resolve_symbol(self, keyword: str) -> tuple:
        """
        解析股票代码（支持名称或代码输入）
        
        Args:
            keyword: 股票代码或名称
            
        Returns:
            tuple: (代码, 名称) 或 (None, None)
        """
        results = self.search_stock(keyword)
        
        if results.empty:
            return None, None
        
        if len(results) == 1:
            row = results.iloc[0]
            return row['代码'], row['名称']
        
        # 多个结果，让用户选择
        print(f"\n找到 {len(results)} 个匹配结果:")
        print("-" * 50)
        for idx, (_, row) in enumerate(results.head(10).iterrows(), 1):
            print(f"  {idx}. {row['代码']} {row['名称']} "
                  f"现价:{row.get('最新价', '-')} 涨跌:{row.get('涨跌幅', '-'):.2f}%")
        
        if len(results) > 10:
            print(f"  ... 还有 {len(results) - 10} 个结果")
        
        print("-" * 50)
        
        try:
            choice = input("请选择序号 (直接回车选第1个): ").strip()
            if not choice:
                choice = 1
            else:
                choice = int(choice)
            
            if 1 <= choice <= min(10, len(results)):
                row = results.iloc[choice - 1]
                return row['代码'], row['名称']
        except (ValueError, KeyboardInterrupt):
            pass
        
        # 默认返回第一个
        row = results.iloc[0]
        return row['代码'], row['名称']
    
    def get_realtime_info(self, symbol: str) -> dict:
        """
        获取股票实时行情
        
        Args:
            symbol: 股票代码
            
        Returns:
            dict: 实时行情数据
        """
        print(f"\n正在获取 {symbol} 实时行情...")
        
        # 获取股票列表（包含实时数据）
        stock_list = self._get_stock_list()
        
        if stock_list.empty:
            print("获取数据失败")
            return {}
        
        # 查找指定股票
        stock = stock_list[stock_list['代码'] == symbol]
        
        if stock.empty:
            print(f"未找到股票: {symbol}")
            return {}
        
        return stock.iloc[0].to_dict()
    
    def get_stock_detail(self, symbol: str) -> dict:
        """
        获取股票详细信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            dict: 股票详细信息
        """
        print(f"\n正在获取 {symbol} 详细信息...")
        return self.fetcher.get_stock_info(symbol)
    
    def get_history_data(self, symbol: str, days: int = 60) -> pd.DataFrame:
        """
        获取历史K线数据
        
        Args:
            symbol: 股票代码
            days: 获取天数
            
        Returns:
            DataFrame: 历史数据
        """
        print(f"\n正在获取 {symbol} 最近 {days} 天历史数据...")
        
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days + 30)).strftime("%Y%m%d")
        
        df = self.fetcher.get_stock_hist(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if df.empty:
            print("获取历史数据失败")
            return pd.DataFrame()
        
        # 只返回最近 N 天
        return df.tail(days)
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        if df.empty:
            return df
        
        # 计算均线
        df = TechnicalIndicators.calculate_ma(df, periods=[5, 10, 20, 60])
        
        # 计算 MACD
        df = TechnicalIndicators.calculate_macd(df)
        
        # 计算 RSI
        df = TechnicalIndicators.calculate_rsi(df)
        
        # 计算 KDJ
        df = TechnicalIndicators.calculate_kdj(df)
        
        # 计算布林带
        df = TechnicalIndicators.calculate_boll(df)
        
        return df
    
    def print_realtime(self, data: dict):
        """打印实时行情"""
        if not data:
            return
        
        print("\n" + "=" * 60)
        print(f"📊 {data.get('名称', '')} ({data.get('代码', '')})")
        print("=" * 60)
        
        # 基本行情
        print(f"\n【实时行情】")
        print(f"  最新价: {data.get('最新价', '-')}")
        print(f"  涨跌幅: {data.get('涨跌幅', '-'):.2f}%" if isinstance(data.get('涨跌幅'), (int, float)) else f"  涨跌幅: -")
        print(f"  今开:   {data.get('今开', '-')}")
        print(f"  最高:   {data.get('最高', '-')}")
        print(f"  最低:   {data.get('最低', '-')}")
        
        # 成交数据
        print(f"\n【成交数据】")
        volume = data.get('成交量', 0)
        if volume:
            print(f"  成交量: {volume/10000:.2f} 万手" if volume > 10000 else f"  成交量: {volume:.0f} 手")
        print(f"  换手率: {data.get('换手率', '-'):.2f}%" if isinstance(data.get('换手率'), (int, float)) else f"  换手率: -")
        print(f"  量比:   {data.get('量比', '-'):.2f}" if isinstance(data.get('量比'), (int, float)) else f"  量比: -")
        print(f"  振幅:   {data.get('振幅', '-'):.2f}%" if isinstance(data.get('振幅'), (int, float)) else f"  振幅: -")
        
        # 市值数据
        print(f"\n【市值数据】")
        total_mv = data.get('总市值', 0)
        float_mv = data.get('流通市值', 0)
        if total_mv:
            print(f"  总市值:   {total_mv/1e8:.2f} 亿")
        if float_mv:
            print(f"  流通市值: {float_mv/1e8:.2f} 亿")
        print(f"  市盈率:   {data.get('市盈率-动态', '-'):.2f}" if isinstance(data.get('市盈率-动态'), (int, float)) else f"  市盈率: -")
        
        print("=" * 60)
    
    def print_detail(self, data: dict):
        """打印详细信息"""
        if not data:
            return
        
        print("\n" + "=" * 60)
        print("📋 公司详细信息")
        print("=" * 60)
        
        for key, value in data.items():
            print(f"  {key}: {value}")
        
        print("=" * 60)
    
    def print_history(self, df: pd.DataFrame, show_indicators: bool = False):
        """打印历史数据"""
        if df.empty:
            return
        
        print("\n" + "=" * 80)
        print("📈 历史K线数据")
        print("=" * 80)
        
        # 设置显示选项
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.unicode.east_asian_width', True)
        
        # 选择显示的列
        if show_indicators:
            display_cols = ['日期', '开盘', '收盘', '最高', '最低', '成交量', 
                          'MA5', 'MA10', 'MA20', 'RSI', 'MACD', 'K', 'D']
        else:
            display_cols = ['日期', '开盘', '收盘', '最高', '最低', '成交量', '涨跌幅']
        
        # 只选择存在的列
        display_cols = [c for c in display_cols if c in df.columns]
        
        # 格式化
        display_df = df[display_cols].copy()
        display_df['日期'] = display_df['日期'].dt.strftime('%Y-%m-%d')
        
        print(display_df.tail(20).to_string(index=False))
        
        # 统计信息
        print("\n" + "-" * 80)
        print(f"数据区间: {df['日期'].min().strftime('%Y-%m-%d')} ~ {df['日期'].max().strftime('%Y-%m-%d')}")
        print(f"最高价: {df['最高'].max():.2f}  最低价: {df['最低'].min():.2f}")
        print(f"平均成交量: {df['成交量'].mean():.0f} 手")
        
        if '涨跌幅' in df.columns:
            up_days = (df['涨跌幅'] > 0).sum()
            down_days = (df['涨跌幅'] < 0).sum()
            print(f"上涨天数: {up_days}  下跌天数: {down_days}")
        
        print("=" * 80)
    
    def print_technical_analysis(self, df: pd.DataFrame):
        """打印技术分析"""
        if df.empty or len(df) < 5:
            return
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        print("\n" + "=" * 60)
        print("🔍 技术分析")
        print("=" * 60)
        
        # 均线分析
        print("\n【均线系统】")
        price = latest['收盘']
        
        for ma in ['MA5', 'MA10', 'MA20', 'MA60']:
            if ma in latest and pd.notna(latest[ma]):
                ma_value = latest[ma]
                diff = (price - ma_value) / ma_value * 100
                status = "↑" if price > ma_value else "↓"
                print(f"  {ma}: {ma_value:.2f} ({status} {abs(diff):.1f}%)")
        
        # 均线排列判断
        if all(ma in latest for ma in ['MA5', 'MA10', 'MA20']):
            ma5, ma10, ma20 = latest['MA5'], latest['MA10'], latest['MA20']
            if price > ma5 > ma10 > ma20:
                print("  状态: 多头排列 ✓")
            elif price < ma5 < ma10 < ma20:
                print("  状态: 空头排列 ✗")
            else:
                print("  状态: 震荡整理")
        
        # MACD 分析
        if 'MACD' in latest and 'Signal' in latest:
            print("\n【MACD指标】")
            macd = latest['MACD']
            signal = latest['Signal']
            hist = latest.get('Histogram', macd - signal)
            
            print(f"  MACD: {macd:.3f}")
            print(f"  Signal: {signal:.3f}")
            print(f"  柱状: {hist:.3f}")
            
            if macd > signal:
                print("  状态: 金叉/多头 ✓")
            else:
                print("  状态: 死叉/空头 ✗")
        
        # RSI 分析
        if 'RSI' in latest and pd.notna(latest['RSI']):
            print("\n【RSI指标】")
            rsi = latest['RSI']
            print(f"  RSI(14): {rsi:.2f}")
            
            if rsi > 70:
                print("  状态: 超买区域 ⚠")
            elif rsi < 30:
                print("  状态: 超卖区域 ⚠")
            else:
                print("  状态: 正常区域")
        
        # KDJ 分析
        if all(x in latest for x in ['K', 'D', 'J']):
            print("\n【KDJ指标】")
            k, d, j = latest['K'], latest['D'], latest['J']
            print(f"  K: {k:.2f}  D: {d:.2f}  J: {j:.2f}")
            
            if k > d:
                print("  状态: K上穿D ✓")
            else:
                print("  状态: K下穿D ✗")
        
        # 布林带分析
        if all(x in latest for x in ['BOLL_UPPER', 'BOLL_MIDDLE', 'BOLL_LOWER']):
            print("\n【布林带】")
            upper = latest['BOLL_UPPER']
            mid = latest['BOLL_MIDDLE']
            lower = latest['BOLL_LOWER']
            
            print(f"  上轨: {upper:.2f}")
            print(f"  中轨: {mid:.2f}")
            print(f"  下轨: {lower:.2f}")
            
            if price > upper:
                print("  状态: 突破上轨 ⚠")
            elif price < lower:
                print("  状态: 跌破下轨 ⚠")
            elif price > mid:
                print("  状态: 中轨上方")
            else:
                print("  状态: 中轨下方")
        
        print("=" * 60)
    
    def query(self, keyword: str, show_hist: bool = False, show_detail: bool = False,
              show_all: bool = False, days: int = 60, show_indicators: bool = False):
        """
        综合查询
        
        Args:
            keyword: 股票代码或名称
            show_hist: 是否显示历史数据
            show_detail: 是否显示详细信息
            show_all: 显示全部信息
            days: 历史数据天数
            show_indicators: 是否显示技术指标
        """
        # 解析股票代码（支持名称搜索）
        symbol, name = self.resolve_symbol(keyword)
        
        if not symbol:
            print(f"\n未找到匹配的股票: {keyword}")
            return
        
        print(f"\n查询股票: {name} ({symbol})")
        
        if show_all:
            show_hist = True
            show_detail = True
            show_indicators = True
        
        # 1. 实时行情（总是显示）
        realtime = self.get_realtime_info(symbol)
        self.print_realtime(realtime)
        
        # 2. 详细信息
        if show_detail:
            detail = self.get_stock_detail(symbol)
            self.print_detail(detail)
        
        # 3. 历史数据
        if show_hist or show_indicators:
            hist = self.get_history_data(symbol, days)
            
            if not hist.empty:
                # 计算技术指标
                hist = self.calculate_indicators(hist)
                
                # 打印历史数据
                self.print_history(hist, show_indicators)
                
                # 技术分析
                if show_indicators:
                    self.print_technical_analysis(hist)


def main():
    parser = argparse.ArgumentParser(
        description='股票信息查询工具 (支持代码或名称搜索)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_stock_query.py 000001              # 用代码查询平安银行
  python run_stock_query.py 平安银行            # 用名称查询
  python run_stock_query.py 茅台                # 模糊搜索
  python run_stock_query.py 中国长城 --hist     # 查询历史K线
  python run_stock_query.py 宁德时代 --tech     # 查询技术指标
  python run_stock_query.py 比亚迪 --all        # 查询全部信息
  python run_stock_query.py 银行                # 搜索包含"银行"的股票
        """
    )
    
    parser.add_argument('keyword', type=str, help='股票代码或名称 (支持模糊搜索)')
    parser.add_argument('--hist', '-H', action='store_true', help='显示历史K线')
    parser.add_argument('--days', '-d', type=int, default=60, help='历史数据天数 (默认60)')
    parser.add_argument('--detail', '-D', action='store_true', help='显示公司详细信息')
    parser.add_argument('--tech', '-t', action='store_true', help='显示技术指标分析')
    parser.add_argument('--all', '-a', action='store_true', help='显示全部信息')
    
    args = parser.parse_args()
    
    # 处理输入（去除可能的前缀）
    keyword = args.keyword.strip()
    if keyword.startswith('sh') or keyword.startswith('sz'):
        keyword = keyword[2:]
    
    # 执行查询
    query = StockQuery()
    query.query(
        keyword=keyword,
        show_hist=args.hist,
        show_detail=args.detail,
        show_all=args.all,
        days=args.days,
        show_indicators=args.tech
    )


if __name__ == "__main__":
    main()
