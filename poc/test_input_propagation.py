#!/usr/bin/env python3
"""
验证 Graph 的 Input Propagation 格式

验证 task 参数是否包含以下格式：
Original Task: [The original task text]

Inputs from previous nodes:
From [node_id]:
- [Agent name]: [Result text]
- [Agent name]: [Another result text]

From [another_node_id]:
- [Agent name]: [Result text]
"""

import os
import re
import logging
from dotenv import load_dotenv
from strands.agent.agent_result import AgentResult
from strands.multiagent import GraphBuilder, MultiAgentBase, MultiAgentResult
from strands.multiagent.base import NodeResult, Status
from strands.types.content import ContentBlock, Message

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


def extract_previous_node_info(task):
    """
    从 task 中提取上一节点的名称和输出
    
    Args:
        task: str 或 list[ContentBlock]
        
    Returns:
        dict: {
            'original_task': str,
            'previous_nodes': [
                {
                    'node_id': str,
                    'outputs': [str, ...]
                },
                ...
            ]
        }
    """
    # 转换 task 为字符串
    if isinstance(task, list):
        task_text = ""
        for item in task:
            if isinstance(item, dict) and 'text' in item:
                task_text += item['text']
    else:
        task_text = str(task)
    
    result = {
        'original_task': None,
        'previous_nodes': []
    }
    
    # 提取 Original Task
    original_match = re.search(r'Original Task:\s*(.+?)(?=\n|$)', task_text, re.DOTALL)
    if original_match:
        result['original_task'] = original_match.group(1).strip()
    else:
        # 如果没有 "Original Task:" 标记，说明是入口节点，整个 task 就是原始任务
        if "Inputs from previous nodes:" not in task_text:
            result['original_task'] = task_text.strip()
            return result
    
    # 提取所有 "From [node_id]:" 块
    # 匹配模式：From node_id: 后面跟着的所有 "- Agent: ..." 行
    from_pattern = r'From\s+(\w+):\s*((?:\s*-\s*Agent:.*\n?)*)'
    from_matches = re.finditer(from_pattern, task_text)
    
    for match in from_matches:
        node_id = match.group(1)
        outputs_block = match.group(2)
        
        # 提取该节点的所有输出
        output_pattern = r'-\s*Agent:\s*(.+?)(?=\n|$)'
        outputs = re.findall(output_pattern, outputs_block)
        outputs = [o.strip() for o in outputs]
        
        result['previous_nodes'].append({
            'node_id': node_id,
            'outputs': outputs
        })
    
    return result


class TaskInspectorNode(MultiAgentBase):
    """检查节点 - 打印接收到的 task 内容"""
    
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        
    async def invoke_async(self, task, invocation_state, **kwargs):
        """检查并打印 task 内容"""
        logger.info(f"\n{'=' * 70}")
        logger.info(f"=== {self.name} 接收到的 task ===")
        logger.info(f"{'=' * 70}")
        
        # 打印 task 的类型和内容
        logger.info(f"task 类型: {type(task)}")
        
        if isinstance(task, str):
            logger.info(f"task 内容:\n{task}")
            
            # 验证格式
            has_original_task = "Original Task:" in task
            has_inputs_from = "Inputs from previous nodes:" in task
            has_from_node = "From " in task
            
            logger.info(f"\n格式验证:")
            logger.info(f"  ✓ 包含 'Original Task:': {has_original_task}")
            logger.info(f"  ✓ 包含 'Inputs from previous nodes:': {has_inputs_from}")
            logger.info(f"  ✓ 包含 'From [node_id]:': {has_from_node}")
            
        elif isinstance(task, list):
            logger.info(f"task 是列表，长度: {len(task)}")
            
            # 打印每个元素
            for i, item in enumerate(task):
                logger.info(f"  [{i}] {type(item)}: {item}")
            
            # 转换为字符串进行格式验证
            task_text = ""
            for item in task:
                if isinstance(item, dict) and 'text' in item:
                    task_text += item['text']
            
            if task_text:
                logger.info(f"\n完整 task 文本:\n{task_text}")
                
                # 验证格式
                has_original_task = "Original Task:" in task_text
                has_inputs_from = "Inputs from previous nodes:" in task_text
                has_from_node = "From " in task_text
                
                logger.info(f"\n格式验证:")
                logger.info(f"  ✓ 包含 'Original Task:': {has_original_task}")
                logger.info(f"  ✓ 包含 'Inputs from previous nodes:': {has_inputs_from}")
                logger.info(f"  ✓ 包含 'From [node_id]:': {has_from_node}")
        
        # 使用提取函数解析 task
        logger.info(f"\n{'=' * 70}")
        logger.info(f"=== 提取上一节点信息 ===")
        logger.info(f"{'=' * 70}")
        
        extracted = extract_previous_node_info(task)
        
        logger.info(f"\n原始任务: {extracted['original_task']}")
        logger.info(f"\n上一节点数量: {len(extracted['previous_nodes'])}")
        
        for i, node_info in enumerate(extracted['previous_nodes']):
            logger.info(f"\n上一节点 [{i+1}]:")
            logger.info(f"  节点ID: {node_info['node_id']}")
            logger.info(f"  输出数量: {len(node_info['outputs'])}")
            for j, output in enumerate(node_info['outputs']):
                logger.info(f"    输出 [{j+1}]: {output}")
        
        logger.info(f"\n{'=' * 70}\n")
        
        # 返回简单结果
        msg = f"{self.name} 处理完成"
        agent_result = AgentResult(
            stop_reason="end_turn",
            message=Message(role="assistant", content=[ContentBlock(text=msg)]),
            metrics=None,
            state={"processed": True}
        )
        
        return MultiAgentResult(
            status=Status.COMPLETED,
            results={self.name: NodeResult(result=agent_result, execution_time=10, status=Status.COMPLETED)},
            execution_count=1,
            execution_time=10
        )


def create_test_graph():
    """创建测试图 - 简单的线性流程"""
    
    node_a = TaskInspectorNode("node_a")
    node_b = TaskInspectorNode("node_b")
    node_c = TaskInspectorNode("node_c")
    
    builder = GraphBuilder()
    builder.add_node(node_a, "node_a")
    builder.add_node(node_b, "node_b")
    builder.add_node(node_c, "node_c")
    
    # 线性流程: node_a -> node_b -> node_c
    builder.add_edge("node_a", "node_b")
    builder.add_edge("node_b", "node_c")
    
    # 配置图
    builder.set_entry_point("node_a")
    builder.set_max_node_executions(10)
    builder.set_execution_timeout(60)
    
    return builder.build()


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("验证 Graph 的 Input Propagation 格式")
    print("=" * 70 + "\n")
    
    print("创建测试图...")
    graph = create_test_graph()
    
    print("\n执行图...")
    print("-" * 70 + "\n")
    
    try:
        # 执行图，传入原始任务
        original_task = "这是原始任务：分析数据并生成报告"
        result = graph(original_task)
        
        print("\n" + "-" * 70)
        print("执行完成！")
        print("=" * 70 + "\n")
        
        # 显示执行路径
        execution_path = ' -> '.join([node.node_id for node in result.execution_order])
        print(f"执行路径: {execution_path}\n")
        
        print("\n" + "=" * 70)
        print("验证完成！")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"执行失败: {e}")
        print("=" * 70 + "\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
