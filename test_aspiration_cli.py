#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
立志功能命令行测试程序

这是一个独立的文字界面测试程序，用于测试立志功能的AI反馈机制。
用户可以通过命令行界面手动输入立志内容和打卡内容，查看AI的反馈效果。

主要功能：
1. 设定目标并获取AI建议
2. 记录打卡并获取AI鼓励
3. 查看目标状态和统计信息
4. 测试各种场景下的AI反馈
"""

import os
import sys
import json
from datetime import date

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from plugins.aspiration.database_manager import DatabaseManager
from plugins.aspiration.goal_manager import GoalManager
from plugins.aspiration.checkin_manager import CheckInManager
from plugins.aspiration.ai_response_generator import AIResponseGenerator
from common.log import logger


class AspirationCLITester:
    """
    立志功能命令行测试器

    提供一个简单的文字界面，让用户可以测试立志功能的各个方面，
    特别是AI反馈机制的效果。
    """

    def __init__(self):
        """初始化测试器"""
        # 使用测试数据库
        self.db_path = "test_aspiration_cli.db"
        self.db_manager = DatabaseManager(self.db_path)
        self.ai_generator = AIResponseGenerator()
        self.goal_manager = GoalManager(self.db_manager)
        self.checkin_manager = CheckInManager(self.db_manager, self.ai_generator)

        # 测试用户ID
        self.test_user_id = "test_user_001"

        print("🎯 立志功能命令行测试器")
        print("=" * 50)
        print("欢迎使用立志功能测试程序！")
        print("您可以在这里测试目标设定和打卡功能的AI反馈效果。")
        print()

    def show_menu(self):
        """显示主菜单"""
        print("\n📋 主菜单：")
        print("1. 设定新目标")
        print("2. 打卡记录")
        print("3. 查看当前目标")
        print("4. 查看打卡历史")
        print("5. 完成目标")
        print("6. 放弃目标")
        print("7. 测试AI反馈")
        print("8. 清除所有数据")
        print("0. 退出程序")
        print("-" * 30)

    def set_goal(self):
        """设定新目标"""
        print("\n🎯 设定新目标")
        print("=" * 20)

        # 检查是否已有活跃目标
        active_goal = self.goal_manager.get_active_goal(self.test_user_id)
        if active_goal:
            print(f"❗ 您已有一个活跃目标：{active_goal['goal_description']}")
            print("请先完成或放弃当前目标后再设定新目标。")
            return

        # 输入目标描述
        description = input("请输入您的目标描述：").strip()
        if not description:
            print("❌ 目标描述不能为空！")
            return

        # 输入计划天数
        try:
            days_str = input("请输入计划坚持的天数（1-1000）：").strip()
            planned_days = int(days_str)
            if planned_days <= 0 or planned_days > 1000:
                print("❌ 计划天数必须在1-1000之间！")
                return
        except ValueError:
            print("❌ 请输入有效的数字！")
            return

        # 创建目标
        print("\n🤖 AI正在分析您的目标...")
        success, message = self.goal_manager.create_goal(
            self.test_user_id, description, planned_days, self.ai_generator
        )

        print("\n" + "=" * 50)
        if success:
            print("✅ 目标创建成功！")
        else:
            print("❌ 目标创建失败！")
        print(message)
        print("=" * 50)

    def checkin(self):
        """打卡记录"""
        print("\n📝 打卡记录")
        print("=" * 20)

        # 检查是否有活跃目标
        active_goal = self.goal_manager.get_active_goal(self.test_user_id)
        if not active_goal:
            print("❗ 您还没有设定目标，请先设定目标再打卡！")
            return

        print(f"当前目标：{active_goal['goal_description']}")
        print()

        # 选择打卡状态
        print("请选择今日完成状态：")
        print("1. 已完成")
        print("2. 部分完成")
        print("3. 未完成")

        choice = input("请输入选项（1-3）：").strip()

        status_map = {
            '1': 'completed',
            '2': 'partial',
            '3': 'failed'
        }

        if choice not in status_map:
            print("❌ 无效的选项！")
            return

        status = status_map[choice]

        # 输入备注（可选）
        note = input("请输入备注（可选，直接回车跳过）：").strip()
        if not note:
            note = None

        # 记录打卡
        print("\n🤖 AI正在生成个性化反馈...")
        success, message = self.checkin_manager.record_checkin(
            self.test_user_id, status, note
        )

        print("\n" + "=" * 50)
        if success:
            print("✅ 打卡成功！")
        else:
            print("❌ 打卡失败！")
        print(message)
        print("=" * 50)

    def view_current_goal(self):
        """查看当前目标"""
        print("\n📊 当前目标状态")
        print("=" * 20)

        goal_details = self.goal_manager.get_goal_details(self.test_user_id)
        print(goal_details)

    def view_checkin_history(self):
        """查看打卡历史"""
        print("\n📈 打卡历史")
        print("=" * 20)

        goal_history = self.goal_manager.get_goal_history(self.test_user_id)
        print(goal_history)

    def complete_goal(self):
        """完成目标"""
        print("\n🎉 完成目标")
        print("=" * 20)

        success, message = self.goal_manager.complete_goal(self.test_user_id)

        print("\n" + "=" * 50)
        if success:
            print("🎉 恭喜完成目标！")
        else:
            print("❌ 操作失败！")
        print(message)
        print("=" * 50)

    def abandon_goal(self):
        """放弃目标"""
        print("\n😔 放弃目标")
        print("=" * 20)

        confirm = input("确定要放弃当前目标吗？(y/N): ").strip().lower()
        if confirm != 'y':
            print("操作已取消。")
            return

        success, message = self.goal_manager.abandon_goal(self.test_user_id)

        print("\n" + "=" * 50)
        if success:
            print("目标已放弃。")
        else:
            print("❌ 操作失败！")
        print(message)
        print("=" * 50)

    def test_ai_feedback(self):
        """测试AI反馈"""
        print("\n🤖 AI反馈测试")
        print("=" * 20)

        print("选择测试类型：")
        print("1. 测试目标建议")
        print("2. 测试打卡鼓励")
        print("3. 测试提醒消息")

        choice = input("请输入选项（1-3）：").strip()

        if choice == '1':
            self._test_goal_suggestion()
        elif choice == '2':
            self._test_checkin_encouragement()
        elif choice == '3':
            self._test_reminder_message()
        else:
            print("❌ 无效的选项！")

    def _test_goal_suggestion(self):
        """测试目标建议"""
        print("\n📝 测试目标建议")
        description = input("请输入要测试的目标描述：").strip()
        if not description:
            print("❌ 目标描述不能为空！")
            return

        print("\n🤖 AI正在生成建议...")
        suggestion = self.ai_generator.generate_goal_suggestion(description)

        print("\n" + "=" * 50)
        print("🤖 AI建议：")
        print(suggestion)
        print("=" * 50)

    def _test_checkin_encouragement(self):
        """测试打卡鼓励"""
        print("\n💪 测试打卡鼓励")

        # 模拟目标信息
        goal_info = {
            'goal_description': '每天读书30分钟',
            'planned_days': 30,
            'days_since_start': 5
        }

        # 选择打卡状态
        print("选择打卡状态：")
        print("1. 已完成")
        print("2. 部分完成")
        print("3. 未完成")

        choice = input("请输入选项（1-3）：").strip()
        status_map = {'1': 'completed', '2': 'partial', '3': 'failed'}

        if choice not in status_map:
            print("❌ 无效的选项！")
            return

        status = status_map[choice]
        note = input("请输入备注（可选）：").strip() or None

        checkin_info = {
            'status': status,
            'note': note
        }

        # 模拟用户统计
        user_stats = {
            'consecutive_days': 3,
            'completion_rate': 80,
            'max_streak': 5,
            'total_checkins': 5
        }

        print("\n🤖 AI正在生成鼓励...")
        encouragement = self.ai_generator.generate_encouragement(
            goal_info, checkin_info, user_stats
        )

        print("\n" + "=" * 50)
        print("🤖 AI鼓励：")
        print(encouragement)
        print("=" * 50)

    def _test_reminder_message(self):
        """测试提醒消息"""
        print("\n⏰ 测试提醒消息")

        # 模拟目标信息
        goal_info = {
            'goal_description': '每天运动30分钟',
            'planned_days': 21
        }

        # 模拟用户统计
        user_stats = {
            'consecutive_days': 2,
            'completion_rate': 75
        }

        print("\n🤖 AI正在生成提醒...")
        reminder = self.ai_generator.generate_reminder(goal_info, user_stats)

        print("\n" + "=" * 50)
        print("🤖 AI提醒：")
        print(reminder)
        print("=" * 50)

    def clear_all_data(self):
        """清除所有数据"""
        print("\n🗑️ 清除所有数据")
        print("=" * 20)

        confirm = input("确定要清除所有测试数据吗？(y/N): ").strip().lower()
        if confirm != 'y':
            print("操作已取消。")
            return

        try:
            # 删除数据库文件
            if os.path.exists(self.db_path):
                os.remove(self.db_path)

            # 重新初始化数据库
            self.db_manager = DatabaseManager(self.db_path)
            self.goal_manager = GoalManager(self.db_manager)
            self.checkin_manager = CheckInManager(self.db_manager, self.ai_generator)

            print("✅ 所有数据已清除！")
        except Exception as e:
            print(f"❌ 清除数据失败：{e}")

    def run(self):
        """运行测试程序"""
        while True:
            try:
                self.show_menu()
                choice = input("请选择操作（0-8）：").strip()

                if choice == '0':
                    print("\n👋 感谢使用立志功能测试程序！")
                    break
                elif choice == '1':
                    self.set_goal()
                elif choice == '2':
                    self.checkin()
                elif choice == '3':
                    self.view_current_goal()
                elif choice == '4':
                    self.view_checkin_history()
                elif choice == '5':
                    self.complete_goal()
                elif choice == '6':
                    self.abandon_goal()
                elif choice == '7':
                    self.test_ai_feedback()
                elif choice == '8':
                    self.clear_all_data()
                else:
                    print("❌ 无效的选项，请重新选择！")

                input("\n按回车键继续...")

            except KeyboardInterrupt:
                print("\n\n👋 程序已退出！")
                break
            except Exception as e:
                print(f"\n❌ 发生错误：{e}")
                input("按回车键继续...")


def main():
    """主函数"""
    try:
        tester = AspirationCLITester()
        tester.run()
    except Exception as e:
        print(f"程序启动失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()