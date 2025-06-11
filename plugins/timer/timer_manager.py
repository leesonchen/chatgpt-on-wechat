"""定时器管理器模块

该模块负责定时器的核心业务逻辑，包括定时器的创建、管理、状态更新等。
它作为业务逻辑层，协调数据库操作和AI分析功能。

主要功能：
1. 定时器的创建和管理
2. 用户输入的AI分析和解析
3. 定时器状态的更新和维护
4. 提醒逻辑的处理
5. 用户交互的协调

特性：
- 智能解析用户输入
- 支持多种重复模式
- 灵活的时间处理
- 完整的状态管理
"""
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import json
from common.log import logger


class TimerManager:
    """
    定时器管理器，负责定时器的核心业务逻辑

    该类封装了定时器功能的核心业务逻辑，提供高级的定时器管理接口。
    它协调数据库操作、AI分析和用户交互，实现完整的定时器功能。

    主要职责：
    - 解析用户输入并创建定时器
    - 管理定时器的生命周期
    - 处理提醒逻辑和用户响应
    - 提供定时器查询和统计功能
    - 协调各个组件的交互

    Attributes:
        db_manager: 数据库管理器实例
        ai_generator: AI回复生成器实例
    """

    def __init__(self, db_manager, ai_generator=None):
        """
        初始化定时器管理器

        Args:
            db_manager: 数据库管理器实例
            ai_generator: AI回复生成器实例（可选）
        """
        self.db_manager = db_manager
        self.ai_generator = ai_generator

    def parse_timer_request(self, user_input: str, user_id: str) -> Dict[str, Any]:
        """
        解析用户的定时器请求

        使用规则和AI相结合的方式解析用户输入，提取定时器信息。

        Args:
            user_input: 用户输入的文本
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 解析结果，包含以下字段：
                - success: 是否解析成功
                - description: 提醒描述
                - remind_time: 提醒时间
                - repeat_type: 重复类型
                - ai_analysis: AI分析结果
                - error_message: 错误信息（如果解析失败）
        """
        try:
            # 首先尝试规则解析
            rule_result = self._parse_with_rules(user_input)
            
            # 如果规则解析成功，使用规则结果
            if rule_result['success']:
                result = rule_result
            else:
                # 规则解析失败，尝试AI解析
                if self.ai_generator:
                    ai_result = self._parse_with_ai(user_input, user_id)
                    result = ai_result if ai_result['success'] else rule_result
                else:
                    result = rule_result

            # 验证解析结果
            if result['success']:
                result = self._validate_timer_data(result)

            return result

        except Exception as e:
            logger.error(f"[Timer] Error parsing timer request: {e}")
            return {
                'success': False,
                'error_message': f'解析定时器请求时发生错误：{str(e)}'
            }

    def _parse_with_rules(self, user_input: str) -> Dict[str, Any]:
        """
        使用规则解析用户输入

        Args:
            user_input: 用户输入

        Returns:
            Dict[str, Any]: 解析结果
        """
        try:
            # 清理输入
            text = user_input.strip()
            
            # 时间模式匹配
            time_patterns = [
                # 绝对时间：明天8点、后天下午3点
                (r'(明天|后天|大后天)\s*(上午|下午|晚上|早上)?\s*(\d{1,2})\s*[点时]', self._parse_relative_date_time),
                # 相对时间：30分钟后、2小时后
                (r'(\d+)\s*(分钟|小时|天)\s*后', self._parse_relative_time),
                # 具体日期时间：12月25日下午3点
                (r'(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*(上午|下午|晚上|早上)?\s*(\d{1,2})\s*[点时]', self._parse_absolute_date_time),
                # 今天的时间：今天下午5点
                (r'今天\s*(上午|下午|晚上|早上)?\s*(\d{1,2})\s*[点时]', self._parse_today_time),
                # 每天、每周等重复模式
                (r'每\s*(天|日|周|星期|月)\s*(上午|下午|晚上|早上)?\s*(\d{1,2})\s*[点时]', self._parse_repeat_time),
            ]

            remind_time = None
            repeat_type = 'once'
            time_match = None

            # 尝试匹配时间模式
            for pattern, parser in time_patterns:
                match = re.search(pattern, text)
                if match:
                    time_result = parser(match)
                    if time_result:
                        remind_time = time_result.get('remind_time')
                        repeat_type = time_result.get('repeat_type', 'once')
                        time_match = match
                        break

            if not remind_time:
                return {
                    'success': False,
                    'error_message': '无法识别时间信息，请使用如"明天8点"、"30分钟后"等格式'
                }

            # 提取描述（去除时间部分）
            description = text
            if time_match:
                description = text.replace(time_match.group(0), '').strip()
            
            # 如果描述为空，使用默认描述
            if not description:
                description = "定时提醒"

            return {
                'success': True,
                'description': description,
                'remind_time': remind_time,
                'repeat_type': repeat_type,
                'ai_analysis': f'规则解析：{text}'
            }

        except Exception as e:
            logger.error(f"[Timer] Error in rule parsing: {e}")
            return {
                'success': False,
                'error_message': f'规则解析失败：{str(e)}'
            }

    def _parse_with_ai(self, user_input: str, user_id: str) -> Dict[str, Any]:
        """
        使用AI解析用户输入

        Args:
            user_input: 用户输入
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 解析结果
        """
        try:
            if not self.ai_generator:
                return {
                    'success': False,
                    'error_message': 'AI解析功能不可用'
                }

            # 构建AI提示词
            prompt = f"""
请分析以下用户输入，提取定时器信息：

用户输入：{user_input}

请以JSON格式返回分析结果，包含以下字段：
- description: 提醒描述
- remind_time: 提醒时间（ISO格式）
- repeat_type: 重复类型（once/daily/weekly/monthly）
- confidence: 解析置信度（0-1）

当前时间：{datetime.now().isoformat()}

示例输出：
{{
    "description": "开会",
    "remind_time": "2024-01-15T14:00:00",
    "repeat_type": "once",
    "confidence": 0.9
}}
"""

            # 调用AI生成回复
            ai_response = self.ai_generator.generate_response(
                user_id=user_id,
                prompt=prompt,
                context_type="timer_parsing"
            )

            # 解析AI回复
            try:
                # 尝试提取JSON
                json_match = re.search(r'\{[^}]+\}', ai_response)
                if json_match:
                    ai_data = json.loads(json_match.group(0))
                    
                    # 验证必要字段
                    if all(key in ai_data for key in ['description', 'remind_time', 'repeat_type']):
                        remind_time = datetime.fromisoformat(ai_data['remind_time'].replace('Z', '+00:00'))
                        
                        return {
                            'success': True,
                            'description': ai_data['description'],
                            'remind_time': remind_time,
                            'repeat_type': ai_data['repeat_type'],
                            'ai_analysis': f'AI解析：{user_input} -> {ai_response}'
                        }
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.warning(f"[Timer] Failed to parse AI response: {e}")

            return {
                'success': False,
                'error_message': 'AI解析失败，请使用更明确的时间表达'
            }

        except Exception as e:
            logger.error(f"[Timer] Error in AI parsing: {e}")
            return {
                'success': False,
                'error_message': f'AI解析出错：{str(e)}'
            }

    def _parse_relative_date_time(self, match) -> Optional[Dict[str, Any]]:
        """
        解析相对日期时间（明天8点、后天下午3点）
        """
        try:
            day_text = match.group(1)  # 明天、后天、大后天
            period = match.group(2)   # 上午、下午、晚上、早上
            hour = int(match.group(3))  # 小时

            # 计算日期偏移
            day_offset = {'明天': 1, '后天': 2, '大后天': 3}.get(day_text, 1)
            
            # 调整小时
            if period in ['下午', '晚上'] and hour < 12:
                hour += 12
            elif period in ['上午', '早上'] and hour == 12:
                hour = 0

            # 计算目标时间
            target_date = datetime.now().date() + timedelta(days=day_offset)
            remind_time = datetime.combine(target_date, datetime.min.time().replace(hour=hour))

            return {
                'remind_time': remind_time,
                'repeat_type': 'once'
            }
        except Exception as e:
            logger.error(f"[Timer] Error parsing relative date time: {e}")
            return None

    def _parse_relative_time(self, match) -> Optional[Dict[str, Any]]:
        """
        解析相对时间（30分钟后、2小时后）
        """
        try:
            amount = int(match.group(1))
            unit = match.group(2)

            # 计算时间偏移
            if unit == '分钟':
                delta = timedelta(minutes=amount)
            elif unit == '小时':
                delta = timedelta(hours=amount)
            elif unit == '天':
                delta = timedelta(days=amount)
            else:
                return None

            remind_time = datetime.now() + delta

            return {
                'remind_time': remind_time,
                'repeat_type': 'once'
            }
        except Exception as e:
            logger.error(f"[Timer] Error parsing relative time: {e}")
            return None

    def _parse_absolute_date_time(self, match) -> Optional[Dict[str, Any]]:
        """
        解析绝对日期时间（12月25日下午3点）
        """
        try:
            month = int(match.group(1))
            day = int(match.group(2))
            period = match.group(3)
            hour = int(match.group(4))

            # 调整小时
            if period in ['下午', '晚上'] and hour < 12:
                hour += 12
            elif period in ['上午', '早上'] and hour == 12:
                hour = 0

            # 计算年份（如果日期已过，则为明年）
            current_year = datetime.now().year
            target_date = datetime(current_year, month, day, hour)
            
            if target_date <= datetime.now():
                target_date = target_date.replace(year=current_year + 1)

            return {
                'remind_time': target_date,
                'repeat_type': 'once'
            }
        except Exception as e:
            logger.error(f"[Timer] Error parsing absolute date time: {e}")
            return None

    def _parse_today_time(self, match) -> Optional[Dict[str, Any]]:
        """
        解析今天的时间（今天下午5点）
        """
        try:
            period = match.group(1)
            hour = int(match.group(2))

            # 调整小时
            if period in ['下午', '晚上'] and hour < 12:
                hour += 12
            elif period in ['上午', '早上'] and hour == 12:
                hour = 0

            # 计算今天的目标时间
            today = datetime.now().date()
            remind_time = datetime.combine(today, datetime.min.time().replace(hour=hour))

            # 如果时间已过，则设为明天
            if remind_time <= datetime.now():
                remind_time += timedelta(days=1)

            return {
                'remind_time': remind_time,
                'repeat_type': 'once'
            }
        except Exception as e:
            logger.error(f"[Timer] Error parsing today time: {e}")
            return None

    def _parse_repeat_time(self, match) -> Optional[Dict[str, Any]]:
        """
        解析重复时间（每天8点、每周一下午3点）
        """
        try:
            repeat_unit = match.group(1)  # 天、日、周、星期、月
            period = match.group(2)      # 上午、下午、晚上、早上
            hour = int(match.group(3))   # 小时

            # 调整小时
            if period in ['下午', '晚上'] and hour < 12:
                hour += 12
            elif period in ['上午', '早上'] and hour == 12:
                hour = 0

            # 确定重复类型
            if repeat_unit in ['天', '日']:
                repeat_type = 'daily'
                # 计算下次提醒时间（今天或明天）
                today = datetime.now().date()
                remind_time = datetime.combine(today, datetime.min.time().replace(hour=hour))
                if remind_time <= datetime.now():
                    remind_time += timedelta(days=1)
            elif repeat_unit in ['周', '星期']:
                repeat_type = 'weekly'
                # 简化处理：设为下周同一天
                remind_time = datetime.now() + timedelta(days=7)
                remind_time = remind_time.replace(hour=hour, minute=0, second=0, microsecond=0)
            elif repeat_unit == '月':
                repeat_type = 'monthly'
                # 简化处理：设为下个月同一天
                remind_time = datetime.now() + timedelta(days=30)
                remind_time = remind_time.replace(hour=hour, minute=0, second=0, microsecond=0)
            else:
                return None

            return {
                'remind_time': remind_time,
                'repeat_type': repeat_type
            }
        except Exception as e:
            logger.error(f"[Timer] Error parsing repeat time: {e}")
            return None

    def _validate_timer_data(self, timer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证定时器数据

        Args:
            timer_data: 定时器数据

        Returns:
            Dict[str, Any]: 验证后的数据
        """
        try:
            # 检查提醒时间是否在过去
            if timer_data['remind_time'] <= datetime.now():
                return {
                    'success': False,
                    'error_message': '提醒时间不能设置在过去'
                }

            # 检查提醒时间是否过于遥远（超过1年）
            if timer_data['remind_time'] > datetime.now() + timedelta(days=365):
                return {
                    'success': False,
                    'error_message': '提醒时间不能超过一年'
                }

            # 验证重复类型
            valid_repeat_types = ['once', 'daily', 'weekly', 'monthly']
            if timer_data['repeat_type'] not in valid_repeat_types:
                timer_data['repeat_type'] = 'once'

            # 验证描述长度
            if len(timer_data['description']) > 200:
                timer_data['description'] = timer_data['description'][:200] + '...'

            return timer_data

        except Exception as e:
            logger.error(f"[Timer] Error validating timer data: {e}")
            return {
                'success': False,
                'error_message': f'数据验证失败：{str(e)}'
            }

    def create_timer(self, user_id: str, timer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建定时器

        Args:
            user_id: 用户ID
            timer_data: 定时器数据

        Returns:
            Dict[str, Any]: 创建结果
        """
        try:
            timer_id = self.db_manager.create_timer(
                user_id=user_id,
                description=timer_data['description'],
                remind_time=timer_data['remind_time'],
                repeat_type=timer_data['repeat_type'],
                ai_analysis=timer_data.get('ai_analysis')
            )

            return {
                'success': True,
                'timer_id': timer_id,
                'message': f'定时器创建成功！将在 {timer_data["remind_time"].strftime("%Y-%m-%d %H:%M")} 提醒您：{timer_data["description"]}'
            }

        except Exception as e:
            logger.error(f"[Timer] Error creating timer: {e}")
            return {
                'success': False,
                'error_message': f'创建定时器失败：{str(e)}'
            }

    def get_user_timers(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户的定时器列表

        Args:
            user_id: 用户ID

        Returns:
            List[Dict[str, Any]]: 定时器列表
        """
        return self.db_manager.get_active_timers(user_id)

    def cancel_timer(self, user_id: str, timer_id: int = None) -> Dict[str, Any]:
        """
        取消定时器

        Args:
            user_id: 用户ID
            timer_id: 定时器ID，如果为None则取消最新的定时器

        Returns:
            Dict[str, Any]: 取消结果
        """
        try:
            if timer_id is None:
                # 获取最新的定时器
                latest_timer = self.db_manager.get_latest_timer(user_id)
                if not latest_timer:
                    return {
                        'success': False,
                        'error_message': '没有找到可取消的定时器'
                    }
                timer_id = latest_timer['id']

            success = self.db_manager.cancel_timer(timer_id, user_id)
            
            if success:
                return {
                    'success': True,
                    'message': '定时器已取消'
                }
            else:
                return {
                    'success': False,
                    'error_message': '取消定时器失败，可能定时器不存在或无权限'
                }

        except Exception as e:
            logger.error(f"[Timer] Error cancelling timer: {e}")
            return {
                'success': False,
                'error_message': f'取消定时器时发生错误：{str(e)}'
            }

    def handle_reminder_response(self, user_id: str, response: str) -> Dict[str, Any]:
        """
        处理用户对提醒的回复

        Args:
            user_id: 用户ID
            response: 用户回复

        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            # 获取待处理的提醒
            pending_reminder = self.db_manager.get_pending_reminder(user_id)
            if not pending_reminder:
                return {
                    'success': False,
                    'error_message': '没有找到待处理的提醒'
                }

            # 分析用户回复
            response_lower = response.lower().strip()
            
            if any(word in response_lower for word in ['完成', '好了', '做完', '已完成', '搞定']):
                # 用户已完成任务
                self.db_manager.update_reminder_record_status(
                    pending_reminder['id'], 'completed', response
                )
                return {
                    'success': True,
                    'action': 'completed',
                    'message': '太棒了！任务已标记为完成 ✅'
                }
            
            elif any(word in response_lower for word in ['延迟', '稍后', '等会', '推迟', '晚点']):
                # 用户要求延迟
                delay_minutes = self._extract_delay_minutes(response)
                return self._handle_delay_request(pending_reminder, delay_minutes, response)
            
            elif any(word in response_lower for word in ['取消', '不要', '算了', '删除']):
                # 用户要求取消
                self.db_manager.update_reminder_record_status(
                    pending_reminder['id'], 'ignored', response
                )
                return {
                    'success': True,
                    'action': 'cancelled',
                    'message': '提醒已取消'
                }
            
            else:
                # 其他回复，询问用户意图
                return {
                    'success': True,
                    'action': 'clarify',
                    'message': '请告诉我：\n1. 已完成 - 如果您已经完成了任务\n2. 延迟X分钟 - 如果需要稍后提醒\n3. 取消 - 如果不需要这个提醒了'
                }

        except Exception as e:
            logger.error(f"[Timer] Error handling reminder response: {e}")
            return {
                'success': False,
                'error_message': f'处理回复时发生错误：{str(e)}'
            }

    def _extract_delay_minutes(self, response: str) -> int:
        """
        从用户回复中提取延迟分钟数

        Args:
            response: 用户回复

        Returns:
            int: 延迟分钟数，默认15分钟
        """
        try:
            # 查找数字
            numbers = re.findall(r'\d+', response)
            if numbers:
                minutes = int(numbers[0])
                # 限制延迟时间在合理范围内
                return min(max(minutes, 1), 1440)  # 1分钟到24小时
            
            # 如果没有找到数字，使用AI推荐的默认时间
            return self._get_recommended_delay_minutes()
            
        except Exception:
            return 15  # 默认15分钟

    def _get_recommended_delay_minutes(self) -> int:
        """
        获取AI推荐的延迟时间

        Returns:
            int: 推荐的延迟分钟数
        """
        # 简单的推荐逻辑，可以根据需要扩展
        current_hour = datetime.now().hour
        
        if 6 <= current_hour < 12:  # 上午
            return 30
        elif 12 <= current_hour < 18:  # 下午
            return 20
        elif 18 <= current_hour < 22:  # 晚上
            return 15
        else:  # 深夜/凌晨
            return 60

    def _handle_delay_request(self, pending_reminder: Dict[str, Any], delay_minutes: int, response: str) -> Dict[str, Any]:
        """
        处理延迟请求

        Args:
            pending_reminder: 待处理的提醒
            delay_minutes: 延迟分钟数
            response: 用户回复

        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            # 更新提醒记录状态
            self.db_manager.update_reminder_record_status(
                pending_reminder['id'], 'delayed', response
            )

            # 创建新的提醒记录
            new_remind_time = datetime.now() + timedelta(minutes=delay_minutes)
            new_record_id = self.db_manager.create_reminder_record(
                pending_reminder['timer_id'],
                pending_reminder['user_id'],
                new_remind_time
            )

            return {
                'success': True,
                'action': 'delayed',
                'message': f'好的，将在 {delay_minutes} 分钟后（{new_remind_time.strftime("%H:%M")}）再次提醒您',
                'new_record_id': new_record_id,
                'delay_minutes': delay_minutes
            }

        except Exception as e:
            logger.error(f"[Timer] Error handling delay request: {e}")
            return {
                'success': False,
                'error_message': f'处理延迟请求时发生错误：{str(e)}'
            }

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户统计信息

        Args:
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 统计信息
        """
        return self.db_manager.get_user_timer_stats(user_id)

    def format_timer_list(self, timers: List[Dict[str, Any]]) -> str:
        """
        格式化定时器列表为可读文本

        Args:
            timers: 定时器列表

        Returns:
            str: 格式化后的文本
        """
        if not timers:
            return "您当前没有活跃的定时器"

        lines = ["📅 您的定时器列表："]
        for i, timer in enumerate(timers, 1):
            remind_time = datetime.fromisoformat(timer['next_remind_time'] or timer['remind_time'])
            repeat_text = {
                'once': '一次性',
                'daily': '每天',
                'weekly': '每周',
                'monthly': '每月'
            }.get(timer['repeat_type'], '一次性')
            
            lines.append(f"{i}. {timer['description']}")
            lines.append(f"   ⏰ {remind_time.strftime('%Y-%m-%d %H:%M')} ({repeat_text})")
            lines.append("")

        return "\n".join(lines)