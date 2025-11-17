# 数据清洗助手

一个基于 AI 的交互式命令行工具，用于处理包含中文商务联系人信息的 CSV 文件。

## 前置要求

- Python 3.9 或更高版本
- OpenAI API 密钥或兼容的 API 提供商（例如通过火山引擎的 DeepSeek）

### 模型要求

**重要**：本工具需要使用具备以下特性的 LLM 模型：

- **思考模式（Reasoning）**：模型必须支持思考/推理模式，以便正确处理复杂的数据分析和修复逻辑
- **上下文窗口**：建议至少 20,000 tokens 的上下文窗口，以处理较大的数据集和复杂的 prompt

**推荐模型**：
- Moonshot AI: `moonshotai/Kimi-K2-Thinking`
- Qwen: `Qwen/Qwen3-Next-80B-A3B-Thinking`
- OpenAI: `gpt-4o`、`gpt-4-turbo`
- DeepSeek: `deepseek-reasoner`
- 其他支持思考模式的兼容模型

## 安装步骤

1. 克隆此仓库：
```bash
git clone <repository-url>
cd data_cleaner_agent_challenge_v2
```

2. 创建并激活虚拟环境：
```bash
# 创建虚拟环境
python -m venv .venv

# 在 macOS/Linux 上激活
source .venv/bin/activate

# 在 Windows 上激活
.venv\Scripts\activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 配置 API 凭证：
```bash
# 复制示例环境变量文件
cp .env.example .env

# 编辑 .env 文件并添加你的 API 密钥
# OPENAI_API_KEY=sk-your-actual-api-key
```

## 配置说明

可以通过 `.env` 文件中的环境变量来配置工具：

### 必需配置
- `OPENAI_API_KEY`（必需）：你的 OpenAI API 密钥或兼容提供商的密钥

### 可选配置
- `OPENAI_BASE_URL`（可选）：OpenAI 兼容 API 的基础 URL
- `MODEL_NAME`（可选）：使用的模型（默认：gpt-4）
- `TEMPERATURE`（可选）：LLM 温度设置（默认：0.3）
- `MAX_TOKENS`（可选）：LLM 响应的最大 token 数（默认：4000）

## 使用方法

### 基本用法

运行数据清洗工具：

```bash
# 交互模式（会提示输入文件名）
python clean_data.py

# 直接指定文件（全自动修复场景）
python clean_data.py test_data_autofix.csv

# 显示详细日志（INFO 级别）
python clean_data.py test_data_autofix.csv -v
# 或
python clean_data.py test_data_autofix.csv -v=info

# 显示调试日志（DEBUG 级别）
python clean_data.py test_data_autofix.csv -v=debug

# 启用可观测性追踪
python clean_data.py test_data_autofix.csv -o

# 组合使用多个选项
python clean_data.py test_data_autofix.csv -v=debug -o
```

### 命令行选项

- `filename`：CSV 文件路径（可选，如果不提供会进入交互模式）
- `-v, --verbose [LEVEL]`：显示详细日志
  - 不带参数或 `-v=info`：INFO 级别日志
  - `-v=debug`：DEBUG 级别日志（显示最详细的信息）
- `-o, --observability`：启用 OpenTelemetry 追踪（需要配置 `OTEL_EXPORTER_OTLP_ENDPOINT`）

### 工作流程

1. **加载数据**：工具会读取指定的 CSV 文件
2. **自动分析**：AI 会自动识别并修复常见的数据问题
3. **用户协助**：对于无法自动修复的问题，工具会请求您的帮助
4. **保存结果**：清理后的数据会保存到 `{原文件名}_cleaned.csv`

### CSV 文件格式

输入的 CSV 文件必须包含以下列（按顺序）：

```
name,gender,title,email,mobile,wechat,remark
```

项目提供了测试数据文件：
- `test_data_autofix.csv` - 全自动修复场景（30行，无需用户交互）
- `test_data_partialfix.csv` - 部分自动修复场景（包含需要用户处理的问题）
- `test_data_full.csv` - 完整测试场景（包含各种复杂问题）

## 项目结构

```
.
├── src/                    # 源代码目录
│   ├── agents/            # Agent 实现
│   ├── prompts/           # Prompt 模板
│   └── graph_workflow.py  # 工作流编排
├── poc/                   # 概念验证脚本
├── test_data*.csv         # 测试数据文件
├── requirements.txt       # Python 依赖
├── .env.example          # 环境变量模板
├── clean_data.py         # 主程序入口
└── README.md             # 本文件
```

## 未来改进方向

### 功能增强
- **批量处理**：支持一次处理多个 CSV 文件
- **自定义规则**：允许用户定义自己的验证规则和自动修复逻辑
- **数据预览**：在处理前提供数据质量报告和预览
- **撤销/重做**：支持在用户交互过程中撤销或重做操作
- **导出报告**：生成详细的数据清洗报告（修复了什么、跳过了什么）

### 性能优化
- **并行处理**：对于大文件，支持并行处理多行数据
- **增量处理**：支持断点续传，处理中断后可以从上次位置继续
- **缓存机制**：缓存 LLM 响应，减少重复调用

### 用户体验
- **Web 界面**：提供基于浏览器的图形界面
- **实时预览**：在修复过程中实时显示修复效果
- **快捷键支持**：在交互模式下支持快捷键操作
- **多语言支持**：支持英文等其他语言的界面

### 可观测性
- **完善追踪**：完善 OpenTelemetry 集成，支持 Jaeger/Zipkin 等追踪系统
- **性能监控**：记录处理时间、API 调用次数等指标
- **错误追踪**：详细的错误日志和堆栈追踪

### 扩展性
- **插件系统**：支持自定义 Agent 和验证规则
- **多种数据源**：支持 Excel、JSON、数据库等其他数据源
- **API 服务**：提供 REST API，方便集成到其他系统

## 许可证

MIT License
