# Implementation Plan

## Phase 1: Foundation (Completed)

- [x] 1. Set up project structure and dependencies
  - Create project directory structure with src/ for source code
  - Create Python virtual environment (venv) setup instructions
  - Create requirements.txt with Strands Agents SDK and dependencies
  - Create .env.example template for API credentials
  - Create .gitignore for Python project
  - _Requirements: 7.1, 8.1_

- [x] 2. Implement CSV data management tools
  - Create src/tools.py module for tool implementations
  - _Requirements: 1.4, 4.1, 6.2, 6.3_

- [x] 2.1 Implement load_csv tool
  - Write load_csv function that accepts filename parameter
  - Validate file exists and is UTF-8 encoded
  - Parse CSV and verify 7-column schema (name, gender, title, email, mobile, wechat, remark)
  - Return success status, row count, columns list, and error message if applicable
  - Store loaded data in global state for other tools to access
  - _Requirements: 1.4, 4.1_

- [x] 2.2 Implement get_row tool
  - Write get_row function that accepts row_number parameter (1-based index)
  - Retrieve row data from global state
  - Return row as dictionary with column names as keys
  - Handle out-of-bounds errors gracefully
  - _Requirements: 4.1_

- [x] 2.3 Implement update_row tool
  - Write update_row function that accepts row_number and updates dictionary
  - Validate column names exist in schema
  - Apply updates to in-memory data structure
  - Return success status and updated row data
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 5.3_

- [x] 2.4 Implement save_csv tool
  - Write save_csv function that accepts optional output_filename parameter
  - Default filename to {original}_cleaned.csv format
  - Write data to UTF-8 encoded CSV file in repository root
  - Preserve column order (name, gender, title, email, mobile, wechat, remark)
  - Return success status, file path, and error message if applicable
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

## Phase 2: Prompts (Refactored Architecture)

- [x] 3. Create specialized prompts for workflow
  - Refactor src/prompts.py to contain three focused prompts
  - _Requirements: 7.2, 7.3_

- [x] 3.1 Create ANALYZE_AND_FIX_PROMPT
  - Define role: data analysis and auto-fix specialist
  - Include CSV schema definition (7 columns with validation rules)
  - Include auto-fix rules with examples
  - Include escalation detection criteria
  - Specify structured output format: {total_rows, auto_fixed[], escalations[]}
  - Emphasize: NO user interaction, only analysis and auto-fixing
  - _Requirements: 1.4, 2.1, 2.2, 2.3, 2.4, 4.1-4.8, 7.2_

- [x] 3.2 Create ESCALATION_HANDLER_PROMPT
  - Define role: single-issue resolution specialist
  - Include schema reference for validation
  - Specify input format: {row, column, issue_type, current_value, description, suggestions}
  - Define user interaction guidelines in Chinese
  - Provide examples of clear issue presentation
  - Specify output format: {success, row, column, new_value, action}
  - Emphasize: Handle ONE issue at a time, wait for user input
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 5.1-5.5, 7.2_

- [x] 3.3 Create FINALIZE_PROMPT
  - Define role: completion and reporting specialist
  - Specify input format: {total_rows, auto_fixed_count, escalations_resolved}
  - Define save operation using save_csv tool
  - Define Chinese summary report format
  - Specify output format: {success, file_path, summary}
  - _Requirements: 6.1, 6.4, 6.5, 7.2_

- [x] 3.4 Add shared validation rules module
  - Extract common validation rules (gender options, 30 job titles, etc.)
  - Create VALIDATION_RULES constant for reuse across prompts
  - Include in all three prompts via reference
  - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

## Phase 3: Workflow Definition

- [x] 4. Create Strands workflow configuration
  - Create src/workflow.py module for workflow definition
  - _Requirements: 7.1, 7.3_

- [x] 4.1 Define workflow structure
  - Import Strands Workflow, Agent, Tool classes
  - Define three-step workflow: analyze_and_fix → handle_escalations → finalize
  - Configure data passing between steps
  - Set up loop for escalations step
  - Enable user interaction for escalations step
  - _Requirements: 7.1, 7.3_

- [x] 4.2 Configure analyzer agent (Step 1)
  - Initialize Agent with ANALYZE_AND_FIX_PROMPT
  - Register all four tools (load_csv, get_row, update_row, save_csv)
  - Set temperature=0.3 for consistency
  - Define output schema: analysis_result
  - _Requirements: 7.3, 7.5_

- [x] 4.3 Configure escalation handler agent (Step 2)
  - Initialize Agent with ESCALATION_HANDLER_PROMPT
  - Register tools: get_row, update_row
  - Set temperature=0.3 for consistency
  - Configure loop over analysis_result.escalations
  - Enable user_interaction=True
  - Define output schema: escalation_results[]
  - _Requirements: 7.3, 7.5_

- [x] 4.4 Configure finalizer agent (Step 3)
  - Initialize Agent with FINALIZE_PROMPT
  - Register tool: save_csv
  - Set temperature=0.3 for consistency
  - Define output schema: final_result
  - _Requirements: 7.3, 7.5_

- [x] 4.5 Add workflow conditional logic
  - Add condition: skip escalations step if analysis_result.escalations is empty
  - Add error handling for each step
  - Add retry logic for transient failures
  - _Requirements: 7.3_

## Phase 4: CLI Entry Point

- [x] 5. Implement workflow launcher
  - Create clean_data.py script in repository root
  - _Requirements: 1.1, 7.1, 7.4_

- [x] 5.1 Implement configuration loading
  - Load environment variables (OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME, TEMPERATURE)
  - Load optional config.json if present
  - Validate required credentials are present
  - Set default values for optional parameters
  - _Requirements: 7.5, 8.2_

- [x] 5.2 Implement user input collection
  - Display Chinese greeting message
  - Prompt user for CSV filename (relative to repo root)
  - Validate filename format
  - _Requirements: 1.2, 1.3_

- [x] 5.3 Execute workflow
  - Import workflow from src/workflow.py
  - Call workflow.execute(input={"filename": user_filename})
  - Handle workflow execution errors
  - Display final_result.summary to user
  - _Requirements: 1.1, 7.4_

- [x] 5.4 Add error handling
  - Handle keyboard interrupts gracefully (Ctrl+C)
  - Display API errors in Chinese
  - Provide troubleshooting hints for common errors
  - _Requirements: 7.4_

## Phase 5: Documentation

- [ ] 6. Update documentation
  - Update README.md with new architecture explanation
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 6.1 Document architecture
  - Explain workflow-based architecture
  - Describe three-phase process (analyze, escalate, finalize)
  - Explain separation of concerns (prompts vs workflow)
  - _Requirements: 8.1_

- [ ] 6.2 Document prerequisites and installation
  - List Python 3.9+ requirement
  - Specify Strands Agents SDK version
  - Document virtual environment setup (python -m venv venv, source venv/bin/activate)
  - Provide pip install command for requirements.txt
  - _Requirements: 8.1_

- [ ] 6.3 Document configuration
  - Explain OPENAI_API_KEY environment variable
  - Explain optional OPENAI_BASE_URL for compatible APIs
  - Explain optional MODEL_NAME and TEMPERATURE variables
  - Provide .env.example file reference
  - _Requirements: 8.2_

- [ ] 6.4 Document usage instructions
  - Provide exact command to launch: python clean_data.py
  - Describe expected greeting in Chinese
  - Explain filename input (relative to repo root)
  - Describe three-phase workflow execution
  - Specify output file location and naming convention ({original}_cleaned.csv)
  - _Requirements: 8.3, 8.4, 8.5_

- [ ] 6.5 Add workflow diagram
  - Create visual representation of three-step workflow
  - Show data flow between steps
  - Illustrate loop for escalations
  - _Requirements: 8.1_

## Phase 6: Testing & Packaging

- [-] 7. Create test suite
  - Create tests/ directory
  - _Requirements: Testing strategy from design.md_

- [x] 7.1 Unit tests for tools
  - Test load_csv with valid/invalid files
  - Test get_row with valid/invalid row numbers
  - Test update_row with valid/invalid updates
  - Test save_csv with various scenarios
  - _Requirements: Tool validation_

- [ ] 7.2 Integration tests for workflow
  - Test auto-fix only scenario (no escalations)
  - Test escalation required scenario
  - Test mixed scenario (auto-fix + escalations)
  - Test error handling (missing file, invalid data)
  - _Requirements: End-to-end validation_

- [ ] 7.3 Prompt validation tests
  - Verify ANALYZE_AND_FIX_PROMPT produces correct output structure
  - Verify ESCALATION_HANDLER_PROMPT handles user input correctly
  - Verify FINALIZE_PROMPT generates proper summary
  - _Requirements: Prompt correctness_

- [ ] 8. Create packaging script
  - Create package.sh script to generate submission zip
  - Include all source code, requirements.txt, .env.example, README.md
  - Exclude .git, __pycache__, .env, and other non-essential files
  - _Requirements: 8.1_
