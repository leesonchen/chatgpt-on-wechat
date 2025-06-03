#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
立志插件核心功能测试脚本
直接测试核心模块，避免插件管理器的复杂性
"""

import sys
import os
import sqlite3
from datetime import date, datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_database_manager():
    """测试数据库管理器"""
    print("=== 测试数据库管理器 ===")

    try:
        # 直接导入数据库管理器
        sys.path.append(os.path.join(project_root, 'plugins', 'aspiration'))
        from database_manager import DatabaseManager

        # 创建测试数据库
        test_db_path = "data/test_core_aspiration.db"
        os.makedirs("data", exist_ok=True)

        db_manager = DatabaseManager(test_db_path)
        print("✓ 数据库管理器初始化成功")

        # 测试创建目标
        test_user_id = "test_user_core_123"
        test_description = "每天学习Python 1小时"
        test_days = 30

        goal_id = db_manager.create_goal(test_user_id, test_description, test_days)
        print(f"✓ 创建目标成功，ID: {goal_id}")

        # 测试获取活跃目标
        active_goal = db_manager.get_active_goal(test_user_id)
        if active_goal:
            print(f"✓ 获取活跃目标成功: {active_goal['goal_description']}")
        else:
            print("✗ 获取活跃目标失败")
            return False

        # 测试创建打卡记录
        checkin_id = db_manager.create_checkin(
            goal_id=goal_id,
            user_id=test_user_id,
            check_date=date.today(),
            status="completed",
            note="今天学习了Python基础语法",
            consecutive_days=1
        )
        print(f"✓ 创建打卡记录成功，ID: {checkin_id}")

        # 测试获取打卡记录
        checkin_record = db_manager.get_checkin_by_date(goal_id, date.today())
        if checkin_record:
            print(f"✓ 获取打卡记录成功: {checkin_record['status']}")
        else:
            print("✗ 获取打卡记录失败")
            return False

        # 测试统计功能
        stats = db_manager.get_user_stats(test_user_id)
        if stats:
            print(f"✓ 获取用户统计成功: 总打卡{stats['total_checkins']}次")
        else:
            print("✗ 获取用户统计失败")

        # 清理测试数据
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            print("✓ 清理测试数据库")

        return True

    except Exception as e:
        print(f"✗ 数据库管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_goal_manager():
    """测试目标管理器"""
    print("\n=== 测试目标管理器 ===")

    try:
        # 导入相关模块
        sys.path.append(os.path.join(project_root, 'plugins', 'aspiration'))
        from database_manager import DatabaseManager
        from goal_manager import GoalManager

        # 创建测试数据库和管理器
        test_db_path = "data/test_core_goal_manager.db"
        os.makedirs("data", exist_ok=True)

        db_manager = DatabaseManager(test_db_path)
        goal_manager = GoalManager(db_manager)

        print("✓ 目标管理器初始化成功")

        # 测试创建目标
        test_user_id = "test_user_goal_456"
        success, message = goal_manager.create_goal(
            user_id=test_user_id,
            description="每天阅读30分钟",
            planned_days=21
        )

        if success:
            print("✓ 目标创建成功")
            print(f"  消息长度: {len(message)} 字符")
        else:
            print(f"✗ 目标创建失败: {message}")
            return False

        # 测试获取目标详情
        success, details = goal_manager.get_goal_details(test_user_id)
        if success:
            print("✓ 获取目标详情成功")
            print(f"  详情长度: {len(details)} 字符")
        else:
            print(f"✗ 获取目标详情失败: {details}")
            return False

        # 测试重复创建目标（应该失败）
        success, message = goal_manager.create_goal(
            user_id=test_user_id,
            description="另一个目标",
            planned_days=15
        )

        if not success:
            print("✓ 重复创建目标正确被拒绝")
        else:
            print("✗ 重复创建目标应该被拒绝")
            return False

        # 清理测试数据
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            print("✓ 清理测试数据库")

        return True

    except Exception as e:
        print(f"✗ 目标管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_checkin_manager():
    """测试打卡管理器"""
    print("\n=== 测试打卡管理器 ===")

    try:
        # 导入相关模块
        sys.path.append(os.path.join(project_root, 'plugins', 'aspiration'))
        from database_manager import DatabaseManager
        from ai_response_generator import AIResponseGenerator
        from checkin_manager import CheckInManager

        # 创建测试数据库和管理器
        test_db_path = "data/test_core_checkin_manager.db"
        os.makedirs("data", exist_ok=True)

        db_manager = DatabaseManager(test_db_path)
        ai_generator = AIResponseGenerator()
        checkin_manager = CheckInManager(db_manager, ai_generator)

        print("✓ 打卡管理器初始化成功")

        # 先创建一个目标
        test_user_id = "test_user_checkin_789"
        goal_id = db_manager.create_goal(test_user_id, "每天运动30分钟", 14)
        print(f"✓ 创建测试目标，ID: {goal_id}")

        # 测试打卡
        success, message = checkin_manager.record_checkin(
            user_id=test_user_id,
            status="completed",
            note="今天跑步30分钟"
        )

        if success:
            print("✓ 打卡记录成功")
            print(f"  消息长度: {len(message)} 字符")
        else:
            print(f"✗ 打卡记录失败: {message}")
            return False

        # 测试重复打卡（应该失败）
        success, message = checkin_manager.record_checkin(
            user_id=test_user_id,
            status="completed",
            note="重复打卡测试"
        )

        if not success:
            print("✓ 重复打卡正确被拒绝")
        else:
            print("✗ 重复打卡应该被拒绝")
            return False

        # 测试无目标打卡（应该失败）
        success, message = checkin_manager.record_checkin(
            user_id="no_goal_user",
            status="completed",
            note="无目标打卡测试"
        )

        if not success:
            print("✓ 无目标打卡正确被拒绝")
        else:
            print("✗ 无目标打卡应该被拒绝")
            return False

        # 清理测试数据
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            print("✓ 清理测试数据库")

        return True

    except Exception as e:
        print(f"✗ 打卡管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_response_generator():
    """测试AI回复生成器"""
    print("\n=== 测试AI回复生成器 ===")

    try:
        # 导入相关模块
        sys.path.append(os.path.join(project_root, 'plugins', 'aspiration'))
        from ai_response_generator import AIResponseGenerator

        # 创建AI回复生成器
        ai_generator = AIResponseGenerator()
        print("✓ AI回复生成器初始化成功")

        # 测试数据
        goal_info = {
            'goal_description': '每天学习Python 1小时',
            'planned_days': 30,
            'start_date': date.today()
        }

        checkin_info = {
            'status': 'completed',
            'user_note': '今天学习了Python基础语法',
            'consecutive_days': 5
        }

        user_stats = {
            'total_checkins': 5,
            'completion_rate': 0.8,
            'current_streak': 5
        }

        # 测试生成鼓励回复
        response = ai_generator.generate_encouragement(goal_info, checkin_info, user_stats)
        if response and len(response) > 10:
            print("✓ 生成鼓励回复成功")
            print(f"  回复长度: {len(response)} 字符")
        else:
            print("✗ 生成鼓励回复失败或内容过短")
            return False

        # 测试生成提醒消息
        reminder = ai_generator.generate_reminder(goal_info, user_stats)
        if reminder and len(reminder) > 10:
            print("✓ 生成提醒消息成功")
            print(f"  提醒长度: {len(reminder)} 字符")
        else:
            print("✗ 生成提醒消息失败或内容过短")
            return False

        return True

    except Exception as e:
        print(f"✗ AI回复生成器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config_loading():
    """测试配置加载"""
    print("\n=== 测试配置加载 ===")

    try:
        config_path = os.path.join(project_root, 'plugins', 'aspiration', 'config.json')

        if not os.path.exists(config_path):
            print("✗ 配置文件不存在")
            return False

        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        print("✓ 配置文件加载成功")

        # 检查必要的配置项
        required_keys = ['enabled', 'database_path', 'reminder_time', 'ai_enabled']
        for key in required_keys:
            if key in config:
                print(f"  ✓ {key}: {config[key]}")
            else:
                print(f"  ✗ 缺少配置项: {key}")
                return False

        return True

    except Exception as e:
        print(f"✗ 配置加载测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("立志插件核心功能测试开始...\n")

    test_results = []

    # 运行各项测试
    test_results.append(("配置加载", test_config_loading()))
    test_results.append(("数据库管理器", test_database_manager()))
    test_results.append(("目标管理器", test_goal_manager()))
    test_results.append(("打卡管理器", test_checkin_manager()))
    test_results.append(("AI回复生成器", test_ai_response_generator()))

    # 输出测试结果
    print("\n=== 测试结果汇总 ===")
    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{total} 项测试通过")

    if passed == total:
        print("🎉 所有核心功能测试通过！立志插件功能正常")
        return True
    else:
        print("⚠️  部分测试失败，请检查相关功能")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)