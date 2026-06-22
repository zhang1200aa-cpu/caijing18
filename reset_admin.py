#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员密码重置脚本

用法：
    python reset_admin.py                    # 重置默认 admin 账户（交互式输入新密码）
    python reset_admin.py --username admin   # 重置指定账户
    python reset_admin.py --password 123456  # 直接指定新密码（非交互式）
    python reset_admin.py --list             # 列出所有管理员

示例：
    python reset_admin.py
    python reset_admin.py --password admin888
    python reset_admin.py --list

Docker 环境：
    方案一（推荐）：在宿主机上直接运行（数据库已挂载到宿主机 ./data/ 目录）
        python reset_admin.py
        python reset_admin.py --password admin888

    方案二：进入容器内部运行
        docker compose exec app python reset_admin.py
        docker compose exec app python reset_admin.py --password admin888
"""

import sys
import os
import argparse
import hashlib

# 确保能导入项目配置
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import config
except ImportError as e:
    print(f"❌ 无法导入项目配置: {e}")
    print("请确保在项目根目录下运行此脚本")
    sys.exit(1)

# 数据库路径
DB_PATH = config.DB_PATH


def get_connection():
    """获取 SQLite 数据库连接"""
    try:
        import sqlite3
    except ImportError:
        print("❌ Python 缺少 sqlite3 模块，无法连接数据库")
        sys.exit(1)

    if not os.path.exists(DB_PATH):
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        print("提示：请先启动一次程序，数据库会在初始化时自动创建")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    """对密码进行哈希处理（优先 bcrypt，备用 SHA256）"""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        # 备用：SHA256
        return 'sha256$' + hashlib.sha256(password.encode()).hexdigest()


def list_admins():
    """列出所有管理员账户"""
    conn = get_connection()
    try:
        cursor = conn.execute("SELECT id, username, created_at FROM admins")
        rows = cursor.fetchall()
        if not rows:
            print("📭 数据库中暂无管理员账户")
            return
        print(f"\n{'='*50}")
        print(f"  管理员账户列表")
        print(f"{'='*50}")
        print(f"{'ID':<20} {'用户名':<15} {'创建时间'}")
        print(f"{'-'*50}")
        for row in rows:
            created = row['created_at'] if row['created_at'] else 'N/A'
            print(f"{row['id']:<20} {row['username']:<15} {created}")
        print(f"{'='*50}\n")
    finally:
        conn.close()


def reset_password(username: str, new_password: str) -> bool:
    """重置指定管理员密码"""
    conn = get_connection()
    try:
        # 检查用户是否存在
        cursor = conn.execute("SELECT id, username FROM admins WHERE username = ?", (username,))
        admin = cursor.fetchone()

        if not admin:
            print(f"❌ 用户 '{username}' 不存在")
            print("提示：默认管理员用户名为 'admin'")
            return False

        # 生成密码哈希
        password_hash = hash_password(new_password)

        # 更新密码
        conn.execute(
            "UPDATE admins SET password_hash = ? WHERE username = ?",
            (password_hash, username)
        )
        conn.commit()
        print(f"✅ 管理员 '{username}' 密码已成功重置！")
        return True
    except Exception as e:
        print(f"❌ 重置密码失败: {e}")
        return False
    finally:
        conn.close()


def interactive_reset(username: str):
    """交互式重置密码"""
    import getpass

    print(f"\n🔑 正在重置管理员 '{username}' 的密码")
    print(f"数据库路径: {DB_PATH}\n")

    while True:
        new_password = getpass.getpass("请输入新密码: ")
        if len(new_password) < 4:
            print("⚠️  密码长度至少 4 位，请重新输入")
            continue
        confirm_password = getpass.getpass("请再次输入新密码: ")
        if new_password != confirm_password:
            print("❌ 两次输入的密码不一致，请重新输入")
            continue
        break

    return reset_password(username, new_password)


def main():
    parser = argparse.ArgumentParser(
        description="管理员密码重置工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python reset_admin.py                         交互式重置默认 admin 密码
  python reset_admin.py --password admin888     直接重置为指定密码
  python reset_admin.py --username root --password 123456  重置其他用户
  python reset_admin.py --list                  查看所有管理员
        """
    )
    parser.add_argument('--username', default='admin', help='要重置的管理员用户名（默认: admin）')
    parser.add_argument('--password', help='新密码（不指定则交互式输入）')
    parser.add_argument('--list', action='store_true', help='列出所有管理员账户')

    args = parser.parse_args()

    # 检查数据库是否存在
    if not os.path.exists(DB_PATH):
        print(f"⚠️  数据库文件不存在: {DB_PATH}")
        print("提示：请先启动一次程序，数据库会在初始化时自动创建")
        sys.exit(1)

    if args.list:
        list_admins()
        return

    if args.password:
        # 非交互模式
        if len(args.password) < 4:
            print("❌ 密码长度至少 4 位")
            sys.exit(1)
        success = reset_password(args.username, args.password)
    else:
        # 交互模式
        success = interactive_reset(args.username)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()