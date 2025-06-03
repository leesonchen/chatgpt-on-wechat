"""
立志功能插件包

这是一个完整的目标管理和打卡系统，为微信机器人提供立志功能支持。
该插件帮助用户设定目标、记录打卡、接收智能提醒，实现目标的持续跟踪和管理。

主要功能模块：
1. aspiration_plugin.py - 主插件类，处理用户交互和命令路由
2. goal_manager.py - 目标管理器，处理目标相关的业务逻辑
3. checkin_manager.py - 打卡管理器，处理打卡记录和状态管理
4. database_manager.py - 数据库管理器，提供数据持久化服务
5. ai_response_generator.py - AI回复生成器，生成个性化反馈
6. ai_prompt_templates.py - AI提示模板，定义各种场景的提示词
7. message_templates.py - 消息模板管理器，提供标准化消息
8. reminder_scheduler.py - 提醒调度器，处理定时提醒任务

核心特性：
- 支持目标设定和管理
- 智能打卡记录系统
- AI生成的个性化回复
- 定时提醒和督促
- 完整的统计和历史记录
- 灵活的配置管理

技术架构：
- 采用模块化设计，职责分离
- SQLite数据库提供可靠的数据存储
- 支持多种交互方式（关键词、数字、自然语言）
- 完善的异常处理和日志记录
- 支持配置化的功能开关

使用方法：
```python
from plugins.aspiration import AspirationPlugin

# 创建插件实例
plugin = AspirationPlugin()

# 注册插件
plugin_manager.register(plugin)
```

版本信息：
- 版本：1.0.0
- 作者：AI Assistant
- 许可：遵循项目主许可协议
"""

from .aspiration_plugin import AspirationPlugin

__version__ = "1.0.0"
__author__ = "AI Assistant"
__all__ = ["AspirationPlugin"]
