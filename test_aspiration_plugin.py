#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
立志插件功能测试脚本
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_plugin_loading():
    """测试插件加载"""
    print("=== 测试插件加载 ===")

    try:
        from plugins.plugin_manager import PluginManager

        # 创建插件管理器实例
        plugin_manager = PluginManager()

        # 扫描并加载插件
        print("扫描插件...")
        new_plugins = plugin_manager.scan_plugins()

        # 检查立志插件是否被加载
        aspiration_found = False
        for name, plugin_cls in plugin_manager.plugins.items():
            if 'aspiration' in name.lower():
                aspiration_found = True
                print(f"✓ 找到立志插件: {name}")
                print(f"  - 版本: {plugin_cls.version}")
                print(f"  - 描述: {plugin_cls.desc}")
                print(f"  - 作者: {plugin_cls.author}")
                print(f"  - 路径: {plugin_cls.path}")
                print(f"  - 启用状态: {plugin_cls.enabled}")
                break

        if not aspiration_found:
            print("✗ 未找到立志插件")
            return False

        return True

    except Exception as e:
        print(f"✗ 插件加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_operations():
    """测试数据库操作"""
    print("\n=== 测试数据库操作 ===")

    try:
        from plugins.aspiration.database_manager import DatabaseManager

        # 创建测试数据库
        test_db_path = "data/test_aspiration.db"
        db_manager = DatabaseManager(test_db_path)

        print("✓ 数据库管理器初始化成功")

        # 测试创建目标
        test_user_id = "test_user_123"
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
        from datetime import date
        checkin_id = db_manager.create_checkin(
            goal_id=goal_id,
            user_id=test_user_id,
            check_date=date.today(),
            status="completed",
            user_note="今天学习了Python基础语法",
            ai_response="很棒！继续保持！",
            consecutive_days=1
        )
        print(f"✓ 创建打卡记录成功，ID: {checkin_id}")

        # 清理测试数据
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
            print("✓ 清理测试数据库")

        return True

    except Exception as e:
        print(f"✗ 数据库操作测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_goal_manager():
    """测试目标管理器"""
    print("\n=== 测试目标管理器 ===")

    try:
        from plugins.aspiration.database_manager import DatabaseManager
        from plugins.aspiration.goal_manager import GoalManager

        # 创建测试数据库和管理器
        test_db_path = "data/test_goal_manager.db"
        db_manager = DatabaseManager(test_db_path)
        goal_manager = GoalManager(db_manager)

        print("✓ 目标管理器初始化成功")

        # 测试创建目标
        test_user_id = "test_user_456"
        success, message = goal_manager.create_goal(
            user_id=test_user_id,
            description="每天阅读30分钟",
            planned_days=21
        )

        if success:
            print("✓ 目标创建成功")
            print(f"  消息: {message[:50]}...")
        else:
            print(f"✗ 目标创建失败: {message}")
            return False

        # 测试获取目标详情
        success, details = goal_manager.get_goal_details(test_user_id)
        if success:
            print("✓ 获取目标详情成功")
        else:
            print(f"✗ 获取目标详情失败: {details}")

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
        from plugins.aspiration.database_manager import DatabaseManager
        from plugins.aspiration.ai_response_generator import AIResponseGenerator
        from plugins.aspiration.checkin_manager import CheckInManager

        # 创建测试数据库和管理器
        test_db_path = "data/test_checkin_manager.db"
        db_manager = DatabaseManager(test_db_path)
        ai_generator = AIResponseGenerator()
        checkin_manager = CheckInManager(db_manager, ai_generator)

        print("✓ 打卡管理器初始化成功")

        # 先创建一个目标
        test_user_id = "test_user_789"
        goal_id = db_manager.create_goal(test_user_id, "每天运动30分钟", 14)

        # 测试打卡
        success, message = checkin_manager.record_checkin(
            user_id=test_user_id,
            status="completed",
            note="今天跑步30分钟"
        )

        if success:
            print("✓ 打卡记录成功")
            print(f"  消息: {message[:50]}...")
        else:
            print(f"✗ 打卡记录失败: {message}")

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

def main():
    """主测试函数"""
    print("立志插件功能测试开始...\n")

    # 确保数据目录存在
    os.makedirs("data", exist_ok=True)

    test_results = []

    # 运行各项测试
    test_results.append(("插件加载", test_plugin_loading()))
    test_results.append(("数据库操作", test_database_operations()))
    test_results.append(("目标管理器", test_goal_manager()))
    test_results.append(("打卡管理器", test_checkin_manager()))

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
        print("🎉 所有测试通过！立志插件功能正常")
        return True
    else:
        print("⚠️  部分测试失败，请检查相关功能")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)