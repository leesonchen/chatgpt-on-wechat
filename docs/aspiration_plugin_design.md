# 立志插件 (Aspiration Plugin) 设计文档

## 1. 功能概述

立志插件是一个帮助用户设定目标、记录打卡、并提供智能提醒和鼓励的微信插件。旨在通过积极的反馈和及时的提醒，帮助用户养成良好习惯，达成个人目标。

核心功能包括：

- **目标设定**：用户可以设定具体的、有计划天数的目标。
- **打卡记录**：用户可以每日记录目标的完成情况（已完成、部分完成、未完成），并添加备注。
- **进度跟踪**：插件会记录用户的打卡历史、连续打卡天数、总完成率等统计数据。
- **智能鼓励**：根据用户的打卡情况和目标进展，通过AI生成个性化的鼓励消息。
- **定时提醒**：在用户设定的时间（默认为晚上9点）发送打卡提醒，防止用户忘记。
- **目标管理**：用户可以查看当前目标详情、历史记录，以及完成或放弃当前目标。

## 2. 模块设计

插件主要由以下几个核心模块组成：

### 2.1. `AspirationPlugin` (主插件类 - `aspiration_plugin.py`)

- **职责**：作为插件的入口和总控制器，负责加载配置、初始化其他模块、处理用户消息和事件。
- **主要功能**：
    - 加载 `config.json` 配置文件。
    - 初始化 `DatabaseManager`, `AIResponseGenerator`, `GoalManager`, `CheckinManager`, `ReminderScheduler`。
    - 注册 `ON_HANDLE_CONTEXT` 事件，处理用户发送的文本消息。
    - 解析用户指令，分发给相应的管理器处理。
    - 管理用户会话状态（例如，在设定目标过程中的多步交互）。
    - 启动和停止提醒调度器。

### 2.2. `DatabaseManager` (数据库管理器 - `database_manager.py`)

- **职责**：负责所有与数据库相关的操作，包括表结构的创建和数据的增删改查。
- **主要功能**：
    - 初始化SQLite数据库和表结构（`user_goals`, `check_in_records`, `reminder_logs`）。
    - 提供目标创建、查询、更新状态（活跃、完成、放弃）的方法。
    - 提供打卡记录创建、查询、更新AI回复的方法。
    - 提供提醒日志记录和查询的方法。
    - 计算用户统计数据，如连续打卡天数、总打卡数、完成率、最长连续打卡等。
    - 查询需要发送提醒的用户列表。

### 2.3. `GoalManager` (目标管理器 - `goal_manager.py`)

- **职责**：处理与用户目标设定和管理相关的逻辑。
- **主要功能**：
    - 创建新目标，并进行输入验证（目标描述、计划天数）。
    - 获取用户当前的活跃目标详情。
    - 处理用户完成目标或放弃目标的请求。
    - 生成目标详情和目标历史的文本消息。

### 2.4. `CheckinManager` (打卡管理器 - `checkin_manager.py`)

- **职责**：处理用户打卡相关的逻辑。
- **主要功能**：
    - 记录用户的打卡行为（已完成、部分完成、未完成）及备注。
    - 检查用户当天是否已打卡。
    - 计算连续打卡天数。
    - 调用 `AIResponseGenerator` 生成鼓励消息。
    - 提供快速打卡指令（如回复数字“1”代表已完成）。
    - 解析用户的打卡消息，提取状态和备注。
    - 生成打卡指南。

### 2.5. `AIResponseGenerator` (AI回复生成器 - `ai_response_generator.py`)

- **职责**：利用AI模型生成个性化的鼓励和提醒消息。
- **主要功能**：
    - 初始化AI Bot实例（复用项目已有的 `create_bot`）。
    - 根据用户的目标信息、打卡情况和统计数据，调用 `AIPromptTemplates` 生成提示词。
    - 调用AI模型接口获取回复。
    - 提供备用的、非AI生成的固定回复，以防AI服务不可用。
    - 生成目标设定时的优化建议。

### 2.6. `AIPromptTemplates` (AI提示词模板 - `ai_prompt_templates.py`)

- **职责**：管理和生成调用AI模型所需的提示词模板。
- **主要功能**：
    - 提供生成鼓励消息的提示词模板。
    - 提供生成提醒消息的提示词模板。
    - 提供生成目标建议的提示词模板。

### 2.7. `ReminderScheduler` (提醒调度器 - `reminder_scheduler.py`)

- **职责**：负责定时任务的调度，主要是每日的打卡提醒。
- **主要功能**：
    - 使用 `schedule` 库，在每日指定时间（如21:00）触发提醒任务。
    - 从数据库查询当日未打卡的活跃目标用户。
    - 调用 `AIResponseGenerator` 生成提醒消息。
    - 通过微信通道发送提醒消息（对于个人订阅号，由于API限制，会将提醒暂存，在用户下次交互时显示）。
    - 记录提醒发送日志。
    - 提供启动和停止调度器的接口。

### 2.8. `__init__.py`

- **职责**：作为Python包的入口，声明插件元信息并导出主插件类。

## 3. 数据模型 (SQLite)

### 3.1. `user_goals` (用户目标表)

| 字段名           | 类型      | 描述                                   |
|------------------|-----------|----------------------------------------|
| `id`             | INTEGER   | 主键, 自增                             |
| `user_id`        | TEXT      | 用户唯一标识                           |
| `goal_description` | TEXT      | 目标描述                               |
| `planned_days`   | INTEGER   | 计划完成天数                           |
| `start_date`     | DATE      | 目标开始日期                           |
| `end_date`       | DATE      | 目标预计结束日期 (根据planned_days计算) |
| `status`         | TEXT      | 目标状态 ('active', 'completed', 'abandoned') |
| `created_at`     | TIMESTAMP | 创建时间                               |
| `updated_at`     | TIMESTAMP | 更新时间                               |

### 3.2. `check_in_records` (打卡记录表)

| 字段名            | 类型      | 描述                                   |
|-------------------|-----------|----------------------------------------|
| `id`              | INTEGER   | 主键, 自增                             |
| `goal_id`         | INTEGER   | 关联到 `user_goals` 表的 `id`          |
| `user_id`         | TEXT      | 用户唯一标识                           |
| `check_date`      | DATE      | 打卡日期                               |
| `status`          | TEXT      | 打卡状态 ('completed', 'partial', 'failed') |
| `user_note`       | TEXT      | 用户备注 (可选)                        |
| `ai_response`     | TEXT      | AI生成的鼓励消息 (可选)                |
| `consecutive_days`| INTEGER   | 截止本次打卡时的连续打卡天数           |
| `created_at`      | TIMESTAMP | 创建时间                               |

### 3.3. `reminder_logs` (提醒记录表)

| 字段名        | 类型      | 描述                                   |
|---------------|-----------|----------------------------------------|
| `id`          | INTEGER   | 主键, 自增                             |
| `user_id`     | TEXT      | 用户唯一标识                           |
| `goal_id`     | INTEGER   | 关联到 `user_goals` 表的 `id`          |
| `reminder_date` | DATE      | 提醒发送日期                           |
| `sent_at`     | TIMESTAMP | 实际发送时间                           |
| `responded`   | BOOLEAN   | 用户是否在收到提醒后有打卡行为 (暂未完全实现) |

## 4. 核心流程

### 4.1. 用户设定新目标

1. 用户发送“立志”或相关指令。
2. `AspirationPlugin` 捕获指令，调用 `GoalManager`。
3. `GoalManager` 检查用户是否已有活跃目标。
   - 若有，提示用户先处理当前目标。
   - 若无，引导用户输入目标描述。
4. 用户输入目标描述。
5. `GoalManager` 引导用户输入计划天数。
6. 用户输入计划天数。
7. `GoalManager` 验证输入，调用 `DatabaseManager` 在 `user_goals` 表创建新目标记录。
8. `GoalManager` 返回成功消息给用户，可包含AI生成的目标优化建议（调用 `AIResponseGenerator`）。

### 4.2. 用户每日打卡

1. 用户发送“打卡”或相关指令（如“1”、“已完成 今天任务很轻松”）。
2. `AspirationPlugin` 捕获指令，调用 `CheckinManager`。
3. `CheckinManager` 获取用户的活跃目标。
   - 若无活跃目标，提示用户先设定目标。
4. `CheckinManager` 检查用户今日是否已打卡。
   - 若已打卡，提示用户。
5. `CheckinManager` 解析用户输入的打卡状态和备注。
6. `CheckinManager` 调用 `DatabaseManager` 计算连续打卡天数。
7. `CheckinManager` 调用 `DatabaseManager` 在 `check_in_records` 表创建打卡记录。
8. `CheckinManager` 调用 `AIResponseGenerator` 生成鼓励消息。
9. `CheckinManager` 调用 `DatabaseManager` 更新打卡记录中的AI回复。
10. `CheckinManager` 返回包含打卡结果和AI鼓励的消息给用户。

### 4.3. 每日定时提醒

1. `ReminderScheduler` 的定时任务在预设时间（如21:00）触发。
2. `ReminderScheduler` 调用 `DatabaseManager` 查询所有拥有活跃目标且当日未打卡的用户列表。
3. 对于每个需要提醒的用户：
   a. `ReminderScheduler` 调用 `DatabaseManager` 获取用户的目标信息和统计数据。
   b. `ReminderScheduler` 调用 `AIResponseGenerator` 生成个性化的提醒消息。
   c. `ReminderScheduler` 尝试通过微信通道发送提醒消息。
      - 如果通道支持主动推送（如认证服务号），则直接发送。
      - 如果通道不支持（如个人订阅号），则将提醒消息暂存（例如写入文件或数据库）。当用户下次与机器人交互时，`AspirationPlugin` 会检查并显示这条待发送的提醒。
   d. `ReminderScheduler` 调用 `DatabaseManager` 在 `reminder_logs` 表记录提醒发送情况。

## 5. 配置文件 (`config.json`)

```json
{
  "enabled": true,
  "database_path": "data/aspiration.db",
  "reminder_time": "21:00",
  "ai_enabled": true
}
```

- `enabled`: 是否启用插件。
- `database_path`: 数据库文件路径。
- `reminder_time`: 每日提醒时间 (HH:MM格式)。
- `ai_enabled`: 是否启用AI生成回复功能。

## 6. 未来展望与可优化点

- **更智能的提醒**：根据用户的打卡习惯和目标类型，动态调整提醒时间或内容。
- **目标模板与推荐**：提供常见的目标模板，或根据用户输入智能推荐目标。
- **数据可视化**：提供更丰富的图表展示用户的打卡历史和成就。
- **社交激励**：允许用户分享目标进展或与好友组队打卡（需平台支持）。
- **更完善的会话管理**：优化目标设定、打卡过程中的多轮对话体验。
- **提醒送达率优化**：针对不同微信账号类型，探索更有效的提醒送达方式。
- **异常处理与日志**：进一步完善各模块的异常捕获和日志记录。
- **单元测试与集成测试**：补充更全面的自动化测试用例。