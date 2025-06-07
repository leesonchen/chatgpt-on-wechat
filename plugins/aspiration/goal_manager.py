"""
目标管理器模块

该模块负责立志功能中目标相关的业务逻辑处理，包括目标的创建、查询、
更新和删除等核心功能。作为业务层组件，它封装了复杂的业务规则和验证逻辑。

主要功能：
1. 目标创建和验证
2. 活跃目标查询和管理
3. 目标状态更新（完成、放弃）
4. 目标信息格式化和展示
5. 目标相关的业务规则验证

设计特点：
- 提供友好的错误提示和成功反馈
- 严格的输入验证和数据清洗
- 支持单用户单活跃目标的业务约束
- 完善的异常处理和日志记录
"""

from typing import Dict, Any, Tuple, Optional
from datetime import date, timedelta
from common.log import logger
from .database_manager import DatabaseManager


class GoalManager:
    """
    目标管理器，处理目标相关的业务逻辑

    该类封装了目标管理的所有业务逻辑，包括创建、查询、更新和删除操作。
    它提供高级的接口，隐藏了数据库操作的复杂性，并实现了业务规则验证。

    主要职责：
    - 执行目标创建前的验证（唯一性、参数合法性等）
    - 格式化目标信息的展示内容
    - 处理目标状态转换的业务逻辑
    - 提供用户友好的反馈消息
    - 维护目标相关的业务约束

    Attributes:
        db: 数据库管理器实例，用于执行数据持久化操作
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化目标管理器

        Args:
            db_manager: 数据库管理器实例，用于数据持久化操作
        """
        self.db = db_manager

    def create_goal(self, user_id: str, description: str, planned_days: int, ai_generator=None) -> Tuple[bool, str]:
        """
        创建新目标

        为指定用户创建一个新的目标。在创建前会进行多项验证，包括检查是否已有活跃目标、
        验证输入参数的合法性等。确保每个用户同时只能有一个活跃目标。
        新增AI检查功能，对目标内容进行适宜性评估和优化建议。

        Args:
            user_id: 用户ID
            description: 目标描述，会自动去除首尾空白字符
            planned_days: 计划坚持的天数，必须在1-1000之间
            ai_generator: AI回复生成器实例，用于生成目标建议

        Returns:
            Tuple[bool, str]: (是否成功, 反馈消息)
            - 成功时返回(True, 包含目标详情和AI建议的成功消息)
            - 失败时返回(False, 具体的错误提示)

        业务规则：
        1. 每个用户同时只能有一个活跃目标
        2. 目标描述不能为空或只包含空白字符
        3. 计划天数必须在1-1000天之间
        4. 自动设置开始日期为今天，结束日期为开始日期+计划天数
        5. AI会检查目标内容的适宜性并提供优化建议

        异常处理：
        - 数据库操作异常会被捕获并记录日志
        - 返回用户友好的错误消息而不是技术细节
        """
        try:
            # 检查是否有活跃目标
            active_goal = self.get_active_goal(user_id)
            if active_goal:
                return False, f"您已有一个活跃目标「{active_goal['goal_description']}」，请先完成或删除现有目标后再设定新目标。\n\n回复「我的目标」查看详情"

            # 验证输入参数
            if not description or not description.strip():
                return False, "目标描述不能为空，请重新输入目标内容"

            if planned_days <= 0 or planned_days > 1000:
                return False, "计划天数需要在1-1000天之间，请重新输入"

            # 清理目标描述
            description = description.strip()

            # AI检查目标内容的适宜性
            ai_feedback = ""
            if ai_generator:
                try:
                    # 生成AI检查和建议
                    ai_suggestion = ai_generator.generate_goal_suggestion(description)
                    ai_feedback = f"\n\n🤖 AI建议：\n{ai_suggestion}"
                except Exception as e:
                    logger.error(f"[Aspiration] AI建议生成失败: {e}")
                    ai_feedback = "\n\n💡 建议：制定具体的执行计划会更有效哦！"

            # 创建新目标
            goal_id = self.db.create_goal(
                user_id=user_id,
                description=description,
                planned_days=planned_days
            )

            success_msg = f"""🎯 目标设定成功！

📝 目标：{description}
📅 计划：{planned_days}天
🏁 开始日期：{date.today().strftime('%Y年%m月%d日')}{ai_feedback}

加油！每一步都是进步，期待您的第一次打卡 💪

回复「打卡」记录今天的进度吧！"""

            return True, success_msg

        except Exception as e:
            logger.error(f"[Aspiration] 创建目标失败: {e}")
            return False, "目标设定失败，请稍后重试"

    def get_active_goal(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户的活跃目标

        查询指定用户当前活跃状态的目标信息。

        Args:
            user_id: 用户ID

        Returns:
            Optional[Dict[str, Any]]: 活跃目标信息字典，如果没有活跃目标则返回None

        注意：
        - 直接调用数据库管理器的对应方法
        - 返回的字典包含目标的所有字段信息
        """
        return self.db.get_active_goal(user_id)

    def complete_goal(self, user_id: str) -> Tuple[bool, str]:
        """
        完成目标

        将用户的活跃目标标记为已完成状态，并生成包含统计信息的完成报告。

        Args:
            user_id: 用户ID

        Returns:
            Tuple[bool, str]: (是否成功, 反馈消息)
            - 成功时返回包含统计数据的庆祝消息
            - 失败时返回相应的错误提示

        处理流程：
        1. 检查用户是否有活跃目标
        2. 获取目标的统计信息（打卡次数、完成率等）
        3. 更新目标状态为'completed'
        4. 生成包含成就总结的完成消息

        生成的完成报告包含：
        - 目标描述
        - 总打卡天数和完成率
        - 最长连续打卡记录
        - 鼓励性的祝贺内容
        """
        try:
            goal = self.get_active_goal(user_id)
            if not goal:
                return False, "您当前没有活跃的目标"

            # 获取统计信息
            stats = self.db.get_user_statistics(user_id, goal['id'])

            # 更新目标状态为已完成
            self.db.update_goal_status(goal['id'], 'completed')

            completion_msg = f"""🎉 恭喜！目标达成！

📝 目标：{goal['goal_description']}
📊 统计：
   • 总打卡：{stats['total_checkins']}天
   • 完成率：{stats['completion_rate']}%
   • 最长连续：{stats['max_streak']}天

您的坚持和努力值得赞扬！💪✨
现在可以设定新的目标，继续您的成长之旅！

回复「立志」设定新目标"""

            return True, completion_msg

        except Exception as e:
            logger.error(f"[Aspiration] 完成目标失败: {e}")
            return False, "操作失败，请稍后重试"

    def abandon_goal(self, user_id: str) -> Tuple[bool, str]:
        """
        放弃目标

        将用户的活跃目标标记为已放弃状态。这是一个软删除操作，
        目标和相关数据仍会保留在数据库中，但状态变为非活跃。

        Args:
            user_id: 用户ID

        Returns:
            Tuple[bool, str]: (是否成功, 反馈消息)
            - 成功时返回鼓励性的放弃确认消息
            - 失败时返回相应的错误提示

        处理逻辑：
        1. 检查用户是否有活跃目标
        2. 更新目标状态为'abandoned'
        3. 生成鼓励用户重新开始的温和消息

        注意：
        - 放弃的目标不会被物理删除，数据仍然保留
        - 用户可以立即设定新的目标
        - 提供温和而鼓励的反馈，不会让用户感到挫败
        """
        try:
            goal = self.get_active_goal(user_id)
            if not goal:
                return False, "您当前没有活跃的目标"

            # 更新目标状态为已放弃
            self.db.update_goal_status(goal['id'], 'abandoned')

            abandon_msg = f"""目标「{goal['goal_description']}」已暂停

没关系，每一次尝试都是宝贵的经验！🌈
当您准备好时，随时可以重新开始。

回复「立志」设定新目标"""

            return True, abandon_msg

        except Exception as e:
            logger.error(f"[Aspiration] 放弃目标失败: {e}")
            return False, "操作失败，请稍后重试"

    def get_goal_details(self, user_id: str) -> str:
        """
        获取目标详情

        生成用户当前活跃目标的详细信息展示，包括目标基本信息、进度统计、
        今日状态和操作指南等。

        Args:
            user_id: 用户ID

        Returns:
            str: 格式化的目标详情消息
            - 如果没有活跃目标，返回引导设定目标的消息
            - 如果有活跃目标，返回包含完整信息的详情页面

        显示内容包括：
        1. 目标基本信息（描述、计划天数）
        2. 进度信息（已进行天数、完成百分比、剩余天数）
        3. 统计数据（总打卡、完成率、连续天数、最长连续）
        4. 今日状态（是否已打卡）
        5. 操作指南（可用的命令提示）

        特点：
        - 信息丰富但结构清晰
        - 使用emoji增强视觉效果
        - 提供actionable的操作建议
        """
        try:
            goal = self.get_active_goal(user_id)
            if not goal:
                return """您当前没有活跃的目标

回复「立志」开始设定您的第一个目标吧！🎯"""

            # 获取统计信息
            stats = self.db.get_user_statistics(user_id, goal['id'])

            # 计算进度
            days_since_start = goal['days_since_start']
            planned_days = goal['planned_days']
            progress_percentage = min(100, (days_since_start / planned_days) * 100)

            # 检查今日是否已打卡
            today = date.today()
            today_checkin = self.db.get_checkin_by_date(goal['id'], today)
            today_status = "✅ 已打卡" if today_checkin else "⏰ 待打卡"

            # 计算剩余天数
            remaining_days = max(0, planned_days - days_since_start + 1)

            details_msg = f"""📊 我的目标详情

🎯 目标：{goal['goal_description']}
📅 计划：{planned_days}天挑战
📈 进度：{days_since_start}/{planned_days}天 ({progress_percentage:.1f}%)
⏱️ 剩余：{remaining_days}天

📊 统计数据：
   • 总打卡：{stats['total_checkins']}天
   • 完成率：{stats['completion_rate']}%
   • 连续打卡：{stats['consecutive_days']}天
   • 最长连续：{stats['max_streak']}天

📌 今日状态：{today_status}

💡 操作指南：
   • 回复「打卡」记录进度
   • 回复「完成目标」结束挑战
   • 回复「放弃目标」暂停目标"""

            return details_msg

        except Exception as e:
            logger.error(f"[Aspiration] 获取目标详情失败: {e}")
            return "获取目标信息失败，请稍后重试"

    def get_goal_history(self, user_id: str) -> str:
        """
        获取目标历史

        显示用户当前活跃目标最近7天的打卡历史记录，提供直观的进度回顾。
        这是一个简化版本，只显示当前活跃目标的历史，不包括已完成或放弃的目标。

        Args:
            user_id: 用户ID

        Returns:
            str: 格式化的历史记录消息
            - 如果没有活跃目标，返回引导消息
            - 如果有活跃目标，返回最近7天的详细记录

        显示内容：
        1. 目标名称
        2. 最近7天的逐日记录，包括：
           - 日期和星期
           - 打卡状态（已完成✅、部分完成⚡、未完成❌、未打卡⭕）
           - 用户备注（如果有）
        3. 简要的统计总结

        特点：
        - 按时间倒序显示（最新的在前）
        - 使用emoji直观显示状态
        - 包含用户的个人备注
        - 提供7天的固定时间窗口
        """
        try:
            goal = self.get_active_goal(user_id)
            if not goal:
                return "您还没有设定过目标，回复「立志」开始吧！"

            # 获取最近7天的打卡记录
            import sqlite3
            from datetime import datetime

            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 获取最近7天的打卡记录
            end_date = date.today()
            start_date = end_date - timedelta(days=6)

            cursor.execute('''
                SELECT check_date, status, user_note
                FROM check_in_records
                WHERE goal_id = ? AND check_date >= ? AND check_date <= ?
                ORDER BY check_date DESC
            ''', (goal['id'], start_date, end_date))

            checkins = cursor.fetchall()
            conn.close()

            # 构建历史记录
            history_msg = f"""📅 最近7天打卡记录

目标：{goal['goal_description']}

"""

            # 创建日期范围
            for i in range(7):
                check_date = end_date - timedelta(days=i)
                date_str = check_date.strftime('%m月%d日')
                weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][check_date.weekday()]

                # 查找该日期的打卡记录
                checkin = next((c for c in checkins if c['check_date'] == check_date.strftime('%Y-%m-%d')), None)

                if checkin:
                    status_emoji = {
                        'completed': '✅',
                        'partial': '⚡',
                        'failed': '❌'
                    }.get(checkin['status'], '❓')

                    status_text = {
                        'completed': '已完成',
                        'partial': '部分完成',
                        'failed': '未完成'
                    }.get(checkin['status'], checkin['status'])

                    line = f"{date_str} {weekday} {status_emoji} {status_text}"
                    if checkin['user_note']:
                        line += f" ({checkin['user_note']})"
                else:
                    line = f"{date_str} {weekday} ⭕ 未打卡"

                history_msg += line + "\n"

            # 添加统计信息
            stats = self.db.get_user_statistics(user_id, goal['id'])
            history_msg += f"""
📊 总体统计：
   • 完成率：{stats['completion_rate']}%
   • 连续天数：{stats['consecutive_days']}天
   • 最长连续：{stats['max_streak']}天"""

            return history_msg

        except Exception as e:
            logger.error(f"[Aspiration] 获取目标历史失败: {e}")
            return "获取历史记录失败，请稍后重试"
