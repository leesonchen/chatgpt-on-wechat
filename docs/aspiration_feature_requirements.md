# "立志"功能需求文档

## 1. 功能概述

### 1.1 功能简介
"立志"功能是一个基于微信公众号的目标管理和督促系统，帮助用户设定目标、记录进度，并通过AI智能回复提供个性化的鼓励和建议。

### 1.2 核心价值
- 帮助用户建立和维持良好习惯
- 通过AI个性化反馈提升用户坚持动力
- 提供数据化的目标管理体验
- 增强公众号用户粘性和活跃度

## 2. 功能架构

### 2.1 系统组件
```
立志功能模块
├── 用户交互层
│   ├── 微信公众号菜单
│   ├── 消息处理器
│   └── 回复生成器
├── 业务逻辑层
│   ├── 目标管理服务
│   ├── 打卡记录服务
│   ├── 提醒调度服务
│   └── AI交互服务
├── 数据存储层
│   ├── 用户目标数据
│   ├── 打卡记录数据
│   └── 用户行为分析数据
└── 定时任务层
    ├── 每日提醒任务
    └── 数据统计任务
```

### 2.2 技术实现方案
- **插件化实现**: 基于现有插件系统开发，便于维护和扩展
- **数据存储**: 使用SQLite本地数据库存储用户数据
- **定时任务**: 使用Python的schedule库实现定时提醒
- **AI集成**: 复用现有的AI Bot接口

## 3. 详细功能需求

### 3.1 微信公众号菜单配置

#### 3.1.1 菜单结构
```
主菜单
├── 智能对话
├── 立志管理
│   ├── 立志 (设定目标)
│   ├── 打卡 (记录进度)
│   ├── 我的目标 (查看当前目标)
│   └── 目标历史 (查看历史记录)
└── 其他功能
```

#### 3.1.2 菜单事件处理
- **立志**: 触发目标设定流程
- **打卡**: 触发打卡记录流程
- **我的目标**: 显示当前活跃目标列表
- **目标历史**: 显示历史目标和统计数据

### 3.2 目标管理功能

#### 3.2.1 目标设定流程
1. **触发方式**:
   - 点击"立志"菜单
   - 发送关键词"立志"、"设定目标"、"新目标"

2. **交互流程**:
   ```
   用户: 点击"立志"菜单
   系统: 请描述您要设定的目标（例如：每天跑步30分钟）
   用户: 每天读书1小时
   系统: 目标已设定："每天读书1小时"
         计划执行多少天？（输入数字，如30表示30天）
   用户: 30
   系统: 太棒了！您的30天读书计划已启动！
         每天晚上21:00我会提醒您打卡哦～
         现在就开始第一天的打卡吧！发送"打卡"记录今天的进度。
   ```

3. **目标属性**:
   - 目标描述（用户输入的目标内容）
   - 计划天数（用户设定的执行周期）
   - 创建时间
   - 状态（进行中/已完成/已放弃）
   - 当前进度（已打卡天数）

#### 3.2.2 目标管理规则
- 每个用户同时只能有一个活跃目标
- 设定新目标前需确认是否替换当前目标
- 目标完成后自动归档到历史记录

### 3.3 打卡功能

#### 3.3.1 打卡流程
1. **触发方式**:
   - 点击"打卡"菜单
   - 发送关键词"打卡"、"完成"、"done"

2. **交互流程**:
   ```
   用户: 点击"打卡"菜单
   系统: 请分享今天的执行情况：
         1. 已完成 ✅
         2. 未完成 ❌
         3. 部分完成 ⚡
   用户: 1
   系统: [AI生成个性化鼓励] 太棒了！您已经坚持了X天，继续加油！
         明天记得继续哦～
   ```

3. **打卡状态**:
   - **已完成**: 完全按计划执行
   - **未完成**: 当天未执行目标
   - **部分完成**: 部分执行目标

#### 3.3.2 打卡记录属性
- 打卡日期
- 完成状态
- 用户备注（可选）
- AI回复内容
- 连续打卡天数

### 3.4 智能提醒功能

#### 3.4.1 提醒机制
- **提醒时间**: 每天晚上21:00
- **提醒条件**: 当天未打卡且有活跃目标
- **提醒内容**: 个性化提醒消息

#### 3.4.2 提醒消息模板
```
🌟 立志提醒 🌟

亲爱的朋友，今天的目标"[目标描述]"还没有打卡哦～

您已经坚持了[X]天，不要让努力白费！
快来分享今天的执行情况吧：

回复"打卡"记录今天的进度
回复"1"表示已完成
回复"2"表示未完成
回复"3"表示部分完成

[AI个性化鼓励语]
```

### 3.5 AI智能回复功能

#### 3.5.1 AI回复场景
1. **打卡成功时**: 根据连续天数和历史表现生成鼓励
2. **打卡失败时**: 根据失败原因和历史数据生成安慰和建议
3. **提醒消息**: 根据用户坚持情况生成个性化提醒

#### 3.5.2 AI Prompt设计
```python
# 打卡成功Prompt
SUCCESS_PROMPT = """
用户刚刚完成了目标打卡，请根据以下信息生成一条鼓励回复（50字以内）：

目标：{goal_description}
连续完成天数：{consecutive_days}
总计划天数：{total_days}
历史完成率：{completion_rate}%

要求：
1. 语气积极正面，充满鼓励
2. 可以提及具体的坚持天数
3. 适当展望未来进展
4. 使用emoji增加亲和力
"""

# 打卡失败Prompt
FAIL_PROMPT = """
用户今天没有完成目标，请根据以下信息生成一条安慰和鼓励的回复（80字以内）：

目标：{goal_description}
连续完成天数：{consecutive_days}
失败次数：{fail_count}
历史完成率：{completion_rate}%

要求：
1. 理解和安慰，不要责备
2. 鼓励明天重新开始
3. 提供具体的建议或方法
4. 保持温暖和支持的语气
"""
```

### 3.6 数据统计功能

#### 3.6.1 个人统计
- 当前目标进度
- 历史目标完成情况
- 总打卡天数
- 平均完成率
- 最长连续天数

#### 3.6.2 统计报告
```
📊 您的立志报告 📊

🎯 当前目标：每天读书1小时
📅 已坚持：15/30天 (50%)
🔥 连续打卡：3天
⭐ 历史完成率：78%
🏆 最长连续：12天

💪 继续加油，您已经超越了60%的用户！
```

## 4. 数据库设计

### 4.1 用户目标表 (user_goals)
```sql
CREATE TABLE user_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(64) NOT NULL,
    goal_description TEXT NOT NULL,
    planned_days INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    status VARCHAR(20) DEFAULT 'active', -- active/completed/abandoned
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 打卡记录表 (check_in_records)
```sql
CREATE TABLE check_in_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id INTEGER NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    check_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL, -- completed/failed/partial
    user_note TEXT,
    ai_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (goal_id) REFERENCES user_goals(id)
);
```

### 4.3 提醒记录表 (reminder_logs)
```sql
CREATE TABLE reminder_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(64) NOT NULL,
    goal_id INTEGER NOT NULL,
    reminder_date DATE NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (goal_id) REFERENCES user_goals(id)
);
```

## 5. 技术实现细节

### 5.1 插件结构
```
plugins/aspiration/
├── __init__.py
├── aspiration.py          # 主插件文件
├── config.json.template   # 配置模板
├── database.py           # 数据库操作
├── scheduler.py          # 定时任务
├── ai_prompts.py         # AI提示词
└── README.md            # 插件说明
```

### 5.2 关键类设计
```python
class AspirationPlugin(Plugin):
    """立志功能主插件类"""

    def __init__(self):
        # 初始化数据库、调度器等
        pass

    def on_handle_context(self, e_context):
        # 处理用户消息
        pass

    def handle_goal_setting(self, context):
        # 处理目标设定
        pass

    def handle_check_in(self, context):
        # 处理打卡
        pass

class GoalManager:
    """目标管理器"""

    def create_goal(self, user_id, description, days):
        # 创建新目标
        pass

    def get_active_goal(self, user_id):
        # 获取活跃目标
        pass

class CheckInManager:
    """打卡管理器"""

    def record_check_in(self, goal_id, status, note=None):
        # 记录打卡
        pass

    def get_check_in_stats(self, goal_id):
        # 获取打卡统计
        pass

class ReminderScheduler:
    """提醒调度器"""

    def start_scheduler(self):
        # 启动定时任务
        pass

    def send_daily_reminders(self):
        # 发送每日提醒
        pass
```

### 5.3 微信公众号菜单配置
```python
# 在WechatMPChannel中添加菜单配置
MENU_CONFIG = {
    "button": [
        {
            "name": "智能对话",
            "type": "click",
            "key": "CHAT"
        },
        {
            "name": "立志管理",
            "sub_button": [
                {
                    "name": "立志",
                    "type": "click",
                    "key": "SET_GOAL"
                },
                {
                    "name": "打卡",
                    "type": "click",
                    "key": "CHECK_IN"
                },
                {
                    "name": "我的目标",
                    "type": "click",
                    "key": "MY_GOALS"
                },
                {
                    "name": "目标历史",
                    "type": "click",
                    "key": "GOAL_HISTORY"
                }
            ]
        }
    ]
}
```

## 6. 开发计划

### 6.1 开发阶段

#### 第一阶段：基础功能（1-2周）
- [ ] 创建插件基础结构
- [ ] 实现数据库设计和初始化
- [ ] 实现目标设定功能
- [ ] 实现基础打卡功能
- [ ] 集成微信公众号菜单

#### 第二阶段：智能功能（1周）
- [ ] 实现AI智能回复
- [ ] 优化用户交互流程
- [ ] 添加数据统计功能

#### 第三阶段：提醒系统（1周）
- [ ] 实现定时提醒功能
- [ ] 添加提醒日志记录
- [ ] 优化提醒策略

#### 第四阶段：完善优化（1周）
- [ ] 添加异常处理
- [ ] 性能优化
- [ ] 用户体验优化
- [ ] 测试和文档完善

### 6.2 测试计划
- 单元测试：数据库操作、业务逻辑
- 集成测试：微信公众号交互、AI回复
- 用户测试：真实用户场景验证

## 7. 风险评估

### 7.1 技术风险
- **数据库性能**: 用户量增长可能影响SQLite性能
- **定时任务稳定性**: 需要确保提醒任务的可靠执行
- **AI回复质量**: 需要持续优化Prompt以提升回复质量

### 7.2 业务风险
- **用户粘性**: 需要设计有效的激励机制保持用户活跃
- **功能复杂度**: 避免功能过于复杂影响用户体验

### 7.3 解决方案
- 考虑后续迁移到MySQL等更强大的数据库
- 实现任务监控和自动重启机制
- 建立用户反馈收集机制持续优化

## 8. 后续扩展

### 8.1 功能扩展
- 多目标并行管理
- 目标分享和社交功能
- 成就系统和积分奖励
- 数据可视化报表
- 目标模板和推荐

### 8.2 技术扩展
- 支持其他消息平台（企业微信、钉钉等）
- 集成更多AI模型
- 添加语音交互支持
- 实现数据导出功能

---

**文档版本**: v1.0
**创建日期**: 2024年12月
**最后更新**: 2024年12月
**负责人**: 开发团队