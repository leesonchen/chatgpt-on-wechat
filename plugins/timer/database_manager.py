"""数据库管理器模块

该模块负责定时器功能的所有数据库操作，包括表结构初始化、数据的增删改查、
统计计算等。使用SQLite作为后端数据库，提供完整的数据持久化服务。

主要功能：
1. 数据库表结构初始化和维护
2. 定时器的CRUD操作
3. 提醒记录的管理
4. 提醒日志的记录
5. 统计数据的计算
6. 数据清理和维护

数据库设计：
- user_timers: 用户定时器表，存储定时器信息
- reminder_records: 提醒记录表，存储提醒执行历史
- reminder_logs: 提醒日志表，记录提醒发送历史

特性：
- 支持事务处理
- 建立适当的索引优化查询性能
- 提供连接池管理
- 支持数据备份和清理
"""
import sqlite3
import os
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import json
from common.log import logger


class DatabaseManager:
    """
    数据库管理器，负责所有数据库操作

    该类封装了定时器功能的所有数据库操作，提供高级的数据访问接口。
    使用SQLite作为后端存储，支持表结构自动初始化和数据迁移。

    主要职责：
    - 管理数据库连接和事务
    - 提供定时器和提醒的CRUD操作
    - 计算各种统计数据
    - 处理数据备份和清理
    - 维护数据完整性和一致性

    Attributes:
        db_path: 数据库文件路径
    """

    def __init__(self, db_path: str = "data/timer.db"):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径，默认为 "data/timer.db"
        """
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """
        初始化数据库表结构

        创建所有必要的表和索引。如果表已存在则不会重复创建。
        该方法是幂等的，可以安全地多次调用。

        创建的表：
        1. user_timers: 用户定时器表
        2. reminder_records: 提醒记录表
        3. reminder_logs: 提醒日志表

        同时创建必要的索引以提高查询性能。
        """
        try:
            # 确保数据库目录存在
            db_dir = os.path.dirname(self.db_path)
            if db_dir:  # 只有当目录不为空时才创建
                os.makedirs(db_dir, exist_ok=True)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 创建用户定时器表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_timers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    remind_time DATETIME NOT NULL,
                    repeat_type TEXT DEFAULT 'once',
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    next_remind_time DATETIME,
                    ai_analysis TEXT
                )
            ''')

            # 创建提醒记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminder_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timer_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    remind_time DATETIME NOT NULL,
                    status TEXT DEFAULT 'pending',
                    response TEXT,
                    delay_minutes INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (timer_id) REFERENCES user_timers (id)
                )
            ''')

            # 创建提醒日志表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminder_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    timer_id INTEGER,
                    message TEXT NOT NULL,
                    send_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'sent',
                    error_message TEXT,
                    FOREIGN KEY (timer_id) REFERENCES user_timers (id)
                )
            ''')

            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_timers_user_id ON user_timers (user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_timers_status ON user_timers (status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_timers_remind_time ON user_timers (remind_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminder_records_user_id ON reminder_records (user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminder_records_status ON reminder_records (status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminder_logs_user_id ON reminder_logs (user_id)')

            conn.commit()
            conn.close()
            logger.info("[Timer] Database initialized successfully")

        except Exception as e:
            logger.error(f"[Timer] Error initializing database: {e}")
            raise

    def create_timer(self, user_id: str, description: str, remind_time: datetime,
                    repeat_type: str = 'once', ai_analysis: str = None) -> int:
        """
        创建新的定时器

        Args:
            user_id: 用户ID
            description: 提醒描述
            remind_time: 提醒时间
            repeat_type: 重复类型 ('once', 'daily', 'weekly', 'monthly')
            ai_analysis: AI分析结果

        Returns:
            int: 新创建的定时器ID

        Raises:
            Exception: 数据库操作失败时抛出异常
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 计算下次提醒时间
            next_remind_time = self._calculate_next_remind_time(remind_time, repeat_type)

            cursor.execute('''
                INSERT INTO user_timers 
                (user_id, description, remind_time, repeat_type, next_remind_time, ai_analysis)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, description, remind_time, repeat_type, next_remind_time, ai_analysis))

            timer_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"[Timer] Created timer {timer_id} for user {user_id}")
            return timer_id

        except Exception as e:
            logger.error(f"[Timer] Error creating timer: {e}")
            raise

    def get_active_timers(self, user_id: str = None) -> List[Dict[str, Any]]:
        """
        获取活跃的定时器列表

        Args:
            user_id: 用户ID，如果为None则获取所有用户的定时器

        Returns:
            List[Dict[str, Any]]: 定时器列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if user_id:
                cursor.execute('''
                    SELECT * FROM user_timers 
                    WHERE user_id = ? AND status = 'active'
                    ORDER BY next_remind_time ASC
                ''', (user_id,))
            else:
                cursor.execute('''
                    SELECT * FROM user_timers 
                    WHERE status = 'active'
                    ORDER BY next_remind_time ASC
                ''')

            timers = [dict(row) for row in cursor.fetchall()]
            conn.close()

            return timers

        except Exception as e:
            logger.error(f"[Timer] Error getting active timers: {e}")
            return []

    def get_due_timers(self, current_time: datetime = None) -> List[Dict[str, Any]]:
        """
        获取到期需要提醒的定时器

        Args:
            current_time: 当前时间，如果为None则使用系统当前时间

        Returns:
            List[Dict[str, Any]]: 到期的定时器列表
        """
        if current_time is None:
            current_time = datetime.now()

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM user_timers 
                WHERE status = 'active' 
                AND next_remind_time <= ?
                ORDER BY next_remind_time ASC
            ''', (current_time,))

            timers = [dict(row) for row in cursor.fetchall()]
            conn.close()

            return timers

        except Exception as e:
            logger.error(f"[Timer] Error getting due timers: {e}")
            return []

    def update_timer_next_remind_time(self, timer_id: int, next_remind_time: datetime = None):
        """
        更新定时器的下次提醒时间

        Args:
            timer_id: 定时器ID
            next_remind_time: 下次提醒时间，如果为None则根据重复类型计算
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if next_remind_time is None:
                # 获取定时器信息以计算下次提醒时间
                cursor.execute('SELECT remind_time, repeat_type FROM user_timers WHERE id = ?', (timer_id,))
                result = cursor.fetchone()
                if result:
                    remind_time, repeat_type = result
                    next_remind_time = self._calculate_next_remind_time(
                        datetime.fromisoformat(remind_time), repeat_type
                    )

            if next_remind_time:
                cursor.execute('''
                    UPDATE user_timers 
                    SET next_remind_time = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (next_remind_time, timer_id))
            else:
                # 如果是一次性提醒，标记为完成
                cursor.execute('''
                    UPDATE user_timers 
                    SET status = 'completed', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (timer_id,))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"[Timer] Error updating timer next remind time: {e}")

    def create_reminder_record(self, timer_id: int, user_id: str, remind_time: datetime) -> int:
        """
        创建提醒记录

        Args:
            timer_id: 定时器ID
            user_id: 用户ID
            remind_time: 提醒时间

        Returns:
            int: 新创建的提醒记录ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO reminder_records 
                (timer_id, user_id, remind_time)
                VALUES (?, ?, ?)
            ''', (timer_id, user_id, remind_time))

            record_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return record_id

        except Exception as e:
            logger.error(f"[Timer] Error creating reminder record: {e}")
            raise

    def update_reminder_record_status(self, record_id: int, status: str, response: str = None) -> bool:
        """
        更新提醒记录状态

        Args:
            record_id: 提醒记录ID
            status: 新状态 ('completed', 'delayed', 'ignored')
            response: 用户回复内容
            
        Returns:
            bool: 操作是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if status == 'completed':
                cursor.execute('''
                    UPDATE reminder_records 
                    SET status = ?, response = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, response, record_id))
            else:
                cursor.execute('''
                    UPDATE reminder_records 
                    SET status = ?, response = ?
                    WHERE id = ?
                ''', (status, response, record_id))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"[Timer] Error updating reminder record status: {e}")
            return False

    def get_pending_reminder(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户的待处理提醒

        Args:
            user_id: 用户ID

        Returns:
            Optional[Dict[str, Any]]: 待处理的提醒记录，如果没有则返回None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT rr.*, ut.description, ut.repeat_type
                FROM reminder_records rr
                JOIN user_timers ut ON rr.timer_id = ut.id
                WHERE rr.user_id = ? AND rr.status = 'pending'
                ORDER BY rr.remind_time DESC
                LIMIT 1
            ''', (user_id,))

            result = cursor.fetchone()
            conn.close()

            return dict(result) if result else None

        except Exception as e:
            logger.error(f"[Timer] Error getting pending reminder: {e}")
            return None

    def cancel_timer(self, timer_id: int, user_id: str) -> bool:
        """
        取消定时器

        Args:
            timer_id: 定时器ID
            user_id: 用户ID（用于权限验证）

        Returns:
            bool: 是否成功取消
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE user_timers 
                SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            ''', (timer_id, user_id))

            success = cursor.rowcount > 0
            conn.commit()
            conn.close()

            return success

        except Exception as e:
            logger.error(f"[Timer] Error cancelling timer: {e}")
            return False

    def get_latest_timer(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户最新的定时器

        Args:
            user_id: 用户ID

        Returns:
            Optional[Dict[str, Any]]: 最新的定时器，如果没有则返回None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM user_timers 
                WHERE user_id = ? AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
            ''', (user_id,))

            result = cursor.fetchone()
            conn.close()

            return dict(result) if result else None

        except Exception as e:
            logger.error(f"[Timer] Error getting latest timer: {e}")
            return None

    def log_reminder(self, user_id: str, timer_id: int, message: str, status: str = 'sent', error_message: str = None):
        """
        记录提醒日志

        Args:
            user_id: 用户ID
            timer_id: 定时器ID
            message: 提醒消息
            status: 发送状态
            error_message: 错误消息（如果有）
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO reminder_logs 
                (user_id, timer_id, message, status, error_message)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, timer_id, message, status, error_message))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"[Timer] Error logging reminder: {e}")

    def get_user_timer_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户定时器统计信息

        Args:
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 获取各种统计数据
            stats = {}

            # 活跃定时器数量
            cursor.execute('SELECT COUNT(*) FROM user_timers WHERE user_id = ? AND status = "active"', (user_id,))
            stats['active_timers'] = cursor.fetchone()[0]

            # 总定时器数量
            cursor.execute('SELECT COUNT(*) FROM user_timers WHERE user_id = ?', (user_id,))
            stats['total_timers'] = cursor.fetchone()[0]

            # 已完成提醒数量
            cursor.execute('SELECT COUNT(*) FROM reminder_records WHERE user_id = ? AND status = "completed"', (user_id,))
            stats['completed_reminders'] = cursor.fetchone()[0]

            # 总提醒数量
            cursor.execute('SELECT COUNT(*) FROM reminder_records WHERE user_id = ?', (user_id,))
            stats['total_reminders'] = cursor.fetchone()[0]

            # 计算完成率
            if stats['total_reminders'] > 0:
                stats['completion_rate'] = round((stats['completed_reminders'] / stats['total_reminders']) * 100, 1)
            else:
                stats['completion_rate'] = 0.0

            conn.close()
            return stats

        except Exception as e:
            logger.error(f"[Timer] Error getting user timer stats: {e}")
            return {
                'active_timers': 0,
                'total_timers': 0,
                'completed_reminders': 0,
                'total_reminders': 0,
                'completion_rate': 0.0
            }

    def _calculate_next_remind_time(self, remind_time: datetime, repeat_type: str) -> Optional[datetime]:
        """
        计算下次提醒时间

        Args:
            remind_time: 当前提醒时间
            repeat_type: 重复类型

        Returns:
            Optional[datetime]: 下次提醒时间，如果是一次性提醒则返回None
        """
        if repeat_type == 'once':
            return None
        elif repeat_type == 'daily':
            return remind_time + timedelta(days=1)
        elif repeat_type == 'weekly':
            return remind_time + timedelta(weeks=1)
        elif repeat_type == 'monthly':
            # 简单实现：加30天
            return remind_time + timedelta(days=30)
        else:
            return None

    def cleanup_old_data(self, days_to_keep: int = 30):
        """
        清理旧数据

        Args:
            days_to_keep: 保留的天数，默认30天
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            # 清理已完成的定时器
            cursor.execute('''
                DELETE FROM user_timers 
                WHERE status IN ('completed', 'cancelled') 
                AND updated_at < ?
            ''', (cutoff_date,))

            # 清理旧的提醒记录
            cursor.execute('''
                DELETE FROM reminder_records 
                WHERE created_at < ?
            ''', (cutoff_date,))

            # 清理旧的日志
            cursor.execute('''
                DELETE FROM reminder_logs 
                WHERE send_time < ?
            ''', (cutoff_date,))

            conn.commit()
            conn.close()

            logger.info(f"[Timer] Cleaned up data older than {days_to_keep} days")

        except Exception as e:
            logger.error(f"[Timer] Error cleaning up old data: {e}")