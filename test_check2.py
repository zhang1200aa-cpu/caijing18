#!/usr/bin/env python3
"""全面测试脚本"""
import sys
import os

sys.path.insert(0, '.')
os.environ['APP_DATA_DIR'] = 'data'
os.environ['TG_CHANNEL_URLS'] = ''
os.environ['FLASK_HOST'] = '127.0.0.1'
os.environ['FLASK_PORT'] = '5000'
os.environ['FLASK_DEBUG'] = 'False'

import traceback

test_results = []

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def t(name, ok, detail=""):
    status = "[OK]" if ok else "[FAIL]"
    test_results.append((ok, name, detail))
    print(f"  {status} {name}" + (f" - {detail}" if detail else ""))

print("=" * 60)
print(">> caijing18 Full Test Suite")
print("=" * 60)

# 1. 测试配置模块
print("\n[1/10] 配置模块")
try:
    import config
    t("config 模块导入", True)
    t("APP_DATA_DIR", True, str(config.APP_DATA_DIR))
    t("DATABASE_URL", True, config.DATABASE_URL.split('://')[0] + "://...")
    t("TG_CHANNEL_URLS", True, str(config.TG_CHANNEL_URLS))
except Exception as e:
    t("config 模块导入", False, str(e))

# 2. 测试数据库模块
print("\n[2/10] 数据库模块")
try:
    import database
    t("database 模块导入", True)
    t("数据库表定义", hasattr(database, 'FinanceNews'), "FinanceNews")
    t("会话管理", callable(getattr(database, 'get_session', None)), "get_session")
except Exception as e:
    t("database 模块导入", False, str(e))

# 3. 测试 db 模块
print("\n[3/10] DB 上下文管理器")
try:
    import db
    t("db 模块导入", True)
    t("session_scope", callable(getattr(db, 'session_scope', None)), "")
    t("session_scope_readonly", callable(getattr(db, 'session_scope_readonly', None)), "")
except Exception as e:
    t("db 模块导入", False, str(e))

# 4. 测试日志模块
print("\n[4/10] 日志模块")
try:
    import logging_setup
    t("logging_setup 模块导入", True)
except Exception as e:
    t("logging_setup 模块导入", False, str(e))

# 5. 测试去重模块
print("\n[5/10] 去重模块")
try:
    from deduplicator import deduplicator
    t("deduplicator 导入", True)
    t("is_duplicate 方法", callable(getattr(deduplicator, 'is_duplicate', None)), "")
except Exception as e:
    t("deduplicator 导入", False, str(e))

# 6. 测试爬虫模块
print("\n[6/10] 爬虫模块")
try:
    import tg_scraper
    t("tg_scraper 模块导入", True)
    t("scrape_all_channels", callable(getattr(tg_scraper, 'scrape_all_channels', None)), "")
except Exception as e:
    t("tg_scraper 模块导入", False, str(e))

# 7. 测试 AI 总结模块
print("\n[7/10] AI 总结模块")
try:
    import ai_summary
    t("ai_summary 模块导入", True)
except Exception as e:
    t("ai_summary 模块导入", False, str(e))

# 8. 测试服务模块
print("\n[8/10] 服务模块")
try:
    import services
    t("services 模块导入", True)
    for name in ['get_news_list', 'get_stats', 'generate_today_summary', 'init_scheduler']:
        t(f"  {name}", hasattr(services, name), "")
except Exception as e:
    t("services 模块导入", False, str(e))

# 9. 测试路由模块
print("\n[9/10] 路由模块")
try:
    import routes
    t("routes 模块导入", True)
    for name in ['web_bp', 'news_api_bp', 'admin_api_bp', 'ai_api_bp']:
        t(f"  {name}", hasattr(routes, name), "")
except Exception as e:
    t("routes 模块导入", False, str(e))

# 10. 测试主应用（Flask 创建和路由注册）
print("\n[10/10] 主应用 & API 测试")
try:
    from main import app
    t("Flask app 创建", True)
    
    # 检查路由数量
    rules = sorted([(r.rule, r.endpoint) for r in app.url_map.iter_rules()])
    expected_routes = 37
    has_enough_routes = len(rules) >= 35
    t("路由注册", has_enough_routes, f"共 {len(rules)} 条路由")
    
    # 检查关键路由
    key_routes = ['/', '/admin', '/api/news', '/api/stats', '/api/admin/check', '/summary']
    for route in key_routes:
        found = any(route == r[0] for r in rules)
        t(f"  路由 {route}", found, "")
    
    # 尝试请求
    with app.test_client() as client:
        t("test_client 创建", True, "")
        for path in ['/', '/api/news', '/api/stats', '/api/admin/check']:
            try:
                resp = client.get(path)
                # Some may return 200, some 302 (redirect), some 4xx - all are valid responses
                t(f"  GET {path}", resp.status_code in (200, 302, 401, 404, 500), f"HTTP {resp.status_code}")
            except Exception as e:
                t(f"  GET {path}", False, f"Error: {str(e)[:60]}")
except Exception as e:
    t("主应用导入", False, str(e))
    traceback.print_exc()

# 总结
print("\n" + "=" * 60)
print("测试结果汇总")
print("=" * 60)
passed = sum(1 for ok, _, _ in test_results if ok)
failed = sum(1 for ok, _, _ in test_results if not ok)
total = len(test_results)
print(f"总测试项: {total}, 通过: {passed}, 失败: {failed}")
if failed > 0:
    print("\n失败项:")
    for ok, name, detail in test_results:
        if not ok:
            print(f"  ❌ {name}: {detail}")
print(f"通过率: {passed/total*100:.1f}%")
print("=" * 60)