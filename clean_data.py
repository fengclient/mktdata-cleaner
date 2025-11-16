#!/usr/bin/env python3
"""
Data Cleaner Agent - CLI Entry Point

This script launches the Data Cleaner Agent workflow to process CSV files
containing Chinese business contact information.

Usage:
    python clean_data.py [filename]
    
Examples:
    python clean_data.py                    # Interactive mode
    python clean_data.py test_data.csv      # Direct file input
"""

import os
import sys
import json
import logging
import argparse
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import pandas as pd

# Load environment variables from .env file
load_dotenv()

# Import workflow execution function
from src.graph_workflow import create_data_cleaning_graph, setup_observability

# Logger will be configured in main() based on command line arguments
logger = logging.getLogger(__name__)


def load_configuration() -> Dict[str, Any]:
    """
    从环境变量加载配置（通过 .env 文件）
    
    Returns:
        包含配置参数的字典
    """
    config = {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_BASE_URL"),
        "model": os.getenv("MODEL_NAME", "gpt-4"),
        "temperature": float(os.getenv("TEMPERATURE", "0.3")),
        "session_id": None,
        "user_id": None
    }
    
    # 验证必需的配置
    if not config["api_key"]:
        print("错误：缺少API密钥")
        print("\n请在 .env 文件中设置 OPENAI_API_KEY")
        print("示例：OPENAI_API_KEY=your-key-here\n")
        sys.exit(1)
    
    return config


def load_csv_data(filename: str) -> Dict[str, Any]:
    """
    使用 pandas 加载 CSV 文件
    
    Returns:
        包含 success, data, row_count, error 的字典
    """
    try:
        # 使用 pandas 读取 CSV，保持空字符串不转换为 NaN
        df = pd.read_csv(filename, encoding='utf-8-sig', keep_default_na=False)
        
        # 验证列名
        expected_columns = ["name", "gender", "title", "email", "mobile", "wechat", "remark"]
        if list(df.columns) != expected_columns:
            return {
                "success": False,
                "data": None,
                "row_count": 0,
                "error": f"列名不匹配。期望: {expected_columns}，实际: {list(df.columns)}"
            }
        
        # 添加行号（1-based）
        df['_row_number'] = range(1, len(df) + 1)
        
        # 转换为字典列表
        rows = df.to_dict('records')
        
        return {
            "success": True,
            "data": rows,
            "row_count": len(rows),
            "columns": expected_columns
        }
        
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "row_count": 0,
            "error": f"加载文件时出错: {str(e)}"
        }


def save_csv_data(filename: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    使用 pandas 保存清理后的数据到 CSV
    
    Args:
        filename: 输出文件名
        rows: 行数据列表（包含 _row_number 字段）
    
    Returns:
        包含 success, file_path, error 的字典
    """
    try:
        # 定义输出列（不包含 _row_number）
        output_columns = ["name", "gender", "title", "email", "mobile", "wechat", "remark"]
        
        # 创建 DataFrame
        df = pd.DataFrame(rows)
        
        # 按 _row_number 排序
        if '_row_number' in df.columns:
            df = df.sort_values('_row_number')
        
        # 只保留输出列
        df = df[output_columns]
        
        # 保存到 CSV
        df.to_csv(filename, index=False, encoding='utf-8')
        
        abs_path = os.path.abspath(filename)
        
        return {
            "success": True,
            "file_path": abs_path
        }
        
    except Exception as e:
        return {
            "success": False,
            "file_path": None,
            "error": f"保存文件时出错: {str(e)}"
        }


def collect_user_input(filename: Optional[str] = None) -> str:
    """
    Display greeting and collect CSV filename from user.
    
    Args:
        filename: Optional filename from command line argument
    
    Returns:
        CSV filename (relative to repository root)
    """
    # If filename provided via command line, validate and return
    if filename:
        if not os.path.exists(filename):
            print(f"错误：文件不存在: {filename}")
            sys.exit(1)
        return filename
    
    # Display Chinese greeting
    print("=" * 60)
    print("欢迎使用数据清洗助手！")
    print("=" * 60)
    print()
    print("这个工具可以帮助您清理CSV文件中的联系人数据。")
    print("它会自动修复常见的格式问题，并在需要时请求您的帮助。")
    print()
    print("-" * 60)
    print()
    
    # Prompt for filename
    while True:
        filename = input("请输入CSV文件名（相对于当前目录）：").strip()
        
        if not filename:
            print("文件名不能为空，请重新输入。\n")
            continue
        
        # Basic validation
        if not filename.endswith('.csv'):
            print("警告：文件名不以.csv结尾，确定这是CSV文件吗？")
            confirm = input("继续？(y/n): ").strip().lower()
            if confirm not in ['y', 'yes', '是']:
                print()
                continue
        
        # Check if file exists
        if not os.path.exists(filename):
            print(f"错误：文件不存在: {filename}")
            print("请确保文件路径正确（相对于当前目录）\n")
            retry = input("重新输入？(y/n): ").strip().lower()
            if retry not in ['y', 'yes', '是']:
                print("已取消。")
                sys.exit(0)
            print()
            continue
        
        return filename


def display_result(result: Dict[str, Any]) -> None:
    """
    Display the final result to the user.
    
    Args:
        result: Final result dictionary from workflow
    """
    print()
    print("=" * 60)
    
    if result.get("success"):
        # Display summary
        print(result.get("summary", "清理完成！"))
    else:
        # Display error
        print("清理过程中出现错误：")
        print(result.get("summary", "未知错误"))
    
    print("=" * 60)
    print()


def handle_error(error: Exception) -> None:
    """
    Handle and display errors in Chinese with troubleshooting hints.
    
    Args:
        error: Exception that occurred
    """
    print()
    print("=" * 60)
    print("错误：执行过程中出现问题")
    print("=" * 60)
    print()
    
    error_message = str(error)
    print(f"错误信息：{error_message}")
    print()
    
    # Provide troubleshooting hints based on error type
    if "API key" in error_message or "api_key" in error_message.lower():
        print("故障排除提示：")
        print("- 请检查您的OPENAI_API_KEY是否正确设置")
        print("- 确保API密钥有效且未过期")
        print("- 如果使用兼容API，请检查OPENAI_BASE_URL设置")
    elif "connection" in error_message.lower() or "network" in error_message.lower():
        print("故障排除提示：")
        print("- 请检查网络连接")
        print("- 如果使用代理，请确保代理设置正确")
        print("- 检查API服务是否可用")
    elif "rate limit" in error_message.lower():
        print("故障排除提示：")
        print("- API调用频率超限，请稍后重试")
        print("- 考虑升级API计划以获得更高的速率限制")
    elif "model" in error_message.lower():
        print("故障排除提示：")
        print("- 请检查MODEL_NAME环境变量是否正确")
        print("- 确保您的API密钥有权访问指定的模型")
        print("- 尝试使用默认模型（gpt-4）")
    else:
        print("故障排除提示：")
        print("- 请检查CSV文件格式是否正确")
        print("- 确保文件是UTF-8编码")
        print("- 查看上面的错误信息以获取更多详情")
    
    print()
    print("=" * 60)
    print()


def main():
    """
    Main entry point for the Data Cleaner Agent.
    
    工作流程：
    1. 解析参数和配置
    2. 加载 CSV 数据
    3. 执行清理工作流
    4. 合并并保存结果
    5. 显示总结
    """
    try:
        # ========== 1. 解析参数和配置 ==========
        parser = argparse.ArgumentParser(
            description='数据清洗助手 - 清理CSV文件中的联系人数据',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="示例:\n  python clean_data.py test_data.csv\n  python clean_data.py test_data.csv -v\n  python clean_data.py test_data.csv -o"
        )
        parser.add_argument('filename', nargs='?', help='CSV文件路径')
        parser.add_argument('-v', '--verbose', action='store_true', help='显示详细日志（INFO级别）')
        parser.add_argument('-o', '--observability', action='store_true', help='启用可观测性追踪（需要配置 OTEL_EXPORTER_OTLP_ENDPOINT）')
        args = parser.parse_args()
        
        # 配置日志级别
        log_level = logging.INFO if args.verbose else logging.WARNING
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)],
            force=True  # 强制重新配置
        )
        
        config = load_configuration()
        filename = collect_user_input(args.filename)
        
        # 如果启用可观测性，设置追踪
        if args.observability:
            otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
            if otlp_endpoint:
                print(f"\n✓ 可观测性已启用: {otlp_endpoint}\n")
                setup_observability(otlp_endpoint)
            else:
                print("\n警告：未配置 OTEL_EXPORTER_OTLP_ENDPOINT，可观测性未启用\n")
        
        print("\n开始处理数据...\n")
        
        # ========== 2. 加载 CSV 数据 ==========
        csv_result = load_csv_data(filename)
        if not csv_result["success"]:
            print(f"\n错误：{csv_result['error']}\n")
            sys.exit(1)
        
        csv_data = csv_result["data"]
        logger.info(f"已加载 {csv_result['row_count']} 行数据")
        
        # ========== 3. 执行清理工作流 ==========
        graph, shared_state = create_data_cleaning_graph(
            model=config["model"],
            temperature=config["temperature"],
            api_key=config["api_key"],
            base_url=config["base_url"],
            session_id=config.get("session_id"),
            user_id=config.get("user_id")
        )
        
        task_data = json.dumps({
            "success": True,
            "row_count": len(csv_data),
            "columns": csv_result["columns"],
            "rows": csv_data
        }, ensure_ascii=False, indent=2)
        
        initial_task = f"""请分析以下CSV数据并进行数据清理：

{task_data}

请返回分析结果，包括：
1. 自动修复的问题列表（auto_fixed）
2. 需要用户处理的问题列表（escalations）
3. 完全正常的行列表（valid_rows）
"""
        
        graph_result = graph(initial_task, invocation_state=shared_state)
        logger.info(f"工作流完成: {' -> '.join([n.node_id for n in graph_result.execution_order])}")
        
        # ========== 4. 检查 shared_state 一致性并合并结果 ==========
        analyzer_output = shared_state.get('analyzer_output', {})
        total_rows = analyzer_output.get('total_rows', 0)
        valid_rows = analyzer_output.get('valid_rows', [])
        auto_fixed = analyzer_output.get('auto_fixed', [])
        escalations = analyzer_output.get('escalations', [])
        user_fixed_rows = shared_state.get('user_fixed_rows', [])
        user_skipped_rows = shared_state.get('user_skipped_rows', [])
        
        # 一致性检查 1: escalations = user_fixed + user_skipped
        escalations_count = len(escalations)
        handled_count = len(user_fixed_rows) + len(user_skipped_rows)
        
        if escalations_count != handled_count:
            error_msg = f"Escalations 处理不一致：{escalations_count} 个问题，但只处理了 {handled_count} 个（{len(user_fixed_rows)} 修复 + {len(user_skipped_rows)} 跳过）"
            logger.error(error_msg)
            print(f"\n{error_msg}\n")
            sys.exit(1)
        
        # 一致性检查 2: total_rows = valid + auto_fixed + user_fixed + user_skipped
        expected_total = len(valid_rows) + len(auto_fixed) + len(user_fixed_rows) + len(user_skipped_rows)
        
        if total_rows != expected_total:
            error_msg = f"总行数不一致：原始 {total_rows} 行，但分类后 {expected_total} 行（{len(valid_rows)} 有效 + {len(auto_fixed)} 自动 + {len(user_fixed_rows)} 用户修复 + {len(user_skipped_rows)} 用户跳过）"
            logger.error(error_msg)
            print(f"\n{error_msg}\n")
            sys.exit(1)
        
        logger.info(f"✓ 一致性检查通过: escalations={escalations_count}, handled={handled_count}, total={total_rows}")
        
        # 合并所有清理后的数据
        # 注意：auto_fixed 的格式是 {_row_number, fixes, fixed_row}，必须提取 fixed_row
        cleaned_rows = []
        cleaned_rows.extend(valid_rows)
        
        # 提取 auto_fixed 中的 fixed_row（必须存在）
        for item in auto_fixed:
            if 'fixed_row' not in item:
                # 缺少 fixed_row 是严重错误
                row_num = item.get('_row_number', 'unknown')
                error_msg = f"严重错误：auto_fixed 项缺少必需的 fixed_row 字段（行 {row_num}）"
                logger.error(error_msg)
                print(f"\n{error_msg}\n")
                sys.exit(1)
            cleaned_rows.append(item['fixed_row'])
        
        # 添加用户修复的行
        cleaned_rows.extend(user_fixed_rows)
        
        # 添加用户跳过的行（保留原始数据）
        cleaned_rows.extend(user_skipped_rows)
        
        # 按行号排序
        cleaned_rows.sort(key=lambda x: x.get('_row_number', 0))
        
        logger.info(f"✓ 合并完成: {len(cleaned_rows)} 行数据")
        
        base_name, ext = os.path.splitext(filename)
        output_filename = f"{base_name}_cleaned{ext}"
        save_result = save_csv_data(output_filename, cleaned_rows)
        
        if not save_result.get("success"):
            print(f"\n错误：{save_result['error']}\n")
            sys.exit(1)
        
        # ========== 5. 显示总结 ==========
        summary_lines = ["✓ 数据清理完成！", ""]
        summary_lines.append(f"清理后的文件已保存到：{save_result['file_path']}")
        summary_lines.append("")
        summary_lines.append("总结：")
        summary_lines.append(f"- 原始数据：{analyzer_output.get('total_rows', 0)} 行")
        summary_lines.append(f"- 无需修复：{len(valid_rows)} 行")
        summary_lines.append(f"- 自动修复：{len(auto_fixed)} 行")
        summary_lines.append(f"- 用户协助解决：{len(user_fixed_rows)} 行")
        if len(user_skipped_rows) > 0:
            summary_lines.append(f"- 用户跳过：{len(user_skipped_rows)} 行（保留原始数据）")
        summary_lines.append("- 所有数据现在都已保存")
        summary_lines.append("")
        summary_lines.append("感谢使用数据清洗助手！")
        
        summary = "\n".join(summary_lines)
        
        display_result({"success": True, "summary": summary})
        
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print()
        print()
        print("=" * 60)
        print("操作已取消")
        print("=" * 60)
        print()
        sys.exit(0)
    except Exception as e:
        # Handle other errors
        handle_error(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
