"""
尾盘选股器启动脚本
快速启动14:30专用尾盘选股器
"""
import sys
sys.path.append('strategies')

from tail_market_strategy import run_tail_market_screener

if __name__ == "__main__":
    print("=" * 70)
    print("启动尾盘选股器 (14:30专用版)")
    print("=" * 70)
    run_tail_market_screener()
