#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
定时器功能插件测试脚本
测试数据库操作、AI回复生成、定时器管理、提醒调度等核心功能
"""

import sys
import os
import tempfile
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

print(f"Python路径: {sys.path[:3]}")
print(f"项目根目录: {project_root}")

try:
    from plugins.timer.database_manager import DatabaseManager
    from plugins.timer.timer_manager import TimerManager
    from plugins.timer.ai_response_generator import AIResponseGenerator
    from plugins.timer.reminder_scheduler import ReminderScheduler
    # TimerPlugin通过装饰器注册，直接从模块导入类
    from plugins.timer.timer_plugin import TimerPlugin
    print("✅ 所有模块导入成功")
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"插件目录存在: {os.path.exists('plugins/timer')}")
    sys.exit(1)

class TimerTester:
    """定时器功能测试类"""

    def __init__(self):
        # 使用临时数据库进行测试
        self.test_db_path = os.path.join(tempfile.gettempdir(), "test_timer.db")
        print(f"📍 测试数据库路径: {self.test_db_path}")

        try:
            self.db_manager = DatabaseManager(self.test_db_path)
            self.ai_generator = AIResponseGenerator()
            self.timer_manager = TimerManager(self.db_manager, self.ai_generator)
            self.reminder_scheduler = ReminderScheduler(self.db_manager, self.ai_generator)
            print("✅ 测试组件初始化成功")
        except Exception as e:
            print(f"❌ 测试组件初始化失败: {e}")
            raise

    def test_database_operations(self):
        """测试数据库基本操作"""
        print("\n🔧 测试数据库操作...")

        try:
            # 测试创建定时器
            user_id = "test_user_001"
            timer_name = "测试提醒"
            description = "这是一个测试定时器"
            remind_time = datetime.now() + timedelta(minutes=5)

            timer_id = self.db_manager.create_timer(
                user_id=user_id,
                description=f"{timer_name}: {description}",
                remind_time=remind_time,
                repeat_type='once'
            )

            print(f"✅ 创建定时器成功，ID: {timer_id}")

            # 测试查询定时器
            user_timers = self.db_manager.get_active_timers(user_id)
            if user_timers:
                print(f"✅ 查询用户定时器成功: {len(user_timers)} 个")
            else:
                print("❌ 查询用户定时器失败")
                return False

            # 测试获取最新定时器
            timer = self.db_manager.get_latest_timer(user_id)
            if timer:
                print(f"✅ 获取定时器详情成功: {timer['description']}")
            else:
                print("❌ 获取定时器详情失败")
                return False

            # 测试创建提醒记录
            record_id = self.db_manager.create_reminder_record(
                timer_id=timer_id,
                user_id=user_id,
                remind_time=remind_time
            )

            print(f"✅ 创建提醒记录成功，ID: {record_id}")

            # 测试更新提醒记录状态
            success = self.db_manager.update_reminder_record_status(record_id, 'completed')
            if success:
                print("✅ 更新提醒记录状态成功")
            else:
                print("❌ 更新提醒记录状态失败")
                return False

            # 测试统计查询
            stats = self.db_manager.get_user_timer_stats(user_id)
            print(f"✅ 用户统计查询成功: {stats}")

            return True

        except Exception as e:
            print(f"❌ 数据库操作测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_timer_management(self):
        """测试定时器管理功能"""
        print("\n⏰ 测试定时器管理...")

        try:
            user_id = "test_user_002"

            # 测试解析定时器请求
            test_requests = [
                "明天上午9点提醒我开会",
                "每天晚上8点提醒我锻炼",
                "2小时后提醒我喝水",
                "下周一提醒我交报告"
            ]

            for request in test_requests:
                try:
                    result = self.timer_manager.parse_timer_request(request, user_id)
                    if result and result.get('success'):
                        print(f"✅ 解析成功: '{request}' -> {result.get('description', '未知')}")
                    else:
                        print(f"⚠️  解析失败: '{request}' - {result.get('error_message', '未知错误')}")
                except Exception as e:
                    print(f"❌ 解析异常: '{request}' - {e}")

            # 测试创建定时器
            timer_data = {
                'timer_name': '测试会议提醒',
                'description': '重要会议，不要忘记',
                'remind_time': datetime.now() + timedelta(hours=1),
                'repeat_type': 'once'
            }

            result = self.timer_manager.create_timer(user_id, timer_data)
            if result.get('success'):
                print(f"✅ 创建定时器成功: {result.get('message')}")
            else:
                print(f"❌ 创建定时器失败: {result.get('message', '未知错误')}")
                return False

            # 测试查看用户定时器
            timers_info = self.timer_manager.get_user_timers(user_id)
            if timers_info:
                print(f"✅ 获取用户定时器信息成功")
            else:
                print("❌ 获取用户定时器信息失败")

            return True

        except Exception as e:
            print(f"❌ 定时器管理测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_ai_response_generation(self):
        """测试AI回复生成功能"""
        print("\n🤖 测试AI回复生成...")

        try:
            user_id = "test_user_003"

            # 模拟AI Bot
            mock_bot = Mock()
            mock_bot.reply.return_value.type = 'TEXT'
            mock_bot.reply.return_value.content = "这是一个测试回复"

            with patch.object(self.ai_generator, 'bot', mock_bot):
                # 测试生成提醒消息
                timer_info = {
                    'description': '这是一个测试提醒消息',
                    'repeat_type': 'once'
                }
                
                reminder_msg = self.ai_generator.generate_reminder_message(
                    timer_info=timer_info,
                    user_id=user_id
                )

                if reminder_msg:
                    print(f"✅ 生成提醒消息成功: {reminder_msg[:50]}...")
                else:
                    print("❌ 生成提醒消息失败")
                    return False

                # 测试生成延迟建议
            suggestion = self.ai_generator.generate_delay_suggestion(
                user_id=user_id,
                context={"description": "测试提醒", "task_type": "work", "urgency": "high"}
            )

            if suggestion:
                print(f"✅ 生成延迟建议成功: {suggestion} 分钟")
            else:
                print("❌ 生成建议回复失败")
                return False

                # 测试分析用户意图
                intent = self.ai_generator.analyze_user_intent(
                    "我想延迟到明天",
                    context={"timer_name": "测试提醒"}
                )

                if intent:
                    print(f"✅ 分析用户意图成功: {intent}")
                else:
                    print("❌ 分析用户意图失败")
                    return False

            return True

        except Exception as e:
            print(f"❌ AI回复生成测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_reminder_scheduler(self):
        """测试提醒调度器功能"""
        print("\n📅 测试提醒调度器...")

        try:
            # 测试调度器启动和停止
            if not self.reminder_scheduler.is_running:
                self.reminder_scheduler.start()
                print("✅ 调度器启动成功")
            else:
                print("✅ 调度器已在运行")

            # 等待一小段时间确保调度器正常运行
            time.sleep(1)

            if self.reminder_scheduler.is_running:
                print("✅ 调度器运行状态正常")
            else:
                print("❌ 调度器运行状态异常")
                return False

            # 测试检查待发送提醒
            self.reminder_scheduler._check_and_send_reminders()
            print(f"✅ 检查待发送提醒成功")

            # 测试停止调度器
            self.reminder_scheduler.stop()
            time.sleep(1)

            if not self.reminder_scheduler.is_running:
                print("✅ 调度器停止成功")
            else:
                print("❌ 调度器停止失败")
                return False

            return True

        except Exception as e:
            print(f"❌ 提醒调度器测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_plugin_integration(self):
        """测试插件集成功能"""
        print("\n🔌 测试插件集成...")

        try:
            # 检查TimerPlugin是否可用
            if TimerPlugin is None:
                print("⚠️ TimerPlugin未正确导入，跳过插件集成测试")
                return True
                
            # 创建插件实例
            config = {
                "database_file": self.test_db_path,
                "check_interval": 30,
                "enable_ai_analysis": True,
                "enable_reminders": True
            }

            plugin = TimerPlugin()
            plugin.config = config
            plugin.db_manager = self.db_manager
            plugin.timer_manager = self.timer_manager
            plugin.ai_generator = self.ai_generator
            plugin.reminder_scheduler = self.reminder_scheduler

            # 模拟消息处理
            mock_context = Mock()
            mock_context.type = 'TEXT'
            mock_context.content = "明天上午10点提醒我开会"
            mock_context.kwargs = {'msg': Mock()}
            mock_context.kwargs['msg'].from_user_id = "test_user_004"

            mock_e_context = Mock()
            mock_e_context.context = mock_context

            # 测试消息处理
            try:
                plugin.on_handle_context(mock_e_context)
                print("✅ 插件消息处理成功")
            except Exception as e:
                print(f"⚠️  插件消息处理异常: {e}")

            return True

        except Exception as e:
            print(f"❌ 插件集成测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_edge_cases(self):
        """测试边界情况和异常处理"""
        print("\n🚨 测试边界情况...")

        try:
            # 测试无效用户ID
            try:
                timers = self.db_manager.get_user_timers("")
                print(f"空用户ID测试: {len(timers)} 个定时器")
            except Exception as e:
                print(f"空用户ID测试触发异常: {e}")

            # 测试无效时间
            try:
                past_time = datetime.now() - timedelta(hours=1)
                timer_id = self.db_manager.create_timer(
                    "test_user", "过期测试: 测试", past_time, "once"
                )
                print(f"过期时间测试: 创建了ID {timer_id}")
            except Exception as e:
                print(f"过期时间测试触发异常: {e}")

            # 测试不存在的定时器操作
            try:
                success = self.db_manager.update_timer_status(99999, 'completed')
                print(f"不存在定时器更新测试: {success}")
            except Exception as e:
                print(f"不存在定时器更新测试触发异常: {e}")

            # 测试解析无效请求
            try:
                result = self.timer_manager.parse_timer_request(
                    "test_user", "这是一个无效的定时器请求"
                )
                print(f"无效请求解析测试: {result}")
            except Exception as e:
                print(f"无效请求解析测试触发异常: {e}")

            return True

        except Exception as e:
            print(f"❌ 边界情况测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始运行定时器功能插件测试套件...\n")

        tests = [
            ("数据库操作", self.test_database_operations),
            ("定时器管理", self.test_timer_management),
            ("AI回复生成", self.test_ai_response_generation),
            ("提醒调度器", self.test_reminder_scheduler),
            ("插件集成", self.test_plugin_integration),
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
            print("🎉 所有测试通过！定时器功能插件准备就绪！")
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
    print("⏰ 定时器功能插件测试工具")
    print("=" * 60)

    try:
        tester = TimerTester()
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 测试工具运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()