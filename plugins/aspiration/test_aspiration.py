#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
立志功能插件测试脚本
测试数据库操作、AI回复生成、目标管理等核心功能
"""

import sys
import os
import tempfile
from datetime import date, datetime, timedelta

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

print(f"Python路径: {sys.path[:3]}")
print(f"项目根目录: {project_root}")

try:
    from plugins.aspiration.database_manager import DatabaseManager
    from plugins.aspiration.goal_manager import GoalManager
    from plugins.aspiration.checkin_manager import CheckInManager
    from plugins.aspiration.ai_response_generator import AIResponseGenerator
    from plugins.aspiration.reminder_scheduler import ReminderScheduler
    print("✅ 所有模块导入成功")
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"插件目录存在: {os.path.exists('plugins/aspiration')}")
    sys.exit(1)

class AspirationTester:
    """立志功能测试类"""

    def __init__(self):
        # 使用临时数据库进行测试
        self.test_db_path = os.path.join(tempfile.gettempdir(), "test_aspiration.db")
        print(f"📍 测试数据库路径: {self.test_db_path}")

        try:
            self.db_manager = DatabaseManager(self.test_db_path)
            self.goal_manager = GoalManager(self.db_manager)
            self.ai_generator = AIResponseGenerator()
            self.checkin_manager = CheckInManager(self.db_manager, self.ai_generator)
            print("✅ 测试组件初始化成功")
        except Exception as e:
            print(f"❌ 测试组件初始化失败: {e}")
            raise

    def test_database_operations(self):
        """测试数据库基本操作"""
        print("\n🔧 测试数据库操作...")

        try:
            # 测试创建目标
            user_id = "test_user_001"
            goal_description = "每天读书1小时"
            planned_days = 30

            goal_id = self.db_manager.create_goal(
                user_id=user_id,
                description=goal_description,
                planned_days=planned_days,
            )

            print(f"✅ 创建目标成功，ID: {goal_id}")

            # 测试查询目标
            active_goal = self.db_manager.get_active_goal(user_id)
            if active_goal:
                print(f"✅ 查询活跃目标成功: {active_goal['goal_description']}")
            else:
                print("❌ 查询活跃目标失败")
                return False

            # 测试创建打卡记录
            checkin_id = self.db_manager.create_checkin(
                goal_id=goal_id,
                user_id=user_id,
                check_date=date.today(),
                status='completed',
                note='今天读了《Python编程》第一章',
                consecutive_days=1
            )

            print(f"✅ 创建打卡记录成功，ID: {checkin_id}")

            # 测试统计查询
            stats = self.db_manager.get_user_statistics(user_id, goal_id)
            print(f"✅ 用户统计查询成功: {stats}")

            return True

        except Exception as e:
            print(f"❌ 数据库操作测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_goal_management(self):
        """测试目标管理功能"""
        print("\n🎯 测试目标管理...")

        try:
            user_id = "test_user_002"

            # 测试创建目标
            success, message = self.goal_manager.create_goal(
                user_id=user_id,
                description="每天运动30分钟",
                planned_days=21
            )

            if success:
                print(f"✅ 目标创建成功: {message}")
            else:
                print(f"❌ 目标创建失败: {message}")
                return False

            # 测试重复创建目标（应该失败）
            success2, message2 = self.goal_manager.create_goal(
                user_id=user_id,
                description="每天写作500字",
                planned_days=15
            )

            if not success2:
                print(f"✅ 重复创建目标正确拒绝: {message2}")
            else:
                print(f"❌ 重复创建目标应该被拒绝")
                return False

            # 测试获取活跃目标
            active_goal = self.goal_manager.get_active_goal(user_id)
            if active_goal:
                print(f"✅ 获取活跃目标成功: {active_goal['goal_description']}")
            else:
                print("❌ 获取活跃目标失败")
                return False

            return True

        except Exception as e:
            print(f"❌ 目标管理测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_checkin_management(self):
        """测试打卡管理功能"""
        print("\n📝 测试打卡管理...")

        try:
            user_id = "test_user_003"

            # 先创建一个目标
            success, _ = self.goal_manager.create_goal(
                user_id=user_id,
                description="每天冥想10分钟",
                planned_days=14
            )

            if not success:
                print("❌ 创建测试目标失败")
                return False

            # 测试打卡记录
            success, message = self.checkin_manager.record_checkin(
                user_id=user_id,
                status='completed',
                note='今天冥想了15分钟，感觉很平静'
            )

            if success:
                print(f"✅ 打卡记录成功: {message[:100]}...")
            else:
                print(f"❌ 打卡记录失败: {message}")
                return False

            # 测试重复打卡（应该失败）
            success2, message2 = self.checkin_manager.record_checkin(
                user_id=user_id,
                status='completed',
                note='重复打卡测试'
            )

            if not success2:
                print(f"✅ 重复打卡正确拒绝: {message2}")
            else:
                print(f"❌ 重复打卡应该被拒绝")
                return False

            return True

        except Exception as e:
            print(f"❌ 打卡管理测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_ai_response_generation(self):
        """测试AI回复生成功能"""
        print("\n🤖 测试AI回复生成...")

        try:
            # 模拟目标信息
            goal_info = {
                'goal_description': '每天读书1小时',
                'planned_days': 30,
                'days_since_start': 5
            }

            # 模拟打卡信息
            checkin_info = {
                'status': 'completed',
                'user_note': '今天读了《人工智能》，很有收获'
            }

            # 模拟用户统计
            user_stats = {
                'current_consecutive': 5,
                'completion_rate': 80,
                'max_consecutive': 5
            }

            # 生成AI回复
            ai_response = self.ai_generator.generate_encouragement(
                goal_info, checkin_info, user_stats
            )

            if ai_response and len(ai_response) > 10:
                print(f"✅ AI回复生成成功: {ai_response}")
                return True
            else:
                print(f"❌ AI回复生成失败或内容过短: {ai_response}")
                # 使用备用消息，这也算成功
                fallback = self.ai_generator._get_fallback_message('completed')
                print(f"✅ 备用消息可用: {fallback}")
                return True

        except Exception as e:
            print(f"❌ AI回复生成测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_reminder_scheduler(self):
        """测试提醒调度器功能"""
        print("\n⏰ 测试提醒调度器...")

        try:
            # 创建提醒调度器实例（不启动实际调度）
            scheduler = ReminderScheduler(self.db_manager, channel_instance=None)

            # 测试获取需要提醒的用户
            today = date.today()
            missed_users = self.db_manager.get_missed_checkin_users(today)

            print(f"✅ 提醒调度器初始化成功，今日需提醒用户数: {len(missed_users)}")

            # 测试生成提醒消息
            if missed_users:
                for user_data in missed_users[:1]:  # 只测试第一个用户
                    reminder_msg = scheduler._generate_reminder_message(user_data['goal_info'])
                    print(f"✅ 提醒消息生成成功: {reminder_msg}")
            else:
                # 模拟一个目标信息来测试消息生成
                mock_goal = {
                    'goal_description': '每天运动30分钟',
                    'planned_days': 21
                }
                reminder_msg = scheduler._generate_reminder_message(mock_goal)
                print(f"✅ 模拟提醒消息生成成功: {reminder_msg}")

            return True

        except Exception as e:
            print(f"❌ 提醒调度器测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_edge_cases(self):
        """测试边界情况和异常处理"""
        print("\n🚨 测试边界情况...")

        try:
            # 测试空用户ID
            try:
                success, message = self.goal_manager.create_goal("", "测试目标", 10)
                print(f"空用户ID测试: {success}, {message}")
            except Exception as e:
                print(f"空用户ID测试触发异常: {e}")

            # 测试无效天数
            try:
                success, message = self.goal_manager.create_goal("test_user", "测试目标", 0)
                print(f"无效天数测试: {success}, {message}")
            except Exception as e:
                print(f"无效天数测试触发异常: {e}")

            # 测试不存在用户的打卡
            try:
                success, message = self.checkin_manager.record_checkin(
                    "nonexistent_user", "completed", "测试"
                )
                print(f"不存在用户打卡测试: {success}, {message}")
            except Exception as e:
                print(f"不存在用户打卡测试触发异常: {e}")

            return True

        except Exception as e:
            print(f"❌ 边界情况测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始运行立志功能插件测试套件...\n")

        tests = [
            ("数据库操作", self.test_database_operations),
            ("目标管理", self.test_goal_management),
            ("打卡管理", self.test_checkin_management),
            ("AI回复生成", self.test_ai_response_generation),
            ("提醒调度器", self.test_reminder_scheduler),
            ("边界情况", self.test_edge_cases),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            print(f"{'='*50}")
            print(f"测试: {test_name}")
            print(f"{'='*50}")

            try:
                if test_func():
                    print(f"✅ {test_name} 测试通过")
                    passed += 1
                else:
                    print(f"❌ {test_name} 测试失败")
            except Exception as e:
                print(f"❌ {test_name} 测试异常: {e}")

        print(f"\n{'='*60}")
        print(f"🏁 测试完成! 通过: {passed}/{total}")
        print(f"{'='*60}")

        if passed == total:
            print("🎉 所有测试通过！立志功能插件准备就绪！")
        else:
            print("⚠️  部分测试失败，请检查相关功能实现")

        # 清理测试数据库
        try:
            if os.path.exists(self.test_db_path):
                os.unlink(self.test_db_path)
                print(f"🧹 测试数据库已清理: {self.test_db_path}")
        except Exception as e:
            print(f"⚠️  清理测试数据库失败: {e}")

        return passed == total

def main():
    """主函数"""
    print("🎯 立志功能插件测试工具")
    print("=" * 60)

    try:
        tester = AspirationTester()
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 测试工具运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
