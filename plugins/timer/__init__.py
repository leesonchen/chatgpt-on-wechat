"""Timer Plugin - 定时器插件

这是一个功能完整的定时器插件，为用户提供智能的定时提醒服务。
插件支持自然语言输入、AI分析、个性化提醒和灵活的时间管理功能。

主要功能：
1. 智能定时器创建 - 用户通过自然语言输入创建定时器
2. AI分析和解析 - 智能分析用户需求并提取时间信息
3. 个性化提醒 - 根据用户情况生成个性化提醒消息
4. 灵活的时间管理 - 支持延迟、取消、完成等操作
5. 统计和分析 - 提供用户使用统计和完成率分析

核心模块：
- timer_plugin.py: 主插件模块，处理用户交互和消息路由
- database_manager.py: 数据库管理器，负责数据持久化
- timer_manager.py: 定时器管理器，处理核心业务逻辑
- ai_response_generator.py: AI回复生成器，生成个性化回复
- reminder_scheduler.py: 提醒调度器，后台定时检查和发送提醒

数据库设计：
- user_timers: 用户定时器表，存储定时器基本信息
- reminder_records: 提醒记录表，跟踪提醒执行历史
- reminder_logs: 提醒日志表，记录所有提醒发送日志

特性：
- 模块化设计，易于维护和扩展
- 使用SQLite数据库，轻量级且可靠
- 支持多种交互方式（文本消息、菜单操作）
- AI驱动的智能分析和回复生成
- 后台定时任务，准确的提醒调度
- 完整的异常处理和日志记录
- 线程安全的并发处理

使用方法：
1. 创建定时器："明天8点提醒我开会"
2. 查看定时器："查看我的定时器"
3. 取消定时器："取消最新的定时器"
4. 回复提醒："完成"、"延迟30分钟"、"取消"
5. 查看统计："我的定时器统计"

配置选项：
- database_file: 数据库文件路径
- check_interval: 提醒检查间隔（秒）
- enable_ai_analysis: 是否启用AI分析
- enable_reminders: 是否启用提醒功能
- max_timers_per_user: 每用户最大定时器数量

依赖：
- sqlite3: 数据库支持
- threading: 后台任务支持
- datetime: 时间处理
- re: 正则表达式
- json: JSON数据处理

作者：AI Assistant
版本：1.0.0
许可：MIT License
"""

__version__ = "1.0.0"
__author__ = "AI Assistant"
__description__ = "智能定时器插件 - 提供自然语言定时提醒服务"

# 导出主要类
from .timer_plugin import TimerPlugin
from .database_manager import DatabaseManager
from .timer_manager import TimerManager
from .ai_response_generator import AIResponseGenerator
from .reminder_scheduler import ReminderScheduler

__all__ = [
    'TimerPlugin',
    'DatabaseManager', 
    'TimerManager',
    'AIResponseGenerator',
    'ReminderScheduler'
]