#!/usr/bin/env python3
"""
测试 Analyzer Agent

这个脚本用于单独测试 analyzer 的行为，
验证它是否能正确分析 CSV 数据并返回 auto_fixed、escalations 和 valid_rows。
"""

import os
import json
import logging
from dotenv import load_dotenv
from strands import Agent
from strands.models.openai import OpenAIModel
from strands.telemetry import StrandsTelemetry
from src.prompts import ANALYZE_AND_FIX_PROMPT

# 配置日志
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

logging.getLogger("strands").setLevel(logging.WARNING)
logging.getLogger("strands_tools").setLevel(logging.WARNING)


# 加载环境变量
load_dotenv()

# # 设置可观测性
# def setup_observability():
#     """Setup observability with OTLP and console exporters."""
#     strands_telemetry = StrandsTelemetry()
#     strands_telemetry.setup_otlp_exporter()
#     strands_telemetry.setup_meter(
#         enable_console_exporter=False,
#         enable_otlp_exporter=True
#     )

# logger.info("🔧 设置可观测性...")
# setup_observability()
# logger.info("✓ 可观测性配置完成")


def create_test_analyzer():
    """创建测试用的 analyzer agent"""
    
    logger.info("🤖 创建 Analyzer Agent...")
    
    # 获取配置
    model = os.getenv("MODEL_NAME", "gpt-4")
    temperature = float(os.getenv("TEMPERATURE", "0.3"))
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    max_tokens = int(os.getenv("MAX_TOKENS", "4000"))
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")
    
    logger.info(f"模型: {model}, 温度: {temperature}, max_tokens: {max_tokens}")
    
    # 创建模型
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
    
    # 使用共享的 Pydantic 模型
    from src.models import AnalyzerResult
    
    # 创建 analyzer agent（使用结构化输出）
    analyzer = Agent(
        name="analyzer",
        system_prompt=ANALYZE_AND_FIX_PROMPT,
        tools=[],  # 没有工具
        model=model_instance,
        callback_handler=None,
        structured_output_model=AnalyzerResult  # 使用结构化输出
    )
    
    logger.info("✓ Agent 创建成功（使用结构化输出）")
    return analyzer


def parse_analyzer_result(result):
    """解析 Analyzer 结果为 JSON（使用 structured_output）"""
    try:
        if not hasattr(result, 'structured_output'):
            raise AttributeError("result 对象没有 structured_output 属性")
        
        if not result.structured_output:
            raise ValueError("structured_output 为空")
        
        logger.info("使用 structured_output")
        structured = result.structured_output
        
        # 转换为字典
        if hasattr(structured, 'model_dump'):
            return structured.model_dump(by_alias=True)
        elif hasattr(structured, 'dict'):
            return structured.dict(by_alias=True)
        else:
            raise TypeError(f"无法将 structured_output 转换为字典，类型: {type(structured)}")
    
    except Exception as e:
        logger.error(f"解析 structured_output 失败: {e}")
        logger.error(f"result 类型: {type(result)}")
        logger.error(f"result 属性: {dir(result)}")
        if hasattr(result, 'structured_output'):
            logger.error(f"structured_output 类型: {type(result.structured_output)}")
        raise


def test_simple_data():
    """测试场景1：简单的测试数据"""
    print("\n" + "="*60)
    print("测试场景1：简单的测试数据")
    print("="*60)
    
    # 构建测试数据
    csv_data = {
        "success": True,
        "file_path": "test.csv",
        "row_count": 5,
        "rows": [
            {
                "_row_number": 1,
                "name": "张三",
                "gender": "男",
                "title": "工程师",
                "email": "zhangsan@example.com",
                "mobile": "13812345678",
                "wechat": "zhangsan_wx",
                "remark": ""
            },
            {
                "_row_number": 2,
                "name": "李四",
                "gender": "女",
                "title": "部门经理",
                "email": "lisi@@example.com",  # 需要自动修复：重复@
                "mobile": "13987654321",
                "wechat": "",
                "remark": ""
            },
            {
                "_row_number": 3,
                "name": "王五",
                "gender": "男性",  # 需要自动修复：标准化为"男"
                "title": "高级工程师",
                "email": "wangwu@example.com",
                "mobile": "138-1234-5678",  # 需要自动修复：删除格式化字符
                "wechat": "wangwu",
                "remark": ""
            },
            {
                "_row_number": 4,
                "name": "赵六",
                "gender": "女",
                "title": "顾问",  # 需要 escalation：不在有效职位列表中
                "email": "zhaoliu@example.com",
                "mobile": "13912345678",
                "wechat": "",
                "remark": ""
            },
            {
                "_row_number": 5,
                "name": "孙七",
                "gender": "男",
                "title": "顾问",  # 需要 escalation：不在有效职位列表中
                "email": "sunqi@example.com",
                "mobile": "136416543",  # 需要 escalation：位数不足
                "wechat": "",
                "remark": ""
            }
        ]
    }
    
    print("\n📋 输入数据:")
    print(f"总行数: {csv_data['row_count']}")
    print("包含以下问题:")
    print("  - 第2行: email 有重复@ (需要自动修复)")
    print("  - 第3行: gender 为'男性' (需要自动修复)")
    print("  - 第3行: mobile 有格式化字符 (需要自动修复)")
    print("  - 第4行: title 为'顾问' (需要 escalation)")
    print("  - 第5行: title 为'顾问' + mobile 只有9位 (需要 escalation，一行多个问题)")
    
    # 构建任务
    csv_json = json.dumps(csv_data, ensure_ascii=False, indent=2)
    task = f"请分析以下CSV数据并进行数据清理：\n\n{csv_json}"
    
    # 创建 analyzer
    analyzer = create_test_analyzer()
    
    # 执行
    print("\n🤖 Analyzer 执行中...")
    logger.info("🚀 开始执行 Analyzer...")
    try:
        result = analyzer(task)
        logger.info("✓ Analyzer 执行完成")
    except Exception as e:
        logger.error(f"✗ Analyzer 执行失败: {e}", exc_info=True)
        raise
    
    print("\n✅ Analyzer 输出:")
    print(result)
    
    # 解析结果
    try:
        parsed_dict = parse_analyzer_result(result)
        logger.info("✓ 结果解析成功")
        
        print("\n📊 解析后的结果:")
        print(json.dumps(parsed_dict, ensure_ascii=False, indent=2))
        
        # 验证结果
        print("\n🔍 验证结果:")
        print(f"  总行数: {parsed_dict.get('total_rows', 'N/A')}")
        print(f"  自动修复数量: {len(parsed_dict.get('auto_fixed', []))}")
        print(f"  需要 escalation 数量: {len(parsed_dict.get('escalations', []))}")
        print(f"  完全正常行数量: {len(parsed_dict.get('valid_rows', []))}")
        
        if parsed_dict.get('auto_fixed'):
            print("\n  自动修复详情:")
            for auto_fixed in parsed_dict['auto_fixed']:
                row_num = auto_fixed['_row_number']
                fixes = auto_fixed['fixes']
                if len(fixes) == 1:
                    fix = fixes[0]
                    print(f"    - 第{row_num}行 {fix['column']}: {fix['old_value']} → {fix['new_value']}")
                else:
                    print(f"    - 第{row_num}行有{len(fixes)}个修复:")
                    for i, fix in enumerate(fixes, 1):
                        print(f"      {i}. {fix['column']}: {fix['old_value']} → {fix['new_value']}")
        
        if parsed_dict.get('escalations'):
            print("\n  Escalation 详情:")
            for esc in parsed_dict['escalations']:
                row_num = esc['_row_number']
                issues = esc['issues']
                if len(issues) == 1:
                    issue = issues[0]
                    print(f"    - 第{row_num}行 {issue['column']}: {issue['issue_type']} - {issue['description']}")
                else:
                    print(f"    - 第{row_num}行有{len(issues)}个问题:")
                    for i, issue in enumerate(issues, 1):
                        print(f"      {i}. {issue['column']}: {issue['issue_type']} - {issue['description']}")
        
    except Exception as e:
        print(f"\n⚠️ 结果解析失败: {e}")
        logger.error(f"结果解析失败: {e}", exc_info=True)
        print("原始输出:", result)


def main():
    """主函数"""
    print("\n🧪 Analyzer Agent 测试")
    print("\n这个脚本测试 analyzer 是否能：")
    print("  1. 正确分析 CSV 数据")
    print("  2. 识别可以自动修复的问题")
    print("  3. 识别需要 escalation 的问题")
    print("  4. 返回正确格式的 JSON")
    
    test_simple_data()
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)
    
    print("\n✅ 验证要点：")
    print("  1. Analyzer 是否处理了所有行？")
    print("  2. 是否正确识别了需要自动修复的问题？")
    print("  3. 是否正确识别了需要 escalation 的问题？")
    print("  4. 输出的 JSON 格式是否正确？")
    print("  5. auto_fixed 是否包含 fixed_row？")
    print("  6. escalations 是否包含 current_row？")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
