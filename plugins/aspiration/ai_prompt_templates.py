"""
AI提示词模板模块

该模块提供立志功能中各种场景的AI提示词模板，用于生成个性化的回复内容。
所有提示词都经过精心设计，以确保AI能生成合适的、有帮助的回复。

主要功能：
1. 提供鼓励回复的提示词模板
2. 提供提醒消息的提示词模板
3. 提供目标建议的提示词模板

设计原则：
- 提示词结构化，包含完整的上下文信息
- 明确指定回复的长度和风格要求
- 根据不同状态提供个性化的指导
- 使用emoji增加回复的亲和力
"""
from typing import Dict, Any
from common.log import logger


class AIPromptTemplates:
    """
    AI提示词模板类

    提供立志功能中各种场景的标准化AI提示词模板。
    所有方法都是静态方法，可以直接调用而无需实例化。

    该类负责：
    - 构建结构化的提示词
    - 整合用户数据到提示词中
    - 确保AI理解上下文和输出要求
    """

    @staticmethod
    def get_encouragement_prompt(goal_info: Dict[str, Any], checkin_info: Dict[str, Any],
                               user_stats: Dict[str, Any]) -> str:
        """
        生成鼓励提示词

        根据用户的目标信息、打卡情况和历史统计数据，构建用于生成
        个性化鼓励回复的AI提示词。

        Args:
            goal_info: 目标信息字典，包含：
                - goal_description: 目标描述
                - planned_days: 计划天数
                - days_since_start: 已开始天数
            checkin_info: 打卡信息字典，包含：
                - status: 打卡状态 ('completed', 'partial', 'failed')
                - note: 用户备注（可选）
            user_stats: 用户统计信息字典，包含：
                - consecutive_days: 连续打卡天数
                - completion_rate: 总完成率
                - max_streak: 最长连续天数

        Returns:
            str: 完整的AI提示词，包含角色设定、用户数据和输出要求
        """
        # 将打卡状态转换为中文描述
        status_text = {
            'completed': '已完成',
            'partial': '部分完成',
            'failed': '未完成'
        }.get(checkin_info['status'], checkin_info['status'])

        prompt = f"""你是一个温暖贴心的目标管理助手，请根据用户的打卡情况生成个性化的鼓励回复。

用户目标信息：
- 目标：{goal_info['goal_description']}
- 计划天数：{goal_info['planned_days']}天
- 已开始：{goal_info.get('days_since_start', 1)}天

今日打卡情况：
- 状态：{status_text}
- 用户备注：{checkin_info.get('note', '无')}

历史统计：
- 连续打卡：{user_stats['consecutive_days']}天
- 总完成率：{user_stats['completion_rate']}%
- 最长连续：{user_stats['max_streak']}天

请生成一条50字以内的温暖鼓励回复，要求：
1. 根据完成状态给予恰当的反馈
2. 提及具体的坚持天数或进展
3. 语气积极正面，使用适当的emoji
4. 如果是失败/部分完成，给予理解和建议

回复内容："""
        return prompt

    @staticmethod
    def get_reminder_prompt(goal_info: Dict[str, Any], user_stats: Dict[str, Any]) -> str:
        """
        生成提醒消息的AI优化提示词

        为未打卡的用户生成温馨提醒消息的AI提示词。

        Args:
            goal_info: 目标信息字典，包含目标描述等信息
            user_stats: 用户统计信息字典，包含连续天数、完成率等

        Returns:
            str: 用于生成提醒消息的AI提示词
        """
        prompt = f"""请为用户生成一条温馨的目标提醒消息。

用户目标：{goal_info['goal_description']}
已坚持：{user_stats['consecutive_days']}天
完成率：{user_stats['completion_rate']}%

生成一条80字以内的提醒消息，要求：
1. 温馨友善，不要有压迫感
2. 提及坚持天数，鼓励继续
3. 包含具体的行动指引
4. 使用适当的emoji增加亲和力

提醒内容："""
        return prompt

    @staticmethod
    def get_goal_suggestion_prompt(description: str) -> str:
        """
        生成目标建议的提示词

        为用户新设定的目标生成优化建议的AI提示词。

        Args:
            description: 用户输入的目标描述

        Returns:
            str: 用于生成目标优化建议的AI提示词

        Note:
            建议内容应该帮助用户将模糊的目标转化为具体、可执行、可衡量的目标
        """
        prompt = f"""用户想要设定一个目标："{description}"

请帮助优化这个目标，使其更加具体、可执行、可衡量。
建议包括：
1. 具体的行动描述
2. 合理的时间安排
3. 可衡量的标准
4. 实用的执行建议

请用50字以内简洁回复，语气鼓励积极。

优化建议："""
        return prompt
