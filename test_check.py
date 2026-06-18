#!/usr/bin/env python3
"""临时测试脚本：检查路由注册和启动问题"""
import sys
import os

sys.path.insert(0, '.')
os.environ['APP_DATA_DIR'] = 'data'
os.environ['TG_CHANNEL_URLS'] = ''
os.environ['FLASK_HOST'] = '127.0.0.1'
os.environ['FLASK_PORT'] = '5000'
os.environ['FLASK_DEBUG'] = 'True'

# 重定向 stdout 到文件
log_file = open('test_check_output.txt', 'w', encoding='utf-8')

print("=== 测试开始 ===", file=log_file)

try:
    from main import app
    print("Flask app created OK", file=log_file)
    
    rules = sorted([(r.rule, r.endpoint) for r in app.url_map.iter_rules()])
    print(f"\n=== 已注册路由 ({len(rules)} 条) ===", file=log_file)
    for rule, endpoint in rules:
        rule_objs = app.url_map._rules_by_endpoint[endpoint]
        rule_obj = rule_objs[0] if isinstance(rule_objs, list) else rule_objs
        methods = ','.join(rule_obj.methods - {'HEAD', 'OPTIONS'})
        print(f"  {methods:8s} {rule} -> {endpoint}", file=log_file)
    
    # 测试请求
    try:
        with app.test_client() as client:
            resp = client.get('/')
            print(f"\nGET / -> 状态码: {resp.status_code}", file=log_file)
            resp = client.get('/api/news')
            print(f"GET /api/news -> 状态码: {resp.status_code}", file=log_file)
            resp = client.get('/admin')
            print(f"GET /admin -> 状态码: {resp.status_code}", file=log_file)
    except Exception as e:
        print(f"\n❌ 请求测试失败: {e}", file=log_file)
    
except Exception as e:
    import traceback
    print(f"\n❌ 导入失败: {e}", file=log_file)
    traceback.print_exc(file=log_file)

print("=== 测试结束 ===", file=log_file)
log_file.close()