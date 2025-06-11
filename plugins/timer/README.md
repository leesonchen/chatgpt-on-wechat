# Timer Plugin - 定时器插件

一个功能完整的智能定时器插件，为用户提供自然语言定时提醒服务。支持AI分析、个性化提醒和灵活的时间管理功能。

## 功能特性

### 🎯 核心功能
- **智能定时器创建** - 支持自然语言输入，如"明天8点提醒我开会"
- **AI分析解析** - 智能分析用户需求并提取时间信息
- **个性化提醒** - 根据用户情况生成个性化提醒消息
- **灵活时间管理** - 支持延迟、取消、完成等操作
- **统计分析** - 提供使用统计和完成率分析

### 🤖 AI驱动
- 自然语言理解和时间解析
- 个性化提醒消息生成
- 智能延迟时间推荐
- 用户意图分析

### ⏰ 时间支持
- **相对时间**："30分钟后"、"2小时后"
- **绝对时间**："明天8点"、"后天下午3点"
- **重复提醒**："每天8点"、"每周一下午3点"
- **具体日期**："12月25日下午3点"

## 安装配置

### 1. 文件结构
```
plugins/timer/
├── timer_plugin.py          # 主插件模块
├── database_manager.py      # 数据库管理器
├── timer_manager.py         # 定时器管理器
├── ai_response_generator.py # AI回复生成器
├── reminder_scheduler.py    # 提醒调度器
├── config.json.template     # 配置模板
├── __init__.py             # 模块初始化
└── README.md               # 说明文档
```

### 2. 配置文件
复制 `config.json.template` 为 `config.json` 并根据需要修改：

```json
{
  "database_file": "data/timer.db",
  "check_interval": 60,
  "enable_ai_analysis": true,
  "enable_reminders": true,
  "max_timers_per_user": 50,
  "default_delay_minutes": 15,
  "cleanup_days": 30
}
```

### 3. 启用插件
在主配置文件中启用timer插件：
```json
{
  "plugins": ["timer"]
}
```

## 使用方法

### 创建定时器
用户可以使用自然语言创建定时器：

```
用户：明天8点提醒我开会
机器人：✅ 定时器设置成功！
📝 任务：开会
⏰ 时间：2024-01-16 08:00
🔔 我会准时提醒您的！

用户：30分钟后提醒我休息
机器人：定时器创建成功！将在 2024-01-15 15:30 提醒您：休息

用户：每天早上7点提醒我锻炼
机器人：定时器设置成功！将每天在 07:00 提醒您：锻炼
```

### 查看定时器
```
用户：查看我的定时器
机器人：📅 您的定时器列表：
1. 开会
   ⏰ 2024-01-16 08:00 (一次性)

2. 锻炼
   ⏰ 2024-01-16 07:00 (每天)
```

### 处理提醒
当提醒时间到达时：
```
机器人：⏰ 提醒时间到了！请记得：开会

您可以回复：
• 完成 - 已完成任务
• 延迟X分钟 - 稍后提醒
• 取消 - 取消提醒

用户：延迟15分钟
机器人：好的，将在 15 分钟后（15:45）再次提醒您

用户：完成
机器人：太棒了！任务已标记为完成 ✅
```

### 取消定时器
```
用户：取消最新的定时器
机器人：定时器已取消
```

### 查看统计
```
用户：我的定时器统计
机器人：📊 您的定时器统计：
• 活跃定时器：3个
• 总定时器：15个
• 完成提醒：12次
• 完成率：80.0%

坚持得很好！继续保持这种自律精神！💪
```

## 技术架构

### 模块设计
```
┌─────────────────┐
│   TimerPlugin   │  ← 主插件模块，处理用户交互
└─────────────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──┐
│Timer  │ │ AI  │
│Manager│ │Gen  │  ← 业务逻辑和AI生成
└───┬───┘ └─────┘
    │
┌───▼───┐ ┌─────────┐
│  DB   │ │Reminder │
│Manager│ │Scheduler│  ← 数据存储和调度
└───────┘ └─────────┘
```

### 数据库设计

#### user_timers 表
```sql
CREATE TABLE user_timers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    description TEXT NOT NULL,
    remind_time DATETIME NOT NULL,
    repeat_type TEXT DEFAULT 'once',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    next_remind_time DATETIME,
    ai_analysis TEXT
);
```

#### reminder_records 表
```sql
CREATE TABLE reminder_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timer_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    remind_time DATETIME NOT NULL,
    status TEXT DEFAULT 'pending',
    response TEXT,
    delay_minutes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (timer_id) REFERENCES user_timers (id)
);
```

#### reminder_logs 表
```sql
CREATE TABLE reminder_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    timer_id INTEGER,
    message TEXT NOT NULL,
    send_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'sent',
    error_message TEXT,
    FOREIGN KEY (timer_id) REFERENCES user_timers (id)
);
```

## 配置选项

### 基础配置
- `database_file`: 数据库文件路径
- `check_interval`: 提醒检查间隔（秒）
- `enable_ai_analysis`: 是否启用AI分析
- `enable_reminders`: 是否启用提醒功能
- `max_timers_per_user`: 每用户最大定时器数量
- `default_delay_minutes`: 默认延迟分钟数
- `cleanup_days`: 数据清理保留天数

### 提醒设置
- `max_delay_minutes`: 最大延迟分钟数
- `min_delay_minutes`: 最小延迟分钟数
- `enable_smart_suggestions`: 启用智能建议
- `enable_encouragement`: 启用鼓励消息

### AI设置
- `enable_personalized_reminders`: 启用个性化提醒
- `enable_intent_analysis`: 启用意图分析
- `response_max_length`: 回复最大长度
- `fallback_to_templates`: 回退到模板

### 调度器设置
- `auto_start`: 自动启动
- `thread_name`: 线程名称
- `maintenance_hour`: 维护时间（小时）
- `error_retry_interval`: 错误重试间隔

## 开发指南

### 扩展功能
1. **添加新的时间解析模式**：在 `TimerManager._parse_with_rules()` 中添加新的正则表达式模式
2. **自定义AI提示词**：修改 `AIResponseGenerator` 中的提示词模板
3. **添加新的提醒类型**：扩展数据库schema和相关业务逻辑
4. **集成外部服务**：在 `ReminderScheduler` 中添加外部通知渠道

### 调试模式
在配置文件中设置 `"debug": true` 启用详细日志：
```json
{
  "debug": true
}
```

### 性能优化
- 数据库索引已优化查询性能
- 使用连接池管理数据库连接
- 后台线程异步处理提醒
- 定期清理过期数据

## 故障排除

### 常见问题

1. **定时器不触发**
   - 检查 `ReminderScheduler` 是否正常运行
   - 确认 `check_interval` 配置合理
   - 查看日志中的错误信息

2. **AI分析失败**
   - 确认AI Bot实例可用
   - 检查 `enable_ai_analysis` 配置
   - 查看AI相关错误日志

3. **数据库错误**
   - 确认数据库文件路径正确
   - 检查文件权限
   - 查看数据库初始化日志

### 日志查看
插件使用统一的日志系统，日志前缀为 `[Timer]`：
```
[Timer] Database initialized successfully
[Timer] ReminderScheduler started
[Timer] Created timer 1 for user user123
[Timer] Reminder sent successfully for timer 1
```

## 许可证

MIT License - 详见LICENSE文件

## 贡献

欢迎提交Issue和Pull Request来改进这个插件！

## 更新日志

### v1.0.0 (2024-01-15)
- 初始版本发布
- 支持自然语言定时器创建
- AI驱动的智能分析和回复
- 完整的提醒调度系统
- 用户统计和数据分析
- 灵活的配置选项