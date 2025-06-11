"""AI回复生成器模块

该模块负责生成个性化的AI回复，包括定时器相关的提醒、建议和交互内容。
它复用现有的AI Bot实例，通过精心设计的提示词模板生成高质量的回复。

主要功能：
1. 生成个性化的提醒消息
2. 提供智能的时间建议
3. 生成鼓励和激励内容
4. 处理用户交互的回复
5. 分析用户输入并提取信息

特性：
- 复用现有AI Bot实例
- 支持多种回复类型
- 提供回退机制
- 内容清理和格式化
- 上下文感知的回复生成
"""
import re
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from common.log import logger


class AIResponseGenerator:
    """
    AI回复生成器，负责生成个性化的AI回复

    该类封装了AI回复生成的核心逻辑，提供多种类型的回复生成功能。
    它与现有的AI Bot实例集成，通过精心设计的提示词生成高质量的回复。

    主要职责：
    - 生成各种类型的AI回复
    - 管理提示词模板
    - 处理AI回复的后处理
    - 提供回退机制
    - 维护回复的一致性和质量

    Attributes:
        bot: AI Bot实例
        fallback_responses: 回退回复模板
    """

    def __init__(self, bot=None):
        """
        初始化AI回复生成器

        Args:
            bot: AI Bot实例，如果为None则使用回退机制
        """
        self.bot = bot
        self.fallback_responses = self._init_fallback_responses()

    def _init_fallback_responses(self) -> Dict[str, List[str]]:
        """
        初始化回退回复模板

        Returns:
            Dict[str, List[str]]: 回退回复模板字典
        """
        return {
            'reminder': [
                "⏰ 提醒时间到了！请记得：{description}",
                "🔔 您设置的提醒：{description}",
                "📝 温馨提醒：{description}",
                "⏰ 时间到！别忘了：{description}"
            ],
            'encouragement': [
                "加油！您可以做到的！💪",
                "相信自己，继续努力！🌟",
                "每一步都是进步！👍",
                "坚持就是胜利！✨"
            ],
            'delay_suggestion': [
                "建议{minutes}分钟后再次提醒您",
                "推荐{minutes}分钟后继续",
                "建议稍后{minutes}分钟再试"
            ],
            'completion_praise': [
                "太棒了！任务完成！🎉",
                "干得漂亮！✅",
                "恭喜您完成任务！👏",
                "很好！又完成一项任务！🌟"
            ],
            'timer_created': [
                "定时器设置成功！我会准时提醒您的 ⏰",
                "好的，已为您设置提醒 📅",
                "定时器已创建，到时间我会通知您 🔔"
            ]
        }

    def generate_response(self, user_id: str, prompt: str, context_type: str = "general", **kwargs) -> str:
        """
        生成AI回复

        Args:
            user_id: 用户ID
            prompt: 提示词
            context_type: 上下文类型
            **kwargs: 额外参数

        Returns:
            str: 生成的回复
        """
        try:
            if self.bot:
                # 使用AI Bot生成回复
                response = self._generate_with_bot(user_id, prompt, context_type, **kwargs)
                if response:
                    return self._clean_response(response)

            # 回退到模板回复
            return self._generate_fallback_response(context_type, **kwargs)

        except Exception as e:
            logger.error(f"[Timer] Error generating AI response: {e}")
            return self._generate_fallback_response(context_type, **kwargs)

    def _generate_with_bot(self, user_id: str, prompt: str, context_type: str, **kwargs) -> Optional[str]:
        """
        使用AI Bot生成回复

        Args:
            user_id: 用户ID
            prompt: 提示词
            context_type: 上下文类型
            **kwargs: 额外参数

        Returns:
            Optional[str]: 生成的回复，失败时返回None
        """
        try:
            # 这里需要根据实际的Bot接口进行调整
            # 假设Bot有一个reply方法
            if hasattr(self.bot, 'reply'):
                # 构建查询对象（根据实际Bot接口调整）
                class MockQuery:
                    def __init__(self, user_id, content):
                        self.from_user_id = user_id
                        self.content = content
                        self.is_group = False
                        self.is_at = False

                query = MockQuery(user_id, prompt)
                reply = self.bot.reply(query, {})
                
                if reply and hasattr(reply, 'content'):
                    return reply.content
                elif isinstance(reply, str):
                    return reply

            return None

        except Exception as e:
            logger.error(f"[Timer] Error using bot for response generation: {e}")
            return None

    def _generate_fallback_response(self, context_type: str, **kwargs) -> str:
        """
        生成回退回复

        Args:
            context_type: 上下文类型
            **kwargs: 模板参数

        Returns:
            str: 回退回复
        """
        try:
            templates = self.fallback_responses.get(context_type, self.fallback_responses['reminder'])
            template = templates[0]  # 使用第一个模板
            
            # 格式化模板
            return template.format(**kwargs)

        except Exception as e:
            logger.error(f"[Timer] Error generating fallback response: {e}")
            return "⏰ 提醒时间到了！"

    def _clean_response(self, response: str) -> str:
        """
        清理AI回复内容

        Args:
            response: 原始回复

        Returns:
            str: 清理后的回复
        """
        try:
            # 移除多余的空白字符
            response = re.sub(r'\s+', ' ', response.strip())
            
            # 移除可能的系统提示
            response = re.sub(r'^(AI:|助手:|回复:|答:)', '', response, flags=re.IGNORECASE)
            
            # 限制长度
            if len(response) > 500:
                response = response[:497] + '...'
            
            return response.strip()

        except Exception as e:
            logger.error(f"[Timer] Error cleaning response: {e}")
            return response

    def generate_reminder_message(self, timer_info: Dict[str, Any], user_id: str) -> str:
        """
        生成提醒消息

        Args:
            timer_info: 定时器信息
            user_id: 用户ID

        Returns:
            str: 提醒消息
        """
        try:
            description = timer_info.get('description', '未知任务')
            repeat_type = timer_info.get('repeat_type', 'once')
            
            # 构建AI提示词
            prompt = f"""
请为用户生成一条友好的提醒消息。

提醒内容：{description}
重复类型：{repeat_type}
当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

要求：
1. 语气友好、鼓励
2. 简洁明了
3. 包含适当的emoji
4. 不超过100字
5. 提醒用户可以回复"完成"、"延迟"或"取消"

示例格式：
⏰ 提醒时间到了！请记得：[任务描述]

您可以回复：
• 完成 - 已完成任务
• 延迟X分钟 - 稍后提醒
• 取消 - 取消提醒
"""

            response = self.generate_response(
                user_id=user_id,
                prompt=prompt,
                context_type="reminder",
                description=description
            )

            # 确保包含操作提示
            if "完成" not in response and "延迟" not in response:
                response += "\n\n您可以回复：\n• 完成 - 已完成任务\n• 延迟X分钟 - 稍后提醒\n• 取消 - 取消提醒"

            return response

        except Exception as e:
            logger.error(f"[Timer] Error generating reminder message: {e}")
            return self._generate_fallback_response("reminder", description=timer_info.get('description', '任务'))

    def generate_delay_suggestion(self, user_id: str, context: Dict[str, Any]) -> int:
        """
        生成延迟时间建议

        Args:
            user_id: 用户ID
            context: 上下文信息

        Returns:
            int: 建议的延迟分钟数
        """
        try:
            current_hour = datetime.now().hour
            task_description = context.get('description', '')
            
            # 构建AI提示词
            prompt = f"""
请根据当前情况为用户推荐合适的延迟提醒时间。

任务描述：{task_description}
当前时间：{datetime.now().strftime('%H:%M')}
当前小时：{current_hour}

请考虑以下因素：
1. 当前时间段（工作时间、休息时间等）
2. 任务类型和紧急程度
3. 用户的作息习惯

请返回一个1-120之间的数字，表示建议的延迟分钟数。
只返回数字，不要其他内容。

参考：
- 工作时间：15-30分钟
- 休息时间：30-60分钟
- 紧急任务：5-15分钟
- 一般任务：15-30分钟
"""

            response = self.generate_response(
                user_id=user_id,
                prompt=prompt,
                context_type="delay_suggestion"
            )

            # 尝试提取数字
            numbers = re.findall(r'\d+', response)
            if numbers:
                minutes = int(numbers[0])
                return min(max(minutes, 1), 120)  # 限制在1-120分钟

            # 回退到基于时间的建议
            return self._get_time_based_delay_suggestion(current_hour)

        except Exception as e:
            logger.error(f"[Timer] Error generating delay suggestion: {e}")
            return self._get_time_based_delay_suggestion(datetime.now().hour)

    def _get_time_based_delay_suggestion(self, hour: int) -> int:
        """
        基于时间的延迟建议

        Args:
            hour: 当前小时

        Returns:
            int: 建议的延迟分钟数
        """
        if 6 <= hour < 9:  # 早晨
            return 20
        elif 9 <= hour < 12:  # 上午
            return 30
        elif 12 <= hour < 14:  # 午餐时间
            return 45
        elif 14 <= hour < 18:  # 下午
            return 25
        elif 18 <= hour < 21:  # 晚上
            return 20
        elif 21 <= hour < 23:  # 夜晚
            return 30
        else:  # 深夜/凌晨
            return 60

    def generate_encouragement(self, user_id: str, context: Dict[str, Any]) -> str:
        """
        生成鼓励消息

        Args:
            user_id: 用户ID
            context: 上下文信息

        Returns:
            str: 鼓励消息
        """
        try:
            stats = context.get('stats', {})
            completion_rate = stats.get('completion_rate', 0)
            
            prompt = f"""
请为用户生成一条鼓励消息。

用户统计：
- 完成率：{completion_rate}%
- 活跃定时器：{stats.get('active_timers', 0)}个
- 总完成数：{stats.get('completed_reminders', 0)}个

要求：
1. 根据完成率给出相应的鼓励
2. 语气积极正面
3. 包含适当的emoji
4. 不超过50字

完成率参考：
- 80%以上：表扬坚持和自律
- 60-80%：鼓励继续努力
- 40-60%：给予支持和建议
- 40%以下：温和鼓励，建议调整
"""

            return self.generate_response(
                user_id=user_id,
                prompt=prompt,
                context_type="encouragement"
            )

        except Exception as e:
            logger.error(f"[Timer] Error generating encouragement: {e}")
            return self._generate_fallback_response("encouragement")

    def generate_completion_praise(self, user_id: str, task_description: str) -> str:
        """
        生成完成任务的赞美消息

        Args:
            user_id: 用户ID
            task_description: 任务描述

        Returns:
            str: 赞美消息
        """
        try:
            prompt = f"""
请为用户完成任务生成一条赞美消息。

完成的任务：{task_description}

要求：
1. 表达真诚的赞美和认可
2. 语气热情积极
3. 包含庆祝的emoji
4. 不超过30字
5. 可以提及坚持的价值

示例风格：
- 太棒了！又完成一项任务！🎉
- 干得漂亮！坚持就是胜利！✨
- 恭喜！您的自律值得赞赏！👏
"""

            return self.generate_response(
                user_id=user_id,
                prompt=prompt,
                context_type="completion_praise",
                description=task_description
            )

        except Exception as e:
            logger.error(f"[Timer] Error generating completion praise: {e}")
            return self._generate_fallback_response("completion_praise")

    def generate_timer_creation_confirmation(self, user_id: str, timer_info: Dict[str, Any]) -> str:
        """
        生成定时器创建确认消息

        Args:
            user_id: 用户ID
            timer_info: 定时器信息

        Returns:
            str: 确认消息
        """
        try:
            description = timer_info.get('description', '')
            remind_time = timer_info.get('remind_time')
            repeat_type = timer_info.get('repeat_type', 'once')
            
            time_str = remind_time.strftime('%Y-%m-%d %H:%M') if remind_time else '未知时间'
            repeat_text = {
                'once': '一次性',
                'daily': '每天',
                'weekly': '每周',
                'monthly': '每月'
            }.get(repeat_type, '一次性')

            prompt = f"""
请为用户生成定时器创建成功的确认消息。

定时器信息：
- 任务：{description}
- 时间：{time_str}
- 重复：{repeat_text}

要求：
1. 确认定时器已创建
2. 简要重述关键信息
3. 语气友好可靠
4. 包含适当的emoji
5. 不超过80字
6. 可以提及准时提醒的承诺

示例格式：
✅ 定时器设置成功！
📝 任务：[任务描述]
⏰ 时间：[时间]
🔔 我会准时提醒您的！
"""

            return self.generate_response(
                user_id=user_id,
                prompt=prompt,
                context_type="timer_created",
                description=description
            )

        except Exception as e:
            logger.error(f"[Timer] Error generating timer creation confirmation: {e}")
            return self._generate_fallback_response("timer_created")

    def analyze_user_intent(self, user_input: str, user_id: str) -> Dict[str, Any]:
        """
        分析用户意图

        Args:
            user_input: 用户输入
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 意图分析结果
        """
        try:
            prompt = f"""
请分析用户输入的意图，判断用户想要执行什么操作。

用户输入：{user_input}

可能的意图类型：
1. create_timer - 创建定时器
2. list_timers - 查看定时器列表
3. cancel_timer - 取消定时器
4. respond_reminder - 回复提醒
5. get_stats - 查看统计
6. help - 获取帮助
7. other - 其他

请以JSON格式返回分析结果：
{{
    "intent": "意图类型",
    "confidence": 0.0-1.0,
    "entities": {{
        "time": "提取的时间信息",
        "description": "提取的描述信息",
        "action": "具体动作"
    }}
}}
"""

            response = self.generate_response(
                user_id=user_id,
                prompt=prompt,
                context_type="intent_analysis"
            )

            # 尝试解析JSON回复
            try:
                json_match = re.search(r'\{[^}]+\}', response)
                if json_match:
                    return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

            # 回退到简单规则分析
            return self._analyze_intent_with_rules(user_input)

        except Exception as e:
            logger.error(f"[Timer] Error analyzing user intent: {e}")
            return self._analyze_intent_with_rules(user_input)

    def _analyze_intent_with_rules(self, user_input: str) -> Dict[str, Any]:
        """
        使用规则分析用户意图

        Args:
            user_input: 用户输入

        Returns:
            Dict[str, Any]: 意图分析结果
        """
        text = user_input.lower().strip()
        
        # 创建定时器的关键词
        if any(word in text for word in ['提醒', '定时', '闹钟', '记得', '别忘', '到时候']):
            return {
                'intent': 'create_timer',
                'confidence': 0.8,
                'entities': {}
            }
        
        # 查看列表的关键词
        elif any(word in text for word in ['列表', '查看', '显示', '有哪些', '所有']):
            return {
                'intent': 'list_timers',
                'confidence': 0.7,
                'entities': {}
            }
        
        # 取消的关键词
        elif any(word in text for word in ['取消', '删除', '不要', '算了']):
            return {
                'intent': 'cancel_timer',
                'confidence': 0.7,
                'entities': {}
            }
        
        # 回复提醒的关键词
        elif any(word in text for word in ['完成', '好了', '延迟', '稍后', '推迟']):
            return {
                'intent': 'respond_reminder',
                'confidence': 0.8,
                'entities': {}
            }
        
        # 统计的关键词
        elif any(word in text for word in ['统计', '数据', '完成率', '情况']):
            return {
                'intent': 'get_stats',
                'confidence': 0.6,
                'entities': {}
            }
        
        # 帮助的关键词
        elif any(word in text for word in ['帮助', '怎么', '如何', '使用', '功能']):
            return {
                'intent': 'help',
                'confidence': 0.7,
                'entities': {}
            }
        
        else:
            return {
                'intent': 'other',
                'confidence': 0.3,
                'entities': {}
            }