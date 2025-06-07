#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
立志功能测试启动器

这是一个简单的启动脚本，提供菜单选择不同的测试程序。
用户可以选择运行手动测试界面或自动化测试。
"""

import os
import sys
import subprocess


def show_menu():
    """显示主菜单"""
    print("🎯 立志功能测试程序")
    print("=" * 50)
    print("请选择要运行的测试程序：")
    print()
    print("1. 手动测试界面 - 文字界面版测试程序")
    print("   可以手动输入立志内容和打卡内容，查看AI反馈")
    print()
    print("2. 自动化测试 - 运行所有测试用例")
    print("   自动验证立志功能的各个方面")
    print()
    print("3. 特定测试 - 运行指定的测试用例")
    print("   运行单个测试方法")
    print()
    print("0. 退出")
    print("-" * 50)


def run_manual_test():
    """运行手动测试界面"""
    print("\n🚀 启动手动测试界面...")
    try:
        subprocess.run([sys.executable, "test_aspiration_cli.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败：{e}")
    except KeyboardInterrupt:
        print("\n程序被用户中断")


def run_auto_test():
    """运行自动化测试"""
    print("\n🚀 启动自动化测试...")
    try:
        result = subprocess.run([sys.executable, "test_aspiration_auto.py"], check=False)
        if result.returncode == 0:
            print("\n✅ 所有测试通过！")
        else:
            print("\n❌ 部分测试失败！")
    except Exception as e:
        print(f"❌ 测试运行失败：{e}")


def run_specific_test():
    """运行特定测试"""
    print("\n📋 可用的测试方法：")
    test_methods = [
        "test_goal_creation_basic",
        "test_goal_creation_validation",
        "test_duplicate_goal_prevention",
        "test_checkin_basic",
        "test_checkin_without_goal",
        "test_duplicate_checkin_prevention",
        "test_goal_completion",
        "test_goal_abandonment",
        "test_ai_goal_suggestion",
        "test_ai_encouragement",
        "test_ai_reminder",
        "test_ai_prompt_templates",
        "test_data_consistency"
    ]

    for i, method in enumerate(test_methods, 1):
        print(f"{i:2d}. {method}")

    try:
        choice = input("\n请输入测试方法编号（1-{}）：".format(len(test_methods))).strip()
        choice_num = int(choice)

        if 1 <= choice_num <= len(test_methods):
            test_method = test_methods[choice_num - 1]
            print(f"\n🚀 运行测试：{test_method}")

            result = subprocess.run(
                [sys.executable, "test_aspiration_auto.py", test_method],
                check=False
            )

            if result.returncode == 0:
                print(f"\n✅ 测试 {test_method} 通过！")
            else:
                print(f"\n❌ 测试 {test_method} 失败！")
        else:
            print("❌ 无效的选择！")

    except ValueError:
        print("❌ 请输入有效的数字！")
    except Exception as e:
        print(f"❌ 运行失败：{e}")


def check_dependencies():
    """检查依赖文件"""
    required_files = [
        "test_aspiration_cli.py",
        "test_aspiration_auto.py",
        "plugins/aspiration/database_manager.py",
        "plugins/aspiration/goal_manager.py",
        "plugins/aspiration/checkin_manager.py",
        "plugins/aspiration/ai_response_generator.py"
    ]

    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)

    if missing_files:
        print("❌ 缺少必要文件：")
        for file_path in missing_files:
            print(f"  - {file_path}")
        print("\n请确保立志功能的所有文件都存在。")
        return False

    return True


def main():
    """主函数"""
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    while True:
        try:
            show_menu()
            choice = input("请选择操作（0-3）：").strip()

            if choice == '0':
                print("\n👋 再见！")
                break
            elif choice == '1':
                run_manual_test()
            elif choice == '2':
                run_auto_test()
            elif choice == '3':
                run_specific_test()
            else:
                print("❌ 无效的选择，请重新输入！")

            if choice != '0':
                input("\n按回车键返回主菜单...")

        except KeyboardInterrupt:
            print("\n\n👋 程序已退出！")
            break
        except Exception as e:
            print(f"\n❌ 发生错误：{e}")
            input("按回车键继续...")


if __name__ == "__main__":
    main()