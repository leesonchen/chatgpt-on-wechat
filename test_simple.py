#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化的立志功能测试脚本
"""

import sys
import os

print("🎯 开始立志功能插件测试")
print("=" * 50)

# 检查项目结构
project_root = os.getcwd()
print(f"项目根目录: {project_root}")

plugins_path = os.path.join(project_root, "plugins")
aspiration_path = os.path.join(plugins_path, "aspiration")

print(f"插件目录存在: {os.path.exists(plugins_path)}")
print(f"立志插件目录存在: {os.path.exists(aspiration_path)}")

if os.path.exists(aspiration_path):
    print("立志插件文件列表:")
    for file in os.listdir(aspiration_path):
        print(f"  - {file}")

# 添加项目根目录到Python路径
sys.path.insert(0, project_root)
print(f"Python路径已添加: {project_root}")

# 尝试导入模块
try:
    from plugins.aspiration.database_manager import DatabaseManager
    print("✅ DatabaseManager 导入成功")
except ImportError as e:
    print(f"❌ DatabaseManager 导入失败: {e}")

try:
    from plugins.aspiration.goal_manager import GoalManager
    print("✅ GoalManager 导入成功")
except ImportError as e:
    print(f"❌ GoalManager 导入失败: {e}")

try:
    from plugins.aspiration.checkin_manager import CheckInManager
    print("✅ CheckInManager 导入成功")
except ImportError as e:
    print(f"❌ CheckInManager 导入失败: {e}")

try:
    from plugins.aspiration.ai_response_generator import AIResponseGenerator
    print("✅ AIResponseGenerator 导入成功")
except ImportError as e:
    print(f"❌ AIResponseGenerator 导入失败: {e}")

try:
    from plugins.aspiration.reminder_scheduler import ReminderScheduler
    print("✅ ReminderScheduler 导入成功")
except ImportError as e:
    print(f"❌ ReminderScheduler 导入失败: {e}")

print("=" * 50)
print("🏁 基础导入测试完成")
