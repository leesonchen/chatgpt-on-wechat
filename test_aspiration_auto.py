#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
立志功能自动化测试程序

这是一个自动化测试程序，用于验证立志功能的基本逻辑和AI反馈机制。
包含各种测试用例，确保功能的正确性和稳定性。

测试范围：
1. 目标管理功能测试
2. 打卡功能测试
3. AI反馈机制测试
4. 边界条件和异常情况测试
5. 数据一致性测试
"""

import os
import sys
import unittest
import tempfile
from datetime import date, datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from plugins.aspiration.database_manager import DatabaseManager
from plugins.aspiration.goal_manager import GoalManager
from plugins.aspiration.checkin_manager import CheckInManager
from plugins.aspiration.ai_response_generator import AIResponseGenerator
from plugins.aspiration.ai_prompt_templates import AIPromptTemplates


class TestAspirationFeatures(unittest.TestCase):
    """
    立志功能测试类

    包含各种测试用例，验证立志功能的正确性。
    """

    def setUp(self):
        """测试前准备"""
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()

        # 初始化组件
        self.db_manager = DatabaseManager(self.temp_db.name)
        self.ai_generator = AIResponseGenerator()
        self.goal_manager = GoalManager(self.db_manager)
        self.checkin_manager = CheckInManager(self.db_manager, self.ai_generator)

        # 测试用户
        self.test_user = "test_user_001"

        print(f"\n🧪 开始测试：{self._testMethodName}")

    def tearDown(self):
        """测试后清理"""
        # 删除临时数据库
        try:
            os.unlink(self.temp_db.name)
        except:
            pass

        print(f"✅ 测试完成：{self._testMethodName}")

    def test_goal_creation_basic(self):
        """测试基本目标创建功能"""
        print("测试基本目标创建...")

        # 测试正常创建
        success, message = self.goal_manager.create_goal(
            self.test_user, "每天读书30分钟", 30, self.ai_generator
        )
        self.assertTrue(success, "目标创建应该成功")
        self.assertIn("目标设定成功", message, "应该包含成功消息")

        # 验证目标已创建
        active_goal = self.goal_manager.get_active_goal(self.test_user)
        self.assertIsNotNone(active_goal, "应该有活跃目标")
        self.assertEqual(active_goal['goal_description'], "每天读书30分钟")
        self.assertEqual(active_goal['planned_days'], 30)

        print("✓ 基本目标创建测试通过")

    def test_goal_creation_validation(self):
        """测试目标创建验证逻辑"""
        print("测试目标创建验证...")

        # 测试空描述
        success, message = self.goal_manager.create_goal(
            self.test_user, "", 30, self.ai_generator
        )
        self.assertFalse(success, "空描述应该失败")
        self.assertIn("目标描述不能为空", message)

        # 测试无效天数
        success, message = self.goal_manager.create_goal(
            self.test_user, "测试目标", 0, self.ai_generator
        )
        self.assertFalse(success, "无效天数应该失败")
        self.assertIn("计划天数需要在1-1000天之间", message)

        success, message = self.goal_manager.create_goal(
            self.test_user, "测试目标", 1001, self.ai_generator
        )
        self.assertFalse(success, "超大天数应该失败")
        self.assertIn("计划天数需要在1-1000天之间", message)

        print("✓ 目标创建验证测试通过")

    def test_duplicate_goal_prevention(self):
        """测试重复目标防止"""
        print("测试重复目标防止...")

        # 创建第一个目标
        success, _ = self.goal_manager.create_goal(
            self.test_user, "第一个目标", 30, self.ai_generator
        )
        self.assertTrue(success, "第一个目标应该创建成功")

        # 尝试创建第二个目标
        success, message = self.goal_manager.create_goal(
            self.test_user, "第二个目标", 20, self.ai_generator
        )
        self.assertFalse(success, "第二个目标应该创建失败")
        self.assertIn("您已有一个活跃目标", message)

        print("✓ 重复目标防止测试通过")

    def test_checkin_basic(self):
        """测试基本打卡功能"""
        print("测试基本打卡功能...")

        # 先创建目标
        self.goal_manager.create_goal(
            self.test_user, "每天运动30分钟", 21, self.ai_generator
        )

        # 测试打卡
        success, message = self.checkin_manager.record_checkin(
            self.test_user, "completed", "今天跑步了5公里"
        )
        self.assertTrue(success, "打卡应该成功")
        self.assertIn("打卡成功", message)
        self.assertIn("AI鼓励", message)

        print("✓ 基本打卡功能测试通过")

    def test_checkin_without_goal(self):
        """测试没有目标时的打卡"""
        print("测试没有目标时的打卡...")

        success, message = self.checkin_manager.record_checkin(
            self.test_user, "completed", "测试备注"
        )
        self.assertFalse(success, "没有目标时打卡应该失败")
        self.assertIn("您还没有设定目标", message)

        print("✓ 没有目标时打卡测试通过")

    def test_duplicate_checkin_prevention(self):
        """测试重复打卡防止"""
        print("测试重复打卡防止...")

        # 创建目标
        self.goal_manager.create_goal(
            self.test_user, "每天学习", 30, self.ai_generator
        )

        # 第一次打卡
        success, _ = self.checkin_manager.record_checkin(
            self.test_user, "completed", "第一次打卡"
        )
        self.assertTrue(success, "第一次打卡应该成功")

        # 第二次打卡（同一天）
        success, message = self.checkin_manager.record_checkin(
            self.test_user, "completed", "第二次打卡"
        )
        self.assertFalse(success, "同一天第二次打卡应该失败")
        self.assertIn("今日已经打卡过了", message)

        print("✓ 重复打卡防止测试通过")

    def test_goal_completion(self):
        """测试目标完成功能"""
        print("测试目标完成功能...")

        # 创建目标
        self.goal_manager.create_goal(
            self.test_user, "测试目标", 7, self.ai_generator
        )

        # 完成目标
        success, message = self.goal_manager.complete_goal(self.test_user)
        self.assertTrue(success, "目标完成应该成功")
        self.assertIn("恭喜！目标达成", message)

        # 验证没有活跃目标
        active_goal = self.goal_manager.get_active_goal(self.test_user)
        self.assertIsNone(active_goal, "完成后应该没有活跃目标")

        print("✓ 目标完成功能测试通过")

    def test_goal_abandonment(self):
        """测试目标放弃功能"""
        print("测试目标放弃功能...")

        # 创建目标
        self.goal_manager.create_goal(
            self.test_user, "测试目标", 14, self.ai_generator
        )

        # 放弃目标
        success, message = self.goal_manager.abandon_goal(self.test_user)
        self.assertTrue(success, "目标放弃应该成功")
        self.assertIn("已暂停", message)

        # 验证没有活跃目标
        active_goal = self.goal_manager.get_active_goal(self.test_user)
        self.assertIsNone(active_goal, "放弃后应该没有活跃目标")

        print("✓ 目标放弃功能测试通过")

    def test_ai_goal_suggestion(self):
        """测试AI目标建议功能"""
        print("测试AI目标建议功能...")

        test_descriptions = [
            "每天读书",
            "减肥",
            "学习编程",
            "早起",
            "运动健身"
        ]

        for description in test_descriptions:
            suggestion = self.ai_generator.generate_goal_suggestion(description)
            self.assertIsInstance(suggestion, str, "建议应该是字符串")
            self.assertGreater(len(suggestion), 10, "建议应该有实质内容")
            print(f"  ✓ '{description}' -> 建议长度: {len(suggestion)}")

        print("✓ AI目标建议功能测试通过")

    def test_ai_encouragement(self):
        """测试AI鼓励功能"""
        print("测试AI鼓励功能...")

        goal_info = {
            'goal_description': '每天读书30分钟',
            'planned_days': 30,
            'days_since_start': 5
        }

        user_stats = {
            'consecutive_days': 3,
            'completion_rate': 80,
            'max_streak': 5,
            'total_checkins': 5
        }

        test_checkins = [
            {'status': 'completed', 'note': '今天读了《Python编程》'},
            {'status': 'partial', 'note': '只读了15分钟'},
            {'status': 'failed', 'note': '今天太忙了'}
        ]

        for checkin_info in test_checkins:
            encouragement = self.ai_generator.generate_encouragement(
                goal_info, checkin_info, user_stats
            )
            self.assertIsInstance(encouragement, str, "鼓励应该是字符串")
            self.assertGreater(len(encouragement), 10, "鼓励应该有实质内容")
            print(f"  ✓ {checkin_info['status']} -> 鼓励长度: {len(encouragement)}")

        print("✓ AI鼓励功能测试通过")

    def test_ai_reminder(self):
        """测试AI提醒功能"""
        print("测试AI提醒功能...")

        goal_info = {
            'goal_description': '每天运动30分钟',
            'planned_days': 21
        }

        user_stats = {
            'consecutive_days': 2,
            'completion_rate': 75
        }

        reminder = self.ai_generator.generate_reminder(goal_info, user_stats)
        self.assertIsInstance(reminder, str, "提醒应该是字符串")
        self.assertGreater(len(reminder), 10, "提醒应该有实质内容")

        print(f"  ✓ 提醒长度: {len(reminder)}")
        print("✓ AI提醒功能测试通过")

    def test_ai_prompt_templates(self):
        """测试AI提示模板"""
        print("测试AI提示模板...")

        # 测试目标建议提示
        goal_prompt = AIPromptTemplates.get_goal_suggestion_prompt("每天读书")
        self.assertIsInstance(goal_prompt, str)
        self.assertIn("每天读书", goal_prompt)

        # 测试目标验证提示
        validation_prompt = AIPromptTemplates.get_goal_validation_prompt("学习编程")
        self.assertIsInstance(validation_prompt, str)
        self.assertIn("学习编程", validation_prompt)

        # 测试鼓励提示
        goal_info = {'goal_description': '运动', 'planned_days': 30}
        checkin_info = {'status': 'completed', 'note': '跑步5公里'}
        user_stats = {
            'consecutive_days': 3,
            'completion_rate': 85,
            'max_streak': 5,
            'total_checkins': 10
        }

        encouragement_prompt = AIPromptTemplates.get_encouragement_prompt(
            goal_info, checkin_info, user_stats
        )
        self.assertIsInstance(encouragement_prompt, str)
        self.assertIn("运动", encouragement_prompt)

        # 测试提醒提示
        reminder_prompt = AIPromptTemplates.get_reminder_prompt(goal_info, user_stats)
        self.assertIsInstance(reminder_prompt, str)
        self.assertIn("运动", reminder_prompt)

        print("✓ AI提示模板测试通过")

    def test_data_consistency(self):
        """测试数据一致性"""
        print("测试数据一致性...")

        # 创建目标
        self.goal_manager.create_goal(
            self.test_user, "数据一致性测试", 10, self.ai_generator
        )

        # 多次打卡
        for i in range(3):
            # 模拟不同日期的打卡（这里简化处理）
            success, _ = self.checkin_manager.record_checkin(
                f"{self.test_user}_{i}", "completed", f"第{i+1}次打卡"
            )
            if i == 0:  # 只有第一个用户有目标
                self.goal_manager.create_goal(
                    f"{self.test_user}_{i}", f"目标{i}", 5, self.ai_generator
                )

        # 验证数据
        goal_details = self.goal_manager.get_goal_details(self.test_user)
        self.assertIsInstance(goal_details, str)

        goal_history = self.goal_manager.get_goal_history(self.test_user)
        self.assertIsInstance(goal_history, str)

        print("✓ 数据一致性测试通过")


class TestRunner:
    """
    测试运行器

    提供友好的测试运行界面和结果展示。
    """

    def __init__(self):
        self.test_suite = unittest.TestLoader().loadTestsFromTestCase(TestAspirationFeatures)

    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 立志功能自动化测试")
        print("=" * 60)
        print("开始执行测试用例...\n")

        # 运行测试
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
        result = runner.run(self.test_suite)

        # 显示结果摘要
        print("\n" + "=" * 60)
        print("📊 测试结果摘要")
        print("=" * 60)
        print(f"总测试数: {result.testsRun}")
        print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
        print(f"失败: {len(result.failures)}")
        print(f"错误: {len(result.errors)}")

        if result.failures:
            print("\n❌ 失败的测试:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback.split('AssertionError: ')[-1].split(chr(10))[0]}")

        if result.errors:
            print("\n💥 错误的测试:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback.split(chr(10))[-2]}")

        if result.wasSuccessful():
            print("\n🎉 所有测试通过！立志功能工作正常。")
        else:
            print("\n⚠️ 部分测试失败，请检查相关功能。")

        return result.wasSuccessful()

    def run_specific_test(self, test_name):
        """运行特定测试"""
        print(f"🧪 运行特定测试: {test_name}")
        print("=" * 60)

        suite = unittest.TestSuite()
        suite.addTest(TestAspirationFeatures(test_name))

        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        return result.wasSuccessful()


def main():
    """主函数"""
    print("🎯 立志功能自动化测试程序")
    print("=" * 60)

    if len(sys.argv) > 1:
        # 运行特定测试
        test_name = sys.argv[1]
        runner = TestRunner()
        success = runner.run_specific_test(test_name)
    else:
        # 运行所有测试
        runner = TestRunner()
        success = runner.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()