"""
快速运行相似股票推荐系统
"""
import sys
sys.path.append('src')

from similar_stocks import demo_find_similar

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════╗
    ║      相似股票推荐系统                         ║
    ║      Similar Stock Recommendation            ║
    ╚═══════════════════════════════════════════════╝
    
    功能说明:
    ✓ 根据技术指标找相似股票
    ✓ 多维度相似度计算
    ✓ 趋势、动量、波动率对比
    ✓ 资金流向相似度
    
    分析维度:
    - 趋势相似度 (MA走势)
    - 动量相似度 (MACD, RSI)
    - 波动率相似度
    - 成交量相似度 (换手率)
    - 估值相似度 (市盈率)
    """)
    
    demo_find_similar()
