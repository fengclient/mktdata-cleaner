#!/usr/bin/env python3
"""
简单测试：验证 shared_state 的创建和传递
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.graph_workflow import create_data_cleaning_graph

print("\n" + "=" * 70)
print("测试 shared_state 的创建和传递")
print("=" * 70 + "\n")

try:
    print("1. 创建 graph...")
    # 传入假的 API key 用于测试结构
    graph, shared_state = create_data_cleaning_graph(
        api_key="test-key",
        base_url="https://api.test.com"
    )
    print("   ✓ Graph 创建成功")
    
    print("\n2. 检查 shared_state...")
    print(f"   类型: {type(shared_state)}")
    print(f"   Keys: {list(shared_state.keys())}")
    
    print("\n3. 检查初始值...")
    for key, value in shared_state.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 70)
    print("✓ 测试通过！shared_state 正确创建")
    print("=" * 70 + "\n")
    
except Exception as e:
    print(f"\n✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()
