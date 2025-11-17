"""
Strands workflow configuration for the Data Cleaner Agent.

This module defines the workflow for cleaning CSV data using a multi-agent graph
architecture with validation loops for iterative data quality improvement.

工作流图结构可视化：
┌─────────────────────────────────────────────────────────────────────────┐
│                         数据清理工作流图                                  │
└─────────────────────────────────────────────────────────────────────────┘

                            ┌──────────────┐
                            │   START      │
                            └──────┬───────┘
                                   │
                                   ▼
                         ┌─────────────────┐
                         │   Analyzer      │
                         │  (分析+自动修复)  │
                         └────────┬────────┘
                                  │
                                  │ process_analyzer_output()
                                  │ (提取 escalations, valid_rows, auto_fixed)
                                  │
                                  ▼
                      ┌──────────────────────┐
                      │ Escalation Router    │
                      │ (检查是否有问题需处理) │
                      └──────┬───────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
         has_escalations?          no_escalations?
                │                         │
                ▼                         ▼
    ┌──────────────────────┐         ┌─────────┐
    │ Escalation Handler   │         │   END   │
    │ (用户交互修复问题)     │         └─────────┘
    └──────────┬───────────┘
               │
               │ process_handler_output()
               │ (保存用户修复的行)
               │
               └──────────┐
                          │
                          ▼
                  (循环回 Router)

关键特性：
- Analyzer: 分析数据，自动修复简单问题，识别需要用户处理的复杂问题
- Router: 管理 escalation 队列，决定是否需要继续处理问题
- Handler: 与用户交互，获取修复方案并应用
- 循环处理: 每次处理一个 escalation，直到全部解决
- 状态管理: Router 维护所有中间结果（auto_fixed, valid_rows, user_fixed_rows）
"""

import os
import json
import logging
from strands import Agent
from strands.models.openai import OpenAIModel
from strands.agent.agent_result import AgentResult
from strands.multiagent import GraphBuilder, MultiAgentBase, MultiAgentResult
from strands.multiagent.base import NodeResult, Status
from strands.types.content import ContentBlock, Message

logger = logging.getLogger(__name__)

# Import prompts
from src.prompts import (
    ANALYZE_AND_FIX_PROMPT,
    ESCALATION_HANDLER_PROMPT
)

# Import Pydantic models
from src.models import AnalyzerResult, HandlerResult

# Import handoff_to_user for human-in-the-loop interactions
from strands_tools import handoff_to_user


class EscalationRouter(MultiAgentBase):
    """
    Custom routing node that checks if there are escalations to handle.
    
    关键职责：
    1. 枚举 escalations
    2. 递增索引（如果上一个节点是 handler）
    3. 返回当前 escalation 给 handler 处理
    """
    
    def __init__(self):
        super().__init__()
        self.name = "escalation_router"
        
    async def invoke_async(self, task, invocation_state, **kwargs):
        """
        Enumerate escalations and construct result for each one.
        Returns the current escalation for handler to process.
        When all escalations are processed, signals completion.
        """
        
        # Read data from invocation_state (which is shared_state)
        analyzer_output = invocation_state.get('analyzer_output', {})
        escalations = analyzer_output.get('escalations', [])
        current_index = invocation_state.get('current_index', 0)
        last_node = invocation_state.get('last_node')
        
        logger.info(f"Router: last_node={last_node}, current_index={current_index}, total={len(escalations)}")
        
        # 关键：如果上一个节点是 handler，递增索引
        if last_node == 'escalation_handler':
            current_index += 1
            invocation_state['current_index'] = current_index
            logger.info(f"Router: 索引递增到 {current_index}")
        
        # Check if there are more escalations to process
        has_more = current_index < len(escalations)
        
        if has_more:
            # Get current escalation and construct message for handler
            current_escalation = escalations[current_index]
            escalation_json = json.dumps(current_escalation, ensure_ascii=False, indent=2)
            msg = f"请处理以下数据质量问题：\n\n{escalation_json}"
            logger.info(f"枚举 escalation {current_index + 1}/{len(escalations)}: row {current_escalation.get('_row_number')}")
        else:
            # All escalations processed
            msg = "✓ 所有问题已处理完成"
            logger.info("所有 escalations 枚举完成")
        
        agent_result = AgentResult(
            stop_reason="end_turn",
            message=Message(role="assistant", content=[ContentBlock(text=msg)]),
            metrics=None,
            state={
                "has_more_escalations": has_more,
                "total_escalations": len(escalations),
                "current_index": current_index
            }
        )
        
        return MultiAgentResult(
            status=Status.COMPLETED,
            results={self.name: NodeResult(result=agent_result, execution_time=10, status=Status.COMPLETED)},
            execution_count=1,
            execution_time=10
        )


def create_data_cleaning_graph(
    model: str = None,
    temperature: float = None,
    api_key: str = None,
    base_url: str = None,
    session_id: str = None,
    user_id: str = None
):
    """
    Create a multi-agent graph for data cleaning workflow.
    
    Graph structure (based on design.md):
    analyzer → escalation_router → (has_escalations? → escalation_handler → router) OR (no_escalations? → END)
    
    Args:
        model: LLM model name (optional, defaults from env)
        temperature: LLM temperature (optional, defaults from env)
        api_key: OpenAI API key (optional, defaults from env)
        base_url: API base URL (optional, defaults from env)
        session_id: Session ID for tracing (optional)
        user_id: User ID for tracing (optional)
        
    Returns:
        Tuple of (graph, shared_state) - graph ready for execution and shared state dict
    """
    
    # 创建共享状态（局部变量，不是全局变量）
    shared_state = {
        'analyzer_output': None,    # Analyzer 的输出结果
        'current_index': 0,          # 当前处理的 escalation 索引
        'user_fixed_rows': [],       # 用户修复的行列表
        'user_skipped_rows': [],     # 用户跳过的行列表（保存原始数据）
        'last_node': None            # 上一个执行的节点名称
    }
    
    # Load configuration from environment if not provided
    if model is None:
        model = os.getenv("MODEL_NAME", "gpt-4")
    if temperature is None:
        temperature = float(os.getenv("TEMPERATURE", "0.3"))
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")
    if base_url is None:
        base_url = os.getenv("OPENAI_BASE_URL")
    
    max_tokens = int(os.getenv("MAX_TOKENS", "4000"))
    
    # Validate API key
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is required. "
            "Please set it in your .env file or pass it as a parameter."
        )
    
    # Create model instance with Together AI configuration
    model_instance = OpenAIModel(
        client_args={
            "api_key": api_key,
            "base_url": base_url
        },
        model_id=model,
        params={
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
    )
    
    # Prepare trace attributes for observability
    trace_attributes = {}
    
    # Add session and user IDs if provided
    if session_id:
        trace_attributes["session.id"] = session_id
    if user_id:
        trace_attributes["user.id"] = user_id
    
    # Create analyzer agent (analysis and auto-fix)
    # No tools needed - receives data directly and returns analysis
    analyzer = Agent(
        name="analyzer",
        system_prompt=ANALYZE_AND_FIX_PROMPT,
        tools=[],  # No tools - pure analysis
        model=model_instance,
        callback_handler=None,
        structured_output_model=AnalyzerResult,  # Use structured output
        trace_attributes=trace_attributes if trace_attributes else None
    )
    
    # Create escalation router (custom routing node)
    router = EscalationRouter()
    
    # Create escalation handler agent
    # Escalation handler only needs handoff_to_user to get user input
    # It returns the fixed row data, which will be saved by edge condition
    escalation_handler = Agent(
        name="escalation_handler",
        system_prompt=ESCALATION_HANDLER_PROMPT,
        tools=[handoff_to_user],  # Only need user interaction tool
        model=model_instance,
        callback_handler=None,
        structured_output_model=HandlerResult,  # Use structured output
        trace_attributes=trace_attributes if trace_attributes else None
    )
    
    # Build the graph
    builder = GraphBuilder()
    builder.add_node(analyzer, "analyzer")
    builder.add_node(router, "escalation_router")
    builder.add_node(escalation_handler, "escalation_handler")
    
    # Condition function to process analyzer output and pass to router
    def process_analyzer_output(state):
        """
        Process analyzer output and store in shared_state.
        This runs when transitioning from analyzer to escalation_router.
        Uses structured_output for reliable data extraction.
        
        注意：condition 函数可能被多次调用，需要保持幂等性。
        """
        # 检查是否已经处理过（避免重复处理）
        if shared_state.get('analyzer_output') is not None:
            logger.info("Analyzer output already processed, skipping")
            return True
        
        analyzer_result = state.results.get("analyzer")
        if not analyzer_result:
            logger.warning("No analyzer result found")
            return True  # Continue anyway

        # Extract structured output from analyzer and store it directly
        try:
            if hasattr(analyzer_result.result, 'structured_output') and analyzer_result.result.structured_output:
                structured = analyzer_result.result.structured_output
                logger.info("Storing structured_output from analyzer")

                # Convert to dict with aliases for storage
                if hasattr(structured, 'model_dump'):
                    analyzer_data = structured.model_dump(by_alias=True)
                elif hasattr(structured, 'dict'):
                    analyzer_data = structured.dict(by_alias=True)
                else:
                    raise TypeError(f"Cannot convert structured_output to dict, type: {type(structured)}")

                logger.info(f"Analyzer results: {len(analyzer_data.get('escalations', []))} escalations, "
                           f"{len(analyzer_data.get('auto_fixed', []))} auto-fixed, "
                           f"{len(analyzer_data.get('valid_rows', []))} valid rows, "
                           f"{analyzer_data.get('total_rows', 0)} total rows")

                # Store analyzer output in shared_state
                shared_state['analyzer_output'] = analyzer_data
                shared_state['current_index'] = 0
                shared_state['user_fixed_rows'] = []
                shared_state['last_node'] = 'analyzer'
            else:
                logger.warning("No structured_output found in analyzer result")
                shared_state['analyzer_output'] = {
                    'escalations': [],
                    'valid_rows': [],
                    'auto_fixed': [],
                    'total_rows': 0
                }
                shared_state['current_index'] = 0
                shared_state['user_fixed_rows'] = []
                shared_state['last_node'] = 'analyzer'

        except Exception as e:
            logger.error(f"Error processing analyzer structured_output: {e}", exc_info=True)
            shared_state['analyzer_output'] = {
                'escalations': [],
                'valid_rows': [],
                'auto_fixed': [],
                'total_rows': 0
            }
            shared_state['current_index'] = 0
            shared_state['user_fixed_rows'] = []
            shared_state['last_node'] = 'analyzer'

        return True  # Always continue to router
    
    # Add edge with condition that processes analyzer output
    builder.add_edge("analyzer", "escalation_router", condition=process_analyzer_output)
    
    # Conditional routing function
    def has_more_escalations(state):
        """
        Check if there are more escalations to process.
        
        使用简洁的 index < length 判断，保持 condition 可重入。
        """
        escalations = shared_state.get('analyzer_output', {}).get('escalations', [])
        current_index = shared_state.get('current_index', 0)
        
        has_more = current_index < len(escalations)
        
        logger.info(f"Condition: has_more_escalations - index={current_index}, total={len(escalations)}, has_more={has_more}")
        
        return has_more
    
    # Condition function to process handler output and save user fix
    def process_handler_output(state):
        """
        Process escalation_handler output and store user-fixed row in shared_state.
        This runs when transitioning from escalation_handler back to escalation_router.
        Uses structured_output for reliable data extraction.
        
        注意：condition 函数可能被多次调用，需要避免重复保存。
        """
        handler_result = state.results.get("escalation_handler")
        if not handler_result:
            logger.warning("No handler result found")
            return True
        
        # Extract structured output from handler
        try:
            if hasattr(handler_result.result, 'structured_output') and handler_result.result.structured_output:
                structured = handler_result.result.structured_output
                logger.info("Using structured_output from handler")
                
                # Convert to dict with aliases
                if hasattr(structured, 'model_dump'):
                    handler_data = structured.model_dump(by_alias=True)
                elif hasattr(structured, 'dict'):
                    handler_data = structured.dict(by_alias=True)
                else:
                    raise TypeError(f"Cannot convert structured_output to dict, type: {type(structured)}")
                
                # 处理 handler 的结果（user_fixed 或 user_skipped）
                success = handler_data.get('success', False)
                
                if success and 'user_fixed' in handler_data and handler_data['user_fixed']:
                    # 用户成功修复
                    user_fixed = handler_data['user_fixed']
                    row_number = user_fixed.get('_row_number')
                    
                    # 检查是否已经记录过
                    user_fixed_rows = shared_state.get('user_fixed_rows', [])
                    already_recorded = any(
                        r.get('_row_number') == row_number 
                        for r in user_fixed_rows
                    )
                    
                    if not already_recorded:
                        user_fixed_rows.append(user_fixed)
                        shared_state['user_fixed_rows'] = user_fixed_rows
                        logger.info(f"Saved user-fixed row {row_number}")
                    else:
                        logger.info(f"Row {row_number} already recorded, skipping")
                        
                elif not success and 'user_skipped' in handler_data and handler_data['user_skipped']:
                    # 用户跳过，保存原始数据
                    user_skipped = handler_data['user_skipped']
                    row_number = user_skipped.get('_row_number')
                    
                    # 检查是否已经记录过
                    user_skipped_rows = shared_state.get('user_skipped_rows', [])
                    already_recorded = any(
                        r.get('_row_number') == row_number 
                        for r in user_skipped_rows
                    )
                    
                    if not already_recorded:
                        user_skipped_rows.append(user_skipped)
                        shared_state['user_skipped_rows'] = user_skipped_rows
                        logger.info(f"Saved user-skipped row {row_number}")
                    else:
                        logger.info(f"Row {row_number} already recorded as skipped, skipping")
                else:
                    logger.warning(f"Handler result missing data: success={success}, has_user_fixed={'user_fixed' in handler_data}, has_user_skipped={'user_skipped' in handler_data}")
            else:
                logger.warning("No structured_output found in handler result")
                
        except Exception as e:
            logger.error(f"Error processing handler structured_output: {e}", exc_info=True)
        
        # 标记上一个节点是 handler（Router 会根据这个来递增索引）
        shared_state['last_node'] = 'escalation_handler'
        
        return True
    
    # Add edges
    # Router -> Handler: only if there are more escalations to process
    builder.add_edge("escalation_router", "escalation_handler", condition=has_more_escalations)
    
    # Handler -> Router: always loop back (no condition needed)
    # Wrapper that processes handler output and always returns True
    def handler_to_router(state):
        process_handler_output(state)
        return True
    
    builder.add_edge("escalation_handler", "escalation_router", condition=handler_to_router)
    
    # When no more escalations, the graph ends at escalation_router
    
    # Configure graph
    builder.set_entry_point("analyzer")
    # builder.set_max_node_executions(500)  # Allow more iterations for multiple escalations
    # builder.set_execution_timeout(600)  # Longer timeout for user interactions
    builder.reset_on_revisit(False)  # Don't reset state when revisiting router
    
    # Build the graph
    graph = builder.build()
    
    # 返回 graph 和 shared_state
    return graph, shared_state


__all__ = ['create_data_cleaning_graph', 'EscalationRouter']
