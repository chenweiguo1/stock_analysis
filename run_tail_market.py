"""
尾盘选股器启动脚本
快速启动14:30专用尾盘选股器

使用方法:
    python run_tail_market.py                    # 默认参数运行
    python run_tail_market.py --workers 15       # 指定线程数
    python run_tail_market.py --min-change 2.0   # 指定最小涨幅
    python run_tail_market.py --exclude-cyb      # 排除创业板
    python run_tail_market.py --debug            # 启用调试日志

筛选条件:
    - 涨幅: 1.3%-5%
    - 量比: >1.0
    - 换手率: 5%-10%
    - 市值: 50-200亿
    - 均线: 多头排列
    - 成交量: 阶梯放量
"""
import sys
import argparse
sys.path.append('strategies')

from tail_market_strategy_old_optimized import run_tail_market_screener_old_optimized

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='尾盘选股器 - 优化版',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_tail_market.py                          # 使用默认参数
  python run_tail_market.py --workers 15             # 使用15个线程
  python run_tail_market.py --min-cap 80 --max-cap 150   # 市值80-150亿
  python run_tail_market.py --exclude-cyb            # 排除创业板
        """
    )
    
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
