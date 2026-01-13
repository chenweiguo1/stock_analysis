"""
尾盘选股器V2启动脚本
支持历史回测，可指定日期进行选股

使用方法:
1. 实时筛选:
   python run_tail_market_v2.py
   
2. 历史回测(指定日期):
   python run_tail_market_v2.py --date 20260106
   
3. 历史回测并检查次日表现:
   python run_tail_market_v2.py --date 20260106 --backtest
"""
import sys
sys.path.append('strategies')

from tail_market_strategy_v2 import run_tail_market_screener_v2

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='尾盘选股器V2 - 支持历史回测')
    parser.add_argument('--date', type=str, default=None, 
                        help='目标日期，格式YYYYMMDD，如20260106')
    parser.add_argument('--backtest', action='store_true',
                        help='回测模式，检查次日表现')
    
    args = parser.parse_args()
    
    print("=" * 70)
    if args.date:
        print(f"启动尾盘选股器V2 (历史回测模式: {args.date})")
    else:
        print("启动尾盘选股器V2 (实时模式)")
    print("=" * 70)
    
    run_tail_market_screener_v2(target_date=args.date, check_next_day=args.backtest)


