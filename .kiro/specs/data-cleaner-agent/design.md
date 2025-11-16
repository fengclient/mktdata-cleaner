# Design Document

## Overview

The Data Cleaner Agent is a multi-agent graph-based application built using the Strands Agents SDK that processes CSV files containing Chinese business contact information. The system uses a **graph architecture** with three specialized nodes (Analyzer, Router, Handler) that work together to analyze data, automatically fix simple issues, and escalate complex problems to users for resolution.

The architecture follows a **graph-based workflow** approach:
- **Analyzer Agent**: Analyzes all data and performs automatic fixes in a single pass
- **Escalation Router**: Custom routing node that manages the escalation queue
- **Escalation Handler Agent**: Interacts with users to resolve complex issues one at a time
- **Structured Output**: Uses Pydantic models for reliable data extraction and validation
- **Shared State**: Maintains workflow state across node executions

This design maximizes reliability through structured outputs, enables iterative problem resolution through graph loops, and provides clear separation between automated and human-assisted processing.

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Entry Point                           │
│                  (clean_data.py)                             │
│  - Loads CSV data using pandas                               │
│  - Creates graph and shared_state                            │
│  - Executes graph with initial task                          │
│  - Merges results and saves cleaned CSV                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Multi-Agent Graph (Strands)                     │
│                                                              │
│                    ┌──────────────┐                          │
│                    │   START      │                          │
│                    └──────┬───────┘                          │
│                           │                                  │
│                           ▼                                  │
│                 ┌─────────────────┐                          │
│                 │   Analyzer      │                          │
│                 │  (Agent Node)   │                          │
│                 │  - Analyzes all │                          │
│                 │  - Auto-fixes   │                          │
│                 │  - Identifies   │                          │
│                 │    escalations  │                          │
│                 └────────┬────────┘                          │
│                          │                                   │
│                          │ process_analyzer_output()         │
│                          │ (stores in shared_state)          │
│                          │                                   │
│                          ▼                                   │
│              ┌──────────────────────┐                        │
│              │ Escalation Router    │                        │
│              │ (Custom Node)        │                        │
│              │ - Enumerates queue   │                        │
│              │ - Manages index      │                        │
│              │ - Routes next issue  │                        │
│              └──────┬───────────────┘                        │
│                     │                                        │
│        ┌────────────┴────────────┐                           │
│        │                         │                           │
│  has_escalations?          no_escalations?                   │
│        │                         │                           │
│        ▼                         ▼                           │
│  ┌──────────────────────┐   ┌─────────┐                     │
│  │ Escalation Handler   │   │   END   │                     │
│  │ (Agent Node)         │   └─────────┘                     │
│  │ - User interaction   │                                   │
│  │ - Validates input    │                                   │
│  │ - Returns fix        │                                   │
│  └──────────┬───────────┘                                   │
│             │                                                │
│             │ process_handler_output()                       │
│             │ (saves user_fixed/skipped)                     │
│             │                                                │
│             └──────────┐                                     │
│                        │                                     │
│                        ▼                                     │
│                (loops back to Router)                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Graph-Based Flow**: Uses Strands multi-agent graph for conditional routing and loops
2. **Structured Output**: Pydantic models ensure reliable data extraction from LLM responses
3. **Shared State Management**: Router maintains all intermediate results across iterations
4. **Single-Pass Analysis**: Analyzer processes entire dataset once, identifying all issues
5. **Sequential Escalation Handling**: Handler processes one escalation at a time with user input
6. **Idempotent Conditions**: Edge conditions are designed to be safely re-entrant
7. **Chinese-First Interface**: All user-facing messages are in Chinese

## Components and Interfaces

### 1. CLI Entry Point (`clean_data.py`)

**Purpose**: Orchestrate the complete data cleaning workflow from file loading to saving

**Responsibilities**:
- Parse command-line arguments (filename, verbose mode, observability)
- Load configuration from environment variables (.env file)
- Load CSV data using pandas
- Create and execute the multi-agent graph
- Perform consistency checks on results
- Merge all cleaned data (valid, auto-fixed, user-fixed, user-skipped)
- Save cleaned CSV file
- Display summary to user

**Key Functions**:

```python
def load_configuration() -> Dict[str, Any]:
    """Load API keys, model settings from environment"""
    
def load_csv_data(filename: str) -> Dict[str, Any]:
    """Load CSV using pandas, add row numbers, validate schema"""
    
def save_csv_data(filename: str, rows: List[Dict]) -> Dict[str, Any]:
    """Save cleaned data to CSV using pandas"""
    
def main():
    """Main workflow orchestration"""
```

**Workflow Steps**:
1. Parse arguments and configure logging
2. Load CSV data with pandas
3. Create graph and shared_state
4. Execute graph with initial task containing all CSV data
5. Validate consistency (escalations = user_fixed + user_skipped)
6. Merge results: valid_rows + auto_fixed + user_fixed + user_skipped
7. Save to `{filename}_cleaned.csv`
8. Display summary

**Command Line Interface**:
```bash
python clean_data.py [filename] [-v] [-o]

Options:
  filename              CSV file path (optional, will prompt if not provided)
  -v, --verbose         Show detailed logs (INFO level)
  -o, --observability   Enable OTLP tracing
```

### 2. Graph Nodes

#### Node 1: Analyzer Agent

**Type**: Strands Agent with structured output

**Purpose**: Analyze all CSV data in a single pass, automatically fix simple issues, and identify complex problems for escalation

**System Prompt**: `ANALYZE_AND_FIX_PROMPT` (from `src/prompts/analyzer_prompt.md`)

**Tools**: None (receives data directly in task description)

**Structured Output Model**: `AnalyzerResult` (Pydantic model)

**Input**: 
- Task description containing JSON with all CSV rows
- Format: `{"success": true, "row_count": N, "columns": [...], "rows": [...]}`

**Output Structure** (via structured_output):
```python
class AnalyzerResult(BaseModel):
    total_rows: int
    auto_fixed: List[AutoFixed]  # Each has: _row_number, fixes[], fixed_row
    escalations: List[Escalation]  # Each has: _row_number, issues[], current_row
    valid_rows: List[ValidRow]  # Completely valid rows
```

**Key Behaviors**:
1. **Single-Pass Processing**: Analyzes all rows in one execution
2. **Auto-Fix Rules**: Applies fixes for clear issues (duplicate chars, formatting, standardization)
3. **Mixed Scenarios**: If a row has both auto-fixable and non-fixable issues:
   - Applies auto-fixes
   - Marks as escalation with `fixes[]` array documenting auto-fixes
   - `current_row` contains already-fixed values
   - `issues[]` only lists remaining problems
4. **No User Interaction**: Pure analysis, no tool calls
5. **Structured Output**: Returns Pydantic model for reliable extraction

**Auto-Fix Categories**:
- Email: Remove duplicate @ symbols
- Mobile: Remove formatting characters, strip country codes
- Gender: Normalize to "男", "女", "未知"
- Title: Fuzzy match to 30 valid titles
- Whitespace: Trim leading/trailing spaces

**Escalation Triggers**:
- Missing digits in mobile number
- Empty required fields (name)
- Contact triad violation (all three empty)
- Multiple values in single field
- Column mismatch (wrong data type)
- Invalid values that can't be auto-fixed
- Non-contact text in contact fields

#### Node 2: Escalation Router

**Type**: Custom MultiAgentBase node

**Purpose**: Manage the escalation queue and route issues to the handler one at a time

**Implementation**: `EscalationRouter` class in `src/graph_workflow.py`

**Responsibilities**:
1. **Enumerate Escalations**: Track current index in escalation queue
2. **Increment Index**: When returning from handler, increment to next escalation
3. **Provide Current Issue**: Extract current escalation and format for handler
4. **Signal Completion**: Return completion status when queue is empty

**State Management** (via shared_state):
- `current_index`: Current position in escalation queue
- `last_node`: Tracks which node executed last (to detect handler completion)

**Routing Logic**:
```python
if last_node == 'escalation_handler':
    current_index += 1  # Move to next escalation
    
has_more = current_index < len(escalations)

if has_more:
    return current_escalation  # Route to handler
else:
    return completion_message  # End graph
```

**Output**: AgentResult with message containing current escalation JSON

#### Node 3: Escalation Handler Agent

**Type**: Strands Agent with structured output and user interaction

**Purpose**: Resolve a single escalation issue through user interaction

**System Prompt**: `ESCALATION_HANDLER_PROMPT` (from `src/prompts/escalation_handler_prompt.md`)

**Tools**: `handoff_to_user` (for user interaction)

**Structured Output Model**: `HandlerResult` (Pydantic model)

**Input**: 
- Task description containing one escalation JSON
- Format: `{"_row_number": N, "issues": [...], "current_row": {...}}`

**Output Structure** (via structured_output):
```python
class HandlerResult(BaseModel):
    success: bool  # True if fixed, False if skipped
    user_fixed: UserFixedRow | None  # Complete row data if fixed
    user_skipped: UserSkippedRow | None  # Original row data if skipped
    reason: str | None  # Explanation
```

**Workflow**:
1. **Explain**: Parse escalation, identify issues
2. **Collect**: Use `handoff_to_user` to present issue and get input
3. **Fix**: Build fixed row data from user input
4. **Validate**: Check if fix meets validation rules
5. **Output**: Return structured result

**Multi-Issue Handling**:
- If `issues[]` has multiple items, collect all fixes in one interaction
- Present all problems together with clear numbering
- Parse user response to extract multiple values

**User Options**:
- Provide fix value(s)
- Choose from suggestions
- Skip (preserves original data)

### 3. Graph Edges and Conditions

#### Edge 1: Analyzer → Router

**Condition Function**: `process_analyzer_output(state)`

**Purpose**: Extract structured output from analyzer and store in shared_state

**Behavior**:
1. Check if already processed (idempotency)
2. Extract `structured_output` from analyzer result
3. Convert Pydantic model to dict with aliases
4. Store in `shared_state['analyzer_output']`
5. Initialize `current_index = 0`
6. Set `last_node = 'analyzer'`
7. Always return `True` (continue to router)

**Data Stored**:
```python
shared_state['analyzer_output'] = {
    'total_rows': int,
    'escalations': List[dict],
    'valid_rows': List[dict],
    'auto_fixed': List[dict]
}
```

#### Edge 2: Router → Handler (Conditional)

**Condition Function**: `has_more_escalations(state)`

**Purpose**: Determine if there are more escalations to process

**Logic**:
```python
escalations = shared_state['analyzer_output']['escalations']
current_index = shared_state['current_index']
return current_index < len(escalations)
```

**Routing**:
- `True`: Route to escalation_handler
- `False`: End graph execution

#### Edge 3: Handler → Router (Loop Back)

**Condition Function**: `handler_to_router(state)` (wrapper around `process_handler_output`)

**Purpose**: Extract handler result and save to shared_state, then loop back

**Behavior**:
1. Extract `structured_output` from handler result
2. Convert Pydantic model to dict
3. Check `success` field:
   - If `True` and has `user_fixed`: Save to `shared_state['user_fixed_rows']`
   - If `False` and has `user_skipped`: Save to `shared_state['user_skipped_rows']`
4. Prevent duplicate saves (check `_row_number`)
5. Set `last_node = 'escalation_handler'` (triggers index increment in router)
6. Always return `True` (continue to router)

**Data Stored**:
```python
shared_state['user_fixed_rows'] = [...]  # Successfully fixed rows
shared_state['user_skipped_rows'] = [...]  # Skipped rows (original data)
```

### 4. Graph Configuration

**Graph Builder**: Uses Strands `GraphBuilder` to construct the multi-agent graph

**Entry Point**: `analyzer` node

**Graph Structure**:
```python
builder = GraphBuilder()

# Add nodes
builder.add_node(analyzer, "analyzer")
builder.add_node(router, "escalation_router")
builder.add_node(escalation_handler, "escalation_handler")

# Add edges with conditions
builder.add_edge("analyzer", "escalation_router", 
                 condition=process_analyzer_output)
builder.add_edge("escalation_router", "escalation_handler", 
                 condition=has_more_escalations)
builder.add_edge("escalation_handler", "escalation_router", 
                 condition=handler_to_router)

# Configure
builder.set_entry_point("analyzer")
builder.set_max_node_executions(500)  # Allow many iterations
builder.set_execution_timeout(600)  # 10 minutes for user interactions
builder.reset_on_revisit(False)  # Preserve state across loops

graph = builder.build()
```

**Shared State Management**:

The graph uses a `shared_state` dictionary (local variable, not global) that is passed as `invocation_state`:

```python
shared_state = {
    'analyzer_output': None,      # Analyzer results
    'current_index': 0,            # Current escalation index
    'user_fixed_rows': [],         # User-fixed rows
    'user_skipped_rows': [],       # User-skipped rows
    'last_node': None              # Last executed node name
}

# Execute graph with shared state
result = graph(initial_task, invocation_state=shared_state)
```

**Execution Flow**:
1. Graph starts at `analyzer` node
2. Analyzer processes all data, returns structured output
3. Edge condition extracts output to shared_state
4. Router checks if escalations exist
5. If yes: Route to handler → handler processes → loop back to router
6. Router increments index and checks again
7. If no more: Graph ends at router
8. CLI merges all results from shared_state

## Data Models

All data models are defined as Pydantic models in `src/models.py` with `ConfigDict(populate_by_name=True)` to support field aliases.

### Row Data Models

**FixedRow / ValidRow / CurrentRow / UserFixedRow / UserSkippedRow**:
```python
class FixedRow(BaseModel):
    row_number: int = Field(alias="_row_number")
    name: str
    gender: str
    title: str
    email: str
    mobile: str
    wechat: str
    remark: str
```

All row models have the same structure with 8 fields (7 data columns + row number).

### Fix and Issue Models

**Fix** (single auto-fix):
```python
class Fix(BaseModel):
    column: str
    old_value: str
    new_value: str
    reason: str
```

**Issue** (single problem):
```python
class Issue(BaseModel):
    column: str
    issue_type: str
    current_value: str
    description: str
    suggestions: List[str]
```

### Analyzer Output Model

**AutoFixed** (one row with multiple fixes):
```python
class AutoFixed(BaseModel):
    row_number: int = Field(alias="_row_number")
    fixes: List[Fix]
    fixed_row: FixedRow  # Complete fixed row data
```

**Escalation** (one row with multiple issues):
```python
class Escalation(BaseModel):
    row_number: int = Field(alias="_row_number")
    issues: List[Issue]
    current_row: CurrentRow  # Complete current row (with auto-fixes applied)
```

**AnalyzerResult** (complete analysis):
```python
class AnalyzerResult(BaseModel):
    total_rows: int
    auto_fixed: List[AutoFixed]
    escalations: List[Escalation]
    valid_rows: List[ValidRow]
```

### Handler Output Model

**HandlerResult**:
```python
class HandlerResult(BaseModel):
    success: bool
    user_fixed: UserFixedRow | None  # If success=True
    user_skipped: UserSkippedRow | None  # If success=False
    reason: str | None
```

### Shared State Structure

```python
shared_state = {
    'analyzer_output': {
        'total_rows': int,
        'auto_fixed': List[dict],  # AutoFixed objects as dicts
        'escalations': List[dict],  # Escalation objects as dicts
        'valid_rows': List[dict]  # ValidRow objects as dicts
    },
    'current_index': int,  # Current position in escalations queue
    'user_fixed_rows': List[dict],  # UserFixedRow objects as dicts
    'user_skipped_rows': List[dict],  # UserSkippedRow objects as dicts
    'last_node': str  # 'analyzer' or 'escalation_handler'
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
- `load_csv_data()` in CLI returns error dict
- CLI displays error message in Chinese
- CLI exits with error code
- User can retry with correct filename

### Validation Errors

**Scenarios**:
- Data doesn't match schema rules
- Contact triad violation (all three empty)
- Invalid field values

**Handling**:
- Analyzer detects violations through prompt-driven analysis
- Auto-fixes trivial issues (documented in `auto_fixed`)
- Escalates ambiguous cases (documented in `escalations`)
- Handler validates user input against rules
- Handler re-prompts if input is invalid
- Continues until all escalations are resolved or skipped

### User Input Errors

**Scenarios**:
- User provides invalid correction
- User input doesn't meet validation rules

**Handling**:
- Handler validates input in step 4 (Validate)
- If invalid: Uses `handoff_to_user` to explain error and re-prompt
- Provides specific error message (e.g., "手机号必须是11位数字")
- Loops back to step 2 (Collect) for new input
- User can always choose to skip

### Consistency Errors

**Scenarios**:
- Escalations count doesn't match handled count
- Total rows don't match sum of categories

**Handling**:
- CLI performs consistency checks after graph execution
- Check 1: `len(escalations) == len(user_fixed) + len(user_skipped)`
- Check 2: `total_rows == len(valid) + len(auto_fixed) + len(user_fixed) + len(user_skipped)`
- If checks fail: Display error and exit
- Prevents data loss or corruption

### API/Model Errors

**Scenarios**:
- API key invalid or missing
- Rate limiting
- Model unavailable
- Network errors

**Handling**:
- Configuration validation at startup
- Strands SDK handles connection errors
- CLI catches exceptions and displays Chinese error messages
- Provides troubleshooting hints based on error type
- Graceful exit with error code

## Testing Strategy

### Unit Testing

**Scope**: Individual components and functions

**Test Files** (in `poc/` directory):
- `test_analyzer.py`: Test analyzer agent with structured output
- `test_escalation_handler.py`: Test handler agent with user interaction
- `test_graph.py`: Test complete graph execution
- `test_input_propagation.py`: Test data flow between nodes
- `test_multi_input_extraction.py`: Test handling multiple issues per row
- `test_shared_state_simple.py`: Test shared state management
- `test_optimized_workflow.py`: Test workflow optimization

**Key Test Areas**:
- Structured output extraction from Pydantic models
- Edge condition functions (idempotency, state updates)
- Router index management and escalation enumeration
- Handler input validation and user interaction
- Shared state consistency across iterations

**Framework**: pytest

### Integration Testing

**Scope**: End-to-end cleaning workflows with real CSV files

**Test Cases**:

1. **Auto-Fix Only**: `test_data_autofix.csv`
   - Only trivial errors (formatting, standardization)
   - Expected: No escalations, all auto-fixed, successful save

2. **Partial Fix**: `test_data_partialfix.csv`
   - Mix of auto-fixable and escalation-required issues
   - Expected: Some auto-fixed, some escalations, sequential handling

3. **Full Workflow**: `test_data_full.csv`
   - Complex scenarios: missing digits, invalid values, mixed issues
   - Expected: Complete workflow with user interactions

4. **Mixed Scenarios**: Rows with both auto-fixable and non-fixable issues
   - Expected: Auto-fixes applied, escalation shows fixed values in `current_row`

5. **User Skip**: User chooses to skip escalations
   - Expected: Original data preserved in `user_skipped_rows`

**Validation**:
- Consistency checks pass
- Output CSV has correct schema
- Row counts match: `total = valid + auto_fixed + user_fixed + user_skipped`
- Escalation counts match: `escalations = user_fixed + user_skipped`

### Prompt Testing

**Scope**: Verify LLM behavior with actual models

**Test Approach**:
- Use real API with test CSV files
- Verify structured output parsing
- Check Chinese language quality
- Validate auto-fix logic
- Test escalation detection
- Verify user interaction flow

**Models Tested**:
- DeepSeek V3.1 via Volcano Engine
- OpenAI GPT-4
- Other OpenAI-compatible endpoints

## Configuration

### Environment Variables (.env file)

```bash
# Required: API credentials
OPENAI_API_KEY=sk-...                    # API key for OpenAI or compatible provider
OPENAI_BASE_URL=https://...              # Base URL for compatible APIs (e.g., Volcano Engine)

# Model configuration
MODEL_NAME=gpt-4                         # Model to use (default: gpt-4)
TEMPERATURE=0.3                          # LLM temperature (default: 0.3)
MAX_TOKENS=4000                          # Max tokens per request (default: 4000)

# Optional: Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://...  # OTLP endpoint for tracing
```

### Configuration Loading

Configuration is loaded in `clean_data.py`:

```python
def load_configuration() -> Dict[str, Any]:
    """Load configuration from environment variables"""
    config = {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_BASE_URL"),
        "model": os.getenv("MODEL_NAME", "gpt-4"),
        "temperature": float(os.getenv("TEMPERATURE", "0.3")),
        "session_id": None,
        "user_id": None
    }
    
    # Validate required fields
    if not config["api_key"]:
        raise ValueError("OPENAI_API_KEY is required")
    
    return config
```

### Graph Configuration

Graph is configured in `create_data_cleaning_graph()`:

```python
# Model instance
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

# Graph builder
builder.set_max_node_executions(500)  # Allow many iterations
builder.set_execution_timeout(600)    # 10 minutes
builder.reset_on_revisit(False)       # Preserve state
```

## Implementation Notes

### Strands SDK Integration

The implementation uses Strands multi-agent graph capabilities:

**Key SDK Components**:
- `Agent`: LLM-powered agent with system prompt and tools
- `GraphBuilder`: Constructs multi-agent graphs with conditional edges
- `MultiAgentBase`: Base class for custom nodes (EscalationRouter)
- `OpenAIModel`: Model wrapper for OpenAI-compatible APIs
- `structured_output_model`: Pydantic model for reliable output parsing

**Graph Creation**:

```python
from strands import Agent
from strands.models.openai import OpenAIModel
from strands.multiagent import GraphBuilder, MultiAgentBase

# Create model instance
model_instance = OpenAIModel(
    client_args={"api_key": api_key, "base_url": base_url},
    model_id=model,
    params={"max_tokens": max_tokens, "temperature": temperature}
)

# Create agents with structured output
analyzer = Agent(
    name="analyzer",
    system_prompt=ANALYZE_AND_FIX_PROMPT,
    tools=[],
    model=model_instance,
    structured_output_model=AnalyzerResult
)

escalation_handler = Agent(
    name="escalation_handler",
    system_prompt=ESCALATION_HANDLER_PROMPT,
    tools=[handoff_to_user],
    model=model_instance,
    structured_output_model=HandlerResult
)

# Build graph
builder = GraphBuilder()
builder.add_node(analyzer, "analyzer")
builder.add_node(router, "escalation_router")
builder.add_node(escalation_handler, "escalation_handler")
builder.add_edge("analyzer", "escalation_router", condition=process_analyzer_output)
builder.add_edge("escalation_router", "escalation_handler", condition=has_more_escalations)
builder.add_edge("escalation_handler", "escalation_router", condition=handler_to_router)

graph = builder.build()
```

### Structured Output Benefits

1. **Reliability**: Pydantic models ensure consistent data structure
2. **Type Safety**: Field types are validated automatically
3. **Alias Support**: Use `_row_number` in JSON, `row_number` in Python
4. **Error Handling**: Invalid outputs are caught early
5. **Documentation**: Models serve as schema documentation

### Prompt Engineering Considerations

1. **Single Responsibility**: Analyzer analyzes, Handler handles user interaction
2. **Structured Output**: Prompts explicitly instruct to return Pydantic-compatible JSON
3. **Chinese Language**: All user-facing text in Chinese
4. **Examples**: Prompts include detailed examples of expected output
5. **Mixed Scenarios**: Analyzer handles rows with both auto-fixable and non-fixable issues
6. **Validation Rules**: Embedded in prompts for LLM to follow

### Performance Considerations

1. **Single-Pass Analysis**: Analyzer processes all rows in one execution (efficient)
2. **Sequential Escalations**: Handler processes one at a time (required for user input)
3. **Token Optimization**: Analyzer receives all data once, no repeated loading
4. **State Efficiency**: Shared state is a local dict, not global (thread-safe)
5. **Graph Loops**: Router manages iterations efficiently with index tracking

## Deployment

### Prerequisites

- Python 3.9+
- Strands Agents SDK (latest version)
- pandas library for CSV operations
- OpenAI-compatible API credentials (OpenAI, Volcano Engine, etc.)

### Installation Steps

```bash
# Clone repository
git clone <repo-url>
cd data_cleaner_agent_challenge_v2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env and add your API key and base URL

# Run agent
python clean_data.py test_data.csv
```

### Usage

```bash
# Interactive mode (prompts for filename)
python clean_data.py

# Direct file input
python clean_data.py test_data.csv

# With verbose logging
python clean_data.py test_data.csv -v

# With observability tracing
python clean_data.py test_data.csv -o
```

### Output

- Cleaned CSV file: `{original_filename}_cleaned.csv`
- Summary displayed in terminal
- Logs (if verbose mode enabled)

## Advantages of This Architecture

1. **Reliability**: Structured output with Pydantic ensures consistent data extraction
2. **Modularity**: Each node has a single, clear responsibility
3. **Scalability**: Graph can handle any number of escalations through loops
4. **Observability**: Graph execution order and state are fully traceable
5. **Maintainability**: Prompts, models, and graph logic are separated
6. **Testability**: Each component can be tested independently
7. **Flexibility**: Easy to add new node types or modify routing logic
8. **Data Integrity**: Consistency checks prevent data loss or corruption
9. **User Experience**: Sequential escalation handling is clear and manageable
10. **State Management**: Shared state pattern is simple and thread-safe

## Key Design Decisions

### Why Graph Architecture?

- **Conditional Routing**: Router decides whether to continue or end based on queue state
- **Loops**: Handler → Router edge creates natural iteration over escalations
- **State Preservation**: `reset_on_revisit(False)` maintains state across loops
- **Separation**: Analysis and handling are completely decoupled

### Why Structured Output?

- **Reliability**: Eliminates JSON parsing errors and format inconsistencies
- **Type Safety**: Pydantic validates all fields automatically
- **Maintainability**: Models serve as living documentation
- **Debugging**: Clear error messages when output doesn't match schema

### Why Shared State?

- **Simplicity**: Local dict passed as `invocation_state`, no global variables
- **Flexibility**: Easy to add new state fields
- **Debugging**: State can be inspected at any point
- **Thread Safety**: Each graph execution has its own state instance

### Why Single-Pass Analysis?

- **Efficiency**: All rows processed in one LLM call
- **Consistency**: Same analysis logic applied to all rows
- **Token Optimization**: Avoids repeated data loading
- **Simplicity**: No need to manage partial analysis state

## Future Enhancements

1. **Parallel Escalations**: Process independent issues concurrently (requires graph modification)
2. **Batch Processing**: Handle multiple CSV files in one execution
3. **Custom Validation Rules**: Allow users to inject additional rules via config
4. **Preview Mode**: Show all changes before applying (add preview node)
5. **Undo Support**: Allow users to revert specific fixes
6. **Export Report**: Generate detailed HTML/PDF report of all changes
7. **Web Interface**: Replace CLI with web UI for better UX
8. **Streaming**: Stream analyzer results as they're generated (for large files)
9. **Incremental Saves**: Save progress after each escalation (for crash recovery)
10. **Multi-Language Support**: Extend beyond Chinese contact data
