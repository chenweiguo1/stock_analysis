"""
快速运行高级筛选器
直接运行此文件即可进行多条件股票筛选
"""
import sys
sys.path.append('src')

from advanced_screener import run_custom_screen

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════╗
    ║      A股高级筛选器                            ║
    ║      Advanced Stock Screener                 ║
    ╚═══════════════════════════════════════════════╝
    
    筛选条件:
    ✓ 股价在MA120附近 (95%-105%)
    ✓ 当日涨幅: 2.5%-5%
    ✓ 最近20天内有涨停
    ✓ 流通市值: 40-300亿
    ✓ 换手率: 5%-10%
    ✓ 排除科创板(688开头)
    ✓ 排除ST股票
    
    开始筛选...
    """)
    
    run_custom_screen()
