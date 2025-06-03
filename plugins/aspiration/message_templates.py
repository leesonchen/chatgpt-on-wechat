"""
消息模板管理器模块

该模块提供立志功能中各种场景下的标准消息模板，包括欢迎消息、指导消息、
提醒消息、鼓励消息等。通过集中管理消息模板，确保用户体验的一致性和
消息内容的专业性。

主要功能：
1. 欢迎和引导消息模板
2. 目标设定流程的各阶段消息
3. 打卡相关的反馈消息
4. 提醒和鼓励消息
5. 错误和异常情况的提示消息
6. 成就和庆祝消息

设计特点：
- 统一的消息风格和语调
- 丰富的emoji使用增强亲和力
- 清晰的操作指导和选项提示
- 个性化的动态内容插入
- 鼓励性和正向的表达方式
"""

from typing import Dict, Any
from datetime import date, datetime


class MessageTemplates:
    """
    消息模板类，提供各种场景的标准化消息模板

    该类集中管理立志功能的所有消息模板，通过静态方法提供不同场景下的
    标准化回复内容。所有模板都经过精心设计，具有一致的风格和语调。

    主要特点：
    - 使用静态方法，无需实例化即可使用
    - 支持动态参数插入，提供个性化内容
    - 统一的emoji使用规范
    - 清晰的结构化布局
    - 鼓励性和专业性的语言风格

    模板分类：
    - 欢迎和引导类模板
    - 目标设定流程模板
    - 打卡反馈模板
    - 提醒和鼓励模板
    - 成就和庆祝模板
    """

    @staticmethod
    def welcome_message() -> str:
        """
        欢迎消息模板

        当用户首次使用立志功能或需要查看帮助信息时显示的欢迎消息。
        提供功能概览和基础操作指导。

        Returns:
            str: 包含功能介绍和操作指南的欢迎消息

        内容包括：
        - 功能介绍
        - 主要操作命令
        - 鼓励性的结尾语
        """
        return """🌟 欢迎使用立志功能！

我可以帮助您：
🎯 设定目标：回复「立志」开始设定新目标
📝 记录打卡：回复「打卡」记录今天的进展
📊 查看统计：回复「我的目标」查看当前状态
📜 历史记录：回复「目标历史」查看过往记录

让我们一起坚持梦想，达成目标！💪"""

    @staticmethod
    def goal_setting_start() -> str:
        """
        开始设定目标的引导消息

        引导用户开始目标设定流程，提供目标描述的示例和建议。

        Returns:
            str: 目标设定开始的引导消息

        特点：
        - 提供具体的目标示例
        - 引导用户使用简洁明确的表达
        - 设定积极的基调
        """
        return """🎯 太好了！让我们开始设定您的目标吧！

请描述您要设定的目标，例如：
• 每天跑步30分钟
• 每天读书1小时
• 每天学习英语
• 早睡早起
• 戒烟戒酒

请用简洁明确的语言描述您的目标："""

    @staticmethod
    def goal_days_request(goal_description: str) -> str:
        """
        请求设定目标天数的消息

        在用户提供目标描述后，请求用户设定计划坚持的天数。
        提供常见的天数选择建议。

        Args:
            goal_description: 用户输入的目标描述

        Returns:
            str: 包含目标确认和天数选择指导的消息

        特点：
        - 确认用户输入的目标
        - 提供科学的天数建议（21天、30天、66天、100天）
        - 每个建议都有对应的说明
        """
        return f"""✅ 目标已确认：{goal_description}

请输入您计划坚持的天数（请输入数字）：

常见选择：
• 21天 - 养成新习惯
• 30天 - 月度挑战
• 66天 - 深度习惯形成
• 100天 - 长期坚持

或者输入您想要的其他天数（1-1000天）："""

    @staticmethod
    def checkin_status_request() -> str:
        """
        请求打卡状态的消息

        引导用户选择当天的目标完成情况，提供标准化的选项和自定义选项。

        Returns:
            str: 包含完成情况选项的打卡状态请求消息

        设计特点：
        - 提供5个标准选项，从完美完成到未完成
        - 包含百分比和描述说明，便于用户理解
        - 支持数字快速选择和文字详细描述两种方式
        - 使用数字emoji增强视觉识别
        """
        return """📝 请选择今天的完成情况：

1️⃣ 完美完成 - 100%达成目标
2️⃣ 基本完成 - 完成了大部分
3️⃣ 部分完成 - 完成了一些
4️⃣ 未完成 - 今天没有行动
5️⃣ 详细说明 - 用文字描述今天的情况

请回复数字或直接描述您今天的情况："""

    @staticmethod
    def no_active_goal() -> str:
        """
        没有活跃目标的提醒消息

        当用户尝试打卡或查看目标信息但没有活跃目标时显示的提醒。

        Returns:
            str: 引导用户设定新目标的提醒消息

        特点：
        - 明确指出用户当前状态
        - 提供明确的下一步操作指导
        - 使用鼓励性的语言激发用户行动
        """
        return """❌ 您目前没有活跃的目标

回复「立志」开始设定新目标，让我们一起开启坚持之旅！💪"""

    @staticmethod
    def goal_already_checked_today() -> str:
        """
        今日已打卡提醒消息

        当用户尝试重复打卡时显示的提醒，告知已经完成当天打卡。

        Returns:
            str: 已打卡的提醒和后续操作建议

        特点：
        - 确认已完成打卡的状态
        - 鼓励用户明天继续坚持
        - 提供查看详细进度的操作指导
        """
        return """✅ 您今天已经打卡了！

明天记得继续坚持哦～
回复「我的目标」查看详细进度"""

    @staticmethod
    def goal_completed_congratulation(goal_info: Dict[str, Any], stats: Dict[str, Any]) -> str:
        """
        目标完成祝贺消息

        当用户成功完成目标时显示的庆祝消息，包含成就总结和鼓励内容。

        Args:
            goal_info: 目标信息字典，包含目标描述、计划天数等
            stats: 统计信息字典，包含完成率、连续天数等数据

        Returns:
            str: 包含成就总结和祝贺内容的完成消息

        特点：
        - 突出显示用户的成就数据
        - 提供正向的鼓励和赞扬
        - 引导用户设定下一个目标
        - 使用庆祝性的emoji增强喜悦感
        """
        return f"""🎉 恭喜您！目标「{goal_info['goal_description']}」已成功完成！

📊 您的成就：
• 总计划天数：{goal_info['planned_days']}天
• 实际打卡：{stats['total_checkins']}天
• 完成率：{stats['completion_rate']:.1f}%
• 最长连续：{stats['max_consecutive']}天

🏆 您的坚持值得赞扬！这份毅力将伴随您走向更多成功！

准备好设定下一个目标了吗？回复「立志」开始新的挑战！"""

    @staticmethod
    def goal_abandoned_message(goal_info: Dict[str, Any]) -> str:
        """
        目标放弃确认消息

        当用户选择放弃目标时显示的确认消息，提供温和的反馈和重新开始的鼓励。

        Args:
            goal_info: 目标信息字典

        Returns:
            str: 放弃确认和鼓励重新开始的消息

        特点：
        - 确认目标已被放弃
        - 提供宽容和理解的态度
        - 鼓励用户重新开始
        - 提供具体的后续操作建议
        """
        return f"""⚠️ 目标「{goal_info['goal_description']}」已被放弃

没关系，重新开始永远不会太晚！
回复「立志」设定新目标，或者
回复「目标历史」查看过往记录"""

    @staticmethod
    def daily_reminder(goal_info: Dict[str, Any], days_passed: int) -> str:
        """
        每日提醒消息

        定时发送给用户的提醒消息，督促用户完成当天的目标。

        Args:
            goal_info: 目标信息字典
            days_passed: 已经过去的天数

        Returns:
            str: 包含目标信息和鼓励内容的每日提醒

        特点：
        - 显示目标进度信息
        - 计算并显示剩余天数
        - 提供打卡操作指导
        - 使用鼓励性的语言激发行动
        """
        remaining_days = goal_info['planned_days'] - days_passed
        return f"""⏰ 晚上好！今天的目标完成了吗？

🎯 目标：{goal_info['goal_description']}
📅 已进行：{days_passed}天
⏳ 剩余：{remaining_days}天

回复「打卡」记录今天的进展！
坚持就是胜利！💪"""

    @staticmethod
    def overdue_reminder(goal_info: Dict[str, Any], overdue_days: int) -> str:
        """逾期提醒消息"""
        return f"""🔔 温馨提醒：您的目标已经{overdue_days}天没有打卡了

🎯 目标：{goal_info['goal_description']}

不要气馁，重新开始就是进步！
回复「打卡」继续您的坚持之旅
或回复「立志」设定新的目标"""

    @staticmethod
    def error_message() -> str:
        """通用错误消息"""
        return """❌ 处理请求时出现了问题

请稍后重试，或联系管理员获取帮助
常用指令：「立志」「打卡」「我的目标」"""

    @staticmethod
    def invalid_input_message() -> str:
        """无效输入消息"""
        return """❓ 输入格式不正确

请按提示输入，或回复以下指令：
• 「立志」- 设定新目标
• 「打卡」- 记录进展
• 「我的目标」- 查看状态
• 「目标历史」- 查看历史"""

    @staticmethod
    def goal_stats_message(goal_info: Dict[str, Any], stats: Dict[str, Any], recent_checkins: list) -> str:
        """目标统计消息"""
        progress_bar = MessageTemplates._create_progress_bar(stats['completion_rate'])

        # 格式化最近打卡记录
        recent_text = ""
        if recent_checkins:
            recent_text = "\n📋 最近打卡：\n"
            for record in recent_checkins[-5:]:  # 显示最近5次
                date_str = record['check_date']
                status = record['status']
                status_emoji = {
                    'completed': '✅',
                    'partial': '⚡',
                    'failed': '❌',
                    'skipped': '⏭️'
                }.get(status, '📝')
                recent_text += f"{status_emoji} {date_str}\n"

        return f"""📊 目标进度报告

🎯 {goal_info['goal_description']}

📈 完成情况：
{progress_bar}
• 打卡天数：{stats['total_checkins']}/{goal_info['planned_days']}天
• 完成率：{stats['completion_rate']:.1f}%
• 连续天数：{stats['current_consecutive']}天
• 最长连续：{stats['max_consecutive']}天

📅 开始日期：{goal_info['start_date']}
⏰ 剩余天数：{goal_info['planned_days'] - stats['total_checkins']}天{recent_text}

回复「打卡」记录今天进展！"""

    @staticmethod
    def _create_progress_bar(completion_rate: float, width: int = 10) -> str:
        """创建进度条"""
        filled = int(completion_rate / 10)
        empty = width - filled
        bar = "█" * filled + "░" * empty
        return f"[{bar}] {completion_rate:.1f}%"

    @staticmethod
    def help_message() -> str:
        """帮助消息"""
        return """📖 立志功能使用指南

🎯 设定目标：
回复「立志」→ 输入目标描述 → 设定天数

📝 记录打卡：
回复「打卡」→ 选择完成状态

📊 查看进度：
• 「我的目标」- 当前目标状态
• 「目标历史」- 历史记录和统计

🔧 目标管理：
• 「完成目标」- 提前完成当前目标
• 「放弃目标」- 放弃当前目标

💡 小贴士：
• 每天21:00会自动提醒打卡
• 支持文字描述打卡情况
• AI会根据您的情况给出鼓励

坚持就是胜利！💪"""
