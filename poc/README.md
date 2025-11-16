# POC（概念验证）

这个目录包含数据清洗助手的各种概念验证和探索性测试脚本。

## POC 文件说明

### 核心功能验证
- `test_analyzer.py` - 验证 Analyzer agent 的分析和自动修复功能
- `test_escalation_handler.py` - 验证 Escalation Handler agent 的用户交互功能
- `test_graph.py` - 验证 Graph 的核心逻辑和 shared_state 方案

### Input Propagation 验证
- `test_input_propagation.py` - 验证 Graph 的 Input Propagation 格式
- `test_multi_input_extraction.py` - 验证从 task 提取多个上游节点信息

### 工作流验证
- `test_optimized_workflow.py` - 验证优化后的 graph_workflow
- `test_shared_state_simple.py` - 简单的 shared_state 验证

## 运行 POC

从项目根目录运行：

```bash
# 运行单个 POC
python poc/test_graph.py

# 运行 shared_state 验证
python poc/test_shared_state_simple.py

# 运行 input propagation 验证
python poc/test_input_propagation.py
```

## 注意事项

- 所有 POC 脚本都需要在项目根目录下运行
- 需要 `.env` 文件配置 API 密钥
- 某些 POC 需要用户交互（如 escalation handler）
