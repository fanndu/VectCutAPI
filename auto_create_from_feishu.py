#!/usr/bin/env python3
"""
自动化从飞书表格创建视频草稿
整合数据读取、配置生成、草稿创建的完整流程
"""

import os
import sys
import json
import subprocess

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_prerequisites():
    """检查前置条件"""
    print("🔍 检查前置条件...")

    # 检查飞书凭证
    if not os.path.exists('.feishu_credentials.json'):
        print("❌ 未找到飞书凭证文件")
        print("请创建 .feishu_credentials.json:")
        print("{")
        print("  {")
        print("    \"app_id\": \"your_app_id\",")
        print("    \"app_secret\": \"your_app_secret\"")
        print("  }")
        return False

    # 检查API服务器
    import requests
    try:
        # 检查服务器是否在运行（任何响应都可以）
        response = requests.get('http://localhost:8080', timeout=2)
        # 服务器响应HTML目录列表是正常的
    except requests.exceptions.ConnectionError:
        print("❌ API服务器未运行")
        print("请启动: python capcut_server.py")
        return False
    except Exception as e:
        print(f"❌ API服务器检查失败: {e}")
        return False

    print("✅ 前置检查通过")
    return True


def main():
    """主流程"""
    print("🚀 飞书自动化视频草稿生成")
    print("=" * 60)

    # 1. 检查前置条件
    if not check_prerequisites():
        return

    # 2. 读取飞书数据并生成配置
    print("\n📊 阶段1: 读取飞书数据")
    print("-" * 40)

    try:
        # 导入配置生成器
        from generate_config_from_feishu import main as generate_config

        # 临时重定向stdout以捕获输出
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            generate_config()
        finally:
            sys.stdout = old_stdout

        # 读取生成的配置
        if os.path.exists('draft_config_feishu.json'):
            with open('draft_config_feishu.json', 'r') as f:
                config = json.load(f)

            print(f"✅ 配置生成成功")
            print(f"   草稿名称: {config['draft_name']}")
            print(f"   视频数量: {len(config['videos']['files'])}")
            print(f"   音频数量: {len(config['voiceovers']['files'])}")

        else:
            print("❌ 配置生成失败")
            return

    except Exception as e:
        print(f"❌ 数据读取失败: {e}")
        print("请检查:")
        print("  1. 飞书凭证是否正确")
        print("  2. 网络连接是否正常")
        print("  3. 表格URL是否有效")
        return

    # 3. 复制配置并生成草稿
    print("\n🎬 阶段2: 生成视频草稿")
    print("-" * 40)

    # 备份原配置
    if os.path.exists('draft_config.json'):
        import shutil
        shutil.copy('draft_config.json', 'draft_config.json.backup')

    # 使用飞书配置
    import shutil
    shutil.copy('draft_config_feishu.json', 'draft_config.json')

    print("✅ 配置文件已更新")

    # 执行生成脚本
    try:
        result = subprocess.run(
            ['python3', 'generate_draft_from_config.py'],
            capture_output=True,
            text=True,
            timeout=120  # 2分钟超时
        )

        if result.returncode == 0:
            print("✅ 草稿生成成功")
            print("\n📊 生成统计:")
            # 从输出中提取关键信息
            for line in result.stdout.split('\n'):
                if '草稿ID:' in line or '时长:' in line or '视频:' in line:
                    print(f"  {line}")
        else:
            print(f"❌ 草稿生成失败")
            print(result.stderr)

    except subprocess.TimeoutExpired:
        print("❌ 生成超时（>2分钟）")
    except Exception as e:
        print(f"❌ 执行错误: {e}")

    finally:
        # 恢复原配置
        if os.path.exists('draft_config.json.backup'):
            shutil.move('draft_config.json.backup', 'draft_config.json')

    print("\n" + "=" * 60)
    print("🎉 处理完成！")


if __name__ == "__main__":
    main()
