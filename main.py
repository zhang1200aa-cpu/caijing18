#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
caijing18 财经新闻聚合平台 - 主程序入口
- 启动 Flask Web 服务器（财经新闻管理面板）
- 后台运行 Telegram Bot（监听频道消息）
- 定时任务管理（数据清理、统计、AI 新闻总结）
- AI 每日财经总结（集成 OpenAI 兼容 API）
"""

import os
import sys
from dotenv import load_dotenv
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# 加载环境变量
load_dotenv()

# ============ 日志配置（兼容 Windows GBK 终端） ============
from logging_setup import setup_logging
logger = setup_logging()

# ============ 导入项目模块 ============
from database import init_database, cleanup_old_data
from tg_scraper import scrape_all_channels
from services import (
    ensure_secret_key, sync_config_channels_to_db,
    get_scrape_interval_minutes, reschedule_scrape_job,
    generate_today_summary, generate_3d_summary, generate_1w_summary, get_stats,
    init_scheduler,
)
from routes import web_bp, news_api_bp, admin_api_bp, ai_api_bp

# ============ Flask 应用配置 ============
app = Flask(__name__, template_folder='web/templates', static_folder='web/static', static_url_path='/static')
app.config['JSON_AS_ASCII'] = False
app.config['JSON_SORT_KEYS'] = False

# 注册蓝图
app.register_blueprint(web_bp)
app.register_blueprint(news_api_bp)
app.register_blueprint(admin_api_bp)
app.register_blueprint(ai_api_bp)

# ============ 定时任务调度器 ============
scheduler = BackgroundScheduler()
scheduler.start()

# 注入 scheduler 到 admin_service
init_scheduler(scheduler)


# ============ 定时任务函数 ============

def cleanup_task():
    """定时清理任务：删除 7 天前的旧数据"""
    logger.info(f"🧹 [Task] 数据清理任务执行 - {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        deleted = cleanup_old_data()
        logger.info(f"✅ [Task] 清理完成，删除了 {deleted} 条旧数据")
    except Exception as e:
        logger.error(f"❌ [Task] 清理失败: {str(e)}")


def stats_task():
    """定时统计任务：生成统计信息"""
    logger.info(f"📊 [Task] 统计任务执行 - {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        stats = get_stats()
        logger.info(f"✅ [Task] 统计信息: {stats}")
    except Exception as e:
        logger.error(f"❌ [Task] 统计失败: {str(e)}")


def scrape_telegram_task():
    """定时抓取 Telegram 公共频道消息"""
    logger.info("=" * 60)
    logger.info(f"🔍 [Scraper] 开始抓取频道消息 - {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    try:
        from database import save_news, get_enabled_channels
        from config import TG_CHANNEL_URLS
        # 先检查是否有可用频道
        db_channels = get_enabled_channels()
        if not db_channels and not TG_CHANNEL_URLS:
            logger.info("⚠️ [Scraper] 未绑定任何 Telegram 频道，跳过抓取")
            return
        total, _ = scrape_all_channels(save_news)
        if total > 0:
            logger.info(f"✅ [Scraper] 抓取完成，本次新增 {total} 条新闻")
            # 尝试发送 TG 推送通知
            _try_send_telegram_notification(f"📰 caijing18 抓取完成\n本次新增 {total} 条新闻")
        else:
            logger.info(f"⏭️ [Scraper] 没有新消息")
    except Exception as e:
        logger.error(f"❌ [Scraper] 抓取失败: {str(e)}")
    logger.info("=" * 60)


def _try_send_telegram_notification(message: str):
    """尝试发送 Telegram 推送通知（静默失败）"""
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        chat_id = os.getenv('TG_NOTIFY_CHAT_ID', '')
        enabled = os.getenv('TG_NOTIFY_ENABLED', 'false').lower() == 'true'
        if bot_token and chat_id and enabled:
            import requests
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            requests.post(url, json={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }, timeout=10)
            logger.info(f"📨 [Notify] TG 推送通知已发送")
    except Exception:
        pass  # 静默失败，通知不是关键功能


def ai_summary_task():
    """定时任务：生成每日 AI 新闻总结"""
    logger.info(f"🤖 [Task] AI 每日总结任务执行 - {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        generate_today_summary(force=True)
        logger.info("✅ [Task] AI 每日总结生成完成")
    except Exception as e:
        logger.error(f"❌ [Task] AI 每日总结生成失败: {str(e)}")


def ai_summary_task_3d():
    """定时任务：生成近 3 天 AI 综合总结"""
    logger.info(f"🤖 [Task] AI 近3天总结任务执行 - {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        generate_3d_summary(force=True)
        logger.info("✅ [Task] AI 近3天总结生成完成")
    except Exception as e:
        logger.error(f"❌ [Task] AI 近3天总结生成失败: {str(e)}")


def ai_summary_task_1w():
    """定时任务：生成近 1 周 AI 综合总结"""
    logger.info(f"🤖 [Task] AI 近1周总结任务执行 - {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        generate_1w_summary(force=True)
        logger.info("✅ [Task] AI 近1周总结生成完成")
    except Exception as e:
        logger.error(f"❌ [Task] AI 近1周总结生成失败: {str(e)}")


# ============ 任务调度配置 ============

def setup_scheduled_jobs():
    """配置并启动所有定时任务"""
    scheduler.add_job(
        cleanup_task,
        CronTrigger(hour=3, minute=0),
        id='cleanup', name='数据清理',
        replace_existing=True
    )
    scheduler.add_job(
        stats_task,
        IntervalTrigger(hours=1),
        id='stats', name='数据统计',
        replace_existing=True
    )
    interval = get_scrape_interval_minutes()
    scheduler.add_job(
        scrape_telegram_task,
        IntervalTrigger(minutes=interval),
        id='tg_scrape', name='TG 频道抓取',
        replace_existing=True
    )
    scheduler.add_job(
        ai_summary_task,
        CronTrigger(hour=9, minute=0),
        id='ai_summary', name='AI 每日总结',
        replace_existing=True
    )
    scheduler.add_job(
        ai_summary_task_3d,
        CronTrigger(hour=9, minute=30),
        id='ai_summary_3d', name='AI 近3天总结',
        replace_existing=True
    )
    scheduler.add_job(
        ai_summary_task_1w,
        CronTrigger(day_of_week='mon', hour=10, minute=0),
        id='ai_summary_1w', name='AI 近1周总结',
        replace_existing=True
    )
    logger.info("✅ [Scheduler] 所有定时任务配置完成")


# ============ 应用入口 ============

if __name__ == '__main__':
    # 设置控制台编码（Windows GBK 兼容）
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("=" * 60)
    print(">> caijing18 财经新闻聚合平台 <<")
    print("=" * 60)
    init_database()
    print("[OK] 数据库初始化完成")

    ensure_secret_key(app)

    sync_config_channels_to_db()

    setup_scheduled_jobs()

    # 首次启动检测：检查是否有可用频道，若无则提示用户绑定
    from database import get_enabled_channels, get_channels, set_setting
    enabled_channels = get_enabled_channels()
    all_channels = get_channels()

    if not all_channels:
        # 首次运行，标记首次启动状态，方便前端检测
        set_setting('_first_run_detected', 'true')
        print("[INFO] 🆕 检测到首次启动，请先添加 Telegram 频道")
        print("[INFO] 📡 管理后台: http://localhost:5000/admin")
        print("[INFO] ⚠️ 请先添加 Telegram 频道后再手动抓取或等待定时抓取")
    else:
        set_setting('_first_run_detected', 'false')
        if enabled_channels:
            print("[启动] 正在执行首次频道抓取...")
            try:
                from database import save_news
                total, _ = scrape_all_channels(save_news)
                print(f"[OK] 首次抓取完成，新增 {total} 条新闻")
            except Exception as e:
                print(f"[WARN] 首次抓取失败: {str(e)}")
        else:
            print("[INFO] ⚠️ 已添加频道但未启用，跳过首次抓取")
            print("[INFO] 请在管理后台启用频道后手动抓取")

    # 检测 Telegram 通知配置
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    notify_chat_id = os.getenv('TG_NOTIFY_CHAT_ID', '')
    if bot_token and notify_chat_id:
        print(f"[OK] 📨 Telegram 订阅通知已配置（Chat ID: {notify_chat_id}）")
    elif bot_token:
        print("[WARN] 📨 已配置 Bot Token 但未设置 TG_NOTIFY_CHAT_ID，通知推送将不生效")
    else:
        print("[INFO] 📨 Telegram 订阅通知未配置，如需推送请在 .env 中设置 TELEGRAM_BOT_TOKEN 和 TG_NOTIFY_CHAT_ID")

    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    print(f"[启动] Web 服务: http://{host}:{port}")
    print("=" * 60)
    app.run(host=host, port=port, debug=debug)
