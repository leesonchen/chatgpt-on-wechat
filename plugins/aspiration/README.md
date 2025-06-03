# 立志功能插件

## 概述

立志功能插件是一个基于微信公众号的目标管理和督促系统，帮助用户设定目标、记录进度，并通过AI智能回复提供个性化的鼓励和建议。

## 功能特性

### 🎯 核心功能
- **目标设定**: 用户可以设定个人目标和坚持天数
- **打卡记录**: 每日记录目标执行情况
- **智能提醒**: 每天21:00自动提醒打卡
- **AI鼓励**: 基于用户历史数据生成个性化鼓励消息
- **数据统计**: 完整的目标进度和统计分析

### 📱 用户交互方式
- **微信菜单**: 通过自定义菜单快速操作
- **关键词触发**: 支持文字指令触发功能
- **智能对话**: 自然语言交互，AI理解用户意图

## 安装配置

### 1. 插件激活
在 `plugins/plugins.json` 中添加插件配置：
```json
{
    "plugins": {
        "Aspiration": {
            "enabled": true,
            "priority": 100
        }
    }
}
```

### 2. 配置参数
修改 `plugins/aspiration/config.json`：
```json
{
    "enabled": true,
    "database_path": "data/aspiration.db",
    "reminder_time": "21:00",
    "max_goals_per_user": 1,
    "ai_enabled": true,
    "debug_mode": false,
    "timezone": "Asia/Shanghai",
    "max_check_days": 1000,
    "default_goal_days": 30
}
```

### 3. 微信公众号菜单配置
在微信公众平台后台配置自定义菜单：

```json
{
    "button": [
        {
            "name": "智能对话",
            "type": "view",
            "url": "你的对话页面URL"
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
                    "name": "目标历史",
                    "key": "GOAL_HISTORY"
                }
            ]
        },
        {
            "name": "其他功能",
            "type": "click",
            "key": "OTHER_FEATURES"
        }
    ]
}
```

## 使用指南

### 📝 设定目标
1. 点击"立志"菜单或发送"立志"
2. 描述您的目标（如：每天读书30分钟）
3. 设定坚持天数（如：30天）
4. 系统确认目标创建成功

### ✅ 打卡记录
用户可以通过多种方式打卡：

**快捷选项**：
- 回复「1」或「已完成」- 100%完成目标
- 回复「2」或「部分完成」- 完成了一部分
- 回复「3」或「未完成」- 今天没有行动

**文字描述**：
- "今天读书45分钟，完成了目标"
- "只跑了15分钟，部分完成"
- "今天太忙了，没有时间运动"

### 📊 查看进度
- **我的目标**: 查看当前目标状态和进度
- **目标历史**: 查看所有历史目标和统计数据

### 🔔 提醒功能
- 每天21:00自动检查未打卡用户
- 发送个性化提醒消息
- 连续未打卡会发送鼓励消息

## 技术架构

### 🏗️ 组件结构
```
aspiration/
├── aspiration_plugin.py      # 主插件文件
├── database_manager.py       # 数据库管理
├── goal_manager.py          # 目标管理
├── checkin_manager.py       # 打卡管理
├── reminder_scheduler.py    # 提醒调度
├── ai_response_generator.py # AI回复生成
├── ai_prompt_templates.py   # AI提示词模板
├── message_templates.py     # 消息模板
├── config.json             # 插件配置
└── test_aspiration.py      # 测试脚本
```

### 🗄️ 数据库设计
- **user_goals**: 用户目标表
- **check_in_records**: 打卡记录表
- **reminder_logs**: 提醒日志表

### 🤖 AI集成
- 复用现有AI Bot实例
- 个性化鼓励消息生成
- 基于用户历史数据的智能建议

## 开发调试

### 运行测试
```bash
cd plugins/aspiration
python test_aspiration.py
```

### 查看日志
```bash
tail -f run.log | grep Aspiration
```

### 常见问题

**Q: 插件启动失败？**
A: 检查配置文件格式，确保数据库目录存在写入权限

**Q: AI回复不工作？**
A: 确认AI模型配置正确，检查网络连接

**Q: 定时提醒不发送？**
A: 个人订阅号无法主动推送，需要认证服务号

**Q: 数据库错误？**
A: 检查数据库文件权限，删除数据库文件重新初始化

## 版本历史

### v1.0.0 (2025-05-29)
- ✅ 基础目标管理功能
- ✅ 打卡记录系统
- ✅ AI智能回复
- ✅ 定时提醒功能
- ✅ 数据统计分析

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交代码
4. 创建 Pull Request

## 许可证

本项目遵循 MIT 许可证。

## 联系支持

如有问题请提交 Issue 或联系开发团队。

---

让目标不再是空想，让坚持成为习惯！💪
