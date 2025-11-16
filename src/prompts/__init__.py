"""
Prompts Package

从 markdown 文件加载所有 agent 的提示词。
"""

import os
from pathlib import Path

# 获取当前目录
PROMPTS_DIR = Path(__file__).parent

def load_prompt(filename: str) -> str:
    """从 markdown 文件加载 prompt"""
    filepath = PROMPTS_DIR / filename
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

# 加载所有 prompts
ANALYZE_AND_FIX_PROMPT = load_prompt('analyzer_prompt.md')
ESCALATION_HANDLER_PROMPT = load_prompt('escalation_handler_prompt.md')

__all__ = [
    'ANALYZE_AND_FIX_PROMPT', 
    'ESCALATION_HANDLER_PROMPT'
]
