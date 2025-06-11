"""提醒调度器模块

该模块负责定时器的调度和提醒发送，使用独立的后台线程实现定时任务。
它集成了AI生成个性化提醒内容，并提供完整的异常处理和线程安全机制。

主要功能：
1. 定时检查到期的提醒
2. 发送个性化提醒消息
3. 管理提醒调度的生命周期
4. 处理提醒发送的异常情况
5. 维护调度器的状态

特性：
- 使用独立后台线程
- 支持动态启停
- 集成AI生成提醒内容
- 完整的异常处理
- 线程安全设计
"""
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from common.log import logger


class ReminderScheduler:
    """
    提醒调度器，负责定时检查和发送提醒

    该类实现了一个独立的后台调度器，定期检查到期的定时器并发送提醒。
    它使用线程安全的设计，支持动态启停，并集成AI生成个性化提醒内容。

    主要职责：
    - 管理调度器的生命周期
    - 定期检查到期的定时器
    - 发送个性化提醒消息
    - 处理提醒发送的异常
    - 维护调度器状态

    Attributes:
        db_manager: 数据库管理器实例
        ai_generator: AI回复生成器实例
        message_sender: 消息发送函数
        check_interval: 检查间隔（秒）
        is_running: 调度器运行状态
        scheduler_thread: 调度器线程
        lock: 线程锁
    """

    def __init__(self, db_manager, ai_generator=None, message_sender: Callable = None, check_interval: int = 60):
        """
        初始化提醒调度器

        Args:
            db_manager: 数据库管理器实例
            ai_generator: AI回复生成器实例（可选）
            message_sender: 消息发送函数
            check_interval: 检查间隔，默认60秒
        """
        self.db_manager = db_manager
        self.ai_generator = ai_generator
        self.message_sender = message_sender
        self.check_interval = check_interval
        
        self.is_running = False
        self.scheduler_thread = None
        self.lock = threading.Lock()
        
        logger.info("[Timer] ReminderScheduler initialized")

    def start(self):
        """
        启动提醒调度器

        创建并启动后台线程来执行定时检查任务。
        如果调度器已经在运行，则不会重复启动。
        """
        with self.lock:
            if self.is_running:
                logger.warning("[Timer] ReminderScheduler is already running")
                return

            self.is_running = True
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop,
                name="TimerReminderScheduler",
                daemon=True
            )
            self.scheduler_thread.start()
            logger.info("[Timer] ReminderScheduler started")

    def stop(self):
        """
        停止提醒调度器

        优雅地停止后台线程，等待当前任务完成。
        """
        with self.lock:
            if not self.is_running:
                logger.warning("[Timer] ReminderScheduler is not running")
                return

            self.is_running = False
            logger.info("[Timer] ReminderScheduler stopping...")

        # 等待线程结束
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=10)
            if self.scheduler_thread.is_alive():
                logger.warning("[Timer] ReminderScheduler thread did not stop gracefully")
            else:
                logger.info("[Timer] ReminderScheduler stopped")

    def is_active(self) -> bool:
        """
        检查调度器是否处于活跃状态

        Returns:
            bool: 调度器是否正在运行
        """
        with self.lock:
            return self.is_running and self.scheduler_thread and self.scheduler_thread.is_alive()

    def _scheduler_loop(self):
        """
        调度器主循环

        在后台线程中运行，定期检查到期的定时器并发送提醒。
        """
        logger.info("[Timer] ReminderScheduler loop started")
        
        while self.is_running:
            try:
                # 检查并处理到期的提醒
                self._check_and_send_reminders()
                
                # 执行维护任务
                self._perform_maintenance()
                
                # 等待下次检查
                self._wait_for_next_check()
                
            except Exception as e:
                logger.error(f"[Timer] Error in scheduler loop: {e}")
                # 发生错误时等待一段时间再继续
                time.sleep(min(self.check_interval, 300))  # 最多等待5分钟

        logger.info("[Timer] ReminderScheduler loop ended")

    def _check_and_send_reminders(self):
        """
        检查并发送到期的提醒
        """
        try:
            # 获取到期的定时器
            due_timers = self.db_manager.get_due_timers()
            
            if not due_timers:
                return

            logger.info(f"[Timer] Found {len(due_timers)} due timers")

            for timer in due_timers:
                try:
                    self._process_due_timer(timer)
                except Exception as e:
                    logger.error(f"[Timer] Error processing timer {timer.get('id')}: {e}")
                    # 记录错误但继续处理其他定时器
                    self.db_manager.log_reminder(
                        timer.get('user_id', ''),
                        timer.get('id', 0),
                        f"Error processing timer: {str(e)}",
                        status='error',
                        error_message=str(e)
                    )

        except Exception as e:
            logger.error(f"[Timer] Error checking due reminders: {e}")

    def _process_due_timer(self, timer: Dict[str, Any]):
        """
        处理单个到期的定时器

        Args:
            timer: 定时器信息
        """
        timer_id = timer['id']
        user_id = timer['user_id']
        
        try:
            # 创建提醒记录
            remind_time = datetime.fromisoformat(timer['next_remind_time'] or timer['remind_time'])
            record_id = self.db_manager.create_reminder_record(timer_id, user_id, remind_time)
            
            # 生成提醒消息
            reminder_message = self._generate_reminder_message(timer, user_id)
            
            # 发送提醒
            success = self._send_reminder_message(user_id, reminder_message)
            
            if success:
                # 记录成功日志
                self.db_manager.log_reminder(
                    user_id, timer_id, reminder_message, status='sent'
                )
                
                # 更新定时器的下次提醒时间
                self.db_manager.update_timer_next_remind_time(timer_id)
                
                logger.info(f"[Timer] Reminder sent successfully for timer {timer_id}")
            else:
                # 记录失败日志
                self.db_manager.log_reminder(
                    user_id, timer_id, reminder_message, 
                    status='failed', error_message='Message sending failed'
                )
                logger.warning(f"[Timer] Failed to send reminder for timer {timer_id}")

        except Exception as e:
            logger.error(f"[Timer] Error processing due timer {timer_id}: {e}")
            # 记录错误
            self.db_manager.log_reminder(
                user_id, timer_id, f"Processing error: {str(e)}",
                status='error', error_message=str(e)
            )

    def _generate_reminder_message(self, timer: Dict[str, Any], user_id: str) -> str:
        """
        生成提醒消息

        Args:
            timer: 定时器信息
            user_id: 用户ID

        Returns:
            str: 提醒消息
        """
        try:
            if self.ai_generator:
                # 使用AI生成个性化提醒
                return self.ai_generator.generate_reminder_message(timer, user_id)
            else:
                # 使用默认模板
                description = timer.get('description', '未知任务')
                return f"⏰ 提醒时间到了！请记得：{description}\n\n您可以回复：\n• 完成 - 已完成任务\n• 延迟X分钟 - 稍后提醒\n• 取消 - 取消提醒"

        except Exception as e:
            logger.error(f"[Timer] Error generating reminder message: {e}")
            # 回退到简单消息
            description = timer.get('description', '任务')
            return f"⏰ 提醒：{description}"

    def _send_reminder_message(self, user_id: str, message: str) -> bool:
        """
        发送提醒消息

        Args:
            user_id: 用户ID
            message: 消息内容

        Returns:
            bool: 是否发送成功
        """
        try:
            if self.message_sender:
                # 使用提供的消息发送函数
                result = self.message_sender(user_id, message)
                return bool(result)
            else:
                # 没有消息发送函数，记录日志
                logger.warning(f"[Timer] No message sender configured, would send to {user_id}: {message}")
                return False

        except Exception as e:
            logger.error(f"[Timer] Error sending reminder message: {e}")
            return False

    def _perform_maintenance(self):
        """
        执行维护任务
        """
        try:
            # 每小时执行一次维护任务
            current_time = datetime.now()
            if current_time.minute == 0:  # 整点时执行
                # 清理旧数据（保留30天）
                self.db_manager.cleanup_old_data(days_to_keep=30)
                logger.info("[Timer] Maintenance tasks completed")

        except Exception as e:
            logger.error(f"[Timer] Error performing maintenance: {e}")

    def _wait_for_next_check(self):
        """
        等待下次检查
        
        使用可中断的等待，以便能够快速响应停止信号。
        """
        # 将等待时间分割为小段，以便能够快速响应停止信号
        wait_segments = max(1, self.check_interval // 10)
        segment_time = self.check_interval / wait_segments
        
        for _ in range(wait_segments):
            if not self.is_running:
                break
            time.sleep(segment_time)

    def force_check(self):
        """
        强制执行一次检查
        
        用于测试或手动触发检查。
        """
        try:
            logger.info("[Timer] Force checking reminders")
            self._check_and_send_reminders()
        except Exception as e:
            logger.error(f"[Timer] Error in force check: {e}")

    def get_pending_reminder(self, user_id: str) -> Optional[str]:
        """
        获取待发送的提醒消息（用于无法主动推送的场景）
        这里我们返回最近一个待处理的记录，以兼容被动提醒模式
        """
        try:
            pending = self.db_manager.get_pending_reminder(user_id)
            if pending:
                return self._generate_reminder_message(pending, user_id)
            return None
        except Exception as e:
            logger.error(f"[Timer] Error getting pending reminder: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """
        获取调度器状态信息

        Returns:
            Dict[str, Any]: 状态信息
        """
        with self.lock:
            return {
                'is_running': self.is_running,
                'is_active': self.is_active(),
                'check_interval': self.check_interval,
                'thread_alive': self.scheduler_thread.is_alive() if self.scheduler_thread else False,
                'thread_name': self.scheduler_thread.name if self.scheduler_thread else None
            }

    def update_check_interval(self, new_interval: int):
        """
        更新检查间隔

        Args:
            new_interval: 新的检查间隔（秒）
        """
        if new_interval < 10:
            logger.warning("[Timer] Check interval too small, minimum is 10 seconds")
            new_interval = 10
        elif new_interval > 3600:
            logger.warning("[Timer] Check interval too large, maximum is 3600 seconds")
            new_interval = 3600

        with self.lock:
            old_interval = self.check_interval
            self.check_interval = new_interval
            logger.info(f"[Timer] Check interval updated from {old_interval}s to {new_interval}s")

    def set_message_sender(self, message_sender: Callable):
        """
        设置消息发送函数

        Args:
            message_sender: 消息发送函数
        """
        self.message_sender = message_sender
        logger.info("[Timer] Message sender updated")

    def restart(self):
        """
        重启调度器
        
        先停止当前调度器，然后重新启动。
        """
        logger.info("[Timer] Restarting ReminderScheduler")
        self.stop()
        time.sleep(1)  # 等待一秒确保完全停止
        self.start()

    def __del__(self):
        """
        析构函数，确保调度器被正确停止
        """
        try:
            if self.is_running:
                self.stop()
        except Exception as e:
            logger.error(f"[Timer] Error stopping scheduler in destructor: {e}")