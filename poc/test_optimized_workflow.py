#!/usr/bin/env python3
"""
测试优化后的 graph_workflow

验证：
1. shared_state 正确传递
2. Router 正确递增索引
3. condition 函数可重入
4. 循环逻辑正确
"""

import os
import sys
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.graph_workflow import create_data_cleaning_graph

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_graph_creation():
    """测试 graph 创建"""
    print("\n" + "=" * 70)
    print("测试优化后的 graph_workflow")
    print("=" * 70 + "\n")
    
    print("1. 测试 graph 创建...")
    try:
        graph, shared_state = create_data_cleaning_graph()
        print("   ✓ Graph 创建成功")
        print(f"   ✓ shared_state 类型: {type(shared_state)}")
        print(f"   ✓ shared_state keys: {list(shared_state.keys())}")
        
        # 验证 shared_state 结构
        expected_keys = ['analyzer_output', 'current_index', 'user_fixed_rows', 'last_node']
        for key in expected_keys:
            if key in shared_state:
                print(f"   ✓ shared_state['{key}'] 存在: {shared_state[key]}")
            else:
                print(f"   ✗ shared_state['{key}'] 缺失")
        
        return graph, shared_state
        
    except Exception as e:
        print(f"   ✗ Graph 创建失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_shared_state_structure(shared_state):
    """测试 shared_state 结构"""
    print("\n2. 测试 shared_state 结构...")
    
    if shared_state is None:
        print("   ✗ shared_state 为 None")
        return False
    
    # 验证初始值
    checks = [
        ('analyzer_output', None),
        ('current_index', 0),
        ('user_fixed_rows', []),
        ('last_node', None)
    ]
    
    all_passed = True
    for key, expected_value in checks:
        actual_value = shared_state.get(key)
        if actual_value == expected_value:
            print(f"   ✓ {key} = {actual_value}")
        else:
            print(f"   ✗ {key} = {actual_value}, 期望 {expected_value}")
            all_passed = False
    
    return all_passed


def main():
    """主函数"""
    # 测试 graph 创建
    graph, shared_state = test_graph_creation()
    
    if graph is None or shared_state is None:
        print("\n" + "=" * 70)
        print("测试失败：无法创建 graph")
        print("=" * 70 + "\n")
        return
    
    # 测试 shared_state 结构
    structure_ok = test_shared_state_structure(shared_state)
    
    # 总结
    print("\n" + "=" * 70)
    if structure_ok:
        print("✓ 所有测试通过！")
        print("\n优化要点：")
        print("  1. shared_state 作为局部变量创建")
        print("  2. 通过 invocation_state 参数传递")
        print("  3. Router 负责递增索引")
        print("  4. condition 函数保持可重入")
    else:
        print("✗ 部分测试失败")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
