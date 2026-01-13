"""
尾盘选股V3启动脚本
综合稳定版 - 多指标评分系统

使用方法:
1. 实时筛选:
   python run_tail_market_v3.py

2. 历史回测(指定日期):
   python run_tail_market_v3.py --date 20260106 --backtest

3. 多日回测:
   python run_tail_market_v3.py --multi --start 20260101 --end 20260107

4. 调整评分阈值:
   python run_tail_market_v3.py --score 70
"""
import sys
sys.path.append('strategies')

from tail_market_strategy_v3 import (
    run_tail_market_v3,
    run_multi_day_backtest,
    TailMarketScreenerV3
)


def main():
    """主函数 - 交互式选择运行模式"""
    print("=" * 70)
    print("🔥 尾盘选股V3 - 综合稳定版")
    print("=" * 70)
    print("\n请选择运行模式:")
    print("  1. 实时筛选 (当前市场)")
    print("  2. 历史回测 (指定日期 + 次日验证)")
    print("  3. 多日回测 (连续多天回测统计)")
    print("  4. 退出")
    
    try:
        choice = input("\n请输入选项 (1-4): ").strip()
        
        if choice == '1':
            print("\n启动实时筛选...")
            score = input("请输入最小评分阈值 (默认60): ").strip()
            min_score = float(score) if score else 60
            run_tail_market_v3(min_score=min_score)
            
        elif choice == '2':
            date = input("请输入目标日期 (YYYYMMDD, 如20260106): ").strip()
            if not date:
                print("未输入日期")
                return
            score = input("请输入最小评分阈值 (默认60): ").strip()
            min_score = float(score) if score else 60
            print(f"\n启动历史回测: {date}")
            run_tail_market_v3(target_date=date, check_next_day=True, min_score=min_score)
            
        elif choice == '3':
            start = input("请输入开始日期 (YYYYMMDD): ").strip()
            end = input("请输入结束日期 (YYYYMMDD): ").strip()
            if not start or not end:
                print("未输入完整日期")
                return
            score = input("请输入最小评分阈值 (默认60): ").strip()
            min_score = float(score) if score else 60
            print(f"\n启动多日回测: {start} ~ {end}")
            run_multi_day_backtest(start, end, min_score)
            
        elif choice == '4':
            print("退出")
            return
        else:
            print("无效选项")
            
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"错误: {e}")


def quick_run():
    """快速运行 - 使用默认参数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='尾盘选股V3 - 综合稳定版')
    parser.add_argument('--date', type=str, default=None, help='目标日期 YYYYMMDD')
    parser.add_argument('--backtest', action='store_true', help='回测模式')
    parser.add_argument('--score', type=float, default=60, help='最小评分')
    parser.add_argument('--multi', action='store_true', help='多日回测')
    parser.add_argument('--start', type=str, help='多日回测开始日期')
    parser.add_argument('--end', type=str, help='多日回测结束日期')
    parser.add_argument('--interactive', '-i', action='store_true', help='交互模式')
    
    args = parser.parse_args()
    
    if args.interactive:
        main()
    elif args.multi and args.start and args.end:
        run_multi_day_backtest(args.start, args.end, args.score)
    else:
        run_tail_market_v3(
            target_date=args.date,
            check_next_day=args.backtest,
            min_score=args.score
        )


if __name__ == "__main__":
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        quick_run()
    else:
        main()


