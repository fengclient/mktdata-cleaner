"""
Pydantic models for data structures used in the data cleaning workflow.

这些模型定义了工作流中使用的所有数据结构，包括：
- Analyzer 的输出结构（AnalyzerResult）
- 自动修复记录（AutoFixed）
- 需要用户处理的问题（Escalation）
- 行数据结构（FixedRow, CurrentRow, ValidRow）
"""

from typing import List
from pydantic import BaseModel, Field, ConfigDict


class FixedRow(BaseModel):
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


class Fix(BaseModel):
    """单个修复"""
    column: str = Field(description="修复的列名")
    old_value: str = Field(description="修复前的值")
    new_value: str = Field(description="修复后的值")
    reason: str = Field(description="修复原因")


class AutoFixed(BaseModel):
    """自动修复的记录（一行可能有多个修复）"""
    model_config = ConfigDict(populate_by_name=True)

    row_number: int = Field(description="行号", alias="_row_number")
    fixes: List[Fix] = Field(description="该行的所有修复列表")
    fixed_row: FixedRow = Field(description="修复后的完整行数据")


class CurrentRow(BaseModel):
    """当前行数据"""
    model_config = ConfigDict(populate_by_name=True)

    row_number: int = Field(description="行号", alias="_row_number")
    name: str = Field(description="姓名")
    gender: str = Field(description="性别")
    title: str = Field(description="职位")
    email: str = Field(description="电子邮件")
    mobile: str = Field(description="手机号")
    wechat: str = Field(description="微信号")
    remark: str = Field(description="备注")


class Issue(BaseModel):
    """单个问题"""
    column: str = Field(description="问题所在列名")
    issue_type: str = Field(description="问题类型")
    current_value: str = Field(description="当前值")
    description: str = Field(description="问题描述")
    suggestions: List[str] = Field(description="建议的解决方案")


class Escalation(BaseModel):
    """需要用户处理的问题（一行可能有多个问题）"""
    model_config = ConfigDict(populate_by_name=True)

    row_number: int = Field(description="行号", alias="_row_number")
    issues: List[Issue] = Field(description="该行的所有问题列表")
    current_row: CurrentRow = Field(description="当前完整行数据")


class ValidRow(BaseModel):
    """完全正常的行"""
    model_config = ConfigDict(populate_by_name=True)

    row_number: int = Field(description="行号", alias="_row_number")
    name: str = Field(description="姓名")
    gender: str = Field(description="性别")
    title: str = Field(description="职位")
    email: str = Field(description="电子邮件")
    mobile: str = Field(description="手机号")
    wechat: str = Field(description="微信号")
    remark: str = Field(description="备注")


class AnalyzerResult(BaseModel):
    """Analyzer 分析结果"""
    total_rows: int = Field(description="总行数")
    auto_fixed: List[AutoFixed] = Field(description="所有自动修复的列表")
    escalations: List[Escalation] = Field(description="所有需要用户处理的问题")
    valid_rows: List[ValidRow] = Field(description="完全正常的行列表")


class UserFixedRow(BaseModel):
    """用户修复后的行数据"""
    model_config = ConfigDict(populate_by_name=True)

    row_number: int = Field(description="行号", alias="_row_number")
    name: str = Field(description="姓名")
    gender: str = Field(description="性别")
    title: str = Field(description="职位")
    email: str = Field(description="电子邮件")
    mobile: str = Field(description="手机号")
    wechat: str = Field(description="微信号")
    remark: str = Field(description="备注")


class UserSkippedRow(BaseModel):
    """用户跳过的行数据（原始数据）"""
    model_config = ConfigDict(populate_by_name=True)

    row_number: int = Field(description="行号", alias="_row_number")
    name: str = Field(description="姓名")
    gender: str = Field(description="性别")
    title: str = Field(description="职位")
    email: str = Field(description="电子邮件")
    mobile: str = Field(description="手机号")
    wechat: str = Field(description="微信号")
    remark: str = Field(description="备注")


class HandlerResult(BaseModel):
    """Escalation Handler 处理结果"""
    success: bool = Field(description="是否成功修复")
    user_fixed: UserFixedRow | None = Field(default=None, description="用户修复后的完整行数据（成功时提供）")
    user_skipped: UserSkippedRow | None = Field(default=None, description="用户跳过的原始行数据（跳过时提供）")
    reason: str | None = Field(default=None, description="修复方法或跳过原因")


__all__ = [
    'FixedRow',
    'Fix',
    'AutoFixed',
    'CurrentRow',
    'Issue',
    'Escalation',
    'ValidRow',
    'AnalyzerResult',
    'UserFixedRow',
    'UserSkippedRow',
    'HandlerResult'
]
