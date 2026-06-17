"""
管理员相关业务逻辑
"""
import hashlib
import os
import logging
from database import get_setting, set_setting, get_channels, add_channel
from config import TG_CHANNEL_URLS
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# 模块级调度器引用，由主程序在启动时注入
_scheduler = None


def init_scheduler(scheduler):
    """注入 APScheduler 实例（由主程序在启动时调用）"""
    global _scheduler
    _scheduler = scheduler


def sync_config_channels_to_db():
    """从配置中同步频道到数据库"""
    added_count = 0
    for url in TG_CHANNEL_URLS:
        try:
            existing = get_channels()
            if not any(c['url'] == url for c in existing):
                add_channel(url)
                added_count += 1
        except Exception as e:
            logger.error(f"同步频道失败 {url}: {str(e)}")

    if added_count > 0:
        logger.info(f"✅ 同步了 {added_count} 个频道到数据库")
    return added_count


def ensure_secret_key(app):
    """确保 Flask session 密钥已设置"""
    secret = get_setting('flask_secret_key', '')
    if not secret:
        secret = hashlib.sha256(os.urandom(32)).hexdigest()
        set_setting('flask_secret_key', secret)
    app.secret_key = secret


def get_scrape_interval_minutes():
    """获取抓取间隔（分钟）"""
    interval_str = get_setting('scrape_interval_minutes', '30')
    try:
        return max(1, int(interval_str))
    except (ValueError, TypeError):
        return 30


def reschedule_scrape_job(interval: int):
    """重新调度抓取任务（使用模块级 scheduler）"""
    if _scheduler is None:
        logger.error("❌ [Scheduler] 调度器未初始化，无法重新调度")
        return
    _scheduler.reschedule_job(
        'tg_scrape',
        trigger=IntervalTrigger(minutes=interval)
    )
    logger.info(f"✅ [Scheduler] 抓取间隔已更新为 {interval} 分钟")
