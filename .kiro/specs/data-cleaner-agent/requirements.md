# Requirements Document

## Introduction

The Data Cleaner Agent is an interactive CLI tool that processes CSV files containing contact information in Chinese business contexts. The system ingests UTF-8 encoded CSV files, automatically fixes detectable data quality issues, and collaborates with users to resolve ambiguous cases. The agent ensures all output data conforms to a strict schema with validation rules for names, gender, titles, contact information (email, mobile, WeChat), and remarks.

## Glossary

- **Agent**: The interactive CLI application that performs data cleaning operations
- **User**: The human operator who launches the Agent and provides input during the cleaning session
- **Dirty CSV**: An input CSV file that may contain data quality issues or schema violations
- **Cleaned CSV**: An output CSV file that satisfies all schema and validation requirements
- **Auto-fix**: Automated correction of data issues without user intervention
- **Escalation**: The process of requesting user input when automated fixes are not possible
- **Schema**: The defined structure with seven columns: name, gender, title, email, mobile, wechat, remark
- **Contact Triad**: The three contact fields (email, mobile, wechat) that cannot all be empty simultaneously

## Requirements

### Requirement 1

**User Story:** As a user, I want to launch the Agent from the terminal with a simple command, so that I can start a data cleaning session without complex setup.

#### Acceptance Criteria

1. THE Agent SHALL accept a launch command from the terminal using a script
2. WHEN the Agent starts, THE Agent SHALL display a greeting message in Chinese introducing its purpose
3. AFTER the greeting, THE Agent SHALL ask for the CSV filename relative to the repository root
4. THE Agent SHALL load UTF-8 encoded CSV files from the specified path

### Requirement 2

**User Story:** As a user, I want the Agent to automatically fix trivial errors without asking me, so that I don't waste time on obvious corrections.

#### Acceptance Criteria

1. WHEN the Agent detects duplicate characters in email addresses such as "myemail@@somewhere.com", THE Agent SHALL remove the duplicate characters to create "myemail@somewhere.com"
2. WHEN the Agent detects gender values that can be normalized to valid options, THE Agent SHALL convert them to one of "男", "女", or "未知"
3. WHEN the Agent detects title values that closely match valid options, THE Agent SHALL normalize them to the exact valid title string
4. WHEN the Agent detects mobile numbers with formatting characters, THE Agent SHALL remove non-digit characters to create a valid mainland China phone number
5. AFTER loading the file and completing auto-fixes, THE Agent SHALL report the total row count and count of automatically corrected issues to the user

### Requirement 3

**User Story:** As a user, I want the Agent to escalate unresolved issues to me when automated fixes are risky or impossible, so that I can make informed decisions about ambiguous cases.

#### Acceptance Criteria

1. WHEN the Agent encounters a mobile number with incorrect digit count such as "136416543" missing a digit, THE Agent SHALL describe the issue with row and column information and request user input for correction
2. WHEN the Agent encounters an empty required field, THE Agent SHALL identify the specific field and row and request the user to provide the missing data
3. WHEN the Agent encounters multiple values in a single-value field such as two emails "a@b.com" and "b@c.com", THE Agent SHALL present the options to the user and request selection or an alternative value
4. WHEN the Agent detects mismatched columns such as an email stored under the mobile field, THE Agent SHALL flag the mismatch and coordinate the correction with the user
5. THE Agent SHALL process escalations sequentially, waiting for user response before proceeding to the next issue

### Requirement 4

**User Story:** As a user, I want the Agent to validate all data against the defined schema with seven columns, so that the output file meets all business requirements.

#### Acceptance Criteria

1. THE Agent SHALL verify that both dirty and cleaned CSV files contain exactly seven columns: "name", "gender", "title", "email", "mobile", "wechat", "remark"
2. THE Agent SHALL verify that the name field is not empty for every row
3. THE Agent SHALL verify that the gender field contains only "男", "女", or "未知" and no other values
4. THE Agent SHALL verify that the title field matches exactly one of the 30 valid Chinese job titles: "首席执行官（CEO）", "首席运营官（COO）", "首席财务官（CFO）", "首席技术官（CTO）", "首席产品官（CPO）", "首席营销官（CMO）", "总经理", "副总经理", "总监", "副总监", "部门经理", "项目经理", "产品经理", "技术经理", "市场经理", "销售经理", "人力资源经理", "行政经理", "财务经理", "工程师", "高级工程师", "软件开发工程师", "测试工程师", "数据分析师", "运营专员", "市场专员", "销售代表", "人力资源专员", "行政助理", "实习生"
5. WHEN the email field is not empty, THE Agent SHALL verify that it conforms to RFC 5322 syntax
6. WHEN the mobile field is not empty, THE Agent SHALL verify that it contains a valid mainland China phone number without country code prefix
7. WHEN the wechat field is not empty, THE Agent SHALL verify that it contains a valid WeChat ID as defined by Tencent
8. THE Agent SHALL verify that at least one of email, mobile, or wechat is not empty for every row

### Requirement 5

**User Story:** As a user, I want the Agent to handle misplaced data intelligently by moving it to the remark field, so that information is preserved in the appropriate location.

#### Acceptance Criteria

1. THE Agent SHALL allow the remark field to contain any string value
2. WHEN the Agent detects non-contact text in contact fields such as "Do not add me on WeChat; call instead" in the wechat column, THE Agent SHALL suggest moving the text to the remark field
3. WHEN the user confirms moving data to remark, THE Agent SHALL move the text to the remark field and clear the original field
4. THE Agent SHALL preserve existing remark content when appending additional text
5. THE Agent SHALL maintain data integrity during field reassignment operations

### Requirement 6

**User Story:** As a user, I want the Agent to save the cleaned data to a new file, so that I have both the original and cleaned versions available.

#### Acceptance Criteria

1. WHEN every row passes the validation rules, THE Agent SHALL write a valid CSV file that follows the defined schema
2. THE Agent SHALL name the output file by appending "_cleaned" to the original filename before the extension
3. THE Agent SHALL save the output file in UTF-8 encoding
4. THE Agent SHALL clearly state where the cleaned file was saved
5. THE Agent SHALL confirm successful completion of the cleaning process

### Requirement 7

**User Story:** As a developer, I want the Agent to be built using the Strands Agents SDK with prompt-based rule enforcement, so that it leverages LLM intelligence rather than hard-coded validation logic.

#### Acceptance Criteria

1. THE Agent SHALL be implemented using the latest version of the Strands Agents SDK
2. THE Agent SHALL enforce most validation and cleaning rules through prompts rather than hard-coded logic
3. THE Agent SHALL utilize the SDK's capabilities for managing LLM interactions and tool usage
4. THE Agent SHALL follow the SDK's patterns for building interactive CLI applications
5. THE Agent SHALL be compatible with OpenAI SDK's Chat/Responses APIs
6. THE Agent SHALL support DeepSeek V3.1 Terminus via Volcano Engine, OpenAI GPT5-nano, or other publicly accessible models

### Requirement 8

**User Story:** As a developer evaluating the Agent, I want clear documentation on how to run the system, so that I can reproduce the results without ambiguity.

#### Acceptance Criteria

1. THE documentation SHALL specify all prerequisite dependencies including the Strands Agents SDK version
2. THE documentation SHALL describe how to provide API credentials through environment variables or configuration files
3. THE documentation SHALL provide the exact command to launch the Agent
4. THE documentation SHALL describe the expected user interaction flow
5. THE documentation SHALL specify the location where output files are written
