#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
caijing18 项目全面测试脚本
避免导入 main.py（因为其模块级代码会启动 scheduler）
"""
import sys, os, io

# Fix terminal encoding - do this FIRST before any logging setup
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

sys.path.insert(0, '.')
os.environ['APP_DATA_DIR'] = 'data'
os.environ['TG_CHANNEL_URLS'] = ''
os.environ['FLASK_DEBUG'] = 'False'

# Reset logging to avoid double-wrapping issues
import logging
logging.getLogger().handlers.clear()

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  \u2705 {name}")
        passed += 1
    else:
        print(f"  \u274c {name} - {detail}")
        failed += 1

def test_equal(name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  \u2705 {name}")
        passed += 1
    else:
        print(f"  \u274c {name} - 期望: {expected}, 实际: {actual}")
        failed += 1

print("=" * 60)
print("\U0001f4cb caijing18 项目全面测试报告")
print("=" * 60)
print()

# ============ 1. 配置模块 ============
print("【1】配置模块测试")
try:
    import config
    test("config 模块导入", True)
    test("APP_DATA_DIR 不为空", bool(config.APP_DATA_DIR))
    test("DB_PATH 包含 finance_data.db", 'finance_data.db' in config.DB_PATH)
    test("DATABASE_URL 包含 sqlite", 'sqlite' in config.DATABASE_URL)
    test("SIMILARITY_THRESHOLD 是 float", isinstance(config.SIMILARITY_THRESHOLD, float))
    test("FINANCE_KEYWORDS 包含分类", len(config.FINANCE_KEYWORDS) >= 8)
    test("TG_CHANNEL_URLS 是 list", isinstance(config.TG_CHANNEL_URLS, list))
    test_equal("TG_CHANNEL_URLS 为空 (测试环境)", config.TG_CHANNEL_URLS, [])
    test("AI_MODEL 不为空", bool(config.AI_MODEL))
    test("FLASK_HOST 已设置", bool(config.FLASK_HOST))
    test("FLASK_PORT 是 int 且 > 0", isinstance(config.FLASK_PORT, int) and config.FLASK_PORT > 0)
except Exception as e:
    test("config 模块导入", False, str(e))
print()

# ============ 2. 日志模块 ============
print("【2】日志配置测试")
try:
    from logging_setup import setup_logging, EncodingStreamHandler
    test("logging_setup 模块导入", True)
    logger = setup_logging()
    test("setup_logging 返回 logger", logger is not None)
    test("EncodingStreamHandler 存在", callable(EncodingStreamHandler))
    # Test logger works
    logger.info("日志测试消息")
    test("logger 正常输出", True)
except Exception as e:
    import traceback
    test("logging_setup 模块导入", False, f"{e}\n{traceback.format_exc()}")
print()

# ============ 3. 数据库模块 ============
print("【3】数据库模块测试")
try:
    from database import (init_database, get_session, get_stats, get_all_settings,
                          get_channels, save_news, get_setting, set_setting,
                          FinanceNews, Settings, Channel, Admin, SummaryTemplate,
                          cleanup_old_data, get_news_by_time_range, search_news_by_text,
                          add_channel, remove_channel, toggle_channel)
    test("database 模块全部导入", True)
    
    engine = init_database()
    test("init_database 返回 engine", engine is not None)
    
    # 检查表 - 兼容 SQLAlchemy 2.0
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    expected_tables = ['finance_news', 'settings', 'channels', 'admins', 'ai_summaries', 'summary_templates']
    for tbl in expected_tables:
        test(f"表 {tbl} 已创建", tbl in tables)
    
    # 检查 ai_summaries 表是否有 is_composite 列
    columns = {c['name'] for c in inspector.get_columns('ai_summaries')}
    test("ai_summaries 表有 is_composite 列", 'is_composite' in columns)
    
    # 统计
    stats = get_stats()
    test("get_stats 返回 dict", isinstance(stats, dict))
    for key in ['total', 'today', 'tag_count', 'sources']:
        test(f"stats 包含 {key}", key in stats)
    
    # 设置存取
    set_setting('test_key', 'test_value_123')
    val = get_setting('test_key')
    test_equal("get_setting 返回正确值", val, 'test_value_123')
    
    all_s = get_all_settings()
    test("get_all_settings 返回 dict", isinstance(all_s, dict))
    test("test_key 在 settings 中", 'test_key' in all_s)
    
    # 清理测试设置
    session = get_session()
    session.query(Settings).filter(Settings.key == 'test_key').delete()
    session.commit()
    
    # 频道管理
    channels = get_channels()
    test("get_channels 返回 list", isinstance(channels, list))
    
    result = add_channel('https://t.me/s/test_channel_xxx', scrape_depth=100)
    test("add_channel 返回 dict", isinstance(result, dict))
    test("add_channel 成功", result.get('success'))
    
    channels2 = get_channels()
    test("add_channel 后 get_channels 增加", len(channels2) > len(channels))
    
    # 重复添加
    result2 = add_channel('https://t.me/s/test_channel_xxx')
    test("add_channel 重复添加返回 False", not result2.get('success'))
    
    # toggle
    channel_id = result['data']['id']
    toggle_result = toggle_channel(channel_id, False)
    test("toggle_channel 成功", toggle_result.get('success'))
    
    # 删除
    remove_result = remove_channel(channel_id)
    test("remove_channel 成功", remove_result.get('success'))
    
    channels3 = get_channels()
    test("remove_channel 后频道减少", len(channels3) == len(channels))
    
    # 新闻保存
    from datetime import datetime, timedelta
    test_id = 'test_comprehensive_001'
    saved = save_news(
        news_id=test_id,
        title='测试新闻：A股三大指数集体上涨',
        content='今日A股三大指数集体上涨，沪指涨超2%，深成指涨超3%，市场情绪回暖。',
        tags='A股,股票,大涨',
        url='https://example.com/test',
        message_id='test_msg_comp_1',
        source='test_channel'
    )
    test("save_news 成功保存", saved)
    
    # 重复保存
    saved2 = save_news(
        news_id=test_id,
        title='test',
        content='test',
        tags='test',
        url='test',
        message_id='test_msg_comp_1',
        source='test'
    )
    test("save_news 重复保存返回 False", not saved2)
    
    # 查询新闻
    news = session.query(FinanceNews).filter(FinanceNews.id == test_id).first()
    test("查询已保存的新闻", news is not None)
    if news:
        test_equal("新闻 title 正确", news.title, '测试新闻：A股三大指数集体上涨')
        test("新闻 content 不为空", bool(news.content))
        test("新闻 source 正确", news.source == 'test_channel')
        test("新闻 tags 包含 A股", 'A股' in (news.tags or ''))
        test("新闻 message_id 正确", news.message_id == 'test_msg_comp_1')
        test("published_time 存在", news.published_time is not None)
    
    # 时间范围查询
    start = datetime.utcnow() - timedelta(days=1)
    end = datetime.utcnow() + timedelta(days=1)
    news_list = get_news_by_time_range(start, end)
    test("get_news_by_time_range 返回 list", isinstance(news_list, list))
    test("测试新闻在时间范围内", any(n['id'] == test_id for n in news_list))
    
    # 搜索
    search_results = search_news_by_text('A股三大指数')
    test("search_news_by_text 返回结果", len(search_results) > 0)
    test("搜索结果包含测试新闻", any(n['id'] == test_id for n in search_results))
    
    # 获取频道(已启用)
    from database import get_enabled_channels
    enabled = get_enabled_channels()
    test("get_enabled_channels 返回 list", isinstance(enabled, list))
    
    # cleanup - 删除测试新闻
    deleted = cleanup_old_data(days=0)
    test("cleanup_old_data 执行完成", True)
    
    news_after = session.query(FinanceNews).filter(FinanceNews.id == test_id).first()
    test("cleanup 后新闻已删除", news_after is None)
    
    session.close()
    
except Exception as e:
    import traceback
    test("数据库测试", False, f"{e}\n{traceback.format_exc()}")
print()

# ============ 4. 数据库 Session 上下文管理器 ============
print("【4】DB Session 上下文管理器测试")
try:
    from db import session_scope, session_scope_readonly
    test("session_scope 可导入", callable(session_scope))
    test("session_scope_readonly 可导入", callable(session_scope_readonly))
    
    with session_scope() as session:
        count = session.query(Settings).count()
        test("session_scope 可正常查询", True)
    
    with session_scope_readonly() as session:
        count = session.query(FinanceNews).count()
        test("session_scope_readonly 可正常查询", True)
except Exception as e:
    test("session 上下文管理器", False, str(e))
print()

# ============ 5. 去重模块 ============
print("【5】去重模块测试")
try:
    from deduplicator import deduplicator
    test("deduplicator 可导入", deduplicator is not None)
    
    # hash
    h1 = deduplicator.generate_hash('test content')
    h2 = deduplicator.generate_hash('test content')
    h3 = deduplicator.generate_hash('different content')
    test_equal("相同内容 hash 一致", h1, h2)
    test("不同内容 hash 不同", h1 != h3)
    test("hash 是 32 位 hex", len(h1) == 32 and all(c in '0123456789abcdef' for c in h1))
    
    # is_duplicate - reason can be None
    is_dup, reason = deduplicator.is_duplicate('测试标题', '测试内容', 'msg_1')
    test("is_duplicate 返回 bool", isinstance(is_dup, bool))
    test("is_duplicate reason 是 str 或 None", isinstance(reason, (str, type(None))))
    
    # similarity
    sim1 = deduplicator.get_similarity('A股市场今日大涨', 'A股市场今日大跌')
    test("相似内容相似度 > 0.5", sim1 > 0.5)
    sim2 = deduplicator.get_similarity('hello world', 'completely different text')
    test("不同内容相似度 < 0.3", sim2 < 0.3)
    sim3 = deduplicator.get_similarity('same text', 'same text')
    test_equal("相同内容相似度 = 1.0", sim3, 1.0)
    
    # 清理测试消息
    from database import get_session, FinanceNews
    sess = get_session()
    sess.query(FinanceNews).filter(FinanceNews.message_id == 'msg_1').delete()
    sess.commit()
    sess.close()
    
except Exception as e:
    import traceback
    test("去重模块测试", False, f"{e}\n{traceback.format_exc()}")
print()

# ============ 6. 标签模块 ============
print("【6】标签模块测试")
try:
    import tagger
    test("tagger 模块可导入", True)
    test("tagger 实例有 extract_tags 方法", hasattr(tagger.tagger, 'extract_tags'))
    test("tagger 实例有 parse_tags 方法", hasattr(tagger.tagger, 'parse_tags'))
    
    # Tagger.extract_tags 返回分类名称（如"股票"），而不是匹配到的原文关键词（如"A股"）
    tagger_obj = tagger.tagger
    tags_str = tagger_obj.extract_tags('今日A股三大指数集体上涨', '沪指涨超2%')
    parsed = tagger_obj.parse_tags(tags_str)
    test("提取 股票 标签（匹配 A股/A股 关键词）", '股票' in parsed)
    test("返回 JSON 字符串", tags_str.startswith('['))
    
    # 多关键词匹配
    tags_str2 = tagger_obj.extract_tags('央行降准降息，比特币突破新高', '楼市回暖')
    parsed2 = tagger_obj.parse_tags(tags_str2)
    test("提取 宏观 标签", '宏观' in parsed2)
    test("提取 加密 标签", '加密' in parsed2)
    test("提取 房产 标签", '房产' in parsed2)
    
    # 无匹配
    tags_str3 = tagger_obj.extract_tags('今天天气', '真好')
    parsed3 = tagger_obj.parse_tags(tags_str3)
    test("无匹配返回默认标签", '其他' in parsed3)
    
    # parse_tags 边界情况
    empty = tagger_obj.parse_tags('')
    test("parse_tags 空字符串返回 []", empty == [])
    invalid = tagger_obj.parse_tags('invalid json')
    test("parse_tags 无效 JSON 返回 []", invalid == [])
    
except Exception as e:
    import traceback
    test("标签模块测试", False, f"{e}\n{traceback.format_exc()}")
print()

# ============ 7. AI 总结模块 ============
print("【7】AI 总结模块测试")
try:
    from ai_summary import generate_news_analysis
    test("ai_summary 可导入", True)
    test("generate_news_analysis 可调用", callable(generate_news_analysis))
except Exception as e:
    test("AI 总结模块导入", False, str(e))
print()

# ============ 8. 服务层 ============
print("【8】服务层测试")
try:
    from services import (news_to_dict, get_news_list, get_news_detail, search_news,
                          get_tags, get_stats as svc_stats)
    from services.admin_service import (ensure_secret_key, sync_config_channels_to_db,
                                        get_scrape_interval_minutes, init_scheduler)
    from services.summary_service import (generate_today_summary, generate_yesterday_summary,
                                          generate_3d_summary, generate_1w_summary,
                                          generate_search_summary, get_summary,
                                          call_ai)
    test("services 模块全部导入", True)
    
    # 先保存一条新闻让服务层有数据
    from database import save_news, cleanup_old_data
    test_svc_id = 'test_svc_001'
    save_news(
        news_id=test_svc_id,
        title='服务层测试新闻',
        content='这是服务层测试内容',
        tags='测试,服务层',
        url='https://example.com/svc',
        message_id='svc_msg_1',
        source='svc_test'
    )
    
    # get_news_list
    news_list, total = get_news_list(limit=10)
    test("get_news_list 返回 tuple", isinstance(news_list, list) and isinstance(total, int))
    test("get_news_list 有数据", len(news_list) > 0)
    
    # news_to_dict
    from database import get_session, FinanceNews
    session = get_session()
    news_obj = session.query(FinanceNews).filter(FinanceNews.id == test_svc_id).first()
    if news_obj:
        d = news_to_dict(news_obj)
        for key in ['id', 'title', 'content', 'tags', 'source', 'url', 'published_time', 'created_time']:
            test(f"news_to_dict 包含 {key}", key in d)
    session.close()
    
    # get_news_detail
    detail = get_news_detail(test_svc_id)
    test("get_news_detail 返回数据", detail is not None)
    if detail:
        test_equal("get_news_detail id 匹配", detail['id'], test_svc_id)
    
    # search_news
    svc_results = search_news('服务层')
    test("search_news 返回结果", len(svc_results) > 0)
    
    # get_tags
    tags_list = get_tags()
    test("get_tags 返回 list", isinstance(tags_list, list))
    if tags_list:
        for key in ['name', 'count']:
            test(f"tags 元素包含 {key}", key in tags_list[0])
    
    # get_stats via service
    svc_stats_result = svc_stats()
    test("service get_stats 返回 dict", isinstance(svc_stats_result, dict))
    
    # admin service
    test("ensure_secret_key 可调用", callable(ensure_secret_key))
    test("sync_config_channels_to_db 可调用", callable(sync_config_channels_to_db))
    test("get_scrape_interval_minutes 可调用", callable(get_scrape_interval_minutes))
    interval = get_scrape_interval_minutes()
    test(f"get_scrape_interval_minutes 返回 {interval}", isinstance(interval, int) and interval > 0)
    
    # summary service
    test("generate_today_summary 可调用", callable(generate_today_summary))
    test("get_summary 可调用", callable(get_summary))
    test("call_ai 可调用", callable(call_ai))
    
    # 清理测试数据
    cleanup_old_data(days=0)
    
except Exception as e:
    import traceback
    test("服务层测试", False, f"{e}\n{traceback.format_exc()}")
print()

# ============ 9. 路由注册 ============
print("【9】路由注册测试")
try:
    from flask import Flask
    app = Flask(__name__, template_folder='web/templates', static_folder='web/static', static_url_path='/static')
    app.config['JSON_AS_ASCII'] = False
    app.config['JSON_SORT_KEYS'] = False
    app.config['SECRET_KEY'] = 'test_secret_key'
    
    from routes.web_routes import web_bp
    from routes.news_api import news_api_bp
    from routes.admin_api import admin_api_bp
    from routes.ai_api import ai_api_bp
    
    app.register_blueprint(web_bp)
    app.register_blueprint(news_api_bp)
    app.register_blueprint(admin_api_bp)
    app.register_blueprint(ai_api_bp)
    
    test("Flask app 创建成功", app is not None)
    
    # 蓝图注册
    blueprints = [b.name for b in app.blueprints.values()]
    test("web_bp 已注册", 'web' in blueprints)
    test("news_api_bp 已注册", 'news_api' in blueprints)
    test("admin_api_bp 已注册", 'admin_api' in blueprints)
    test("ai_api_bp 已注册", 'ai_api' in blueprints)
    
    # 路由数量
    rules = list(app.url_map.iter_rules())
    test("路由数量 >= 35", len(rules) >= 35)
    
    # 关键路由存在
    routes = {r.rule for r in rules}
    key_routes = ['/', '/admin', '/api/news', '/api/admin/login', '/summary',
                  '/api/summary/today', '/api/summary/yesterday', '/api/stats',
                  '/api/tags', '/api/ai/status']
    for route in key_routes:
        test(f"路由 {route} 已注册", route in routes)
    
    # 测试 HTTP 请求
    with app.test_client() as client:
        resp = client.get('/')
        test("GET / 返回 200", resp.status_code == 200)
        
        resp = client.get('/admin')
        test("GET /admin 返回 200", resp.status_code == 200)
        
        resp = client.get('/summary')
        test("GET /summary 返回 200", resp.status_code == 200)
        
        resp = client.get('/api/news')
        test("GET /api/news 返回 200", resp.status_code == 200)
        
        resp = client.get('/api/stats')
        test("GET /api/stats 返回 200", resp.status_code == 200)
        
        resp = client.get('/api/tags')
        test("GET /api/tags 返回 200", resp.status_code == 200)
        
        resp = client.get('/api/admin/check')
        test("GET /api/admin/check 返回 200", resp.status_code == 200)
        
        resp = client.get('/api/ai/status')
        test("GET /api/ai/status 返回 200", resp.status_code == 200)
        
        resp = client.get('/api/ai/status')
        data = resp.get_json()
        test("ai/status 返回 JSON", data is not None)
        test("ai/status 包含 success", data.get('success'))
        
        resp = client.get('/api/news/nonexistent')
        test("GET /api/news/nonexistent 返回 404", resp.status_code == 404)
        
        # 安全检测: /api/admin/settings 缺少 @login_required 装饰器
        resp = client.get('/api/admin/settings')
        if resp.status_code == 401:
            test("【安全】/api/admin/settings 未登录返回 401", True)
        else:
            test("【安全】/api/admin/settings 缺少登录保护", False,
                 f"返回 {resp.status_code}，未登录可访问")
        
        # Test login
        resp = client.post('/api/admin/login', json={'username': 'admin', 'password': 'admin'})
        test("POST /api/admin/login 成功", resp.status_code == 200)
        data = resp.get_json()
        test("login 返回 success", data is not None and data.get('success'))
        
        # Test wrong password
        resp = client.post('/api/admin/login', json={'username': 'admin', 'password': 'wrong'})
        test("POST /api/admin/login 密码错误返回 200", resp.status_code == 200)
        data = resp.get_json()
        test("密码错误返回 success=false", data is not None and not data.get('success', True))
        
        # Test empty params
        resp = client.post('/api/admin/login', json={})
        test("POST /api/admin/login 空参数返回 200", resp.status_code == 200)
        data = resp.get_json()
        test("空参数返回 success=false", data is not None and not data.get('success', True))
        
        # Test search summary API
        resp = client.post('/api/summary/search', json={'keyword': ''})
        test("POST /api/summary/search 空关键词", resp.status_code == 200)
        data = resp.get_json()
        test("空关键词返回 success=false", data is not None and not data.get('success', True))
        
        resp = client.post('/api/summary/search', json={'keyword': 'test'})
        test("POST /api/summary/search 正常请求", resp.status_code == 200)
        
        # Test news search
        resp = client.get('/api/news/search?q=A股')
        test("GET /api/news/search 返回 200", resp.status_code == 200)
        
        # Test news detail
        resp = client.get('/api/news/nonexistent_id')
        test("GET /api/news/无ID 返回 404", resp.status_code == 404)
        
except Exception as e:
    import traceback
    test("路由注册测试", False, f"{e}\n{traceback.format_exc()}")
print()

# ============ 10. Telegram Scraper（逻辑测试） ============
print("【10】Telegram Scraper 模块测试")
try:
    from tg_scraper import (load_seen_messages, save_seen_messages,
                            extract_links_from_text, generate_news_id,
                            get_channel_name_from_url)
    test("tg_scraper 模块导入", True)
    
    # extract_links
    links = extract_links_from_text('点击 https://example.com 查看详情')
    test("extract_links_from_text 提取链接", len(links) > 0)
    test('提取的链接以 https:// 开头', links[0].startswith('https://'))
    
    links2 = extract_links_from_text('没有链接')
    test("无链接时返回空列表", len(links2) == 0)
    
    links3 = extract_links_from_text('t.me/s/channel_name')
    test("提取 t.me 链接", len(links3) > 0)
    test("t.me 链接补全 https", 'https://' in links3[0])
    
    links4 = extract_links_from_text('多个链接 https://a.com 和 https://b.com')
    test("提取多个链接", len(links4) >= 2)
    
    links5 = extract_links_from_text('链接带括号）https://example.com）')
    test("链接去括号", links5[0] == 'https://example.com')
    
    # generate_news_id
    nid1 = generate_news_id('https://example.com', 'test_channel')
    nid2 = generate_news_id('https://example.com', 'test_channel')
    nid3 = generate_news_id('https://example.com', 'other_channel')
    test_equal("相同输入生成相同 news_id", nid1, nid2)
    test("不同频道生成不同 news_id", nid1 != nid3)
    test("news_id 长度 = 16", len(nid1) == 16)
    
    # get_channel_name
    name = get_channel_name_from_url('https://t.me/s/Financial_Express')
    test_equal("提取频道名 Financial_Express", name, 'Financial_Express')
    
    name2 = get_channel_name_from_url('https://t.me/s/Test_Channel/')
    test_equal("提取频道名(带斜杠)", name2, 'Test_Channel')
    
    # 空路径返回 's' (URL 解析行为)
    name3 = get_channel_name_from_url('https://t.me/s/')
    test("提取空频道名返回 's'", name3 == 's')
    
    # seen cache
    save_seen_messages({'test1', 'test2', 'test3'})
    loaded = load_seen_messages()
    test("save/load seen messages 一致", len(loaded) == 3)
    test("seen 包含 test1", 'test1' in loaded)
    
except Exception as e:
    import traceback
    test("Telegram Scraper 测试", False, f"{e}\n{traceback.format_exc()}")
print()

# ============ 11. 模块间引用检查 ============
print("【11】模块导入完整性检查")
modules_to_check = [
    'config', 'database', 'db', 'deduplicator', 'tagger', 'logging_setup',
    'ai_summary', 'telegram_bot', 'tg_scraper',
    'routes', 'routes.web_routes', 'routes.news_api', 'routes.admin_api', 'routes.ai_api',
    'services', 'services.news_service', 'services.summary_service', 'services.admin_service',
]
for mod_name in modules_to_check:
    try:
        __import__(mod_name)
        test(f"模块 {mod_name} 导入成功", True)
    except Exception as e:
        test(f"模块 {mod_name} 导入成功", False, str(e))
print()

# ============ 12. 边界条件测试 ============
print("【12】边界条件测试")
try:
    from database import add_channel, remove_channel, toggle_channel, save_news
    from database import update_channel_scrape_depth
    from database import get_session, FinanceNews
    
    # 空字符串
    result = add_channel('')
    test("add_channel 空 URL 失败", not result.get('success'))
    
    # 不存在的频道
    result = remove_channel('nonexistent_id')
    test("remove_channel 不存在的频道", not result.get('success'))
    
    result = toggle_channel('nonexistent_id', True)
    test("toggle_channel 不存在的频道", not result.get('success'))
    
    result = update_channel_scrape_depth('nonexistent_id', 500)
    test("update_channel_scrape_depth 不存在的频道", not result.get('success'))
    
    # 空内容保存
    result = save_news('test_empty', '', '', '', '', '', '')
    test("save_news 空内容保存不报错", True)
    
    # 验证密码
    from database import verify_admin_password, change_admin_password
    result = verify_admin_password('nonexistent', 'password')
    test("verify_admin_password 不存在用户返回 False", not result)
    
    # 修改密码-错误原密码
    result = change_admin_password('admin', 'wrong_old', 'newpass')
    test("change_admin_password 错误原密码", not result.get('success'))
    
    # 修改密码-太短
    result = change_admin_password('admin', 'admin', 'ab')
    test("change_admin_password 密码太短", not result.get('success'))
    
    # 有效修改密码
    result = change_admin_password('admin', 'admin', 'newadmin')
    test("change_admin_password 成功", result.get('success'))
    
    # 验证新密码
    result = verify_admin_password('admin', 'newadmin')
    test("verify_admin_password 新密码有效", result)
    
    # 改回原密码
    change_admin_password('admin', 'newadmin', 'admin')
    
except Exception as e:
    import traceback
    test("边界条件测试", False, f"{e}\n{traceback.format_exc()}")
print()

# ============ 13. 总结信息 ============
print("=" * 60)
print("\U0001f4ca 测试结果总结")
print("=" * 60)
total = passed + failed
print(f"  总测试数: {total}")
print(f"  \u2705 通过: {passed}")
print(f"  \u274c 失败: {failed}")
if total > 0:
    print(f"  通过率: {passed/total*100:.1f}%")
print()

if failed > 0:
    print("\u26a0\ufe0f 存在失败的测试项，请检查以上 \u274c 标记的详细错误信息")
else:
    print("\U0001f389 所有测试通过！")

print()
print("=" * 60)
print("\U0001f4cb 代码质量检查")
print("=" * 60)

print()
print("文件统计:")
import glob
py_files = glob.glob('**/*.py', recursive=True)
py_files = [f for f in sorted(py_files) if not f.startswith('.') and '\\venv' not in f and '\\env' not in f and '\\node_modules' not in f]
for f in py_files:
    try:
        with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
            lines = len(fh.readlines())
        print(f"  {f}: {lines} 行")
    except:
        pass
print()
print("\U0001f4dd 测试完成")