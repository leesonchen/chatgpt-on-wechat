# "立志"功能技术实现指南

## 1. 技术架构分析

### 1.1 当前项目技术栈确认
基于对现有项目的分析，确认以下技术要点：

**核心框架**：
- Python 3.x
- 微信公众号通道 (wechatmp)
- 豆包AI模型 (Doubao)
- 插件系统架构

**关键技术能力**：
- ✅ 事件驱动的插件系统
- ✅ 微信公众号API集成
- ✅ 用户会话管理
- ✅ 定时任务支持
- ✅ 数据存储能力
- ✅ AI模型集成

**重要限制**：
- 个人订阅号无法主动推送消息
- 认证服务号可通过客服接口主动推送
- 自定义菜单需在微信公众平台后台配置

## 2. 实现方案设计

### 2.1 插件开发策略

#### 2.1.1 插件目录结构
```
plugins/aspiration/
├── __init__.py
├── aspiration_plugin.py      # 主插件文件
├── goal_manager.py          # 目标管理器
├── checkin_manager.py       # 打卡管理器
├── reminder_scheduler.py    # 提醒调度器
├── database_manager.py      # 数据库管理
├── ai_prompt_templates.py   # AI提示词模板
├── message_templates.py     # 消息模板
├── config.json             # 插件配置
└── README.md               # 说明文档
```

#### 2.1.2 插件主文件实现要点
```python
# aspiration_plugin.py
import plugins
from plugins import *
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger

@plugins.register(
    name="Aspiration",
    desire_priority=100,
    hidden=False,
    desc="立志功能插件，支持目标设定和打卡记录",
    version="1.0",
    author="AI Assistant",
)
class AspirationPlugin(Plugin):
    def __init__(self):
        super().__init__()
        # 初始化组件
        self.goal_manager = GoalManager()
        self.checkin_manager = CheckInManager()
        self.reminder_scheduler = ReminderScheduler()

        # 注册事件处理器
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        logger.info("[Aspiration] 立志功能插件初始化完成")

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type != ContextType.TEXT:
            return

        content = e_context["context"].content.strip()
        user_id = e_context["context"]["session_id"]

        # 处理菜单点击事件
        if content in ["立志", "SET_GOAL"]:
            self.handle_goal_setting(e_context, user_id)
        elif content in ["打卡", "CHECK_IN"]:
            self.handle_check_in(e_context, user_id)
        elif content in ["我的目标", "MY_GOALS"]:
            self.handle_my_goals(e_context, user_id)
        # ... 其他处理逻辑
```

### 2.2 数据库设计实现

#### 2.2.1 数据库初始化
```python
# database_manager.py
import sqlite3
import os
from datetime import datetime, date

class DatabaseManager:
    def __init__(self, db_path="data/aspiration.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """初始化数据库表结构"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

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

        conn.commit()
        conn.close()
        logger.info("[Aspiration] 数据库初始化完成")
```

### 2.3 微信公众号集成方案

#### 2.3.1 自定义菜单配置
由于微信公众号的自定义菜单需要在微信公众平台后台配置，这里提供配置方案：

```json
{
    "button": [
        {
            "type": "click",
            "name": "智能对话",
            "key": "CHAT_MODE"
        },
        {
            "name": "立志管理",
            "sub_button": [
                {
                    "type": "click",
                    "name": "立志",
                    "key": "SET_GOAL"
                },
                {
                    "type": "click",
                    "name": "打卡",
                    "key": "CHECK_IN"
                },
                {
                    "type": "click",
                    "name": "我的目标",
                    "key": "MY_GOALS"
                },
                {
                    "type": "click",
                    "name": "目标统计",
                    "key": "GOAL_STATS"
                }
            ]
        },
        {
            "name": "帮助",
            "sub_button": [
                {
                    "type": "click",
                    "name": "使用说明",
                    "key": "HELP"
                },
                {
                    "type": "click",
                    "name": "联系客服",
                    "key": "CONTACT"
                }
            ]
        }
    ]
}
```

#### 2.3.2 菜单事件处理增强
需要在`wechatmp_channel.py`中增加对自定义菜单事件的处理：

```python
# 在WechatMPChannel类中添加
def handle_click_event(self, msg):
    """处理菜单点击事件"""
    event_key = msg.get('EventKey', '')
    user_id = msg.get('FromUserName', '')

    # 构造上下文，模拟文本消息
    context = Context()
    context.type = ContextType.TEXT
    context.content = event_key  # 将事件key作为消息内容
    context['session_id'] = user_id
    context['msg'] = msg

    # 发送到插件系统处理
    self._handle(context)
```

### 2.4 定时提醒系统实现

#### 2.4.1 提醒调度器设计
```python
# reminder_scheduler.py
import schedule
import time
import threading
from datetime import datetime, date
from channel.wechatmp.wechatmp_channel import WechatMPChannel

class ReminderScheduler:
    def __init__(self, db_manager, channel_instance):
        self.db_manager = db_manager
        self.channel = channel_instance
        self.is_running = False

    def start(self):
        """启动定时任务"""
        if self.is_running:
            return

        # 每日21:00执行提醒检查
        schedule.every().day.at("21:00").do(self.send_daily_reminders)

        # 启动后台线程
        self.is_running = True
        reminder_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        reminder_thread.start()

        logger.info("[Aspiration] 提醒调度器已启动")

    def _run_scheduler(self):
        """后台运行调度器"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次

    def send_daily_reminders(self):
        """发送每日提醒"""
        today = date.today()

        # 查找今日未打卡的活跃目标
        missed_users = self.db_manager.get_missed_checkin_users(today)

        for user_data in missed_users:
            user_id = user_data['user_id']
            goal_info = user_data['goal_info']

            # 生成提醒消息
            reminder_msg = self._generate_reminder_message(goal_info)

            # 发送提醒（需要认证服务号的客服接口权限）
            try:
                self.channel.send_active_message(user_id, reminder_msg)
                # 记录提醒日志
                self.db_manager.log_reminder_sent(user_id, goal_info['id'], today)
                logger.info(f"[Aspiration] 已向用户 {user_id} 发送提醒")
            except Exception as e:
                logger.error(f"[Aspiration] 发送提醒失败: {e}")
```

#### 2.4.2 主动推送消息实现
在`wechatmp_channel.py`中添加主动推送能力（需要认证服务号）：

```python
def send_active_message(self, user_id, message):
    """主动发送消息给用户（需要客服接口权限）"""
    if not self.access_token:
        logger.error("[WechatMP] 无access_token，无法主动发送消息")
        return False

    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={self.access_token}"

    data = {
        "touser": user_id,
        "msgtype": "text",
        "text": {
            "content": message
        }
    }

    try:
        response = requests.post(url, json=data)
        result = response.json()
        if result.get('errcode') == 0:
            return True
        else:
            logger.error(f"[WechatMP] 主动发送消息失败: {result}")
            return False
    except Exception as e:
        logger.error(f"[WechatMP] 主动发送消息异常: {e}")
        return False
```

### 2.5 AI集成方案

#### 2.5.1 AI提示词模板设计
```python
# ai_prompt_templates.py
class AIPromptTemplates:

    @staticmethod
    def get_encouragement_prompt(goal_info, checkin_info, user_stats):
        """生成鼓励提示词"""
        prompt = f"""你是一个温暖贴心的目标管理助手，请根据用户的打卡情况生成个性化的鼓励回复。

用户目标信息：
- 目标：{goal_info['description']}
- 计划天数：{goal_info['planned_days']}天
- 已开始：{goal_info['days_since_start']}天

今日打卡情况：
- 状态：{checkin_info['status']}
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
    def get_reminder_prompt(goal_info, user_stats):
        """生成提醒消息的AI优化提示词"""
        prompt = f"""请为用户生成一条温馨的目标提醒消息。

用户目标：{goal_info['description']}
已坚持：{user_stats['consecutive_days']}天
完成率：{user_stats['completion_rate']}%

生成一条80字以内的提醒消息，要求：
1. 温馨友善，不要有压迫感
2. 提及坚持天数，鼓励继续
3. 包含具体的行动指引
4. 使用适当的emoji增加亲和力

提醒内容："""
        return prompt
```

#### 2.5.2 AI回复生成器
```python
# ai_response_generator.py
from bot.bot_factory import create_bot

class AIResponseGenerator:
    def __init__(self):
        # 复用现有的AI Bot实例
        self.bot = create_bot("doubao")  # 或从配置中获取

    def generate_encouragement(self, goal_info, checkin_info, user_stats):
        """生成鼓励回复"""
        prompt = AIPromptTemplates.get_encouragement_prompt(
            goal_info, checkin_info, user_stats
        )

        try:
            response = self.bot.reply(prompt)
            return response.content if response else "加油！继续坚持！💪"
        except Exception as e:
            logger.error(f"[Aspiration] AI回复生成失败: {e}")
            return self._get_fallback_message(checkin_info['status'])

    def _get_fallback_message(self, status):
        """获取备用回复消息"""
        fallback_messages = {
            'completed': "太棒了！今天的目标达成了！继续保持这个势头！💪✨",
            'partial': "虽然没有完全完成，但有进展就是好的！明天继续努力！🌟",
            'failed': "没关系，明天是新的开始！每一次尝试都是进步！🌈💪"
        }
        return fallback_messages.get(status, "继续加油！💪")
```

## 3. 核心业务逻辑实现

### 3.1 目标管理器
```python
# goal_manager.py
class GoalManager:
    def __init__(self, db_manager):
        self.db = db_manager

    def create_goal(self, user_id, description, planned_days):
        """创建新目标"""
        # 检查是否有活跃目标
        active_goal = self.get_active_goal(user_id)
        if active_goal:
            return False, "您已有一个活跃目标，请先完成或删除现有目标"

        # 创建新目标
        start_date = date.today()
        end_date = start_date + timedelta(days=planned_days)

        goal_id = self.db.create_goal(
            user_id=user_id,
            description=description,
            planned_days=planned_days,
            start_date=start_date,
            end_date=end_date
        )

        return True, f"目标设定成功！开始您的{planned_days}天挑战吧！"

    def get_active_goal(self, user_id):
        """获取用户的活跃目标"""
        return self.db.get_active_goal(user_id)

    def get_goal_stats(self, goal_id):
        """获取目标统计信息"""
        return self.db.get_goal_statistics(goal_id)
```

### 3.2 打卡管理器
```python
# checkin_manager.py
class CheckInManager:
    def __init__(self, db_manager, ai_generator):
        self.db = db_manager
        self.ai_generator = ai_generator

    def record_checkin(self, user_id, status, note=None):
        """记录打卡"""
        # 获取活跃目标
        goal = self.db.get_active_goal(user_id)
        if not goal:
            return False, "您还没有设定目标，请先点击"立志"设定目标"

        # 检查今日是否已打卡
        today = date.today()
        existing_checkin = self.db.get_checkin_by_date(goal['id'], today)
        if existing_checkin:
            return False, "今日已经打卡过了哦！明天继续加油！"

        # 计算连续天数
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

        # 生成AI回复
        user_stats = self.db.get_user_statistics(user_id, goal['id'])
        checkin_info = {
            'status': status,
            'note': note
        }

        ai_response = self.ai_generator.generate_encouragement(
            goal, checkin_info, user_stats
        )

        # 更新AI回复到数据库
        self.db.update_checkin_ai_response(checkin_id, ai_response)

        return True, ai_response
```

## 4. 部署和配置指南

### 4.1 插件安装步骤

1. **创建插件目录**：
   ```bash
   mkdir -p plugins/aspiration
   ```

2. **部署插件文件**：将所有插件代码文件放入`plugins/aspiration/`目录

3. **配置插件**：
   ```json
   // plugins/aspiration/config.json
   {
       "enabled": true,
       "database_path": "data/aspiration.db",
       "reminder_time": "21:00",
       "max_goals_per_user": 1,
       "ai_enabled": true,
       "debug_mode": false
   }
   ```

4. **重启服务**：重启chatgpt-on-wechat服务以加载插件

### 4.2 微信公众号配置

1. **设置自定义菜单**：
   - 登录微信公众平台
   - 进入"自定义菜单"设置
   - 按照提供的JSON配置创建菜单

2. **启用客服接口**（如需主动推送）：
   - 确保公众号已认证为服务号
   - 在"开发"-"接口权限"中确认客服接口已开通

### 4.3 数据库备份策略

```python
# backup_scheduler.py
import shutil
from datetime import datetime

def backup_database():
    """备份数据库"""
    source = "data/aspiration.db"
    backup_name = f"data/backups/aspiration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    os.makedirs("data/backups", exist_ok=True)
    shutil.copy2(source, backup_name)

    logger.info(f"[Aspiration] 数据库已备份到: {backup_name}")

# 在ReminderScheduler中添加每日备份
schedule.every().day.at("02:00").do(backup_database)
```

## 5. 测试和验证

### 5.1 功能测试清单

- [ ] 目标设定流程测试
- [ ] 打卡记录功能测试
- [ ] AI回复生成测试
- [ ] 定时提醒功能测试
- [ ] 数据统计准确性测试
- [ ] 异常情况处理测试
- [ ] 并发用户操作测试

### 5.2 性能监控

```python
# 在关键方法中添加性能监控
import time
from functools import wraps

def performance_monitor(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        duration = end_time - start_time
        if duration > 2.0:  # 超过2秒记录警告
            logger.warning(f"[Aspiration] {func.__name__} 执行耗时: {duration:.2f}秒")

        return result
    return wrapper
```

## 6. 运维和监控

### 6.1 日志配置
```python
# 在插件中配置专门的日志记录
import logging

aspiration_logger = logging.getLogger('aspiration')
aspiration_logger.setLevel(logging.INFO)

handler = logging.FileHandler('logs/aspiration.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
aspiration_logger.addHandler(handler)
```

### 6.2 关键指标监控
- 每日活跃用户数
- 目标设定成功率
- 打卡完成率
- AI回复生成成功率
- 提醒发送成功率
- 系统响应时间

---

**文档版本**: v1.0
**创建日期**: 2024年12月
**最后更新**: 2024年12月
**适用项目**: chatgpt-on-wechat
**技术负责人**: 开发团队
