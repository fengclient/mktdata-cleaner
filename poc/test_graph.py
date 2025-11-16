#!/usr/bin/env python3
"""
测试 Graph 核心逻辑 - 使用 shared_state 方案

验证：
1. shared_state 作为局部变量传递
2. 节点通过 invocation_state 访问 shared_state
3. condition 函数通过闭包访问 shared_state
4. 循环逻辑：router -> handler -> router
"""

import os
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


class DataProcessor(MultiAgentBase):
    """模拟 Analyzer - 处理数据并输出 escalations"""
    
    def __init__(self):
        super().__init__()
        self.name = "processor"
        
    async def invoke_async(self, task, invocation_state, **kwargs):
        """处理数据，模拟 analyzer 的行为"""
        logger.info("=== DataProcessor 执行 ===")
        
        # 模拟分析结果 - 生成 3 个 escalations
        escalations = [
            {'_row_number': 1, 'issue': 'problem1'},
            {'_row_number': 2, 'issue': 'problem2'},
            {'_row_number': 3, 'issue': 'problem3'}
        ]
        
        msg = f"处理完成，发现 {len(escalations)} 个问题"
        logger.info(f"DataProcessor 输出: {msg}")
        
        # 返回结果，包含 escalations
        agent_result = AgentResult(
            stop_reason="end_turn",
            message=Message(role="assistant", content=[ContentBlock(text=msg)]),
            metrics=None,
            state={
                "escalations": escalations,
                "processed": True
            }
        )
        
        return MultiAgentResult(
            status=Status.COMPLETED,
            results={self.name: NodeResult(result=agent_result, execution_time=10, status=Status.COMPLETED)},
            execution_count=1,
            execution_time=10
        )


class ItemRouter(MultiAgentBase):
    """模拟 EscalationRouter - 枚举 escalations"""
    
    def __init__(self):
        super().__init__()
        self.name = "router"
        
    async def invoke_async(self, task, invocation_state, **kwargs):
        """枚举项目，决定是否还有更多项目需要处理"""
        logger.info("=== ItemRouter 执行 ===")
        
        # 现在 invocation_state 就是 shared_state！
        last_node = invocation_state.get('last_node')
        escalations = invocation_state.get('escalations', [])
        current_index = invocation_state.get('current_index', 0)
        
        logger.info(f"Router: last_node={last_node}, current_index={current_index}, total={len(escalations)}")
        
        # 关键：如果上一个节点是 handler，递增索引
        if last_node == 'handler':
            current_index += 1
            invocation_state['current_index'] = current_index
            logger.info(f"Router: 索引递增到 {current_index}")
            msg = f"继续处理下一个问题"
        elif last_node == 'processor':
            msg = f"开始处理 {len(escalations)} 个问题"
        else:
            msg = "Router 初始化"
        
        # 如果还有问题要处理
        if current_index < len(escalations):
            current_esc = escalations[current_index]
            msg += f"\n当前: 第{current_esc['_row_number']}行 - {current_esc['issue']}"
        else:
            msg = "所有问题已处理完成"
        
        logger.info(f"Router: {msg}")
        
        # 返回结果
        agent_result = AgentResult(
            stop_reason="end_turn",
            message=Message(role="assistant", content=[ContentBlock(text=msg)]),
            metrics=None,
            state={
                "current_index": current_index,
                "total_escalations": len(escalations),
                "has_more": current_index < len(escalations)
            }
        )
        
        return MultiAgentResult(
            status=Status.COMPLETED,
            results={self.name: NodeResult(result=agent_result, execution_time=10, status=Status.COMPLETED)},
            execution_count=1,
            execution_time=10
        )


class ItemHandler(MultiAgentBase):
    """模拟 EscalationHandler - 处理单个 escalation"""
    
    def __init__(self):
        super().__init__()
        self.name = "handler"
        
    async def invoke_async(self, task, invocation_state, **kwargs):
        """处理当前项目"""
        logger.info("=== ItemHandler 执行 ===")
        
        # 从 invocation_state (shared_state) 读取当前 escalation
        escalations = invocation_state.get('escalations', [])
        current_index = invocation_state.get('current_index', 0)
        
        if current_index < len(escalations):
            current_esc = escalations[current_index]
            
            # Fake 用户输入（简化）
            fake_user_input = f"fixed_value_for_row_{current_esc['_row_number']}"
            
            msg = f"已处理第{current_esc['_row_number']}行，修复值: {fake_user_input}"
            logger.info(f"Handler: {msg}")
            
            # 标记上一个节点是 handler（Router 会根据这个来递增索引）
            invocation_state['last_node'] = 'handler'
            
            # 构造修复结果
            user_fixed = {
                "_row_number": current_esc['_row_number'],
                "fixed_value": fake_user_input
            }
            
            # 返回修复结果
            agent_result = AgentResult(
                stop_reason="end_turn",
                message=Message(role="assistant", content=[ContentBlock(text=msg)]),
                metrics=None,
                state={
                    "user_fixed": user_fixed
                }
            )
        else:
            msg = "没有项目需要处理"
            agent_result = AgentResult(
                stop_reason="end_turn",
                message=Message(role="assistant", content=[ContentBlock(text=msg)]),
                metrics=None,
                state={}
            )
        
        return MultiAgentResult(
            status=Status.COMPLETED,
            results={self.name: NodeResult(result=agent_result, execution_time=10, status=Status.COMPLETED)},
            execution_count=1,
            execution_time=10
        )


def create_test_graph():
    """创建测试图"""
    
    # 创建共享状态（局部变量，不是全局变量）
    shared_state = {
        'escalations': [],          # 所有 escalations 列表
        'current_index': 0,         # 当前处理的索引
        'user_fixed_rows': [],      # 用户修复的行列表
        'last_node': None           # 上一个节点名称
    }
    
    processor = DataProcessor()
    router = ItemRouter()
    handler = ItemHandler()
    
    builder = GraphBuilder()
    builder.add_node(processor, "processor")
    builder.add_node(router, "router")
    builder.add_node(handler, "handler")
    
    # 定义 condition 函数（通过闭包访问 shared_state）
    
    def process_analyzer_output(state):
        """从 analyzer 提取结果，存入 shared_state（只在第一次调用时执行）"""
        logger.info("=== Condition: process_analyzer_output ===")
        
        # 检查是否已经处理过（避免重复）
        if shared_state.get('escalations'):
            logger.info("escalations 已存在，跳过")
            return True
        
        # 提取 analyzer 结果
        analyzer_result = state.results.get('processor')
        if analyzer_result:
            multi_result = analyzer_result.result
            if hasattr(multi_result, 'results') and 'processor' in multi_result.results:
                agent_result = multi_result.results['processor'].result
                if hasattr(agent_result, 'state'):
                    analyzer_state = agent_result.state
                    escalations = analyzer_state.get('escalations', [])
                    
                    # 存入 shared_state
                    shared_state['escalations'] = escalations
                    shared_state['current_index'] = 0
                    shared_state['last_node'] = 'processor'
                    
                    logger.info(f"提取到 {len(escalations)} 个 escalations")
        
        return True
    
    def has_more_escalations(state):
        """判断是否还有更多 escalations 需要处理（纯判断，不修改状态）"""
        logger.info("=== Condition: has_more_escalations ===")
        
        # 用 index < length 判断
        escalations = shared_state.get('escalations', [])
        current_index = shared_state.get('current_index', 0)
        
        has_more = current_index < len(escalations)
        
        logger.info(f"current_index={current_index}, total={len(escalations)}, has_more={has_more}")
        
        return has_more
    
    def handler_to_router(state):
        """handler 处理完后循环回 router（纯判断，保存修复结果）"""
        logger.info("=== Condition: handler_to_router ===")
        
        # 提取 handler 结果并保存
        handler_result = state.results.get('handler')
        if handler_result:
            multi_result = handler_result.result
            if hasattr(multi_result, 'results') and 'handler' in multi_result.results:
                agent_result = multi_result.results['handler'].result
                if hasattr(agent_result, 'state'):
                    handler_state = agent_result.state
                    user_fixed = handler_state.get('user_fixed')
                    
                    # 保存修复结果（检查是否已存在，避免重复）
                    if user_fixed:
                        row_number = user_fixed.get('_row_number')
                        already_recorded = any(
                            r.get('_row_number') == row_number 
                            for r in shared_state.get('user_fixed_rows', [])
                        )
                        
                        if not already_recorded:
                            shared_state['user_fixed_rows'].append(user_fixed)
                            logger.info(f"记录修复: {user_fixed}")
                        else:
                            logger.info(f"跳过重复记录: row {row_number}")
        
        # 标记上一个节点是 handler（router 会根据这个来递增索引）
        shared_state['last_node'] = 'handler'
        
        return True
    
    # 添加边
    builder.add_edge("processor", "router", condition=process_analyzer_output)
    builder.add_edge("router", "handler", condition=has_more_escalations)
    builder.add_edge("handler", "router", condition=handler_to_router)
    
    # 配置图
    builder.set_entry_point("processor")
    builder.set_max_node_executions(20)
    builder.set_execution_timeout(60)
    builder.reset_on_revisit(False)
    
    # 构建图并返回 (graph, shared_state)
    graph = builder.build()
    return graph, shared_state


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("测试 Graph 核心逻辑 - shared_state 方案")
    print("=" * 60 + "\n")
    
    print("创建测试图...")
    graph, shared_state = create_test_graph()
    
    print("\n执行图...")
    print("-" * 60 + "\n")
    
    try:
        # 关键：在调用 graph 时传递 invocation_state
        result = graph("开始处理数据", invocation_state=shared_state)
        
        print("\n" + "-" * 60)
        print("执行完成！")
        print("=" * 60 + "\n")
        
        # 显示执行路径
        execution_path = ' -> '.join([node.node_id for node in result.execution_order])
        print(f"执行路径: {execution_path}\n")
        
        # 显示节点执行次数
        print("节点执行次数:")
        node_counts = {}
        for node in result.execution_order:
            node_counts[node.node_id] = node_counts.get(node.node_id, 0) + 1
        for node_id, count in node_counts.items():
            print(f"  {node_id}: {count} 次")
        
        # 显示最终 shared_state
        print(f"\n最终 shared_state:")
        print(f"  escalations: {len(shared_state.get('escalations', []))} 个")
        print(f"  user_fixed_rows: {len(shared_state.get('user_fixed_rows', []))} 个")
        print(f"  current_index: {shared_state.get('current_index', 0)}")
        print(f"  last_node: {shared_state.get('last_node')}")
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"执行失败: {e}")
        print("=" * 60 + "\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
