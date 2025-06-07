"""
立志功能主插件模块

这是立志功能的核心插件模块，负责整合所有子模块并处理用户交互。
该插件支持目标设定、打卡记录、智能提醒等完整的目标管理功能。

主要功能：
1. 目标设定和管理
2. 打卡记录和状态跟踪
3. 智能AI回复和建议
4. 定时提醒调度
5. 用户会话状态管理
6. 完整的命令处理系统

架构设计：
- 采用模块化设计，各组件职责明确
- 支持多种交互方式（关键词、数字、自然语言）
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
from .database_manager import DatabaseManager
from .goal_manager import GoalManager
from .checkin_manager import CheckInManager
from .ai_response_generator import AIResponseGenerator
from .reminder_scheduler import ReminderScheduler


@plugins.register(
    name="Aspiration",
    desire_priority=100,
    hidden=False,
    desc="立志功能插件，支持目标设定和打卡记录",
    version="1.0",
    author="AI Assistant",
)
class AspirationPlugin(Plugin):
    """
    立志功能主插件类

    该插件是立志功能的入口点，负责：
    - 初始化所有子模块
    - 处理用户消息和命令
    - 管理用户会话状态
    - 协调各组件间的交互
    - 提供完整的目标管理流程

    插件特性：
    - 支持自然语言交互
    - 智能命令识别
    - 多状态会话管理
    - AI增强的用户体验
    - 定时提醒功能

    Attributes:
        config: 插件配置信息
        db_manager: 数据库管理器
        ai_generator: AI回复生成器
        goal_manager: 目标管理器
        checkin_manager: 打卡管理器
        reminder_scheduler: 提醒调度器
        user_sessions: 用户会话状态字典
    """

    def __init__(self):
        """
        初始化立志功能插件

        按顺序初始化各个子模块，建立组件间的依赖关系。
        如果配置启用，将自动启动提醒调度器。
        """
        # Set name and path *before* super().__init__()
        # Directly set the name instead of relying on class attribute
        self.name = "Aspiration"  # Explicitly set name to match the register decorator
        self.path = os.path.abspath(os.path.dirname(__file__))
        logger.info(f"[Aspiration] Init Start: self.name explicitly set to: {self.name}")
        logger.info(f"[Aspiration] Init Start: self.path explicitly set to: {self.path}")

        super().__init__()
        logger.info(f"[Aspiration] Init After Super: self.path={getattr(self, 'path', 'self.path NOT SET after super')}")
        logger.info(f"[Aspiration] Init After Super: self.name={getattr(self, 'name', 'self.name NOT SET after super')}")

        # 注册事件处理函数
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        self.handlers[Event.ON_RECEIVE_MESSAGE] = self.on_receive_message
        logger.info(f"[Aspiration] Event handlers registered: {self.handlers}")

        try:
            if not hasattr(self, 'path') or not self.path:
                logger.error("[Aspiration] CRITICAL: self.path is not set or empty before _load_config! This will likely cause errors.")
                # Optionally, raise an error here if this condition is fatal
                # raise ValueError("[Aspiration] Plugin path is critically not set or empty.")

            # 加载插件配置 (确保在其他组件初始化之前加载)
            logger.info(f"[Aspiration] About to load config. Effective path for _load_config: {self.path}")
            self.config = self._load_config()
            logger.info(f"[Aspiration] Config loaded: {type(self.config)}")

            if not hasattr(self, 'path') or not self.path: # Check again, though unlikely to change if class attr
                logger.error("[Aspiration] CRITICAL: self.path is not set or empty before db_path setup after config load!")

            logger.info(f"[Aspiration] Setting up db_path. Effective path for db_path: {self.path}")
            db_file_name = self.config.get('database_file', "aspiration.db")
            logger.info(f"[Aspiration] Database file name from config: {db_file_name}")
            self.db_path = os.path.join(self.path, db_file_name)
            logger.info(f"[Aspiration] Full db_path: {self.db_path}")

            # 初始化数据库管理器
            logger.info("[Aspiration] Initializing DatabaseManager...")
            self.db_mgr = DatabaseManager(self.db_path)
            logger.info("[Aspiration] DatabaseManager initialized.")

            # 初始化AI回复生成器
            logger.info("[Aspiration] Initializing AIResponseGenerator...")
            self.ai_generator = AIResponseGenerator()
            logger.info("[Aspiration] AIResponseGenerator initialized.")

            logger.info("[Aspiration] Initializing GoalManager...")
            self.goal_manager = GoalManager(self.db_mgr)
            logger.info("[Aspiration] GoalManager initialized.")

            logger.info("[Aspiration] Initializing CheckInManager...")
            self.checkin_manager = CheckInManager(self.db_mgr, self.ai_generator)
            logger.info("[Aspiration] CheckInManager initialized.")

            # 初始化提醒调度器
            logger.info("[Aspiration] Initializing ReminderScheduler...")
            reminder_time_str = self.config.get('reminder_time', '21:00')
            self.reminder_scheduler = ReminderScheduler(
                self.db_mgr,
                self.ai_generator,
                reminder_time=reminder_time_str
            )
            logger.info(f"[Aspiration] ReminderScheduler initialized with time: {reminder_time_str}.")

            self.user_sessions = {}

            enable_reminders_flag = self.config.get("enable_reminders", True)
            if enable_reminders_flag:
                logger.info("[Aspiration] Starting ReminderScheduler as enable_reminders is true...")
                self.reminder_scheduler.start()
                logger.info("[Aspiration] ReminderScheduler started.")
            else:
                logger.info("[Aspiration] ReminderScheduler not started as enable_reminders is false.")

            logger.info("[Aspiration] 立志功能插件初始化完成 (end of try block in __init__)")

        except Exception as e:
            logger.error(f"[Aspiration] EXCEPTION during __init__ after super(): {str(e)}", exc_info=True)
            # Re-raise the original exception to see it in test output
            raise

    def _load_config(self):
        """加载插件配置文件"""
        config_path = os.path.join(self.path, "config.json")
        default_config_path = os.path.join(self.path, "config.json.template")

        try:
            if not os.path.exists(config_path):
                if os.path.exists(default_config_path):
                    import shutil
                    shutil.copy(default_config_path, config_path)
                    logger.info(f"[Aspiration] Copied default config to {config_path}")
                else:
                    logger.warn(f"[Aspiration] Default config template not found at {default_config_path}")
                    return {}

            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info("[Aspiration] Plugin config loaded.")
                return config
        except FileNotFoundError:
            logger.warn(f"[Aspiration] Config file not found at {config_path}. Using default settings.")
            return {}
        except json.JSONDecodeError:
            logger.error(f"[Aspiration] Error decoding config file {config_path}. Using default settings.")
            return {}
        except Exception as e:
            logger.error(f"[Aspiration] Error loading config: {e}. Using default settings.")
            return {}

    def _save_config(self, config):
        """
        保存插件配置

        从config.json文件中读取插件配置，如果文件不存在或读取失败，
        则返回默认配置。

        Returns:
            dict: 插件配置字典，包含数据库路径、提醒时间等设置
        """
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[Aspiration] 加载配置失败: {e}")
            # 返回默认配置
            return {
                'enabled': True,
                'database_path': 'data/aspiration.db',
                'reminder_time': '21:00',
                'ai_enabled': True
            }

    def on_handle_context(self, e_context: EventContext):
        """
        处理用户消息的主入口

        这是插件处理用户消息的核心方法，负责：
        1. 检查消息类型（仅处理文本消息）
        2. 检查是否有待发送的提醒
        3. 判断是否为立志相关指令
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
            # 如果有待发送的提醒，先显示提醒
            reply = Reply()
            reply.type = ReplyType.TEXT
            reply.content = pending_reminder + "\n\n" + "回复「打卡」记录今天的进展！"
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return

        # 处理立志相关指令
        if self._is_aspiration_command(content):
            reply = self._handle_aspiration_command(content, user_id)
            if reply:
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS

    def _is_aspiration_command(self, content: str) -> bool:
        """
        判断是否为立志相关指令

        通过关键词匹配和会话状态检查，判断用户消息是否与立志功能相关。

        Args:
            content: 用户输入的消息内容

        Returns:
            bool: 如果是立志相关指令返回True，否则返回False
        """
        content_lower = content.lower()

        # 立志功能的关键词列表
        aspiration_keywords = [
            # 中文关键词
            '立志', '目标', '打卡', '我的目标', '目标历史', '完成目标', '放弃目标',
            # 英文关键词（备用）
            'set_goal', 'check_in', 'my_goals', 'goal_stats', 'goal_history',
            # 快捷选项
            '1', '2', '3', '已完成', '部分完成', '未完成', 'done', 'partial', 'failed'
        ]

        # 检查是否包含关键词
        for keyword in aspiration_keywords:
            if keyword in content_lower:
                return True

        # 检查用户是否在设定目标的会话中
        return content.startswith('/') or self._is_in_goal_setting_session(content)

    def _is_in_goal_setting_session(self, content: str) -> bool:
        """
        检查用户是否在目标设定会话中

        Args:
            content: 用户输入内容

        Returns:
            bool: 如果用户在目标设定流程中返回True

        Note:
            这里可以添加更复杂的会话状态检查逻辑
        """
        # 这里可以添加会话状态检查逻辑
        # 比如检查用户是否在等待输入目标描述或天数
        return False

    def _handle_aspiration_command(self, content: str, user_id: str) -> Reply:
        """
        处理立志相关指令的核心路由方法

        根据用户输入的内容，路由到相应的处理方法。支持多种命令格式：
        - 关键词命令（如"立志"、"打卡"）
        - 数字选项（如"1"、"2"、"3"）
        - 自然语言描述
        - 目标管理操作

        Args:
            content: 用户输入内容
            user_id: 用户ID

        Returns:
            Reply: 回复对象，包含回复内容和类型
        """
        try:
            content = content.strip()
            content_lower = content.lower()

            reply = Reply()
            reply.type = ReplyType.TEXT

            # 处理主菜单命令
            if content in ['立志', 'SET_GOAL']:
                reply.content = self._handle_goal_setting_start(user_id)
            elif content in ['打卡', 'CHECK_IN']:
                reply.content = self._handle_checkin_start(user_id)
            elif content in ['我的目标', 'MY_GOALS']:
                reply.content = self.goal_manager.get_goal_details(user_id)
            elif content in ['目标统计', 'GOAL_STATS']:
                reply.content = self.goal_manager.get_goal_details(user_id)
            elif content in ['目标历史', 'GOAL_HISTORY']:
                reply.content = self.goal_manager.get_goal_history(user_id)

            # 处理目标管理指令
            elif any(keyword in content_lower for keyword in ['完成目标', 'complete_goal']):
                success, message = self.goal_manager.complete_goal(user_id)
                reply.content = message
            elif any(keyword in content_lower for keyword in ['放弃目标', 'abandon_goal']):
                success, message = self.goal_manager.abandon_goal(user_id)
                reply.content = message

            # 处理快捷打卡指令
            elif content in ['1'] or any(keyword in content_lower for keyword in ['已完成', 'done']):
                success, message = self.checkin_manager.quick_checkin_completed(user_id)
                reply.content = message
            elif content in ['2'] or any(keyword in content_lower for keyword in ['部分完成', 'partial']):
                note = self._extract_note_from_message(content, ['2', '部分完成', 'partial'])
                success, message = self.checkin_manager.quick_checkin_partial(user_id, note)
                reply.content = message
            elif content in ['3'] or any(keyword in content_lower for keyword in ['未完成', 'failed']):
                note = self._extract_note_from_message(content, ['3', '未完成', 'failed'])
                success, message = self.checkin_manager.quick_checkin_failed(user_id, note)
                reply.content = message

            # 处理自然语言打卡消息
            elif self._is_checkin_message(content):
                status, note = self.checkin_manager.parse_checkin_message(content)
                if status:
                    success, message = self.checkin_manager.record_checkin(user_id, status, note)
                    reply.content = message
                else:
                    reply.content = self.checkin_manager.get_checkin_guide(user_id)

            # 处理数字输入（可能是目标天数或打卡选项）
            elif content.isdigit() and 1 <= int(content) <= 1000:
                reply.content = self._handle_goal_duration_input(user_id, int(content))

            # 处理普通文本（可能是目标描述）
            elif len(content) > 2 and not content.startswith('/'):
                reply.content = self._handle_potential_goal_description(user_id, content)

            # 默认显示帮助信息
            else:
                reply.content = self._get_help_message()

            return reply

        except Exception as e:
            logger.error(f"[Aspiration] 处理指令失败: {e}")
            reply = Reply()
            reply.type = ReplyType.TEXT
            reply.content = "处理请求时出现错误，请稍后重试"
            return reply

    def _handle_goal_setting_start(self, user_id: str) -> str:
        """
        处理目标设定开始

        检查用户是否已有活跃目标，如果有则提示用户先处理现有目标，
        否则引导用户开始设定新目标。

        Args:
            user_id: 用户ID

        Returns:
            str: 回复消息内容
        """
        # 检查是否已有活跃目标
        active_goal = self.goal_manager.get_active_goal(user_id)
        if active_goal:
            return f"""您已有一个活跃目标：

📝 {active_goal['goal_description']}
📅 已进行 {active_goal['days_since_start']} 天

如需设定新目标，请先完成或放弃当前目标：
• 回复「完成目标」结束当前挑战
• 回复「放弃目标」暂停当前目标
• 回复「我的目标」查看详细信息"""

        # 设置用户会话状态为等待目标描述
        self.user_sessions[user_id] = {'state': 'waiting_goal_description'}

        return """🎯 立志 - 设定新目标

请描述您要坚持的目标：

💡 目标建议：
• 具体可执行：「每天读书30分钟」
• 时间明确：「每天晚上跑步」
• 可以量化：「每天写500字」

请直接输入您的目标描述："""

    def _handle_checkin_start(self, user_id: str) -> str:
        """
        处理打卡开始

        获取用户的打卡指南，如果用户没有活跃目标会提示设定目标。

        Args:
            user_id: 用户ID

        Returns:
            str: 打卡指南或提示信息
        """
        return self.checkin_manager.get_checkin_guide(user_id)

    def _handle_potential_goal_description(self, user_id: str, content: str) -> str:
        """
        处理可能的目标描述

        根据用户的会话状态，判断用户输入是否为目标描述或其他内容。
        支持目标设定的多步骤流程。

        Args:
            user_id: 用户ID
            content: 用户输入内容

        Returns:
            str: 相应的回复消息
        """
        session = self.user_sessions.get(user_id, {})

        if session.get('state') == 'waiting_goal_description':
            # 用户正在设定目标描述
            self.user_sessions[user_id] = {
                'state': 'waiting_goal_duration',
                'goal_description': content
            }

            return f"""目标描述已记录：「{content}」

请输入计划坚持的天数（1-1000天）：

💡 建议：
• 初学者：7-30天
• 有经验：30-90天
• 长期目标：90天以上

请输入数字："""

        elif session.get('state') == 'waiting_goal_duration':
            # 用户可能输入了非数字的天数描述
            return """请输入有效的天数（纯数字）：

例如：30（表示30天）

或者回复「取消」取消目标设定"""

        else:
            # 用户没有在设定目标，可能是想要立志
            return """您是要设定新目标吗？

回复「立志」开始设定目标
回复「打卡」记录今日进展
回复「我的目标」查看当前目标"""

    def _handle_goal_duration_input(self, user_id: str, days: int) -> str:
        """
        处理目标天数输入

        当用户输入数字时，根据会话状态判断是设定目标天数还是打卡选项。

        Args:
            user_id: 用户ID
            days: 输入的数字

        Returns:
            str: 处理结果消息
        """
        session = self.user_sessions.get(user_id, {})

        if session.get('state') == 'waiting_goal_duration' and 'goal_description' in session:
            # 完成目标设定
            description = session['goal_description']

            # 清除会话状态
            self.user_sessions.pop(user_id, None)

            # 创建目标，传入AI生成器用于生成建议
            success, message = self.goal_manager.create_goal(user_id, description, days, self.ai_generator)

            return message
        else:
            # 用户没有在设定目标流程中，可能是打卡选项
            return self._handle_checkin_number(user_id, str(days))

    def _handle_checkin_number(self, user_id: str, number: str) -> str:
        """
        处理打卡数字选项

        将数字选项转换为相应的打卡操作。

        Args:
            user_id: 用户ID
            number: 数字选项字符串

        Returns:
            str: 打卡结果消息
        """
        if number == '1':
            success, message = self.checkin_manager.quick_checkin_completed(user_id)
        elif number == '2':
            success, message = self.checkin_manager.quick_checkin_partial(user_id)
        elif number == '3':
            success, message = self.checkin_manager.quick_checkin_failed(user_id)
        else:
            message = self.checkin_manager.get_checkin_guide(user_id)

        return message

    def _is_checkin_message(self, content: str) -> bool:
        """
        判断是否为打卡消息

        通过关键词匹配判断用户输入是否为打卡相关的自然语言描述。

        Args:
            content: 用户输入内容

        Returns:
            bool: 如果是打卡消息返回True
        """
        content_lower = content.lower()
        checkin_keywords = [
            # 完成状态关键词
            '已完成', '完成了', '完成', 'done', '已做', '做完',
            # 部分完成关键词
            '部分完成', '部分', '一半', 'partial',
            # 未完成关键词
            '未完成', '没完成', '未做', '没做', 'failed', 'miss'
        ]

        return any(keyword in content_lower for keyword in checkin_keywords)

    def _extract_note_from_message(self, content: str, keywords: list) -> str:
        """
        从消息中提取备注

        移除关键词后的剩余内容作为用户备注。

        Args:
            content: 原始消息内容
            keywords: 要移除的关键词列表

        Returns:
            str: 提取的备注内容，如果为空则返回空字符串
        """
        content = content.strip()
        for keyword in keywords:
            if keyword in content:
                note = content.replace(keyword, '').strip()
                return note if note else ""
        return ""

    def _get_help_message(self) -> str:
        """
        获取帮助信息

        Returns:
            str: 完整的功能使用帮助信息
        """
        return """🎯 立志功能帮助

📝 主要功能：
• 立志：设定新目标
• 打卡：记录每日进展
• 我的目标：查看目标详情
• 目标历史：查看打卡记录

⚡ 快捷操作：
• 回复「1」表示已完成
• 回复「2」表示部分完成
• 回复「3」表示未完成

💡 使用说明：
1. 首先设定一个明确的目标
2. 每天记录执行情况
3. 坚持打卡，养成习惯
4. AI会根据您的情况给予鼓励

开始您的立志之旅吧！💪"""

    def on_receive_message(self, e_context: EventContext):
        """
        接收消息事件处理

        预留的消息处理扩展点，可以在这里添加额外的消息处理逻辑。

        Args:
            e_context: 事件上下文
        """
        # 可以在这里添加额外的消息处理逻辑
        pass

    def get_help_text(self, **kwargs):
        """
        获取插件帮助文本

        为插件系统提供的标准帮助文本接口。

        Returns:
            插件帮助文本
        """
        return self._get_help_message()

    def __del__(self):
        """
        析构函数，停止调度器

        确保在插件销毁时正确停止提醒调度器，释放资源。
        """
        try:
            if hasattr(self, 'reminder_scheduler'):
                self.reminder_scheduler.stop()
        except:
            pass


class AspirationPlugin(Plugin):
    """
    志AspirationPlugin(Plugin):
    """
    def __init__(self):
        logger.info("--- AspirationPlugin.__init__ ---")
        # Log class attributes set by PluginMetaclass
        logger.info(f"[Aspiration Init] Class Attr: AspirationPlugin.path = '{getattr(AspirationPlugin, 'path', 'NOT SET')}'")
        logger.info(f"[Aspiration Init] Class Attr: AspirationPlugin.name = '{getattr(AspirationPlugin, 'name', 'NOT SET')}'")

        super().__init__() # This calls Plugin.__init__ which sets self.path and self.name from class attributes
                           # and then calls self.load_config()

        logger.info(f"[Aspiration Init] Post-Super: Instance self.path = '{getattr(self, 'path', 'NOT SET')}' (set by Plugin.__init__ from AspirationPlugin.path)")
        logger.info(f"[Aspiration Init] Post-Super: Instance self.name = '{getattr(self, 'name', 'NOT SET')}' (set by Plugin.__init__ from AspirationPlugin.name)")

        try:
            if not hasattr(self, 'path') or not self.path:
                logger.error("[Aspiration Init] CRITICAL FAILURE: self.path is not valid after super().__init__(). This is the root cause if path is empty/None here.")

            # _load_config() is called by super().__init__() via self.load_config(),
            # but we call it here again to ensure our specific logic runs if the base load_config is generic.
            # However, the base Plugin.load_config() already loads config.json from self.path.
            # Our _load_config is more about ensuring template exists and specific parsing.
            # For now, let's assume base load_config populates self.config, and our _load_config refines/validates it.
            # If AspirationPlugin overrides load_config() itself, then super().__init__() would call that.
            # Let's check if we have overridden load_config or if _load_config is a helper.
            # Assuming _load_config is our main config loader, called after super's potential loading.
            self._load_config()

            logger.info(f"[Aspiration Init] Config loaded. Reminder time: {self.config.get('reminder_time')}")
            db_file = self.config.get("database_file", "aspiration.db")
            self.db_path = os.path.join(self.path, db_file) # self.path must be valid here
            logger.info(f"[Aspiration Init] Database path set to: {self.db_path}")

            # Initialize sub-modules
            logger.info("[Aspiration] Initializing DatabaseManager...")
            self.db_mgr = DatabaseManager(self.db_path)
            logger.info("[Aspiration] DatabaseManager initialized.")

            # 初始化AI回复生成器
            logger.info("[Aspiration] Initializing AIResponseGenerator...")
            self.ai_generator = AIResponseGenerator()
            logger.info("[Aspiration] AIResponseGenerator initialized.")

            logger.info("[Aspiration] Initializing GoalManager...")
            self.goal_manager = GoalManager(self.db_mgr)
            logger.info("[Aspiration] GoalManager initialized.")

            logger.info("[Aspiration] Initializing CheckInManager...")
            self.checkin_manager = CheckInManager(self.db_mgr, self.ai_generator)
            logger.info("[Aspiration] CheckInManager initialized.")

            # 初始化提醒调度器
            logger.info("[Aspiration] Initializing ReminderScheduler...")
            reminder_time_str = self.config.get('reminder_time', '21:00')
            self.reminder_scheduler = ReminderScheduler(
                self.db_mgr,
                self.ai_generator,
                reminder_time=reminder_time_str
            )
            logger.info(f"[Aspiration] ReminderScheduler initialized with time: {reminder_time_str}.")

            self.user_sessions = {}

            enable_reminders_flag = self.config.get("enable_reminders", True)
            if enable_reminders_flag:
                logger.info("[Aspiration] Starting ReminderScheduler as enable_reminders is true...")
                self.reminder_scheduler.start()
                logger.info("[Aspiration] ReminderScheduler started.")
            else:
                logger.info("[Aspiration] ReminderScheduler not started as enable_reminders is false.")

            logger.info("[Aspiration] 立志功能插件初始化完成 (end of try block in __init__)")

        except Exception as e:
            logger.error(f"[Aspiration] EXCEPTION during __init__ after super(): {str(e)}", exc_info=True)
            # Re-raise the original exception to see it in test output
            raise

    def _load_config(self):
        """加载插件配置文件"""
        config_path = os.path.join(self.path, "config.json")
        default_config_path = os.path.join(self.path, "config.json.template")

        try:
            if not os.path.exists(config_path):
                if os.path.exists(default_config_path):
                    import shutil
                    shutil.copy(default_config_path, config_path)
                    logger.info(f"[Aspiration] Copied default config to {config_path}")
                else:
                    logger.warn(f"[Aspiration] Default config template not found at {default_config_path}")
                    return {}

            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info("[Aspiration] Plugin config loaded.")
                return config
        except FileNotFoundError:
            logger.warn(f"[Aspiration] Config file not found at {config_path}. Using default settings.")
            return {}
        except json.JSONDecodeError:
            logger.error(f"[Aspiration] Error decoding config file {config_path}. Using default settings.")
            return {}
        except Exception as e:
            logger.error(f"[Aspiration] Error loading config: {e}. Using default settings.")
            return {}

    def _save_config(self, config):
        """
        保存插件配置

        从config.json文件中读取插件配置，如果文件不存在或读取失败，
        则返回默认配置。

        Returns:
            dict: 插件配置字典，包含数据库路径、提醒时间等设置
        """
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[Aspiration] 加载配置失败: {e}")
            # 返回默认配置
            return {
                'enabled': True,
                'database_path': 'data/aspiration.db',
                'reminder_time': '21:00',
                'ai_enabled': True
            }

    def on_handle_context(self, e_context: EventContext):
        """
        处理用户消息的主入口

        这是插件处理用户消息的核心方法，负责：
        1. 检查消息类型（仅处理文本消息）
        2. 检查是否有待发送的提醒
        3. 判断是否为立志相关指令
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
            # 如果有待发送的提醒，先显示提醒
            reply = Reply()
            reply.type = ReplyType.TEXT
            reply.content = pending_reminder + "\n\n" + "回复「打卡」记录今天的进展！"
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return

        # 处理立志相关指令
        if self._is_aspiration_command(content):
            reply = self._handle_aspiration_command(content, user_id)
            if reply:
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS

    def _is_aspiration_command(self, content: str) -> bool:
        """
        判断是否为立志相关指令

        通过关键词匹配和会话状态检查，判断用户消息是否与立志功能相关。

        Args:
            content: 用户输入的消息内容

        Returns:
            bool: 如果是立志相关指令返回True，否则返回False
        """
        content_lower = content.lower()

        # 立志功能的关键词列表
        aspiration_keywords = [
            # 中文关键词
            '立志', '目标', '打卡', '我的目标', '目标历史', '完成目标', '放弃目标',
            # 英文关键词（备用）
            'set_goal', 'check_in', 'my_goals', 'goal_stats', 'goal_history',
            # 快捷选项
            '1', '2', '3', '已完成', '部分完成', '未完成', 'done', 'partial', 'failed'
        ]

        # 检查是否包含关键词
        for keyword in aspiration_keywords:
            if keyword in content_lower:
                return True

        # 检查用户是否在设定目标的会话中
        return content.startswith('/') or self._is_in_goal_setting_session(content)

    def _is_in_goal_setting_session(self, content: str) -> bool:
        """
        检查用户是否在目标设定会话中

        Args:
            content: 用户输入内容

        Returns:
            bool: 如果用户在目标设定流程中返回True

        Note:
            这里可以添加更复杂的会话状态检查逻辑
        """
        # 这里可以添加会话状态检查逻辑
        # 比如检查用户是否在等待输入目标描述或天数
        return False

    def _handle_aspiration_command(self, content: str, user_id: str) -> Reply:
        """
        处理立志相关指令的核心路由方法

        根据用户输入的内容，路由到相应的处理方法。支持多种命令格式：
        - 关键词命令（如"立志"、"打卡"）
        - 数字选项（如"1"、"2"、"3"）
        - 自然语言描述
        - 目标管理操作

        Args:
            content: 用户输入内容
            user_id: 用户ID

        Returns:
            Reply: 回复对象，包含回复内容和类型
        """
        try:
            content = content.strip()
            content_lower = content.lower()

            reply = Reply()
            reply.type = ReplyType.TEXT

            # 处理主菜单命令
            if content in ['立志', 'SET_GOAL']:
                reply.content = self._handle_goal_setting_start(user_id)
            elif content in ['打卡', 'CHECK_IN']:
                reply.content = self._handle_checkin_start(user_id)
            elif content in ['我的目标', 'MY_GOALS']:
                reply.content = self.goal_manager.get_goal_details(user_id)
            elif content in ['目标统计', 'GOAL_STATS']:
                reply.content = self.goal_manager.get_goal_details(user_id)
            elif content in ['目标历史', 'GOAL_HISTORY']:
                reply.content = self.goal_manager.get_goal_history(user_id)

            # 处理目标管理指令
            elif any(keyword in content_lower for keyword in ['完成目标', 'complete_goal']):
                success, message = self.goal_manager.complete_goal(user_id)
                reply.content = message
            elif any(keyword in content_lower for keyword in ['放弃目标', 'abandon_goal']):
                success, message = self.goal_manager.abandon_goal(user_id)
                reply.content = message

            # 处理快捷打卡指令
            elif content in ['1'] or any(keyword in content_lower for keyword in ['已完成', 'done']):
                success, message = self.checkin_manager.quick_checkin_completed(user_id)
                reply.content = message
            elif content in ['2'] or any(keyword in content_lower for keyword in ['部分完成', 'partial']):
                note = self._extract_note_from_message(content, ['2', '部分完成', 'partial'])
                success, message = self.checkin_manager.quick_checkin_partial(user_id, note)
                reply.content = message
            elif content in ['3'] or any(keyword in content_lower for keyword in ['未完成', 'failed']):
                note = self._extract_note_from_message(content, ['3', '未完成', 'failed'])
                success, message = self.checkin_manager.quick_checkin_failed(user_id, note)
                reply.content = message

            # 处理自然语言打卡消息
            elif self._is_checkin_message(content):
                status, note = self.checkin_manager.parse_checkin_message(content)
                if status:
                    success, message = self.checkin_manager.record_checkin(user_id, status, note)
                    reply.content = message
                else:
                    reply.content = self.checkin_manager.get_checkin_guide(user_id)

            # 处理数字输入（可能是目标天数或打卡选项）
            elif content.isdigit() and 1 <= int(content) <= 1000:
                reply.content = self._handle_goal_duration_input(user_id, int(content))

            # 处理普通文本（可能是目标描述）
            elif len(content) > 2 and not content.startswith('/'):
                reply.content = self._handle_potential_goal_description(user_id, content)

            # 默认显示帮助信息
            else:
                reply.content = self._get_help_message()

            return reply

        except Exception as e:
            logger.error(f"[Aspiration] 处理指令失败: {e}")
            reply = Reply()
            reply.type = ReplyType.TEXT
            reply.content = "处理请求时出现错误，请稍后重试"
            return reply

    def _handle_goal_setting_start(self, user_id: str) -> str:
        """
        处理目标设定开始

        检查用户是否已有活跃目标，如果有则提示用户先处理现有目标，
        否则引导用户开始设定新目标。

        Args:
            user_id: 用户ID

        Returns:
            str: 回复消息内容
        """
        # 检查是否已有活跃目标
        active_goal = self.goal_manager.get_active_goal(user_id)
        if active_goal:
            return f"""您已有一个活跃目标：

📝 {active_goal['goal_description']}
📅 已进行 {active_goal['days_since_start']} 天

如需设定新目标，请先完成或放弃当前目标：
• 回复「完成目标」结束当前挑战
• 回复「放弃目标」暂停当前目标
• 回复「我的目标」查看详细信息"""

        # 设置用户会话状态为等待目标描述
        self.user_sessions[user_id] = {'state': 'waiting_goal_description'}

        return """🎯 立志 - 设定新目标

请描述您要坚持的目标：

💡 目标建议：
• 具体可执行：「每天读书30分钟」
• 时间明确：「每天晚上跑步」
• 可以量化：「每天写500字」

请直接输入您的目标描述："""

    def _handle_checkin_start(self, user_id: str) -> str:
        """
        处理打卡开始

        获取用户的打卡指南，如果用户没有活跃目标会提示设定目标。

        Args:
            user_id: 用户ID

        Returns:
            str: 打卡指南或提示信息
        """
        return self.checkin_manager.get_checkin_guide(user_id)

    def _handle_potential_goal_description(self, user_id: str, content: str) -> str:
        """
        处理可能的目标描述

        根据用户的会话状态，判断用户输入是否为目标描述或其他内容。
        支持目标设定的多步骤流程。

        Args:
            user_id: 用户ID
            content: 用户输入内容

        Returns:
            str: 相应的回复消息
        """
        session = self.user_sessions.get(user_id, {})

        if session.get('state') == 'waiting_goal_description':
            # 用户正在设定目标描述
            self.user_sessions[user_id] = {
                'state': 'waiting_goal_duration',
                'goal_description': content
            }

            return f"""目标描述已记录：「{content}」

请输入计划坚持的天数（1-1000天）：

💡 建议：
• 初学者：7-30天
• 有经验：30-90天
• 长期目标：90天以上

请输入数字："""

        elif session.get('state') == 'waiting_goal_duration':
            # 用户可能输入了非数字的天数描述
            return """请输入有效的天数（纯数字）：

例如：30（表示30天）

或者回复「取消」取消目标设定"""

        else:
            # 用户没有在设定目标，可能是想要立志
            return """您是要设定新目标吗？

回复「立志」开始设定目标
回复「打卡」记录今日进展
回复「我的目标」查看当前目标"""

    def _handle_goal_duration_input(self, user_id: str, days: int) -> str:
        """
        处理目标天数输入

        当用户输入数字时，根据会话状态判断是设定目标天数还是打卡选项。

        Args:
            user_id: 用户ID
            days: 输入的数字

        Returns:
            str: 处理结果消息
        """
        session = self.user_sessions.get(user_id, {})

        if session.get('state') == 'waiting_goal_duration' and 'goal_description' in session:
            # 完成目标设定
            description = session['goal_description']

            # 清除会话状态
            self.user_sessions.pop(user_id, None)

            # 创建目标，传入AI生成器用于生成建议
            success, message = self.goal_manager.create_goal(user_id, description, days, self.ai_generator)

            return message
        else:
            # 用户没有在设定目标流程中，可能是打卡选项
            return self._handle_checkin_number(user_id, str(days))

    def _handle_checkin_number(self, user_id: str, number: str) -> str:
        """
        处理打卡数字选项

        将数字选项转换为相应的打卡操作。

        Args:
            user_id: 用户ID
            number: 数字选项字符串

        Returns:
            str: 打卡结果消息
        """
        if number == '1':
            success, message = self.checkin_manager.quick_checkin_completed(user_id)
        elif number == '2':
            success, message = self.checkin_manager.quick_checkin_partial(user_id)
        elif number == '3':
            success, message = self.checkin_manager.quick_checkin_failed(user_id)
        else:
            message = self.checkin_manager.get_checkin_guide(user_id)

        return message

    def _is_checkin_message(self, content: str) -> bool:
        """
        判断是否为打卡消息

        通过关键词匹配判断用户输入是否为打卡相关的自然语言描述。

        Args:
            content: 用户输入内容

        Returns:
            bool: 如果是打卡消息返回True
        """
        content_lower = content.lower()
        checkin_keywords = [
            # 完成状态关键词
            '已完成', '完成了', '完成', 'done', '已做', '做完',
            # 部分完成关键词
            '部分完成', '部分', '一半', 'partial',
            # 未完成关键词
            '未完成', '没完成', '未做', '没做', 'failed', 'miss'
        ]

        return any(keyword in content_lower for keyword in checkin_keywords)

    def _extract_note_from_message(self, content: str, keywords: list) -> str:
        """
        从消息中提取备注

        移除关键词后的剩余内容作为用户备注。

        Args:
            content: 原始消息内容
            keywords: 要移除的关键词列表

        Returns:
            str: 提取的备注内容，如果为空则返回空字符串
        """
        content = content.strip()
        for keyword in keywords:
            if keyword in content:
                note = content.replace(keyword, '').strip()
                return note if note else ""
        return ""

    def _get_help_message(self) -> str:
        """
        获取帮助信息

        Returns:
            str: 完整的功能使用帮助信息
        """
        return """🎯 立志功能帮助

📝 主要功能：
• 立志：设定新目标
• 打卡：记录每日进展
• 我的目标：查看目标详情
• 目标历史：查看打卡记录

⚡ 快捷操作：
• 回复「1」表示已完成
• 回复「2」表示部分完成
• 回复「3」表示未完成

💡 使用说明：
1. 首先设定一个明确的目标
2. 每天记录执行情况
3. 坚持打卡，养成习惯
4. AI会根据您的情况给予鼓励

开始您的立志之旅吧！💪"""

    def on_receive_message(self, e_context: EventContext):
        """
        接收消息事件处理

        预留的消息处理扩展点，可以在这里添加额外的消息处理逻辑。

        Args:
            e_context: 事件上下文
        """
        # 可以在这里添加额外的消息处理逻辑
        pass

    def get_help_text(self, **kwargs):
        """
        获取插件帮助文本

        为插件系统提供的标准帮助文本接口。

        Returns:
            插件帮助文本
        """
        return self._get_help_message()

    def __del__(self):
        """
        析构函数，停止调度器

        确保在插件销毁时正确停止提醒调度器，释放资源。
        """
        try:
            if hasattr(self, 'reminder_scheduler'):
                self.reminder_scheduler.stop()
        except:
            pass
