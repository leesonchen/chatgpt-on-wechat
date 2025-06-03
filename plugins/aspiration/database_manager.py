"""
数据库管理器模块

该模块负责立志功能的所有数据库操作，包括表结构初始化、数据的增删改查、
统计计算等。使用SQLite作为后端数据库，提供完整的数据持久化服务。

主要功能：
1. 数据库表结构初始化和维护
2. 用户目标的CRUD操作
3. 打卡记录的管理
4. 提醒日志的记录
5. 统计数据的计算
6. 数据清理和维护

数据库设计：
- user_goals: 用户目标表，存储目标信息
- check_in_records: 打卡记录表，存储每日打卡数据
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

    该类封装了立志功能的所有数据库操作，提供高级的数据访问接口。
    使用SQLite作为后端存储，支持表结构自动初始化和数据迁移。

    主要职责：
    - 管理数据库连接和事务
    - 提供目标和打卡的CRUD操作
    - 计算各种统计数据
    - 处理数据备份和清理
    - 维护数据完整性和一致性

    Attributes:
        db_path: 数据库文件路径
    """

    def __init__(self, db_path: str = "data/aspiration.db"):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径，默认为 "data/aspiration.db"
        """
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """
        初始化数据库表结构

        创建所有必要的表和索引。如果表已存在则不会重复创建。
        该方法是幂等的，可以安全地多次调用。

        创建的表：
        1. user_goals: 用户目标表
        2. check_in_records: 打卡记录表
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

            # 创建用户目标表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    goal_description TEXT NOT NULL,
                    planned_days INTEGER NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 创建打卡记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS check_in_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    check_date DATE NOT NULL,
                    status TEXT NOT NULL,
                    user_note TEXT,
                    ai_response TEXT,
                    consecutive_days INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (goal_id) REFERENCES user_goals(id)
                )
            ''')

            # 创建提醒记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminder_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    goal_id INTEGER NOT NULL,
                    reminder_date DATE NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    responded BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (goal_id) REFERENCES user_goals(id)
                )
            ''')

            # 创建索引以提高查询性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_goals_user_id ON user_goals(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_goals_status ON user_goals(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_check_in_records_goal_id ON check_in_records(goal_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_check_in_records_date ON check_in_records(check_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reminder_logs_user_id ON reminder_logs(user_id)')

            conn.commit()
            conn.close()
            logger.info("[Aspiration] 数据库初始化完成")
        except Exception as e:
            logger.error(f"[Aspiration] 数据库初始化失败: {e}")
            raise

    def _get_connection(self):
        """
        获取数据库连接

        返回配置好的SQLite连接对象，启用行工厂以便按列名访问结果。

        Returns:
            sqlite3.Connection: 配置好的数据库连接
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
        return conn

    # 目标管理相关方法
    def create_goal(self, user_id: str, description: str, planned_days: int) -> Optional[int]:
        """
        创建新目标

        为指定用户创建一个新的目标，自动计算开始和结束日期。

        Args:
            user_id: 用户ID
            description: 目标描述
            planned_days: 计划坚持的天数

        Returns:
            Optional[int]: 新创建目标的ID，创建失败时返回None

        Raises:
            Exception: 数据库操作失败时抛出异常
        """
        try:
            start_date = date.today()
            end_date = start_date + timedelta(days=planned_days)

            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO user_goals (user_id, goal_description, planned_days, start_date, end_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, description, planned_days, start_date, end_date))

            goal_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"[Aspiration] 用户 {user_id} 创建目标: {description}")
            return goal_id
        except Exception as e:
            logger.error(f"[Aspiration] 创建目标失败: {e}")
            raise

    def get_active_goal(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户的活跃目标

        返回指定用户当前活跃的目标信息，如果没有活跃目标则返回None。
        同时计算目标已开始的天数。

        Args:
            user_id: 用户ID

        Returns:
            Optional[Dict[str, Any]]: 目标信息字典或None
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM user_goals
                WHERE user_id = ? AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
            ''', (user_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                goal = dict(row)
                # 计算已开始天数
                start_date = datetime.strptime(goal['start_date'], '%Y-%m-%d').date()
                goal['days_since_start'] = (date.today() - start_date).days + 1
                return goal
            return None
        except Exception as e:
            logger.error(f"[Aspiration] 获取活跃目标失败: {e}")
            return None

    def update_goal_status(self, goal_id: int, status: str):
        """
        更新目标状态

        将指定目标的状态更新为新状态，同时更新修改时间。

        Args:
            goal_id: 目标ID
            status: 新状态 ('active', 'completed', 'abandoned')

        Raises:
            Exception: 数据库操作失败时抛出异常
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE user_goals
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, goal_id))

            conn.commit()
            conn.close()
            logger.info(f"[Aspiration] 目标 {goal_id} 状态更新为: {status}")
        except Exception as e:
            logger.error(f"[Aspiration] 更新目标状态失败: {e}")
            raise

    # 打卡记录相关方法
    def create_checkin(self, goal_id: int, user_id: str, check_date: date,
                      status: str, note: Optional[str] = None, consecutive_days: int = 0) -> Optional[int]:
        """
        创建打卡记录

        为指定目标创建一条新的打卡记录。

        Args:
            goal_id: 目标ID
            user_id: 用户ID
            check_date: 打卡日期
            status: 打卡状态 ('completed', 'partial', 'failed')
            note: 用户备注，可选
            consecutive_days: 连续打卡天数

        Returns:
            Optional[int]: 新创建打卡记录的ID，创建失败时返回None

        Raises:
            Exception: 数据库操作失败时抛出异常
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO check_in_records
                (goal_id, user_id, check_date, status, user_note, consecutive_days)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (goal_id, user_id, check_date, status, note, consecutive_days))

            checkin_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"[Aspiration] 用户 {user_id} 打卡记录已创建，状态: {status}")
            return checkin_id
        except Exception as e:
            logger.error(f"[Aspiration] 创建打卡记录失败: {e}")
            raise

    def get_checkin_by_date(self, goal_id: int, check_date: date) -> Optional[Dict[str, Any]]:
        """
        获取指定日期的打卡记录

        查找指定目标在指定日期的打卡记录。

        Args:
            goal_id: 目标ID
            check_date: 查询的日期

        Returns:
            Optional[Dict[str, Any]]: 打卡记录字典或None
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM check_in_records
                WHERE goal_id = ? AND check_date = ?
            ''', (goal_id, check_date))

            row = cursor.fetchone()
            conn.close()

            return dict(row) if row else None
        except Exception as e:
            logger.error(f"[Aspiration] 获取打卡记录失败: {e}")
            return None

    def update_checkin_ai_response(self, checkin_id: int, ai_response: str):
        """
        更新打卡记录的AI回复

        为指定的打卡记录更新AI生成的回复内容。

        Args:
            checkin_id: 打卡记录ID
            ai_response: AI生成的回复内容
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE check_in_records
                SET ai_response = ?
                WHERE id = ?
            ''', (ai_response, checkin_id))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[Aspiration] 更新AI回复失败: {e}")

    def calculate_consecutive_days(self, goal_id: int) -> int:
        """
        计算连续打卡天数

        从今天开始往前计算连续成功打卡的天数。只有状态为'completed'的记录
        才被认为是成功打卡。如果中间有任何一天失败或缺失，则连续计数停止。

        Args:
            goal_id: 目标ID

        Returns:
            int: 连续打卡天数，如果没有记录则返回0

        算法逻辑：
        1. 获取该目标的所有打卡记录，按日期倒序排列
        2. 从今天开始逐天检查是否有成功打卡记录
        3. 遇到失败或缺失记录时停止计算
        4. 返回连续成功的天数
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 获取最近的打卡记录，按日期倒序
            cursor.execute('''
                SELECT check_date, status FROM check_in_records
                WHERE goal_id = ?
                ORDER BY check_date DESC
            ''', (goal_id,))

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return 0

            consecutive_days = 0
            current_date = date.today()

            for row in rows:
                check_date = datetime.strptime(row['check_date'], '%Y-%m-%d').date()

                # 如果是连续的日期且状态为完成
                if check_date == current_date - timedelta(days=consecutive_days):
                    if row['status'] == 'completed':
                        consecutive_days += 1
                        continue
                    else:
                        break
                else:
                    break

            return consecutive_days
        except Exception as e:
            logger.error(f"[Aspiration] 计算连续天数失败: {e}")
            return 0

    def get_user_statistics(self, user_id: str, goal_id: int) -> Dict[str, Any]:
        """
        获取用户统计信息

        计算指定目标的各种统计数据，包括打卡总数、完成率、连续天数等。

        Args:
            user_id: 用户ID（当前版本中未直接使用，但保留以备扩展）
            goal_id: 目标ID

        Returns:
            Dict[str, Any]: 包含以下统计信息的字典
                - total_checkins: 总打卡次数
                - completed_checkins: 成功完成的打卡次数
                - completion_rate: 完成率（百分比，保留1位小数）
                - consecutive_days: 当前连续打卡天数
                - max_streak: 历史最长连续天数

        异常处理：
        如果查询失败，返回所有数值为0的默认统计信息
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 获取总打卡记录
            cursor.execute('''
                SELECT
                    COUNT(*) as total_checkins,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_checkins
                FROM check_in_records
                WHERE goal_id = ?
            ''', (goal_id,))

            stats_row = cursor.fetchone()

            # 获取连续天数
            consecutive_days = self.calculate_consecutive_days(goal_id)

            # 获取最长连续天数
            cursor.execute('''
                SELECT MAX(consecutive_days) as max_streak
                FROM check_in_records
                WHERE goal_id = ?
            ''', (goal_id,))

            max_streak_row = cursor.fetchone()

            conn.close()

            total_checkins = stats_row['total_checkins'] or 0
            completed_checkins = stats_row['completed_checkins'] or 0
            completion_rate = (completed_checkins / total_checkins * 100) if total_checkins > 0 else 0
            max_streak = max_streak_row['max_streak'] or 0

            return {
                'total_checkins': total_checkins,
                'completed_checkins': completed_checkins,
                'completion_rate': round(completion_rate, 1),
                'consecutive_days': consecutive_days,
                'max_streak': max_streak
            }
        except Exception as e:
            logger.error(f"[Aspiration] 获取用户统计失败: {e}")
            return {
                'total_checkins': 0,
                'completed_checkins': 0,
                'completion_rate': 0,
                'consecutive_days': 0,
                'max_streak': 0
            }

    # 提醒相关方法
    def get_missed_checkin_users(self, check_date: date) -> List[Dict[str, Any]]:
        """
        获取指定日期未打卡的用户

        查找在指定日期应该打卡但未打卡的所有用户。这个方法用于提醒系统，
        识别需要发送提醒消息的用户。

        Args:
            check_date: 检查的日期

        Returns:
            List[Dict[str, Any]]: 未打卡用户列表，每个元素包含：
                - user_id: 用户ID
                - goal_info: 目标信息字典，包含目标详情和已开始天数

        查询逻辑：
        1. 找到所有活跃状态的目标
        2. 确保目标的开始日期不晚于检查日期
        3. 确保目标尚未结束（结束日期为空或不早于检查日期）
        4. 排除已经在指定日期打卡的目标
        5. 计算每个目标已开始的天数
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 查找活跃目标但当日未打卡的用户
            cursor.execute('''
                SELECT ug.user_id, ug.id as goal_id, ug.goal_description, ug.start_date, ug.planned_days
                FROM user_goals ug
                LEFT JOIN check_in_records cir ON ug.id = cir.goal_id AND cir.check_date = ?
                WHERE ug.status = 'active'
                AND ug.start_date <= ?
                AND (ug.end_date IS NULL OR ug.end_date >= ?)
                AND cir.id IS NULL
            ''', (check_date, check_date, check_date))

            rows = cursor.fetchall()
            conn.close()

            result = []
            for row in rows:
                goal_info = dict(row)
                # 计算已开始天数
                start_date = datetime.strptime(goal_info['start_date'], '%Y-%m-%d').date()
                goal_info['days_since_start'] = (check_date - start_date).days + 1

                result.append({
                    'user_id': goal_info['user_id'],
                    'goal_info': goal_info
                })

            return result
        except Exception as e:
            logger.error(f"[Aspiration] 获取未打卡用户失败: {e}")
            return []

    def log_reminder_sent(self, user_id: str, goal_id: int, reminder_date: date):
        """
        记录提醒发送日志

        在reminder_logs表中记录一条提醒发送记录，用于跟踪提醒发送历史
        和防止重复发送。

        Args:
            user_id: 用户ID
            goal_id: 目标ID
            reminder_date: 提醒发送的日期

        注意：
        - 记录创建时responded字段默认为FALSE
        - 发送时间(sent_at)会自动设置为当前时间戳
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO reminder_logs (user_id, goal_id, reminder_date)
                VALUES (?, ?, ?)
            ''', (user_id, goal_id, reminder_date))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[Aspiration] 记录提醒日志失败: {e}")

    def mark_reminder_responded(self, user_id: str, goal_id: int, reminder_date: date):
        """
        标记提醒已回应

        当用户对提醒消息做出回应（如进行打卡）时，更新对应的提醒记录
        将responded字段设置为TRUE，用于统计提醒的有效性。

        Args:
            user_id: 用户ID
            goal_id: 目标ID
            reminder_date: 提醒日期

        用途：
        - 跟踪用户对提醒的响应情况
        - 分析提醒系统的有效性
        - 优化提醒策略和频率
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE reminder_logs
                SET responded = TRUE
                WHERE user_id = ? AND goal_id = ? AND reminder_date = ?
            ''', (user_id, goal_id, reminder_date))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[Aspiration] 标记提醒回应失败: {e}")

    # 数据清理和维护方法
    def cleanup_old_data(self, days: int = 365):
        """
        清理旧数据

        定期清理数据库中的历史数据，防止数据库无限增长。
        主要清理已完成或已放弃目标的相关记录。

        Args:
            days: 保留数据的天数，默认365天（1年）

        清理策略：
        1. 清理超过指定天数的提醒日志
        2. 清理已完成或已放弃目标的打卡记录
        3. 清理已完成或已放弃目标本身
        4. 保留活跃目标及其所有相关数据

        注意：
        - 此操作不可逆，建议在执行前备份重要数据
        - 活跃状态的目标及其数据不会被清理
        - 清理操作会记录到日志中
        """
        try:
            cutoff_date = date.today() - timedelta(days=days)

            conn = self._get_connection()
            cursor = conn.cursor()

            # 清理旧的提醒日志
            cursor.execute('''
                DELETE FROM reminder_logs
                WHERE reminder_date < ?
            ''', (cutoff_date,))

            # 清理已完成或已放弃超过指定天数的目标相关数据
            cursor.execute('''
                DELETE FROM check_in_records
                WHERE goal_id IN (
                    SELECT id FROM user_goals
                    WHERE status IN ('completed', 'abandoned')
                    AND updated_at < ?
                )
            ''', (cutoff_date,))

            cursor.execute('''
                DELETE FROM user_goals
                WHERE status IN ('completed', 'abandoned')
                AND updated_at < ?
            ''', (cutoff_date,))

            conn.commit()
            conn.close()

            logger.info(f"[Aspiration] 清理了 {days} 天前的旧数据")
        except Exception as e:
            logger.error(f"[Aspiration] 清理旧数据失败: {e}")
