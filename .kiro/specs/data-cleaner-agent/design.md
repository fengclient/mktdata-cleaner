# Design Document

## Overview

The Data Cleaner Agent is a workflow-orchestrated application built using the Strands Agents SDK that processes CSV files containing Chinese business contact information. The system uses **specialized prompts** for different phases (analysis, escalation handling, finalization) orchestrated by a **Strands workflow**, separating concerns between data processing logic and user interaction flow.

The architecture follows a **separation of concerns** approach:
- **Prompts**: Focus on data analysis, auto-fixing, and decision-making
- **Workflow**: Handles orchestration, looping, and user confirmation
- **Tools**: Provide stateless CSV operations

This design maximizes modularity, testability, and allows each component to be optimized independently.

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Entry Point                           │
│                  (workflow launcher)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Strands Workflow Engine                     │
│                                                              │
│  Step 1: Analyze & Auto-Fix                                 │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Agent: Analyzer                                   │     │
│  │  Prompt: ANALYZE_AND_FIX_PROMPT                    │     │
│  │  Output: {auto_fixed[], escalations[]}             │     │
│  └────────────────────────────────────────────────────┘     │
│                     │                                        │
│                     ▼                                        │
│  Step 2: Handle Escalations (Loop)                          │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Agent: Escalation Handler                         │     │
│  │  Prompt: ESCALATION_HANDLER_PROMPT                 │     │
│  │  Loop: For each escalation                         │     │
│  │  User Interaction: Yes                             │     │
│  └────────────────────────────────────────────────────┘     │
│                     │                                        │
│                     ▼                                        │
│  Step 3: Finalize & Save                                    │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Agent: Finalizer                                  │     │
│  │  Prompt: FINALIZE_PROMPT                           │     │
│  │  Output: {file_path, summary}                      │     │
│  └────────────────────────────────────────────────────┘     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      Tool Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ load_csv     │  │ save_csv     │  │ get_row      │      │
│  │              │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Separation of Concerns**: Prompts focus on data logic; workflow handles orchestration
2. **Single Responsibility**: Each prompt has one clear job (analyze, handle escalation, finalize)
3. **Workflow-Driven Flow**: Looping and user interaction managed by Strands workflow, not prompt
4. **Stateless Tools**: Tools perform simple I/O operations without business logic
5. **Structured Output**: Prompts return structured data for workflow decision-making
6. **Chinese-First Interface**: All user-facing messages are in Chinese

## Components and Interfaces

### 1. CLI Entry Point

**Purpose**: Launch the Strands workflow and provide initial input

**Implementation**:
- Python script (e.g., `clean_data.py`) that executes the workflow
- Prompts user for CSV filename
- Initializes workflow with configuration (model, API keys, tools)
- Executes workflow and displays results

**Interface**:
```python
# Command line execution
python clean_data.py

# Workflow execution
workflow.execute(input={"filename": user_provided_filename})
```

### 2. Prompts (Three Specialized Prompts)

#### Prompt A: `ANALYZE_AND_FIX_PROMPT`

**Purpose**: Analyze entire CSV file and perform all auto-fixes in one pass

**Responsibilities**:
- Load CSV file using `load_csv` tool
- Iterate through all rows using `get_row` tool
- Identify data quality issues
- Auto-fix clear issues (formatting, standardization) using `update_row` tool
- Return structured analysis report

**Input**: 
- `filename`: CSV file path

**Output Structure**:
```python
{
    "total_rows": 100,
    "auto_fixed": [
        {
            "row": 5,
            "column": "email",
            "old_value": "test@@example.com",
            "new_value": "test@example.com",
            "reason": "删除重复@符号"
        }
    ],
    "escalations": [
        {
            "row": 12,
            "column": "mobile",
            "issue_type": "missing_digits",
            "current_value": "136416543",
            "description": "手机号只有9位，需要11位",
            "suggestions": ["请提供完整的11位手机号"]
        }
    ]
}
```

**Key Sections**:
1. **Schema Definition**: 7 columns with validation rules
2. **Auto-Fix Rules**: When and how to fix automatically
3. **Escalation Detection**: When to flag for user input
4. **No User Interaction**: This prompt does NOT interact with users

#### Prompt B: `ESCALATION_HANDLER_PROMPT`

**Purpose**: Handle a single escalation issue with user interaction

**Responsibilities**:
- Receive one escalation issue
- Present issue to user in clear Chinese
- Provide options or examples
- Receive user input
- Apply fix using `update_row` tool
- Return fix result

**Input**:
```python
{
    "row": 12,
    "column": "mobile",
    "issue_type": "missing_digits",
    "current_value": "136416543",
    "description": "手机号只有9位，需要11位",
    "suggestions": ["请提供完整的11位手机号"]
}
```

**Output Structure**:
```python
{
    "success": true,
    "row": 12,
    "column": "mobile",
    "new_value": "13641654321",
    "action": "用户提供了完整手机号"
}
```

**Key Sections**:
1. **Issue Presentation**: Clear Chinese explanation
2. **User Guidance**: Options, examples, format requirements
3. **Input Validation**: Verify user input meets requirements
4. **Single Issue Focus**: Only handle one problem at a time

#### Prompt C: `FINALIZE_PROMPT`

**Purpose**: Save cleaned data and generate summary report

**Responsibilities**:
- Use `save_csv` tool to write cleaned data
- Generate Chinese summary report
- Return file path and statistics

**Input**:
```python
{
    "total_rows": 100,
    "auto_fixed_count": 15,
    "escalations_resolved": 3
}
```

**Output Structure**:
```python
{
    "success": true,
    "file_path": "/path/to/data_cleaned.csv",
    "summary": "清理完成！共处理100行数据，自动修复15个问题，用户协助解决3个问题。"
}
```

**Key Sections**:
1. **Save Operation**: Call `save_csv` with default naming
2. **Summary Generation**: Create user-friendly Chinese report
3. **Completion Confirmation**: Clear success message

### 3. Tool Layer

The agent has access to the following tools for file operations:

#### Tool: `load_csv`

**Purpose**: Load a CSV file from the repository root

**Parameters**:
- `filename` (string): Relative path to the CSV file

**Returns**:
- `success` (boolean): Whether the file was loaded successfully
- `row_count` (integer): Number of data rows (excluding header)
- `columns` (list): Column names
- `error` (string, optional): Error message if loading failed

**Behavior**:
- Validates file exists
- Checks UTF-8 encoding
- Verifies 7-column schema
- Loads data into memory for processing

#### Tool: `get_row`

**Purpose**: Retrieve a specific row for inspection or modification

**Parameters**:
- `row_number` (integer): 1-based row index

**Returns**:
- `row_data` (object): Dictionary with column names as keys
- `error` (string, optional): Error if row doesn't exist

**Behavior**:
- Returns current state of the row (including any modifications)
- Used by LLM to inspect specific rows when analyzing issues

#### Tool: `update_row`

**Purpose**: Modify one or more fields in a specific row

**Parameters**:
- `row_number` (integer): 1-based row index
- `updates` (object): Dictionary of column names to new values

**Returns**:
- `success` (boolean): Whether update succeeded
- `updated_row` (object): The row after updates

**Behavior**:
- Applies changes to in-memory data structure
- Validates that column names exist
- Does not perform validation (LLM handles that)

#### Tool: `save_csv`

**Purpose**: Write the cleaned data to a new CSV file

**Parameters**:
- `output_filename` (string): Name for the cleaned file (defaults to `{original}_cleaned.csv`)

**Returns**:
- `success` (boolean): Whether save succeeded
- `file_path` (string): Full path where file was saved
- `error` (string, optional): Error message if save failed

**Behavior**:
- Writes UTF-8 encoded CSV
- Preserves column order
- Creates file in repository root

### 4. Workflow Definition (Strands Workflow)

**Purpose**: Orchestrate the three-phase cleaning process

**Workflow Steps**:

```yaml
workflow: data_cleaner
input:
  filename: string

steps:
  - name: analyze_and_fix
    agent: analyzer
    prompt: ANALYZE_AND_FIX_PROMPT
    input:
      filename: $input.filename
    output: analysis_result
    
  - name: check_escalations
    condition: analysis_result.escalations.length > 0
    
  - name: handle_escalations
    when: check_escalations
    loop: analysis_result.escalations
    agent: escalation_handler
    prompt: ESCALATION_HANDLER_PROMPT
    input: $loop.current
    user_interaction: true
    output: escalation_results
    
  - name: finalize
    agent: finalizer
    prompt: FINALIZE_PROMPT
    input:
      total_rows: $analysis_result.total_rows
      auto_fixed_count: $analysis_result.auto_fixed.length
      escalations_resolved: $escalation_results.length
    output: final_result

output: final_result
```

**State Management**:
- `analysis_result`: Passed from Step 1 to Step 2 and Step 3
- `escalation_results`: Collected from loop iterations
- `final_result`: Returned to CLI

**Workflow Responsibilities**:
- Execute steps in sequence
- Loop through escalations
- Manage user interaction timing
- Pass data between steps
- Handle errors and retries

## Data Models

### CSV Data Structure (Tool Layer)

The in-memory representation of the CSV file (managed by tools.py):

```python
{
    "filename": "example_dirty_data.csv",
    "columns": ["name", "gender", "title", "email", "mobile", "wechat", "remark"],
    "rows": [
        {
            "name": "张三",
            "gender": "男",
            "title": "工程师",
            "email": "zhangsan@example.com",
            "mobile": "13812345678",
            "wechat": "zhangsan123",
            "remark": ""
        },
        // ... more rows
    ]
}
```

### Analysis Result (Step 1 Output)

```python
{
    "total_rows": 100,
    "auto_fixed": [
        {
            "row": int,
            "column": str,
            "old_value": str,
            "new_value": str,
            "reason": str  # Chinese explanation
        }
    ],
    "escalations": [
        {
            "row": int,
            "column": str,
            "issue_type": str,  # e.g., "missing_digits", "empty_required", "multiple_values"
            "current_value": str,
            "description": str,  # Chinese description
            "suggestions": [str]  # Chinese suggestions
        }
    ]
}
```

### Escalation Result (Step 2 Output)

```python
{
    "success": bool,
    "row": int,
    "column": str,
    "new_value": str,
    "action": str  # Chinese description of what was done
}
```

### Final Result (Step 3 Output)

```python
{
    "success": bool,
    "file_path": str,
    "summary": str  # Chinese summary report
}
```

## Error Handling

### File Loading Errors

**Scenarios**:
- File not found
- Invalid UTF-8 encoding
- Wrong number of columns
- Malformed CSV

**Handling**:
- `load_csv` tool returns error message
- LLM explains the issue to user in Chinese
- Agent asks for corrected filename or exits gracefully

### Validation Errors

**Scenarios**:
- Data doesn't match schema rules
- Contact triad violation (all three empty)

**Handling**:
- LLM detects violations through prompt-driven analysis
- Auto-fixes trivial issues
- Escalates ambiguous cases to user
- Continues until all rows are valid

### User Input Errors

**Scenarios**:
- User provides invalid correction
- User input doesn't resolve the issue

**Handling**:
- LLM validates user input against rules
- Politely explains why input is invalid
- Re-prompts for correct input
- Provides examples if helpful

### API/Model Errors

**Scenarios**:
- API key invalid or missing
- Rate limiting
- Model unavailable
- OpenAI-compatible API endpoint issues

**Handling**:
- Strands SDK handles connection errors
- Clear error messages to user
- Graceful exit with instructions

## Testing Strategy

### Unit Testing

**Scope**: Individual tool functions

**Tests**:
- `load_csv`: Valid file, missing file, wrong encoding, wrong columns
- `get_row`: Valid row, out of bounds, empty data
- `update_row`: Valid updates, invalid column names, type handling
- `save_csv`: Successful save, permission errors, path handling

**Framework**: pytest

### Integration Testing

**Scope**: End-to-end cleaning workflows

**Test Cases**:

1. **Auto-Fix Only**: CSV with only trivial errors that can be auto-fixed
   - Expected: No user escalations, successful save

2. **Escalation Required**: CSV with missing phone digit
   - Expected: Agent asks user for correction, applies fix, saves

3. **Multiple Issues**: CSV with mix of auto-fixable and escalation-required issues
   - Expected: Auto-fixes reported, escalations processed sequentially, saves

4. **Column Mismatch**: Email in mobile column
   - Expected: Agent detects mismatch, coordinates correction with user

5. **Contact Triad Violation**: Row with all contact fields empty
   - Expected: Agent escalates, requests at least one contact method

6. **Remark Migration**: Non-contact text in contact field
   - Expected: Agent suggests moving to remark, applies on confirmation

**Approach**:
- Mock LLM responses for deterministic testing
- Provide sample dirty CSV files
- Verify cleaned output matches expected schema
- Validate conversation flow

### Prompt Testing

**Scope**: Verify LLM behavior with actual model

**Tests**:
- Load example_dirty_data.csv
- Verify auto-fixes are applied correctly
- Verify escalations are triggered appropriately
- Verify Chinese language responses
- Verify final output validity

**Approach**:
- Manual testing with real model
- Document expected behaviors
- Iterate on prompt based on results

## Configuration

### Environment Variables

```bash
# Required: API credentials for OpenAI-compatible API
OPENAI_API_KEY=sk-...                    # API key for OpenAI or compatible provider
OPENAI_BASE_URL=https://...              # Optional: Base URL for compatible APIs

# Optional: Model selection
MODEL_NAME=gpt-4                         # Default model to use

# Optional: Behavior tuning
MAX_AUTO_FIXES=100                       # Safety limit on auto-fixes
TEMPERATURE=0.3                          # LLM temperature for consistency
```

### Configuration File

Optional `config.json` for advanced settings:

```json
{
    "model": {
        "name": "gpt-4",
        "temperature": 0.3,
        "max_tokens": 2000,
        "base_url": null
    },
    "behavior": {
        "max_auto_fixes": 100,
        "escalation_threshold": "medium"
    },
    "output": {
        "default_suffix": "_cleaned",
        "encoding": "utf-8"
    }
}
```

## Implementation Notes

### Strands SDK Integration

The Strands Agents SDK provides:
- Workflow definition and execution
- Agent initialization per step
- Tool registration and execution
- Step orchestration and data passing
- User interaction management

**Key SDK Usage**:

```python
from strands import Workflow, Agent, Tool

# Define tools (shared across all agents)
tools = [
    Tool(name="load_csv", function=load_csv_impl, description="..."),
    Tool(name="get_row", function=get_row_impl, description="..."),
    Tool(name="update_row", function=update_row_impl, description="..."),
    Tool(name="save_csv", function=save_csv_impl, description="..."),
]

# Define workflow
workflow = Workflow(
    name="data_cleaner",
    steps=[
        {
            "name": "analyze_and_fix",
            "agent": Agent(
                model="gpt-4",
                system_prompt=ANALYZE_AND_FIX_PROMPT,
                tools=tools,
                temperature=0.3
            ),
            "output": "analysis_result"
        },
        {
            "name": "handle_escalations",
            "loop": "analysis_result.escalations",
            "agent": Agent(
                model="gpt-4",
                system_prompt=ESCALATION_HANDLER_PROMPT,
                tools=tools,
                temperature=0.3
            ),
            "user_interaction": True,
            "output": "escalation_results"
        },
        {
            "name": "finalize",
            "agent": Agent(
                model="gpt-4",
                system_prompt=FINALIZE_PROMPT,
                tools=tools,
                temperature=0.3
            ),
            "output": "final_result"
        }
    ]
)

# Execute workflow
result = workflow.execute(input={"filename": "data.csv"})
```

### Prompt Engineering Considerations

1. **Specificity**: Each prompt has clear, focused responsibilities
2. **Structured Output**: Prompts return JSON-like structured data for workflow
3. **No Overlap**: Analyzer doesn't interact with users; Handler doesn't analyze
4. **Examples**: Include examples of expected input/output formats
5. **Language**: Chinese for user-facing messages, structured data for workflow
6. **Statelessness**: Each prompt operates independently with provided input

### Performance Considerations

1. **Token Usage**: Analyzer processes entire file in one pass; optimize for large files
2. **Latency**: Escalations handled sequentially by workflow; each requires user input
3. **Model Selection**: Use cheaper model for analysis, premium for escalations if needed
4. **Parallel Processing**: Future enhancement - handle independent escalations in parallel
5. **Tool Call Efficiency**: Batch `get_row` calls in analyzer phase

## Deployment

### Prerequisites

- Python 3.9+
- Strands Agents SDK (latest version)
- OpenAI-compatible API credentials

### Installation Steps

```bash
# Clone repository
git clone <repo-url>
cd data_cleaner_agent_challenge_v2

# Install dependencies
pip install -r requirements.txt

# Configure credentials
export OPENAI_API_KEY=sk-...

# Run agent
python clean_data.py
```

### Packaging

For distribution:
- Include requirements.txt with pinned versions
- Provide .env.example template
- Include README with setup instructions
- Package as zip for evaluation

## Advantages of This Architecture

1. **Modularity**: Each prompt can be tested and optimized independently
2. **Reusability**: Escalation handler can be reused in other workflows
3. **Observability**: Workflow tracks each step's input/output
4. **Flexibility**: Easy to add new steps (e.g., preview, validation)
5. **Cost Optimization**: Different models for different steps
6. **Maintainability**: Clear separation between analysis logic and flow control
7. **Testability**: Mock workflow steps independently

## Future Enhancements

1. **Parallel Escalations**: Handle independent issues concurrently
2. **Preview Step**: Add workflow step to show changes before applying
3. **Batch Mode**: Process multiple CSV files in one workflow execution
4. **Custom Rules**: Inject additional validation rules into analyzer prompt
5. **Export Report**: Add reporting step to workflow
6. **Web Interface**: Replace CLI with web-based workflow trigger
