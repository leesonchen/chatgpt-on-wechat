"""定时器插件主模块

这是定时器功能的核心插件模块，负责整合所有子模块并处理用户交互。
该插件支持智能定时提醒设定、提醒执行、延迟提醒等完整的定时提醒功能。

主要功能：
1. 智能定时提醒设定和管理
2. 定时提醒执行和状态跟踪
3. AI智能分析用户需求
4. 延迟提醒和重复提醒
5. 用户会话状态管理
6. 完整的命令处理系统

架构设计：
- 采用模块化设计，各组件职责明确
- 支持多种交互方式（关键词、自然语言）
- 提供完善的错误处理和回退机制
- 支持配置化的功能开关
"""

import os
import json
import plugins
from plugins import *
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from typing import Optional, Dict, Any
from channel.channel import ChannelFactory
from .database_manager import DatabaseManager
from .timer_manager import TimerManager
from .ai_response_generator import AIResponseGenerator
from .reminder_scheduler import ReminderScheduler


@plugins.register(
    name="Timer",
    desire_priority=100,
    hidden=False,
    desc="定时器插件，支持智能定时提醒设定和管理",
    version="1.0",
    author="AI Assistant",
)
class TimerPlugin(Plugin):
    """
    定时器功能主插件类

    该插件是定时器功能的入口点，负责：
    - 初始化所有子模块
    - 处理用户消息和命令
    - 管理用户会话状态
    - 协调各组件间的交互
    - 提供完整的定时提醒流程

    插件特性：
    - 支持自然语言交互
    - 智能命令识别
    - 多状态会话管理
    - AI增强的用户体验
    - 定时提醒功能
    - 延迟提醒功能

    Attributes:
        config: 插件配置信息
        db_manager: 数据库管理器
        ai_generator: AI回复生成器
        timer_manager: 定时器管理器
        reminder_scheduler: 提醒调度器
        user_sessions: 用户会话状态字典
    """

    def __init__(self):
        """
        初始化定时器功能插件

        按顺序初始化各个子模块，建立组件间的依赖关系。
        如果配置启用，将自动启动提醒调度器。
        """
        # Set name and path *before* super().__init__()
        self.name = "Timer"
        self.path = os.path.abspath(os.path.dirname(__file__))
        logger.info(f"[Timer] Init Start: self.name explicitly set to: {self.name}")
        logger.info(f"[Timer] Init Start: self.path explicitly set to: {self.path}")

        super().__init__()
        logger.info(f"[Timer] Init After Super: self.path={getattr(self, 'path', 'self.path NOT SET after super')}")
        logger.info(f"[Timer] Init After Super: self.name={getattr(self, 'name', 'self.name NOT SET after super')}")

        # 注册事件处理函数
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        self.handlers[Event.ON_RECEIVE_MESSAGE] = self.on_receive_message
        logger.info(f"[Timer] Event handlers registered: {self.handlers}")

        try:
            if not hasattr(self, 'path') or not self.path:
                logger.error("[Timer] CRITICAL: self.path is not set or empty before _load_config!")

            # 加载插件配置
            logger.info(f"[Timer] About to load config. Effective path for _load_config: {self.path}")
            self.config = self._load_config()
            logger.info(f"[Timer] Config loaded: {type(self.config)}")

            logger.info(f"[Timer] Setting up db_path. Effective path for db_path: {self.path}")
            db_file_name = self.config.get('database_file', "timer.db")
            logger.info(f"[Timer] Database file name from config: {db_file_name}")
            self.db_path = os.path.join(self.path, db_file_name)
            logger.info(f"[Timer] Full db_path: {self.db_path}")

            # 初始化数据库管理器
            logger.info("[Timer] Initializing DatabaseManager...")
            self.db_mgr = DatabaseManager(self.db_path)
            logger.info("[Timer] DatabaseManager initialized.")

            # 初始化AI回复生成器
            logger.info("[Timer] Initializing AIResponseGenerator...")
            self.ai_generator = AIResponseGenerator()
            logger.info("[Timer] AIResponseGenerator initialized.")

            logger.info("[Timer] Initializing TimerManager...")
            self.timer_manager = TimerManager(self.db_mgr)
            logger.info("[Timer] TimerManager initialized.")

            # 初始化提醒调度器
            logger.info("[Timer] Initializing ReminderScheduler...")
            self.reminder_scheduler = ReminderScheduler(
                self.db_mgr,
                self.ai_generator
            )
            logger.info(f"[Timer] ReminderScheduler initialized.")

            # 设置消息发送函数
            self.reminder_scheduler.set_message_sender(self._send_active_message)
            logger.info("[Timer] Message sender set for ReminderScheduler.")

            self.user_sessions = {}

            enable_reminders_flag = self.config.get("enable_reminders", True)
            if enable_reminders_flag:
                logger.info("[Timer] Starting ReminderScheduler as enable_reminders is true...")
                self.reminder_scheduler.start()
                logger.info("[Timer] ReminderScheduler started.")
            else:
                logger.info("[Timer] ReminderScheduler not started as enable_reminders is false.")

            logger.info("[Timer] 定时器功能插件初始化完成")

        except Exception as e:
            logger.error(f"[Timer] EXCEPTION during __init__ after super(): {str(e)}", exc_info=True)
            raise

    def _send_active_message(self, user_id: str, message: str, channel=None) -> bool:
        """
        主动发送消息给用户
        Args:
            user_id: 用户ID
            message: 消息内容
            channel: 通道对象
        Returns:
            bool: 是否发送成功
        """
        try:
            if not channel:
                channel_type = conf().get("channel_type", "wechatmp")
                channel = ChannelFactory.create_channel(channel_type)

            reply = Reply(ReplyType.TEXT, message)
            context = Context(ContextType.TEXT, content=message)
            context["session_id"] = user_id
            context["receiver"] = user_id
            
            # 增加对is_group的判断，避免发送到错误的会话
            # 对于主动发送的提醒，我们通常认为是私聊
            context['isgroup'] = False

            channel.send(reply, context)
            logger.info(f"[Timer] Sent active message to {user_id} via {channel.name}")
            return True
        except Exception as e:
            logger.error(f"[Timer] Failed to send active message: {e}")
            return False

    def _load_config(self):
        """加载插件配置文件"""
        config_path = os.path.join(self.path, "config.json")
        default_config_path = os.path.join(self.path, "config.json.template")

        try:
            if not os.path.exists(config_path):
                if os.path.exists(default_config_path):
                    import shutil
                    shutil.copy(default_config_path, config_path)
                    logger.info(f"[Timer] Copied default config to {config_path}")
                else:
                    logger.warn(f"[Timer] Default config template not found at {default_config_path}")
                    return {}

            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info("[Timer] Plugin config loaded.")
                return config
        except FileNotFoundError:
            logger.warn(f"[Timer] Config file not found at {config_path}. Using default settings.")
            return {}
        except json.JSONDecodeError:
            logger.error(f"[Timer] Error decoding config file {config_path}. Using default settings.")
            return {}
        except Exception as e:
            logger.error(f"[Timer] Error loading config: {e}. Using default settings.")
            return {}

    def on_handle_context(self, e_context: EventContext):
        """
        处理用户消息的主入口

        这是插件处理用户消息的核心方法，负责：
        1. 检查消息类型（仅处理文本消息）
        2. 检查是否有待发送的提醒
        3. 判断是否为定时器相关指令
        4. 路由到相应的处理方法

        Args:
            e_context: 事件上下文，包含用户消息和会话信息
        """
        # 只处理文本消息
        if e_context["context"].type != ContextType.TEXT:
            return

        content = e_context["context"].content.strip()
        user_id = e_context["context"].get("session_id", "unknown")

        # 检查是否有待发送的提醒（用于个人订阅号的被动推送）
        pending_reminder = self.reminder_scheduler.get_pending_reminder(user_id)
        if pending_reminder:
            # 如果有待处理的提醒，并且通道支持被动回复，则先显示提醒
            self._reply_with_pending_reminder(e_context, pending_reminder)
            return

        # 处理定时器相关指令
        if self._is_timer_command(content):
            # 将channel对象传递给命令处理器
            reply = self._handle_timer_command(content, user_id, e_context['channel'])
            if reply:
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS

    def _reply_with_pending_reminder(self, e_context: EventContext, reminder_message: str):
        """回复待处理的提醒"""
        reply = Reply(ReplyType.TEXT, reminder_message)
        e_context["reply"] = reply
        e_context.action = EventAction.BREAK_PASS

    def _is_timer_command(self, content: str) -> bool:
        """
        判断是否为定时器相关指令

        通过关键词匹配和会话状态检查，判断用户消息是否与定时器功能相关。

        Args:
            content: 用户输入的消息内容

        Returns:
            bool: 如果是定时器相关指令返回True，否则返回False
        """
        content_lower = content.lower()

        # 定时器功能的关键词列表
        timer_keywords = [
            # 中文关键词
            '定时器', '定时提醒', '提醒我', '设置提醒', '我的提醒', '提醒列表', '取消提醒', '延迟提醒',
            '完成', '延迟', '稍后提醒', '帮助', '使用说明',
            # 英文关键词（备用）
            'timer', 'reminder', 'remind', 'set_timer', 'my_timers', 'cancel_timer', 'delay',
            'complete', 'done', 'later', 'help'
        ]

        # 检查是否包含关键词
        for keyword in timer_keywords:
            if keyword in content_lower:
                return True

        # 检查用户是否在会话状态中
        return False

    def _handle_timer_command(self, content: str, user_id: str, channel=None) -> Optional[Reply]:
        """
        处理定时器相关命令

        根据用户输入的内容，路由到相应的处理方法。

        Args:
            content: 用户输入内容
            user_id: 用户ID
            channel: 通道对象
        Returns:
            Reply: 回复对象，如果无需回复则返回None
        """
        content_lower = content.lower()
        reply = Reply()
        reply.type = ReplyType.TEXT

        try:
            if '定时器' in content_lower or '设置提醒' in content_lower or '提醒我' in content_lower:
                # 设置新的定时提醒
                reply.content = self._handle_set_timer(content, user_id)
            elif '我的提醒' in content_lower or '提醒列表' in content_lower:
                # 查看提醒列表
                reply.content = self._handle_list_timers(user_id)
            elif '取消提醒' in content_lower:
                # 取消提醒
                reply.content = self._handle_cancel_timer(content, user_id)
            elif '完成' in content_lower:
                # 标记提醒为完成
                reply.content = self._handle_complete_reminder(user_id)
            elif '延迟' in content_lower or '稍后提醒' in content_lower:
                # 延迟提醒
                reply.content = self._handle_delay_reminder(content, user_id)
            elif '帮助' in content_lower or '使用说明' in content_lower:
                # 显示帮助信息
                reply.content = self._get_help_message()
            else:
                # 默认处理：尝试解析为设置提醒的自然语言
                reply.content = self._handle_set_timer(content, user_id)

            return reply

        except Exception as e:
            logger.error(f"[Timer] Error handling command: {e}")
            reply.content = "抱歉，处理您的请求时出现了错误，请稍后再试。"
            return reply

    def _handle_set_timer(self, content: str, user_id: str) -> str:
        """
        处理设置定时提醒的请求

        使用AI分析用户的自然语言输入，提取定时提醒的相关信息。

        Args:
            content: 用户输入内容
            user_id: 用户ID

        Returns:
            str: 处理结果消息
        """
        try:
            # 使用AI分析用户需求
            analysis_result = self.ai_generator.analyze_timer_request(content)
            
            if not analysis_result or not analysis_result.get('success'):
                return "抱歉，我无法理解您的提醒需求，请尝试更具体的描述，例如：\n\n• 明天上午9点提醒我开会\n• 30分钟后提醒我喝水\n• 每天晚上8点提醒我运动"

            # 创建定时提醒
            success, message = self.timer_manager.create_timer(
                user_id=user_id,
                description=analysis_result['description'],
                remind_time=analysis_result['remind_time'],
                repeat_type=analysis_result.get('repeat_type', 'once'),
                ai_generator=self.ai_generator
            )

            return message

        except Exception as e:
            logger.error(f"[Timer] Error setting timer: {e}")
            return "设置提醒时出现错误，请稍后再试。"

    def _handle_list_timers(self, user_id: str) -> str:
        """
        处理查看提醒列表的请求

        Args:
            user_id: 用户ID

        Returns:
            str: 提醒列表信息
        """
        try:
            return self.timer_manager.get_timer_list(user_id)
        except Exception as e:
            logger.error(f"[Timer] Error listing timers: {e}")
            return "获取提醒列表时出现错误，请稍后再试。"

    def _handle_cancel_timer(self, content: str, user_id: str) -> str:
        """
        处理取消提醒的请求

        Args:
            content: 用户输入内容
            user_id: 用户ID

        Returns:
            str: 处理结果消息
        """
        try:
            # 简单实现：取消最近的一个提醒
            success, message = self.timer_manager.cancel_latest_timer(user_id)
            return message
        except Exception as e:
            logger.error(f"[Timer] Error canceling timer: {e}")
            return "取消提醒时出现错误，请稍后再试。"

    def _handle_complete_reminder(self, user_id: str) -> str:
        """
        处理完成提醒的请求

        Args:
            user_id: 用户ID

        Returns:
            str: 处理结果消息
        """
        try:
            success, message = self.timer_manager.complete_reminder(user_id)
            return message
        except Exception as e:
            logger.error(f"[Timer] Error completing reminder: {e}")
            return "标记完成时出现错误，请稍后再试。"

    def _handle_delay_reminder(self, content: str, user_id: str) -> str:
        """
        处理延迟提醒的请求

        Args:
            content: 用户输入内容
            user_id: 用户ID

        Returns:
            str: 处理结果消息
        """
        try:
            # 使用AI分析延迟时间
            delay_analysis = self.ai_generator.analyze_delay_request(content)
            
            if delay_analysis and delay_analysis.get('success'):
                delay_minutes = delay_analysis.get('delay_minutes', 15)
            else:
                delay_minutes = 15  # 默认延迟15分钟

            success, message = self.timer_manager.delay_reminder(user_id, delay_minutes)
            return message
        except Exception as e:
            logger.error(f"[Timer] Error delaying reminder: {e}")
            return "延迟提醒时出现错误，请稍后再试。"

    def _get_help_message(self) -> str:
        """
        获取帮助信息

        Returns:
            str: 帮助信息文本
        """
        return """🕐 定时器功能使用说明

📝 设置提醒：
• 直接描述您的需求，例如：
  - "明天上午9点提醒我开会"
  - "30分钟后提醒我喝水"
  - "每天晚上8点提醒我运动"

📋 查看提醒：
• 发送「我的提醒」或「提醒列表」

❌ 取消提醒：
• 发送「取消提醒」

✅ 完成提醒：
• 收到提醒后回复「完成」

⏰ 延迟提醒：
• 收到提醒后回复「延迟」或"X分钟后提醒"

💡 小贴士：
• 支持自然语言描述
• 支持一次性和重复提醒
• AI会智能分析您的需求"""

    def on_receive_message(self, e_context: EventContext):
        """
        接收消息事件处理

        Args:
            e_context: 事件上下文
        """
        pass

    def __del__(self):
        """
        析构函数，确保资源正确释放
        """
        try:
            if hasattr(self, 'reminder_scheduler') and self.reminder_scheduler:
                self.reminder_scheduler.stop()
                logger.info("[Timer] ReminderScheduler stopped during cleanup.")
        except Exception as e:
            logger.error(f"[Timer] Error during cleanup: {e}")