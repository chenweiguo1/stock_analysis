"""
尾盘选股器启动脚本
快速启动14:30专用尾盘选股器

使用方法:
1. 原版(慢): python run_tail_market.py
2. 优化版(快): python run_tail_market.py --optimized
3. 指定线程数: python run_tail_market.py --optimized --workers 15
"""
import sys
import argparse
sys.path.append('strategies')

from tail_market_strategy import run_tail_market_screener
from tail_market_strategy_old import run_tail_market_screener_old
from tail_market_strategy_old_optimized import run_tail_market_screener_old_optimized

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='尾盘选股器')
    parser.add_argument('--optimized', action='store_true', 
                       help='使用优化版(并行处理，速度快3-5倍)')
    parser.add_argument('--workers', type=int, default=10,
                       help='并行线程数(仅优化版有效，默认10)')
    
    args = parser.parse_args()
    
    if args.optimized:
        print("=" * 70)
        print("启动尾盘选股器 - 优化版 (并行处理)")
        print("=" * 70)
        run_tail_market_screener_old_optimized(max_workers=args.workers)
    else:
        print("=" * 70)
        print("启动尾盘选股器 - 原版")
        print("=" * 70)
        print("提示: 使用 --optimized 参数可启用优化版(速度快3-5倍)")
        print("=" * 70)
        run_tail_market_screener_old()

