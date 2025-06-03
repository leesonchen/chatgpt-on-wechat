"""
提醒调度器模块

该模块负责立志功能的定时提醒系统，包括每日打卡提醒、数据维护等定时任务。
使用schedule库实现定时任务调度，运行在独立的后台线程中。

主要功能：
1. 定时发送打卡提醒消息
2. 检测未打卡用户并发送提醒
3. 定期执行数据维护任务
4. 灵活的提醒时间配置
5. 线程安全的调度管理

设计特点：
- 使用后台线程避免阻塞主程序
- 支持动态启停调度器
- 集成AI生成个性化提醒内容
- 完善的异常处理和日志记录
- 支持多种定时任务类型
"""

"""
提醒调度器模块

该模块负责立志功能的定时提醒系统，包括每日打卡提醒、数据维护等定时任务。
使用schedule库实现定时任务调度，运行在独立的后台线程中。

主要功能：
1. 定时发送打卡提醒消息
2. 检测未打卡用户并发送提醒
3. 定期执行数据维护任务
4. 灵活的提醒时间配置
5. 线程安全的调度管理

设计特点：
- 使用后台线程避免阻塞主程序
- 支持动态启停调度器
- 集成AI生成个性化提醒内容
- 完善的异常处理和日志记录
- 支持多种定时任务类型
"""

import schedule
import time
import threading
import os
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from common.log import logger
from .database_manager import DatabaseManager
from .ai_response_generator import AIResponseGenerator


class ReminderScheduler:
    """
    提醒调度器，负责定时任务的管理和执行

    该类实现了立志功能的定时提醒系统，主要用于发送每日打卡提醒和执行维护任务。
    使用schedule库进行任务调度，运行在独立的后台线程中以避免阻塞主程序。

    主要职责：
    - 管理定时任务的生命周期
    - 检测需要提醒的用户
    - 发送个性化的提醒消息
    - 执行定期维护任务
    - 提供线程安全的启停控制

    Attributes:
        db_manager: 数据库管理器实例
        ai_generator: AI回复生成器实例
        channel: 消息发送通道实例
        reminder_time: 每日提醒时间（HH:MM格式）
        is_running: 调度器运行状态
        scheduler_thread: 后台调度线程
    """

    def __init__(self, db_manager: DatabaseManager, ai_generator: AIResponseGenerator,
                 channel_instance=None, reminder_time: str = "21:00"):
        """
        初始化提醒调度器

        Args:
            db_manager: 数据库管理器实例
            ai_generator: AI回复生成器实例
            channel_instance: 消息发送通道实例，可选
            reminder_time: 每日提醒时间，默认21:00
        """
        self.db_manager = db_manager
        self.ai_generator = ai_generator
        self.channel = channel_instance
        self.reminder_time = reminder_time
        self.is_running = False
        self.scheduler_thread = None

    def start(self):
        """
        启动定时任务

        启动后台调度线程，开始执行定时任务。如果调度器已在运行，
        则记录警告信息并直接返回。

        定时任务包括：
        - 每日指定时间的打卡提醒检查
        - 每日凌晨2点的维护任务

        异常处理：
        - 启动失败时会记录错误日志
        """
        if self.is_running:
            logger.warning("[Aspiration] 提醒调度器已在运行")
            return

        try:
            # 每日指定时间执行提醒检查
            schedule.every().day.at(self.reminder_time).do(self.send_daily_reminders)

            # 每日凌晨2点执行数据备份（如果需要的话）
            schedule.every().day.at("02:00").do(self.daily_maintenance)

            # 启动后台线程
            self.is_running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()

            logger.info(f"[Aspiration] 提醒调度器已启动，提醒时间: {self.reminder_time}")
        except Exception as e:
            logger.error(f"[Aspiration] 启动提醒调度器失败: {e}")

    def stop(self):
        """
        停止定时任务

        停止后台调度线程并清除所有定时任务。
        """
        self.is_running = False
        schedule.clear()
        logger.info("[Aspiration] 提醒调度器已停止")

    def _run_scheduler(self):
        """
        后台运行调度器

        在后台线程中持续运行，每分钟检查一次是否有待执行的任务。
        包含异常处理，确保单个任务失败不会影响整个调度器。
        """
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"[Aspiration] 调度器运行异常: {e}")
                time.sleep(60)

    def send_daily_reminders(self):
        """发送每日提醒"""
        try:
            today = date.today()
            logger.info(f"[Aspiration] 开始执行每日提醒检查: {today}")

            # 查找今日未打卡的活跃目标用户
            missed_users = self.db_manager.get_missed_checkin_users(today)

            if not missed_users:
                logger.info("[Aspiration] 没有需要提醒的用户")
                return

            sent_count = 0
            failed_count = 0

            for user_data in missed_users:
                try:
                    user_id = user_data['user_id']
                    goal_info = user_data['goal_info']

                    # 获取用户统计信息
                    user_stats = self.db_manager.get_user_statistics(user_id, goal_info['id'])

                    # 生成提醒消息
                    if self.ai_generator:
                        reminder_msg = self.ai_generator.generate_reminder(goal_info, user_stats)
                    else:
                        reminder_msg = self._generate_fallback_reminder(goal_info, user_stats)

                    # 发送提醒（这里需要实际的发送逻辑）
                    success = self._send_reminder_message(user_id, reminder_msg)

                    if success:
                        # 记录提醒日志
                        self.db_manager.log_reminder_sent(user_id, goal_info['id'], today)
                        sent_count += 1
                        logger.info(f"[Aspiration] 已向用户 {user_id} 发送提醒")
                    else:
                        failed_count += 1
                        logger.warning(f"[Aspiration] 向用户 {user_id} 发送提醒失败")

                    # 添加延迟，避免发送过快
                    time.sleep(1)

                except Exception as e:
                    logger.error(f"[Aspiration] 处理用户提醒时出错: {e}")
                    failed_count += 1

            logger.info(f"[Aspiration] 每日提醒完成，发送成功: {sent_count}, 失败: {failed_count}")

        except Exception as e:
            logger.error(f"[Aspiration] 每日提醒执行失败: {e}")

    def _send_reminder_message(self, user_id: str, message: str) -> bool:
        """发送提醒消息"""
        try:
            # 注意：这里需要根据实际的微信公众号通道来实现
            # 由于个人订阅号无法主动推送，这里先记录日志
            # 如果是认证服务号，可以使用客服接口主动推送

            if self.channel and hasattr(self.channel, 'send_active_message'):
                # 如果通道支持主动推送
                return self.channel.send_active_message(user_id, message)
            else:
                # 对于个人订阅号，无法主动推送，只能在用户下次交互时提醒
                logger.info(f"[Aspiration] 记录提醒消息（无法主动推送）: 用户 {user_id}")                # 这里可以将提醒消息存储起来，在用户下次交互时显示
                self._store_pending_reminder(user_id, message)
                return True

        except Exception as e:
            logger.error(f"[Aspiration] 发送提醒消息失败: {e}")
            return False

    def _store_pending_reminder(self, user_id: str, message: str):
        """存储待发送的提醒消息（用于个人订阅号）"""
        try:
            # 将提醒消息存储到数据库或文件中，用户下次交互时显示
            # 这里简单实现，实际可以扩展
            pending_file = f"data/pending_reminders.txt"
            os.makedirs(os.path.dirname(pending_file), exist_ok=True)

            with open(pending_file, 'a', encoding='utf-8') as f:
                f.write(f"{user_id}|{datetime.now().isoformat()}|{message}\n")

        except Exception as e:
            logger.error(f"[Aspiration] 存储待发送提醒失败: {e}")

    def get_pending_reminder(self, user_id: str) -> Optional[str]:
        """获取用户的待发送提醒"""
        try:
            pending_file = f"data/pending_reminders.txt"
            if not os.path.exists(pending_file):
                return None

            lines = []
            found_reminder = None

            with open(pending_file, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('|', 2)
                    if len(parts) == 3 and parts[0] == user_id:
                        if not found_reminder:  # 只取最新的一条
                            found_reminder = parts[2]
                    else:
                        lines.append(line)

            # 如果找到提醒，从文件中移除已读的提醒
            if found_reminder:
                with open(pending_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

            return found_reminder

        except Exception as e:
            logger.error(f"[Aspiration] 获取待发送提醒失败: {e}")
            return None

    def _generate_fallback_reminder(self, goal_info: Dict[str, Any], user_stats: Dict[str, Any]) -> str:
        """生成备用提醒消息"""
        consecutive_days = user_stats.get('consecutive_days', 0)
        goal_desc = goal_info.get('goal_description', '您的目标')

        if consecutive_days > 0:
            return f"""🌟 立志提醒

亲爱的朋友，今天的「{goal_desc}」还没有打卡哦～

您已经坚持了{consecutive_days}天，不要让努力白费！
快来分享今天的执行情况吧：

回复「打卡」记录今天的进展
回复「1」表示已完成
回复「2」表示部分完成
回复「3」表示未完成

每一天的坚持都值得鼓励！💪"""
        else:
            return f"""🌟 立志提醒

亲爱的朋友，今天的「{goal_desc}」还没有打卡哦～

回复「打卡」记录今天的进展，开始您的坚持之旅！

回复「1」表示已完成
回复「2」表示部分完成
回复「3」表示未完成

相信自己，您可以做到的！💪✨"""

    def daily_maintenance(self):
        """每日维护任务"""
        try:
            logger.info("[Aspiration] 开始执行每日维护任务")

            # 清理过期数据（可选）
            # self.db_manager.cleanup_old_data(days=365)

            # 这里可以添加其他维护任务
            # 比如数据备份、统计报告等

            logger.info("[Aspiration] 每日维护任务完成")

        except Exception as e:
            logger.error(f"[Aspiration] 每日维护任务失败: {e}")

    def test_reminder(self, user_id: str) -> str:
        """测试提醒功能（仅用于调试）"""
        try:
            goal = self.db_manager.get_active_goal(user_id)
            if not goal:
                return "您当前没有活跃目标，无法测试提醒"

            user_stats = self.db_manager.get_user_statistics(user_id, goal['id'])

            if self.ai_generator:
                reminder_msg = self.ai_generator.generate_reminder(goal, user_stats)
            else:
                reminder_msg = self._generate_fallback_reminder(goal, user_stats)

            return f"测试提醒消息：\n\n{reminder_msg}"

        except Exception as e:
            logger.error(f"[Aspiration] 测试提醒失败: {e}")
            return "测试提醒失败"
