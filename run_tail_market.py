"""
快速运行尾盘选股策略
"""
import sys
sys.path.append('src')
sys.path.append('strategies')

from tail_market_strategy import run_tail_market_screen

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════╗
    ║      尾盘选股策略                             ║
    ║      Tail Market Stock Screening             ║
    ╚═══════════════════════════════════════════════╝
    
    策略条件:
    ✓ 涨幅: 1.3%-5%
    ✓ 量比: >1 (当日成交量/近5日均量)
    ✓ 换手率: 5%-10%
    ✓ 流通市值: 50-200亿
    ✓ 成交量: 阶梯式抬高(持续放量)
    ✓ 均线: MA5>MA10>MA20>MA60 (多头排列)
    ✓ 分时: 全天价格在均价线之上
    ✓ 尾盘: 14:30后创新高,回踩不破均价线
    
    开始筛选...
    """)
    
    run_tail_market_screen()
