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


def get_summary_schedule() -> dict:
    """获取定时总结的时间配置"""
    from database import get_setting
    return {
        'today': {
            'time': get_setting('summary_time_today', '09:00'),
            'enabled': get_setting('summary_today_enabled', 'true'),
        },
        '3d': {
            'time': get_setting('summary_time_3d', '09:30'),
            'enabled': get_setting('summary_3d_enabled', 'true'),
        },
        '1w': {
            'day': get_setting('summary_day_1w', 'mon'),
            'time': get_setting('summary_time_1w', '10:00'),
            'enabled': get_setting('summary_1w_enabled', 'true'),
        },
    }


def update_summary_schedule(range_type: str, data: dict) -> dict:
    """更新定时总结的时间配置"""
    from database import set_setting
    try:
        if range_type == 'today':
            if 'time' in data:
                set_setting('summary_time_today', data['time'])
            if 'enabled' in data:
                set_setting('summary_today_enabled', data['enabled'])
        elif range_type == '3d':
            if 'time' in data:
                set_setting('summary_time_3d', data['time'])
            if 'enabled' in data:
                set_setting('summary_3d_enabled', data['enabled'])
        elif range_type == '1w':
            if 'day' in data:
                set_setting('summary_day_1w', data['day'])
            if 'time' in data:
                set_setting('summary_time_1w', data['time'])
            if 'enabled' in data:
                set_setting('summary_1w_enabled', data['enabled'])
        else:
            return {'success': False, 'message': f'未知的总结类型: {range_type}'}

        # 如果调度器已初始化，重新调度总结任务
        if _scheduler is not None:
            _reschedule_summary_jobs()

        return {'success': True, 'message': '总结时间已更新'}
    except Exception as e:
        logger.error(f"更新总结时间失败: {e}")
        return {'success': False, 'message': str(e)}


def _reschedule_summary_jobs():
    """重新调度所有总结任务（基于数据库中的时间配置）"""
    from database import get_setting
    from apscheduler.triggers.cron import CronTrigger

    schedule = get_summary_schedule()

    # 每日总结
    if schedule['today']['enabled'] == 'true':
        time_parts = schedule['today']['time'].split(':')
        _scheduler.reschedule_job(
            'ai_summary',
            trigger=CronTrigger(hour=int(time_parts[0]), minute=int(time_parts[1]))
        )
        logger.info(f"✅ [Scheduler] 每日总结时间已更新为 {schedule['today']['time']}")

    # 近3天总结
    if schedule['3d']['enabled'] == 'true':
        time_parts = schedule['3d']['time'].split(':')
        _scheduler.reschedule_job(
            'ai_summary_3d',
            trigger=CronTrigger(hour=int(time_parts[0]), minute=int(time_parts[1]))
        )
        logger.info(f"✅ [Scheduler] 近3天总结时间已更新为 {schedule['3d']['time']}")

    # 近1周总结
    if schedule['1w']['enabled'] == 'true':
        time_parts = schedule['1w']['time'].split(':')
        _scheduler.reschedule_job(
            'ai_summary_1w',
            trigger=CronTrigger(day_of_week=schedule['1w']['day'], hour=int(time_parts[0]), minute=int(time_parts[1]))
        )
        logger.info(f"✅ [Scheduler] 近1周总结时间已更新为 {schedule['1w']['day']} {schedule['1w']['time']}")
