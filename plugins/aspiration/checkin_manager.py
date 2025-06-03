"""
打卡管理器模块

该模块负责处理用户的打卡相关操作，包括记录打卡、解析打卡消息、
生成打卡指南等功能。它与数据库管理器和AI回复生成器协作，
提供完整的打卡体验。

主要功能：
1. 记录和验证用户打卡
2. 解析自然语言打卡消息
3. 计算连续打卡天数
4. 生成个性化的打卡回复
5. 提供打卡指南和状态查询

设计特点：
- 支持多种打卡状态（完成/部分完成/未完成）
- 自动解析用户备注和状态
- 防重复打卡机制
- AI增强的个性化回复
"""
from typing import Dict, Any, Tuple, Optional
from datetime import date
from common.log import logger
from .database_manager import DatabaseManager
from .ai_response_generator import AIResponseGenerator


class CheckInManager:
    """
    打卡管理器

    负责处理用户的所有打卡相关操作。该类作为打卡功能的核心控制器，
    协调数据库操作、AI回复生成和用户交互。

    主要职责：
    - 验证打卡的有效性
    - 解析用户的打卡消息
    - 记录打卡数据到数据库
    - 生成个性化的回复内容
    - 提供打卡指导和帮助

    Attributes:
        db: 数据库管理器实例
        ai_generator: AI回复生成器实例
    """

    def __init__(self, db_manager: DatabaseManager, ai_generator: AIResponseGenerator):
        """
        初始化打卡管理器

        Args:
            db_manager: 数据库管理器实例，用于数据持久化
            ai_generator: AI回复生成器实例，用于生成智能回复
        """
        self.db = db_manager
        self.ai_generator = ai_generator

    def record_checkin(self, user_id: str, status: str, note: Optional[str] = None) -> Tuple[bool, str]:
        """
        记录打卡

        这是打卡功能的核心方法，负责验证打卡有效性、记录数据、
        计算统计信息并生成个性化回复。

        Args:
            user_id: 用户ID
            status: 打卡状态，必须为 'completed', 'partial', 'failed' 之一
            note: 用户备注，可选

        Returns:
            Tuple[bool, str]: (是否成功, 回复消息)

        处理流程：
        1. 验证打卡状态的有效性
        2. 检查用户是否有活跃目标
        3. 检查今日是否已打卡
        4. 计算连续打卡天数
        5. 记录打卡数据
        6. 生成AI回复
        7. 构建完整的回复消息
        """
        try:
            # 验证打卡状态
            valid_statuses = ['completed', 'partial', 'failed']
            if status not in valid_statuses:
                return False, f"无效的打卡状态，请选择：已完成、部分完成、未完成"

            # 获取活跃目标
            goal = self.db.get_active_goal(user_id)
            if not goal:
                return False, """您还没有设定目标，请先设定目标再打卡

回复「立志」开始设定您的第一个目标吧！🎯"""

            # 检查今日是否已打卡
            today = date.today()
            existing_checkin = self.db.get_checkin_by_date(goal['id'], today)
            if existing_checkin:
                return False, f"""今日已经打卡过了哦！

今日状态：{self._get_status_text(existing_checkin['status'])}
明天记得继续打卡！💪

回复「我的目标」查看详细信息"""

            # 计算连续天数（只有完成状态才增加连续天数）
            consecutive_days = self.db.calculate_consecutive_days(goal['id'])
            if status == 'completed':
                consecutive_days += 1
            else:
                consecutive_days = 0

            # 记录打卡
            checkin_id = self.db.create_checkin(
                goal_id=goal['id'],
                user_id=user_id,
                check_date=today,
                status=status,
                note=note,
                consecutive_days=consecutive_days
            )

            # 获取用户统计信息
            user_stats = self.db.get_user_statistics(user_id, goal['id'])

            # 生成AI回复
            checkin_info = {
                'status': status,
                'note': note
            }

            ai_response = self.ai_generator.generate_encouragement(goal, checkin_info, user_stats)

            # 更新AI回复到数据库
            self.db.update_checkin_ai_response(checkin_id, ai_response)

            # 构建回复消息
            status_emoji = self._get_status_emoji(status)
            status_text = self._get_status_text(status)

            response_msg = f"""{status_emoji} 打卡成功！

📝 目标：{goal['goal_description']}
📅 日期：{today.strftime('%Y年%m月%d日')}
✅ 状态：{status_text}"""

            if note:
                response_msg += f"\n💭 备注：{note}"

            response_msg += f"""

📊 您的进展：
   • 连续打卡：{user_stats['consecutive_days']}天
   • 总完成率：{user_stats['completion_rate']}%
   • 总打卡：{user_stats['total_checkins']}天

🤖 AI鼓励：
{ai_response}

明天记得继续哦！回复「打卡」继续记录 💪"""

            return True, response_msg

        except Exception as e:
            logger.error(f"[Aspiration] 记录打卡失败: {e}")
            return False, "打卡记录失败，请稍后重试"

    def quick_checkin_completed(self, user_id: str) -> Tuple[bool, str]:
        """
        快速打卡 - 已完成

        提供快捷的完成状态打卡功能。

        Args:
            user_id: 用户ID

        Returns:
            Tuple[bool, str]: 打卡结果
        """
        return self.record_checkin(user_id, 'completed')

    def quick_checkin_partial(self, user_id: str, note: Optional[str] = None) -> Tuple[bool, str]:
        """
        快速打卡 - 部分完成

        提供快捷的部分完成状态打卡功能。

        Args:
            user_id: 用户ID
            note: 用户备注，可选

        Returns:
            Tuple[bool, str]: 打卡结果
        """
        return self.record_checkin(user_id, 'partial', note)

    def quick_checkin_failed(self, user_id: str, note: Optional[str] = None) -> Tuple[bool, str]:
        """
        快速打卡 - 未完成

        提供快捷的未完成状态打卡功能。

        Args:
            user_id: 用户ID
            note: 用户备注，可选

        Returns:
            Tuple[bool, str]: 打卡结果
        """
        return self.record_checkin(user_id, 'failed', note)

    def get_checkin_guide(self, user_id: str) -> str:
        """
        获取打卡指南

        根据用户的状态生成相应的打卡指导信息。检查用户是否有活跃目标，
        是否今日已打卡，并提供相应的操作指导。

        Args:
            user_id: 用户ID

        Returns:
            str: 打卡指南消息
        """
        goal = self.db.get_active_goal(user_id)
        if not goal:
            return """您还没有设定目标

回复「立志」开始设定您的第一个目标吧！🎯"""

        # 检查今日是否已打卡
        today = date.today()
        existing_checkin = self.db.get_checkin_by_date(goal['id'], today)

        if existing_checkin:
            status_text = self._get_status_text(existing_checkin['status'])
            return f"""今日已打卡：{status_text}

明天记得继续哦！💪
回复「我的目标」查看详细统计"""

        guide_msg = f"""📝 打卡指南

🎯 今日目标：{goal['goal_description']}

请选择今日完成情况：

1️⃣ 已完成 - 回复「1」或「已完成」
2️⃣ 部分完成 - 回复「2」或「部分完成」
3️⃣ 未完成 - 回复「3」或「未完成」

💡 小贴士：
   • 可以添加备注说明具体情况
   • 例如：「1 今天跑了5公里」
   • 或者：「2 只完成了一半，明天加油」"""

        return guide_msg

    def _get_status_emoji(self, status: str) -> str:
        """
        获取状态对应的emoji

        Args:
            status: 打卡状态

        Returns:
            str: 对应的emoji符号
        """
        emoji_map = {
            'completed': '✅',
            'partial': '⚡',
            'failed': '❌'
        }
        return emoji_map.get(status, '❓')

    def _get_status_text(self, status: str) -> str:
        """
        获取状态对应的中文文本

        Args:
            status: 打卡状态

        Returns:
            str: 对应的中文描述
        """
        text_map = {
            'completed': '已完成',
            'partial': '部分完成',
            'failed': '未完成'
        }
        return text_map.get(status, status)

    def parse_checkin_message(self, message: str) -> Tuple[str, str]:
        """
        解析打卡消息，返回状态和备注

        智能解析用户的自然语言打卡消息，提取出打卡状态和用户备注。
        支持多种表达方式和中英文关键词。

        Args:
            message: 用户输入的打卡消息

        Returns:
            Tuple[str, str]: (状态, 备注) 如果无法识别则状态为None

        解析逻辑：
        1. 优先处理数字选项（1、2、3）
        2. 匹配中文关键词（已完成、部分完成、未完成）
        3. 匹配英文关键词（done、partial、failed）
        4. 提取关键词外的其他内容作为备注
        """
        message = message.strip()

        # 处理数字选项
        if message.startswith('1'):
            note = message[1:].strip() if len(message) > 1 else ""
            return 'completed', note
        elif message.startswith('2'):
            note = message[1:].strip() if len(message) > 1 else ""
            return 'partial', note
        elif message.startswith('3'):
            note = message[1:].strip() if len(message) > 1 else ""
            return 'failed', note

        # 处理文字描述
        message_lower = message.lower()

        # 匹配完成状态的关键词
        if any(keyword in message_lower for keyword in ['已完成', '完成了', '完成', 'done', '已做', '做完']):
            # 提取备注（移除关键词部分）
            for keyword in ['已完成', '完成了', '完成', 'done', '已做', '做完']:
                if keyword in message:
                    note = message.replace(keyword, '').strip()
                    return 'completed', note if note else ""

        # 匹配部分完成状态的关键词
        if any(keyword in message_lower for keyword in ['部分完成', '部分', '一半', 'partial']):
            for keyword in ['部分完成', '部分', '一半', 'partial']:
                if keyword in message:
                    note = message.replace(keyword, '').strip()
                    return 'partial', note if note else ""

        # 匹配未完成状态的关键词
        if any(keyword in message_lower for keyword in ['未完成', '没完成', '未做', '没做', 'failed', 'miss']):
            for keyword in ['未完成', '没完成', '未做', '没做', 'failed', 'miss']:
                if keyword in message:
                    note = message.replace(keyword, '').strip()
                    return 'failed', note if note else ""        # 如果无法识别，返回None
        return None, None
