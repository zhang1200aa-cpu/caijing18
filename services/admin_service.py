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

# 存储自动备份任务函数的引用（由主程序在启动时注册）
_backup_task_func = None


def init_scheduler(scheduler):
    """注入 APScheduler 实例（由主程序在启动时调用）"""
    global _scheduler
    _scheduler = scheduler


def register_ai_task_func(job_id: str, func):
    """注册 AI 总结任务函数引用（由主程序在启动时调用）"""
    _ai_task_funcs[job_id] = func


def register_backup_task_func(func):
    """注册自动备份任务函数引用（由主程序在启动时调用）"""
    global _backup_task_func
    _backup_task_func = func


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


# ======== 自动刷新间隔相关 ========

def get_auto_refresh_interval() -> int:
    """获取每日总结自动刷新频率（分钟）"""
    interval_str = get_setting('auto_refresh_interval_minutes', '10')
    try:
        return max(1, int(interval_str))
    except (ValueError, TypeError):
        return 10


def update_auto_refresh_interval(minutes: int) -> dict:
    """更新每日总结自动刷新频率"""
    try:
        minutes = int(minutes)
        if minutes < 1:
            return {'success': False, 'message': '刷新间隔必须大于 0'}
        if minutes > 1440:
            return {'success': False, 'message': '刷新间隔不能超过 1440 分钟（24小时）'}
        
        set_setting('auto_refresh_interval_minutes', str(minutes))
        
        # 如果调度器已初始化，重新调度刷新任务
        if _scheduler is not None:
            _reschedule_auto_refresh_job(minutes)
        
        return {'success': True, 'message': f'每日总结自动刷新频率已更新为每 {minutes} 分钟'}
    except Exception as e:
        logger.error(f"更新自动刷新频率失败: {e}")
        return {'success': False, 'message': str(e)}


def _reschedule_auto_refresh_job(minutes: int = None):
    """重新调度每日总结自动刷新任务"""
    if _scheduler is None:
        logger.error("❌ [Scheduler] 调度器未初始化，无法重新调度自动刷新")
        return
    
    if minutes is None:
        minutes = get_auto_refresh_interval()
    
    job_id = 'auto_refresh_today_summary'
    
    # 检查任务是否存在
    job_exists = False
    try:
        job_exists = _scheduler.get_job(job_id) is not None
    except Exception:
        job_exists = False
    
    trigger = IntervalTrigger(minutes=minutes)
    
    if job_exists:
        try:
            _scheduler.reschedule_job(job_id, trigger=trigger)
            logger.info(f"✅ [Scheduler] 每日总结自动刷新频率已更新为每 {minutes} 分钟")
        except JobLookupError:
            job_exists = False
    
    if not job_exists:
        # 获取函数引用并添加任务
        from services.summary_service import auto_refresh_today_summary
        _scheduler.add_job(
            auto_refresh_today_summary,
            trigger,
            id=job_id,
            name='今日总结自动刷新（每{minutes}分钟）',
            replace_existing=True
        )
        logger.info(f"✅ [Scheduler] 每日总结自动刷新已新增，间隔: 每 {minutes} 分钟")


def get_summary_schedule() -> dict:
    """获取定时总结的时间配置（返回布尔类型 enabled）"""
    from database import get_setting
    def _is_enabled(key: str, default: str = 'true') -> bool:
        """读取启用状态，兼容大小写 True/False 和 true/false"""
        val = get_setting(key, default)
        return val.lower() == 'true' if val else (default.lower() == 'true')
    return {
        'today': {
            'time': get_setting('summary_time_today', '09:00'),
            'enabled': _is_enabled('summary_today_enabled', 'true'),
        },
        'yesterday': {
            'time': get_setting('summary_time_yesterday', '08:00'),
            'enabled': _is_enabled('summary_yesterday_enabled', 'true'),
        },
        '3d': {
            'time': get_setting('summary_time_3d', '09:30'),
            'enabled': _is_enabled('summary_3d_enabled', 'true'),
        },
        '1w': {
            'day': get_setting('summary_day_1w', 'mon'),
            'time': get_setting('summary_time_1w', '10:00'),
            'enabled': _is_enabled('summary_1w_enabled', 'true'),
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
                        set_setting('summary_today_enabled', 'true' if s['enabled'] else 'false')
                elif t == 'yesterday':
                    if 'time' in s:
                        set_setting('summary_time_yesterday', s['time'])
                    if 'enabled' in s:
                        set_setting('summary_yesterday_enabled', 'true' if s['enabled'] else 'false')
                elif t == '3d':
                    if 'time' in s:
                        set_setting('summary_time_3d', s['time'])
                    if 'enabled' in s:
                        set_setting('summary_3d_enabled', 'true' if s['enabled'] else 'false')
                elif t == '1w':
                    if 'day' in s:
                        set_setting('summary_day_1w', s['day'])
                    if 'time' in s:
                        set_setting('summary_time_1w', s['time'])
                    if 'enabled' in s:
                        set_setting('summary_1w_enabled', 'true' if s['enabled'] else 'false')
        elif range_type == 'today':
            if 'time' in data:
                set_setting('summary_time_today', data['time'])
            if 'enabled' in data:
                set_setting('summary_today_enabled', 'true' if data['enabled'] else 'false')
        elif range_type == 'yesterday':
            if 'time' in data:
                set_setting('summary_time_yesterday', data['time'])
            if 'enabled' in data:
                set_setting('summary_yesterday_enabled', 'true' if data['enabled'] else 'false')
        elif range_type == '3d':
            if 'time' in data:
                set_setting('summary_time_3d', data['time'])
            if 'enabled' in data:
                set_setting('summary_3d_enabled', 'true' if data['enabled'] else 'false')
        elif range_type == '1w':
            if 'day' in data:
                set_setting('summary_day_1w', data['day'])
            if 'time' in data:
                set_setting('summary_time_1w', data['time'])
            if 'enabled' in data:
                set_setting('summary_1w_enabled', 'true' if data['enabled'] else 'false')
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


# ======== 定时自动备份调度 ========

def get_backup_schedule() -> dict:
    """获取每日备份时间配置（按具体时间 HH:MM 触发，生成 .db + .json 两个文件）"""
    from database import get_setting
    def _is_on(key: str, default: str = 'false') -> bool:
        val = get_setting(key, default)
        return val.lower() == 'true' if val else (default.lower() == 'true')
    return {
        'enabled': _is_on('daily_backup_enabled', 'false'),
        'time': get_setting('daily_backup_time', '04:00'),
        'keep_count': int(get_setting('backup_keep_count', '10')),
    }


def update_backup_schedule(data: dict) -> dict:
    """更新每日备份配置（启用/禁用、执行时间）"""
    from database import set_setting
    try:
        if 'enabled' in data:
            set_setting('daily_backup_enabled', 'true' if data['enabled'] else 'false')
        if 'time' in data:
            # 验证时间格式 HH:MM
            time_val = data['time']
            if isinstance(time_val, str) and ':' in time_val:
                parts = time_val.split(':')
                h, m = int(parts[0]), int(parts[1])
                if 0 <= h <= 23 and 0 <= m <= 59:
                    set_setting('daily_backup_time', time_val)
        if 'keep_count' in data:
            val = max(1, min(100, int(data['keep_count'])))
            set_setting('backup_keep_count', str(val))

        # 如果调度器已初始化，重新调度备份任务
        if _scheduler is not None:
            _reschedule_backup_job()

        return {'success': True, 'message': '每日备份设置已更新'}
    except Exception as e:
        logger.error(f"更新每日备份设置失败: {e}")
        return {'success': False, 'message': str(e)}


def init_backup_schedule():
    """初始化每日备份调度（应用启动时调用）"""
    _reschedule_backup_job()


def _reschedule_backup_job():
    """重新调度每日备份任务（基于具体的 HH:MM 时间，使用 CronTrigger 每天执行）"""
    schedule = get_backup_schedule()

    job_exists = False
    try:
        job_exists = _scheduler.get_job('auto_backup') is not None
    except Exception:
        job_exists = False

    if schedule['enabled']:
        time_str = schedule['time']  # "HH:MM"
        parts = time_str.split(':')
        hour = int(parts[0])
        minute = int(parts[1])
        trigger = CronTrigger(hour=hour, minute=minute)
        
        if job_exists:
            try:
                _scheduler.reschedule_job('auto_backup', trigger=trigger)
                logger.info(f"✅ [Scheduler] 每日备份时间已更新为每天 {time_str}")
            except JobLookupError:
                job_exists = False

        if not job_exists:
            func = _backup_task_func
            if func:
                _scheduler.add_job(
                    func,
                    trigger,
                    id='auto_backup',
                    name='每日备份',
                    replace_existing=True
                )
                logger.info(f"✅ [Scheduler] 每日备份已启用，时间: 每天 {time_str}")
            else:
                logger.warning("⚠️ [Scheduler] 每日备份函数未注册，无法添加定时任务")
    else:
        if job_exists:
            try:
                _scheduler.remove_job('auto_backup')
                logger.info("⏹️ [Scheduler] 每日备份已禁用并移除")
            except JobLookupError:
                pass
        else:
            logger.info("⏹️ [Scheduler] 每日备份保持禁用状态")