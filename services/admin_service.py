"""
管理员相关业务逻辑
"""
import hashlib
import os
import logging
from database import get_setting, set_setting, get_channels, add_channel
from config import TG_CHANNEL_URLS
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError

logger = logging.getLogger(__name__)

# 模块级调度器引用，由主程序在启动时注入
_scheduler = None

# 存储 AI 总结任务函数的引用字典，由主程序在启动时注册
_ai_task_funcs = {}


def init_scheduler(scheduler):
    """注入 APScheduler 实例（由主程序在启动时调用）"""
    global _scheduler
    _scheduler = scheduler


def register_ai_task_func(job_id: str, func):
    """注册 AI 总结任务函数引用（由主程序在启动时调用）"""
    _ai_task_funcs[job_id] = func


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
    """获取定时总结的时间配置（返回布尔类型 enabled）"""
    from database import get_setting
    return {
        'today': {
            'time': get_setting('summary_time_today', '09:00'),
            'enabled': get_setting('summary_today_enabled', 'true') == 'true',
        },
        'yesterday': {
            'time': get_setting('summary_time_yesterday', '08:00'),
            'enabled': get_setting('summary_yesterday_enabled', 'true') == 'true',
        },
        '3d': {
            'time': get_setting('summary_time_3d', '09:30'),
            'enabled': get_setting('summary_3d_enabled', 'true') == 'true',
        },
        '1w': {
            'day': get_setting('summary_day_1w', 'mon'),
            'time': get_setting('summary_time_1w', '10:00'),
            'enabled': get_setting('summary_1w_enabled', 'true') == 'true',
        },
    }


def update_summary_schedule(range_type: str, data: dict) -> dict:
    """更新定时总结的时间配置"""
    from database import set_setting
    try:
        if range_type == 'all':
            # 批量保存所有类型的设置
            settings = data.get('settings', {})
            for t in ['today', 'yesterday', '3d', '1w']:
                s = settings.get(t, {})
                if t == 'today':
                    if 'time' in s:
                        set_setting('summary_time_today', s['time'])
                    if 'enabled' in s:
                        set_setting('summary_today_enabled', s['enabled'])
                elif t == 'yesterday':
                    if 'time' in s:
                        set_setting('summary_time_yesterday', s['time'])
                    if 'enabled' in s:
                        set_setting('summary_yesterday_enabled', s['enabled'])
                elif t == '3d':
                    if 'time' in s:
                        set_setting('summary_time_3d', s['time'])
                    if 'enabled' in s:
                        set_setting('summary_3d_enabled', s['enabled'])
                elif t == '1w':
                    if 'day' in s:
                        set_setting('summary_day_1w', s['day'])
                    if 'time' in s:
                        set_setting('summary_time_1w', s['time'])
                    if 'enabled' in s:
                        set_setting('summary_1w_enabled', s['enabled'])
        elif range_type == 'today':
            if 'time' in data:
                set_setting('summary_time_today', data['time'])
            if 'enabled' in data:
                set_setting('summary_today_enabled', data['enabled'])
        elif range_type == 'yesterday':
            if 'time' in data:
                set_setting('summary_time_yesterday', data['time'])
            if 'enabled' in data:
                set_setting('summary_yesterday_enabled', data['enabled'])
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
    """重新调度所有总结任务（基于数据库中的时间配置）
    支持：更新已存在任务、移除被禁用任务、新增被重新启用的任务
    """
    schedule = get_summary_schedule()

    # 定义所有总结任务配置（job_id, enabled, trigger 构建函数, 描述）
    task_configs = [
        {
            'job_id': 'ai_summary',
            'name': '每日总结',
            'enabled': schedule['today']['enabled'],
            'time': schedule['today']['time'],
            'desc': schedule['today']['time'],
            'trigger_builder': lambda t, sid='today': CronTrigger(hour=int(t.split(':')[0]), minute=int(t.split(':')[1])),
        },
        {
            'job_id': 'ai_summary_yesterday',
            'name': '昨日总结',
            'enabled': schedule['yesterday']['enabled'],
            'time': schedule['yesterday']['time'],
            'desc': schedule['yesterday']['time'],
            'trigger_builder': lambda t, sid='yesterday': CronTrigger(hour=int(t.split(':')[0]), minute=int(t.split(':')[1])),
        },
        {
            'job_id': 'ai_summary_3d',
            'name': '近3天总结',
            'enabled': schedule['3d']['enabled'],
            'time': schedule['3d']['time'],
            'desc': schedule['3d']['time'],
            'trigger_builder': lambda t, sid='3d': CronTrigger(hour=int(t.split(':')[0]), minute=int(t.split(':')[1])),
        },
        {
            'job_id': 'ai_summary_1w',
            'name': '近1周总结',
            'enabled': schedule['1w']['enabled'],
            'time': schedule['1w']['time'],
            'desc': f"{schedule['1w']['day']} {schedule['1w']['time']}",
            'trigger_builder': lambda t, sid='1w': CronTrigger(
                day_of_week=schedule[sid]['day'],
                hour=int(t.split(':')[0]),
                minute=int(t.split(':')[1])
            ),
        },
    ]

    for cfg in task_configs:
        job_id = cfg['job_id']

        # 检查任务是否存在
        job_exists = False
        try:
            job_exists = _scheduler.get_job(job_id) is not None
        except Exception:
            job_exists = False

        if cfg['enabled']:
            trigger = cfg['trigger_builder'](cfg['time'])
            if job_exists:
                # 任务存在 → 直接更新触发时间
                try:
                    _scheduler.reschedule_job(job_id, trigger=trigger)
                    logger.info(f"✅ [Scheduler] {cfg['name']} 时间已更新为 {cfg['desc']}")
                except JobLookupError:
                    # 被其他线程移除等竞态情况，回退到添加
                    job_exists = False

            if not job_exists:
                # 任务不存在（之前被移除或首次创建）→ 如果有函数引用则添加
                func = _ai_task_funcs.get(job_id)
                if func:
                    _scheduler.add_job(
                        func,
                        trigger,
                        id=job_id,
                        name=f'AI {cfg["name"]}',
                        replace_existing=True
                    )
                    logger.info(f"✅ [Scheduler] {cfg['name']} 已新增，时间: {cfg['desc']}")
                else:
                    logger.warning(f"⚠️ [Scheduler] {cfg['name']} 函数未注册，无法添加定时任务。请重启应用。")
        else:
            # 禁用状态 → 如果任务存在则移除
            if job_exists:
                try:
                    _scheduler.remove_job(job_id)
                    logger.info(f"⏹️ [Scheduler] {cfg['name']} 已禁用并移除")
                except JobLookupError:
                    logger.info(f"⏹️ [Scheduler] {cfg['name']} 不存在（无需移除）")
            else:
                logger.info(f"⏹️ [Scheduler] {cfg['name']} 保持禁用状态")