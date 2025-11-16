#!/usr/bin/env python3
"""
测试 EscalationHandler Agent

这个脚本用于单独测试 escalation_handler 的行为，
验证它是否能正确使用 handoff_to_user 工具并返回 user_fixed 数据。
"""

import os
import json
import logging
from dotenv import load_dotenv
from strands import Agent
from strands.models.openai import OpenAIModel
from strands.telemetry import StrandsTelemetry
from strands_tools import handoff_to_user
from src.prompts import ESCALATION_HANDLER_PROMPT

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

# 设置可观测性
def setup_observability():
    """Setup observability with OTLP and console exporters."""
    strands_telemetry = StrandsTelemetry()
    strands_telemetry.setup_otlp_exporter()
    strands_telemetry.setup_meter(
        enable_console_exporter=False,
        enable_otlp_exporter=True
    )

# logger.info("🔧 设置可观测性...")
# setup_observability()
# logger.info("✓ 可观测性配置完成")

def parse_agent_result(result):
    """解析 Agent 结果为 JSON（使用 structured_output）"""
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


def create_test_handler():
    """创建测试用的 escalation handler agent"""
    
    logger.info("🤖 创建 EscalationHandler Agent...")
    
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
    
    # 定义输出结构
    from pydantic import BaseModel, Field
    from typing import Optional, Dict, Any
    
    from pydantic import ConfigDict
    
    class UserFixed(BaseModel):
        """修复后的行数据"""
        model_config = ConfigDict(populate_by_name=True)
        
        row_number: int = Field(description="行号", alias="_row_number")
        name: str = Field(description="姓名")
        gender: str = Field(description="性别")
        title: str = Field(description="职位")
        email: str = Field(description="电子邮件")
        mobile: str = Field(description="手机号")
        wechat: str = Field(description="微信号")
        remark: str = Field(description="备注")
    
    class EscalationResult(BaseModel):
        """Escalation 处理结果"""
        success: bool = Field(description="是否成功修复")
        user_fixed: Optional[UserFixed] = Field(None, description="修复后的完整行数据")
        reason: Optional[str] = Field(None, description="失败原因（如果 success=false）")
    
    # 创建 handler agent
    handler = Agent(
        name="escalation_handler",
        system_prompt=ESCALATION_HANDLER_PROMPT,
        tools=[handoff_to_user],  # 只使用 handoff_to_user
        model=model_instance,
        structured_output_model=EscalationResult,  # 使用结构化输出
        callback_handler=None  # 抑制 console 输出
    )
    
    logger.info("✓ Agent 创建成功（使用结构化输出）")
    return handler


def test_missing_digits():
    """测试场景1：手机号位数不足（示例1）"""
    print("\n" + "="*60)
    print("测试场景1：手机号位数不足")
    print("="*60)
    
    # 构建 escalation 数据（使用统一的 issues 数组格式）
    escalation = {
        "_row_number": 5,
        "issues": [
            {
                "column": "mobile",
                "issue_type": "missing_digits",
                "current_value": "136416543",
                "description": "手机号只有9位，需要11位",
                "suggestions": ["请提供完整的11位手机号"]
            }
        ],
        "current_row": {
            "_row_number": 5,
            "name": "张三",
            "gender": "男",
            "title": "工程师",
            "email": "zhangsan@example.com",
            "mobile": "136416543",
            "wechat": "zhangsan_wx",
            "remark": ""
        }
    }
    
    print("\n📝 期望交互:")
    print('第5行的手机号"136416543"只有9位数字，需要11位。')
    print('请提供完整的11位手机号码。')
    print('\n示例：13812345678')
    print('\n💡 建议输入: 13641654321')
    
    # 构建任务
    escalation_json = json.dumps(escalation, ensure_ascii=False, indent=2)
    task = f"请处理以下数据质量问题：\n\n{escalation_json}"
    
    print("\n📋 输入任务:")
    print(task)
    
    # 创建 handler
    handler = create_test_handler()
    
    # 执行
    print("\n🤖 Handler 执行中...")
    print("(Agent 会使用 handoff_to_user 向你请求输入)")
    
    logger.info("🚀 开始执行 Handler...")
    try:
        result = handler(task)
        logger.info("✓ Handler 执行完成")
    except Exception as e:
        logger.error(f"✗ Handler 执行失败: {e}", exc_info=True)
        raise
    
    print("\n✅ Handler 输出:")
    print(result)
    
    # 解析结果
    try:
        parsed_dict = parse_agent_result(result)
        logger.info("✓ 结果解析成功")
        
        print("\n📊 解析后的结果:")
        print(json.dumps(parsed_dict, ensure_ascii=False, indent=2))
        
        if 'user_fixed' in parsed_dict and parsed_dict['user_fixed']:
            print("\n✓ 包含 user_fixed 字段")
            user_fixed = parsed_dict['user_fixed']
            print(f"  行号: {user_fixed.get('_row_number')}")
            print(f"  姓名: {user_fixed.get('name')}")
            print(f"  修正后的手机号: {user_fixed.get('mobile')}")
            logger.info(f"修正后手机号: {user_fixed.get('mobile')}")
        else:
            print("\n⚠️ 缺少 user_fixed 字段")
            logger.warning("缺少 user_fixed 字段")
    except Exception as e:
        print(f"\n⚠️ 结果解析失败: {e}")
        logger.error(f"结果解析失败: {e}", exc_info=True)
        print("原始输出:", result)


def test_invalid_value():
    """测试场景2：职位无效（示例2）"""
    print("\n" + "="*60)
    print("测试场景2：职位无效")
    print("="*60)
    
    # 构建 escalation 数据（使用统一的 issues 数组格式）
    escalation = {
        "_row_number": 10,
        "issues": [
            {
                "column": "title",
                "issue_type": "invalid_value",
                "current_value": "顾问",
                "description": "职位不在有效列表中",
                "suggestions": ["总监", "部门经理", "项目经理"]
            }
        ],
        "current_row": {
            "_row_number": 10,
            "name": "李四",
            "gender": "女",
            "title": "顾问",
            "email": "lisi@example.com",
            "mobile": "13987654321",
            "wechat": "",
            "remark": ""
        }
    }
    
    print("\n📝 期望交互:")
    print('第10行的职位"顾问"不在有效职位列表中。')
    print('\n可能相关的职位：')
    print('1. 总监')
    print('2. 部门经理')
    print('3. 项目经理')
    print('\n请选择一个职位（输入编号）。')
    print('\n💡 建议输入: 2')
    
    escalation_json = json.dumps(escalation, ensure_ascii=False, indent=2)
    task = f"请处理以下数据质量问题：\n\n{escalation_json}"
    
    print("\n📋 输入任务:")
    print(task)
    
    handler = create_test_handler()
    
    print("\n🤖 Handler 执行中...")
    logger.info("🚀 开始执行 Handler...")
    result = handler(task)
    logger.info("✓ Handler 执行完成")
    
    print("\n✅ Handler 输出:")
    print(result)
    
    # 解析结果
    try:
        parsed_dict = parse_agent_result(result)
        logger.info("✓ 结果解析成功")
        
        print("\n📊 解析后的结果:")
        print(json.dumps(parsed_dict, ensure_ascii=False, indent=2))
        
        if 'user_fixed' in parsed_dict and parsed_dict['user_fixed']:
            print("\n✓ 包含 user_fixed 字段")
            user_fixed = parsed_dict['user_fixed']
            print(f"  修正后的职位: {user_fixed.get('title')}")
            logger.info(f"修正后职位: {user_fixed.get('title')}")
        else:
            print("\n⚠️ 缺少 user_fixed 字段")
    except Exception as e:
        print(f"\n⚠️ 结果解析失败: {e}")
        logger.error(f"结果解析失败: {e}", exc_info=True)


def test_non_contact_text():
    """测试场景3：非联系信息文本（示例3）"""
    print("\n" + "="*60)
    print("测试场景3：非联系信息文本")
    print("="*60)
    
    # 构建 escalation 数据（使用统一的 issues 数组格式）
    escalation = {
        "_row_number": 18,
        "issues": [
            {
                "column": "wechat",
                "issue_type": "non_contact_text",
                "current_value": "不要加我微信，请打电话",
                "description": "字段包含说明文字而非联系信息",
                "suggestions": ["移动到备注字段"]
            }
        ],
        "current_row": {
            "_row_number": 18,
            "name": "王五",
            "gender": "男",
            "title": "工程师",
            "email": "wangwu@example.com",
            "mobile": "13912345678",
            "wechat": "不要加我微信，请打电话",
            "remark": ""
        }
    }
    
    print("\n📝 期望交互:")
    print('第18行的微信号字段包含："不要加我微信，请打电话"')
    print('\n这看起来不是微信ID，而是一条说明。')
    print('\n建议：')
    print('- 将这段文字移到备注字段')
    print('- 清空微信号字段')
    print('\n是否接受这个建议？（是/否）')
    print('\n💡 建议输入: 是')
    
    escalation_json = json.dumps(escalation, ensure_ascii=False, indent=2)
    task = f"请处理以下数据质量问题：\n\n{escalation_json}"
    
    print("\n📋 输入任务:")
    print(task)
    
    handler = create_test_handler()
    
    print("\n🤖 Handler 执行中...")
    logger.info("🚀 开始执行 Handler...")
    result = handler(task)
    logger.info("✓ Handler 执行完成")
    
    print("\n✅ Handler 输出:")
    print(result)
    
    # 解析结果
    try:
        parsed_dict = parse_agent_result(result)
        logger.info("✓ 结果解析成功")
        
        print("\n📊 解析后的结果:")
        print(json.dumps(parsed_dict, ensure_ascii=False, indent=2))
        
        if 'user_fixed' in parsed_dict and parsed_dict['user_fixed']:
            print("\n✓ 包含 user_fixed 字段")
            user_fixed = parsed_dict['user_fixed']
            print(f"  修正后的备注: {user_fixed.get('remark')}")
            print(f"  微信号已清空: {user_fixed.get('wechat') == ''}")
            logger.info(f"备注内容: {user_fixed.get('remark')}")
        else:
            print("\n⚠️ 缺少 user_fixed 字段")
    except Exception as e:
        print(f"\n⚠️ 结果解析失败: {e}")
        logger.error(f"结果解析失败: {e}", exc_info=True)


def test_user_skip():
    """测试场景4：用户跳过（示例4）"""
    print("\n" + "="*60)
    print("测试场景4：用户跳过")
    print("="*60)
    
    # 构建 escalation 数据（使用统一的 issues 数组格式）
    escalation = {
        "_row_number": 25,
        "issues": [
            {
                "column": "mobile",
                "issue_type": "missing_digits",
                "current_value": "138123",
                "description": "手机号只有6位，需要11位",
                "suggestions": ["请提供完整的11位手机号"]
            }
        ],
        "current_row": {
            "_row_number": 25,
            "name": "赵六",
            "gender": "男",
            "title": "销售代表",
            "email": "zhaoliu@example.com",
            "mobile": "138123",
            "wechat": "",
            "remark": ""
        }
    }
    
    print("\n📝 期望交互:")
    print('第25行的手机号"138123"只有6位数字，需要11位。')
    print('请提供完整的11位手机号码。')
    print('\n示例：13812345678')
    print('\n💡 建议输入: 跳过 或 不知道')
    
    escalation_json = json.dumps(escalation, ensure_ascii=False, indent=2)
    task = f"请处理以下数据质量问题：\n\n{escalation_json}"
    
    print("\n📋 输入任务:")
    print(task)
    
    handler = create_test_handler()
    
    print("\n🤖 Handler 执行中...")
    logger.info("🚀 开始执行 Handler...")
    result = handler(task)
    logger.info("✓ Handler 执行完成")
    
    print("\n✅ Handler 输出:")
    print(result)
    
    # 解析结果
    try:
        parsed_dict = parse_agent_result(result)
        logger.info("✓ 结果解析成功")
        
        print("\n📊 解析后的结果:")
        print(json.dumps(parsed_dict, ensure_ascii=False, indent=2))
        
        if parsed_dict.get('success') == False:
            print("\n✓ 用户选择跳过")
            print(f"  原因: {parsed_dict.get('reason', 'N/A')}")
            logger.info(f"用户跳过: {parsed_dict.get('reason')}")
        elif 'user_fixed' in parsed_dict:
            print("\n⚠️ 期望用户跳过，但返回了 user_fixed")
    except Exception as e:
        print(f"\n⚠️ 结果解析失败: {e}")
        logger.error(f"结果解析失败: {e}", exc_info=True)


def test_multiple_issues():
    """测试场景5：一行有多个问题"""
    print("\n" + "="*60)
    print("测试场景5：一行有多个问题")
    print("="*60)
    
    # 构建 escalation 数据（一行有多个问题）
    escalation = {
        "_row_number": 15,
        "issues": [
            {
                "column": "mobile",
                "issue_type": "missing_digits",
                "current_value": "136416543",
                "description": "手机号只有9位，需要11位",
                "suggestions": ["请提供完整的11位手机号"]
            },
            {
                "column": "title",
                "issue_type": "invalid_value",
                "current_value": "顾问",
                "description": "职位不在有效列表中",
                "suggestions": ["总监", "部门经理", "项目经理"]
            }
        ],
        "current_row": {
            "_row_number": 15,
            "name": "王五",
            "gender": "男",
            "title": "顾问",
            "email": "wangwu@example.com",
            "mobile": "136416543",
            "wechat": "",
            "remark": ""
        }
    }
    
    print("\n📝 期望交互:")
    print('第15行有2个问题需要修复：')
    print('')
    print('问题1：mobile字段 - 手机号只有9位，需要11位')
    print('问题2：title字段 - 职位不在有效列表中')
    print('')
    print('💡 建议输入: 13641654321, 部门经理')
    print('或分行输入：')
    print('  13641654321')
    print('  部门经理')
    
    escalation_json = json.dumps(escalation, ensure_ascii=False, indent=2)
    task = f"请处理以下数据质量问题：\n\n{escalation_json}"
    
    print("\n📋 输入任务:")
    print(task)
    
    handler = create_test_handler()
    
    print("\n🤖 Handler 执行中...")
    logger.info("🚀 开始执行 Handler...")
    result = handler(task)
    logger.info("✓ Handler 执行完成")
    
    print("\n✅ Handler 输出:")
    print(result)
    
    # 解析结果
    try:
        parsed_dict = parse_agent_result(result)
        logger.info("✓ 结果解析成功")
        
        print("\n📊 解析后的结果:")
        print(json.dumps(parsed_dict, ensure_ascii=False, indent=2))
        
        if 'user_fixed' in parsed_dict and parsed_dict['user_fixed']:
            print("\n✓ 包含 user_fixed 字段")
            user_fixed = parsed_dict['user_fixed']
            print(f"  修正后的手机号: {user_fixed.get('mobile')}")
            print(f"  修正后的职位: {user_fixed.get('title')}")
            logger.info(f"修正后手机号: {user_fixed.get('mobile')}, 职位: {user_fixed.get('title')}")
        else:
            print("\n⚠️ 缺少 user_fixed 字段")
    except Exception as e:
        print(f"\n⚠️ 结果解析失败: {e}")
        logger.error(f"结果解析失败: {e}", exc_info=True)


def interactive_test():
    """交互式测试：自定义 escalation"""
    print("\n" + "="*60)
    print("交互式测试")
    print("="*60)
    
    print("\n你可以输入自定义的 escalation JSON，或使用默认示例。")
    print("按 Enter 使用默认示例，或输入 'skip' 跳过。")
    
    user_input = input("\n输入 escalation JSON (或按 Enter): ").strip()
    
    if user_input.lower() == 'skip':
        print("跳过交互式测试")
        return
    
    if not user_input:
        # 使用默认示例（使用统一的 issues 数组格式）
        escalation = {
            "_row_number": 20,
            "issues": [
                {
                    "column": "mobile",
                    "issue_type": "missing_digits",
                    "current_value": "138123",
                    "description": "手机号只有6位，需要11位",
                    "suggestions": ["请提供完整的11位手机号"]
                }
            ],
            "current_row": {
                "_row_number": 20,
                "name": "测试用户",
                "gender": "男",
                "title": "工程师",
                "email": "test@example.com",
                "mobile": "138123",
                "wechat": "",
                "remark": ""
            }
        }
    else:
        try:
            escalation = json.loads(user_input)
        except json.JSONDecodeError:
            print("❌ 无效的 JSON 格式")
            return
    
    escalation_json = json.dumps(escalation, ensure_ascii=False, indent=2)
    task = f"请处理以下数据质量问题：\n\n{escalation_json}"
    
    print("\n📋 输入任务:")
    print(task)
    
    handler = create_test_handler()
    
    print("\n🤖 Handler 执行中...")
    logger.info("🚀 开始执行 Handler...")
    result = handler(task)
    logger.info("✓ Handler 执行完成")
    
    print("\n✅ Handler 输出:")
    print(result)
    
    # 解析结果
    try:
        parsed_dict = parse_agent_result(result)
        logger.info("✓ 结果解析成功")
        
        print("\n📊 解析后的结果:")
        print(json.dumps(parsed_dict, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"\n⚠️ 结果解析失败: {e}")
        logger.error(f"结果解析失败: {e}", exc_info=True)


def main():
    """主函数"""
    print("\n🧪 EscalationHandler Agent 测试")
    print("\n这个脚本测试 escalation_handler 是否能：")
    print("  1. 使用 handoff_to_user 工具与用户交互")
    print("  2. 返回包含 user_fixed 字段的 JSON")
    print("  3. user_fixed 包含修正后的完整行数据")
    
    print("\n选择测试场景（基于 prompt 示例）：")
    print("  1 - 示例1：手机号位数不足")
    print("  2 - 示例2：职位无效")
    print("  3 - 示例3：非联系信息文本")
    print("  4 - 示例4：用户跳过")
    print("  5 - 示例5：一行有多个问题")
    print("  a - 运行所有示例测试")
    print("  q - 退出")
    
    choice = input("\n请选择 (1-5, a 或 q): ").strip()
    
    if choice == '1':
        test_missing_digits()
    elif choice == '2':
        test_invalid_value()
    elif choice == '3':
        test_non_contact_text()
    elif choice == '4':
        test_user_skip()
    elif choice == '5':
        test_multiple_issues()
    elif choice.lower() == 'a':
        test_missing_digits()
        test_invalid_value()
        test_non_contact_text()
        test_user_skip()
        test_multiple_issues()
    elif choice.lower() == 'q':
        print("\n退出测试")
        return
    else:
        print("\n❌ 无效的选择")
        return
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)
    
    print("\n✅ 验证要点：")
    print("  1. Handler 是否调用了 handoff_to_user？")
    print("  2. 输出是否包含 user_fixed 字段？")
    print("  3. user_fixed 是否包含完整的7个字段？")
    print("  4. user_fixed 是否包含 _row_number？")
    print("  5. 修正后的值是否正确？")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n测试被中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
