"""
AI回复生成器模块

该模块负责生成立志功能中的AI智能回复，包括：
- 根据用户打卡情况生成个性化鼓励回复
- 生成目标提醒消息
- 为新设定的目标提供优化建议

主要功能：
1. 复用现有的AI Bot实例，确保与系统配置一致
2. 通过AI提示词模板生成个性化回复
3. 提供回退机制，确保在AI不可用时仍能正常工作
4. 清理AI回复内容，移除不必要的前缀

依赖：
- bot.bot_factory: 用于创建AI Bot实例
- bridge.context: 提供上下文对象
- config: 获取系统配置信息
- .ai_prompt_templates: AI提示词模板
"""
from typing import Dict, Any, Optional
from bot.bot_factory import create_bot
from bridge.context import Context,ContextType
from bridge.reply import Reply
from common.log import logger
from .ai_prompt_templates import AIPromptTemplates


class AIResponseGenerator:
    """
    AI回复生成器

    负责生成立志功能中的各种AI智能回复，包括鼓励消息、提醒消息和目标建议。
    该类会复用系统现有的AI Bot实例，确保回复风格与系统一致。

    主要特性：
    - 自动获取系统配置的AI模型
    - 支持多种场景的回复生成
    - 提供回退机制保证功能可用性
    - 自动清理回复内容格式

    Attributes:
        bot: AI Bot实例，用于生成回复
    """

    def __init__(self):
        """
        初始化AI回复生成器

        尝试获取当前配置的AI模型，并创建对应的Bot实例。
        如果初始化失败，将提供一个简单的回退机制。
        """
        # 复用现有的AI Bot实例
        try:
            # 从配置中获取当前使用的模型
            from config import conf
            model_type = conf().get("model", "gpt-3.5-turbo")
            from bot.bot_factory import create_bot
            self.bot = create_bot(model_type)
            logger.info(f"[Aspiration] AI回复生成器初始化完成，使用模型: {model_type}")
        except Exception as e:
            logger.error(f"[Aspiration] AI回复生成器初始化失败: {e}")
            logger.info(f"[Aspiration] 将使用内置的简单回复生成器")
            self.bot = None

    def generate_encouragement(self, goal_info: Dict[str, Any], checkin_info: Dict[str, Any],
                              user_stats: Dict[str, Any]) -> str:
        """
        生成鼓励回复

        根据用户的目标信息、打卡情况和历史统计数据生成个性化的鼓励回复。

        Args:
            goal_info: 目标信息字典，包含目标描述、计划天数等
            checkin_info: 打卡信息字典，包含状态、备注等
            user_stats: 用户统计信息字典，包含连续天数、完成率等

        Returns:
            str: 生成的鼓励回复文本

        Note:
            如果AI不可用，会返回预设的回退消息
        """
        if not self.bot:
            return self._get_fallback_message(checkin_info['status'])

        # 使用AI提示词模板生成提示词
        prompt = AIPromptTemplates.get_encouragement_prompt(goal_info, checkin_info, user_stats)

        try:
            # 创建Context对象
            context = Context()
            context.content = prompt
            context.type = ContextType.TEXT
            context["session_id"] = "12345678"

            # 调用AI Bot生成回复
            response = self.bot.reply(prompt, context)

            if response and hasattr(response, 'content') and response.content:
                # 清理回复内容，移除可能的前缀
                content = response.content.strip()
                if content.startswith('回复内容：'):
                    content = content[5:].strip()
                return content
            else:
                return self._get_fallback_message(checkin_info['status'])

        except Exception as e:
            logger.error(f"[Aspiration] AI回复生成失败: {e}")
            return self._get_fallback_message(checkin_info['status'])

    def generate_reminder(self, goal_info: Dict[str, Any], user_stats: Dict[str, Any]) -> str:
        """
        生成提醒消息

        为未打卡的用户生成个性化的提醒消息，考虑用户的坚持情况和目标进度。

        Args:
            goal_info: 目标信息字典
            user_stats: 用户统计信息字典

        Returns:
            str: 生成的提醒消息文本
        """
        if not self.bot:
            return self._get_fallback_reminder(goal_info, user_stats)

        prompt = AIPromptTemplates.get_reminder_prompt(goal_info, user_stats)

        try:
            context = Context()
            context.content = prompt
            context.type = ContextType.TEXT
            context["session_id"] = "12345678"
            
            response = self.bot.reply(prompt, context)

            if response and hasattr(response, 'content') and response.content:
                content = response.content.strip()
                if content.startswith('提醒内容：'):
                    content = content[5:].strip()
                return content
            else:
                return self._get_fallback_reminder(goal_info, user_stats)

        except Exception as e:
            logger.error(f"[Aspiration] AI提醒生成失败: {e}")
            return self._get_fallback_reminder(goal_info, user_stats)

    def generate_goal_suggestion(self, description: str) -> str:
        """
        生成目标建议

        为用户新设定的目标提供优化建议，使目标更具体、可执行、可衡量。

        Args:
            description: 用户输入的目标描述

        Returns:
            str: 生成的目标优化建议
        """
        if not self.bot:
            return f"目标「{description}」设定成功！制定具体的执行计划会更有效哦！"

        prompt = AIPromptTemplates.get_goal_suggestion_prompt(description)

        try:
            context = Context()
            context.content = prompt
            context.type = ContextType.TEXT
            context["session_id"] = "12345678"

            response = self.bot.reply(prompt, context)

            if response and hasattr(response, 'content') and response.content:
                content = response.content.strip()
                if content.startswith('优化建议：'):
                    content = content[5:].strip()
                return content
            else:
                return f"目标「{description}」设定成功！制定具体的执行计划会更有效哦！"

        except Exception as e:
            logger.error(f"[Aspiration] AI建议生成失败: {e}")
            return f"目标「{description}」设定成功！制定具体的执行计划会更有效哦！"

    def _get_fallback_message(self, status: str) -> str:
        """
        获取备用回复消息

        当AI不可用时，根据打卡状态返回预设的鼓励消息。

        Args:
            status: 打卡状态 ('completed', 'partial', 'failed')

        Returns:
            str: 备用的鼓励消息
        """
        fallback_messages = {
            'completed': "太棒了！今天的目标达成了！继续保持这个势头！💪✨",
            'partial': "虽然没有完全完成，但有进展就是好的！明天继续努力！🌟",
            'failed': "没关系，明天是新的开始！每一次尝试都是进步！🌈💪"
        }
        return fallback_messages.get(status, "继续加油！💪")

    def _get_fallback_reminder(self, goal_info: Dict[str, Any], user_stats: Dict[str, Any]) -> str:
        """
        获取备用提醒消息

        当AI不可用时，根据用户统计信息生成标准化的提醒消息。

        Args:
            goal_info: 目标信息字典
            user_stats: 用户统计信息字典

        Returns:
            str: 备用的提醒消息
        """
        consecutive_days = user_stats.get('consecutive_days', 0)
        goal_desc = goal_info.get('goal_description', '您的目标')

        if consecutive_days > 0:
            return f"🌟 立志提醒\n\n亲爱的朋友，今天的「{goal_desc}」还没有打卡哦～\n您已经坚持了{consecutive_days}天，不要让努力白费！\n\n回复「打卡」记录今天的进展吧！💪"
        else:
            return f"🌟 立志提醒\n\n亲爱的朋友，今天的「{goal_desc}」还没有打卡哦～\n\n回复「打卡」记录今天的进展，开始您的坚持之旅！💪"
