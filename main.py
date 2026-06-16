#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
caijing18 财经新闻聚合平台 - 主程序入口
- 启动 Flask Web 服务器（财经新闻管理面板）
- 后台运行 Telegram Bot（监听频道消息）
- 定时任务管理（数据清理、统计、AI 新闻总结）
- AI 每日财经总结（集成 OpenAI 兼容 API）

URL 格式：
  /summary/YYYYMMDD/1  - 当日总结（基于当天全部新闻，不限制条数）
  /summary/YYYYMMDD/3  - 近三天总结（基于三天每日总结综合生成）
  /summary/YYYYMMDD/7  - 近一周总结（基于七天每日总结综合生成）
  /summary/1           - 当日总结简写
  /summary/3           - 近三天总结简写
  /summary/7           - 近一周总结简写
"""

import os
import sys
import logging
import hashlib
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request, session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import atexit

# 加载环境变量
load_dotenv()

# ============ 日志配置 ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# ============ 导入项目模块 ============
from database import (
    init_database, get_session, cleanup_old_data, get_stats,
    FinanceNews, save_news, save_ai_summary, get_latest_ai_summary,
    get_ai_summary_by_date, get_ai_summaries_by_date_range,
    get_enabled_channels, add_channel, get_channels,
    get_setting, set_setting, get_all_settings
)
from ai_summary import generate_daily_summary, generate_merged_summary, generate_news_analysis, list_available_models
from tg_scraper import scrape_all_channels

# ============ Flask 应用配置 ============
app = Flask(__name__, template_folder='web/templates')
app.config['JSON_AS_ASCII'] = False
app.config['JSON_SORT_KEYS'] = False

# ============ 定时任务调度器 ============
scheduler = BackgroundScheduler()
scheduler.start()


# ============ 定时任务函数 ============

def cleanup_task():
    """定时清理任务：删除 7 天前的旧数据"""
    logger.info(f"🧹 [Task] 数据清理任务执行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        deleted = cleanup_old_data()
        logger.info(f"✅ [Task] 清理完成，删除了 {deleted} 条旧数据")
    except Exception as e:
        logger.error(f"❌ [Task] 清理失败: {str(e)}")


def stats_task():
    """定时统计任务：生成统计信息"""
    logger.info(f"📊 [Task] 统计任务执行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        stats = get_stats()
        logger.info(f"✅ [Task] 统计信息: {stats}")
    except Exception as e:
        logger.error(f"❌ [Task] 统计失败: {str(e)}")


def scrape_telegram_task():
    """定时抓取 Telegram 公共频道消息"""
    logger.info("=" * 60)
    logger.info(f"🔍 [Scraper] 开始抓取频道消息 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    try:
        total = scrape_all_channels(save_news)
        if total > 0:
            logger.info(f"✅ [Scraper] 抓取完成，本次新增 {total} 条新闻")
        else:
            logger.info(f"⏭️ [Scraper] 没有新消息")
    except Exception as e:
        logger.error(f"❌ [Scraper] 抓取失败: {str(e)}")
    logger.info("=" * 60)


def ai_summary_task():
    """定时任务：生成每日 AI 新闻总结"""
    logger.info(f"🤖 [Task] AI 每日总结任务执行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        _generate_summary_for_range('1d', '每日', 1)
        logger.info("✅ [Task] AI 每日总结生成完成")
    except Exception as e:
        logger.error(f"❌ [Task] AI 每日总结生成失败: {str(e)}")


def ai_summary_task_3d():
    """定时任务：生成近 3 天 AI 综合总结"""
    logger.info(f"🤖 [Task] AI 近3天总结任务执行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        _generate_merged_summary_for_range('3d', '近3天', 3)
        logger.info("✅ [Task] AI 近3天总结生成完成")
    except Exception as e:
        logger.error(f"❌ [Task] AI 近3天总结生成失败: {str(e)}")


def ai_summary_task_1w():
    """定时任务：生成近 1 周 AI 综合总结"""
    logger.info(f"🤖 [Task] AI 近1周总结任务执行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        _generate_merged_summary_for_range('1w', '近1周', 7)
        logger.info("✅ [Task] AI 近1周总结生成完成")
    except Exception as e:
        logger.error(f"❌ [Task] AI 近1周总结生成失败: {str(e)}")


# ============ 工具函数 ============

def _get_date_range(days: int, ref_date: str = None):
    """
    获取日期范围（使用 UTC 时间，与数据库 datetime.utcnow 保持一致）

    Args:
        days: 往前推的天数
        ref_date: 参考日期 YYYYMMDD，None 则用今天

    Returns:
        (start_datetime, date_label, ref_datetime)
    """
    if ref_date:
        try:
            # ref_date 是本地日期 YYYYMMDD，转换为 UTC 起始时间
            local_ref = datetime.strptime(ref_date, '%Y%m%d')
            local_ref = local_ref.replace(hour=0, minute=0, second=0, microsecond=0)
            ref = local_ref - timedelta(hours=8)  # 转换为 UTC
        except ValueError:
            ref = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # 使用本地日期转换到 UTC，确保覆盖完整本地日
        local_now = datetime.utcnow() + timedelta(hours=8)
        local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        ref = local_midnight - timedelta(hours=8)

    start_time = ref - timedelta(days=days - 1)
    start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # date_label 用本地日期（东八区）
    if ref_date:
        date_label = f"{ref_date[:4]}-{ref_date[4:6]}-{ref_date[6:8]}"
    else:
        local_now = datetime.utcnow() + timedelta(hours=8)
        date_label = local_now.strftime('%Y-%m-%d')

    return start_time, date_label, ref


def _generate_summary_for_range(
    range_key: str, range_label: str, days: int,
    top_per_tag: int = 9999, ref_date: str = None
):
    """
    生成指定范围的基础 AI 总结

    Args:
        range_key: 范围键值 '1d'/'3d'/'1w'
        range_label: 友好名称
        days: 天数
        top_per_tag: 每标签最多取多少条
        ref_date: 参考日期 YYYYMMDD
    """
    start_time, date_label, _ = _get_date_range(days, ref_date)

    session = get_session()
    try:
        news_list = session.query(FinanceNews).filter(
            FinanceNews.created_time >= start_time
        ).order_by(FinanceNews.published_time.desc()).all()
    finally:
        session.close()

    if not news_list:
        logger.warning(f"⚠️ [AI] {range_label}总结: 无新闻数据，跳过生成")
        return False

    logger.info(f"🤖 [AI] {range_label}总结: 共 {len(news_list)} 条新闻，开始生成...")

    # 将 ORM 对象转为字典（ai_summary 模块需要 dict 类型）
    news_dicts = _news_orm_to_dict_list(news_list)

    # 生成总结
    success = generate_daily_summary(
        news_items=news_dicts,
        time_range=range_label,
        date_label=date_label,
        save_func=save_ai_summary
    )

    if success:
        logger.info(f"✅ [AI] {range_label}总结生成完成（{len(news_list)} 条）")
    else:
        logger.warning(f"⚠️ [AI] {range_label}总结生成失败")

    return success


def _generate_merged_summary_for_range(
    range_key: str, range_label: str, days: int, ref_date: str = None
):
    """
    生成合并的 AI 总结（用于 3d/1w）
    先生成每天的单独总结，再合并
    """
    start_time, date_label, ref = _get_date_range(days, ref_date)

    session = get_session()
    try:
        news_list = session.query(FinanceNews).filter(
            FinanceNews.created_time >= start_time
        ).order_by(FinanceNews.published_time.desc()).all()
    finally:
        session.close()

    if not news_list:
        logger.warning(f"⚠️ [AI] {range_label}总结: 无新闻数据，跳过生成")
        return False

    logger.info(f"🤖 [AI] {range_label}总结: 共 {len(news_list)} 条新闻，开始生成...")

    # 将 ORM 对象转为字典（ai_summary 模块需要 dict 类型）
    news_dicts = _news_orm_to_dict_list(news_list)

    success = generate_merged_summary(
        daily_summaries=news_dicts,
        time_range=range_label,
        date_label=date_label,
    )

    if success:
        logger.info(f"✅ [AI] {range_label}总结生成完成（{len(news_list)} 条）")
    else:
        logger.warning(f"⚠️ [AI] {range_label}总结生成失败")

    return success


def news_to_dict(news):
    """将 FinanceNews 对象转为字典（UTC 时间添加 +00:00 标记以便前端正确处理）"""
    pub_time = news.published_time.isoformat() if news.published_time else None
    if pub_time and not pub_time.endswith('+00:00') and not pub_time.endswith('Z'):
        pub_time += '+00:00'
    cre_time = news.created_time.isoformat() if news.created_time else None
    if cre_time and not cre_time.endswith('+00:00') and not cre_time.endswith('Z'):
        cre_time += '+00:00'
    return {
        'id': news.id,
        'title': news.title,
        'content': news.content,
        'source': news.source,
        'tags': news.tags.split(',') if news.tags else [],
        'url': news.url,
        'message_id': news.message_id,
        'published_time': pub_time,
        'created_time': cre_time,
    }


def _news_orm_to_dict_list(news_list) -> list:
    """将 FinanceNews ORM 对象列表转为字典列表（供 AI 总结模块使用）"""
    results = []
    for news in news_list:
        tags = news.tags.split(',') if news.tags else []
        results.append({
            'title': news.title,
            'content': news.content,
            'tags': tags,
            'source': news.source or 'Telegram',
            'url': news.url,
            'published_time': news.published_time.isoformat() if news.published_time else None,
            'created_time': news.created_time.isoformat() if news.created_time else None,
        })
    return results


def _get_range_news_count(days: int, ref_date: str = None) -> int:
    """获取指定范围内的新闻数量"""
    start_time, _, _ = _get_date_range(days, ref_date)
    session = get_session()
    try:
        count = session.query(FinanceNews).filter(
            FinanceNews.created_time >= start_time
        ).count()
        return count
    except Exception as e:
        logger.error(f"❌ [_get_range_news_count] 查询失败: {e}")
        return 0
    finally:
        session.close()


def get_scrape_interval_minutes() -> int:
    """获取当前抓取间隔（分钟）"""
    val = get_setting('scrape_interval_minutes', '30')
    try:
        return max(1, int(val))
    except (ValueError, TypeError):
        return 30


def reschedule_scrape_job(interval_minutes: int):
    """重新调度抓取任务"""
    try:
        scheduler.reschedule_job(
            'tg_scrape',
            trigger=IntervalTrigger(minutes=interval_minutes)
        )
        logger.info(f"✅ [Scheduler] 抓取间隔已更新为 {interval_minutes} 分钟")
        return True
    except Exception as e:
        logger.error(f"❌ [Scheduler] 重新调度失败: {str(e)}")
        return False


def sync_config_channels_to_db():
    """将 config.py 中的 TG_CHANNELS 自动同步到数据库，并返回是否新增了频道"""
    added = 0
    try:
        import config
        existing_channels = get_channels()
        existing_urls = {c['url'].rstrip('/') for c in existing_channels}

        for url in getattr(config, 'TG_CHANNEL_URLS', []):
            url = url.rstrip('/')
            if url not in existing_urls:
                result = add_channel(url)
                if result.get('success'):
                    added += 1
                    logger.info(f"✅ [Sync] 已自动添加频道: {url}")
                else:
                    logger.info(f"⏭️ [Sync] 频道已存在: {url}")

        logger.info(f"✅ [Sync] 配置频道同步完成，新增 {added} 个频道")
        return added
    except Exception as e:
        logger.error(f"❌ [Sync] 频道同步失败: {str(e)}")
        return 0


# ============ 路由：网页页面 ============

@app.route('/')
def index():
    """首页"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"❌ [Web] 首页加载失败: {str(e)}")
        return f"<h1>服务器错误</h1><p>{str(e)}</p>", 500


@app.route('/news')
def news_page():
    """新闻列表页面"""
    try:
        return render_template('news.html')
    except Exception as e:
        logger.error(f"❌ [Web] 新闻页加载失败: {str(e)}")
        return f"<h1>服务器错误</h1><p>{str(e)}</p>", 500


@app.route('/summary')
@app.route('/summary/<path:path>')
def summary_page(path='1'):
    """AI 总结页面"""
    try:
        parts = path.split('/')
        if len(parts) == 2 and parts[0].isdigit() and len(parts[0]) == 8:
            # /summary/YYYYMMDD/[1|3|7]
            date_str = parts[0]
            range_num = int(parts[1]) if len(parts) > 1 else 1
        elif len(parts) == 1 and parts[0].isdigit():
            # /summary/1 或 /summary/3 或 /summary/7
            local_now = datetime.utcnow() + timedelta(hours=8)
            date_str = local_now.strftime('%Y%m%d')
            range_num = int(parts[0])
        else:
            # 默认显示当天的 1d 总结
            local_now = datetime.utcnow() + timedelta(hours=8)
            date_str = local_now.strftime('%Y%m%d')
            range_num = 1

        range_map = {1: '1d', 3: '3d', 7: '1w'}
        range_key = range_map.get(range_num, '1d')

        # 格式化成 date_label
        date_label = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

        # 查询总结
        summary = get_ai_summary_by_date(range_key, date_label)

        if summary:
            return render_template('summary.html', summary=summary)

        # 没有则生成
        date_str_full = date_str
        success = _generate_summary_for_range('1d', '今日', 1, ref_date=date_str_full)

        if success:
            summary = get_ai_summary_by_date('1d', date_label)
            if summary:
                return render_template('summary.html', summary=summary)

        return render_template('summary.html', error="暂无今日总结，请稍后再试")

    except Exception as e:
        logger.error(f"❌ [Web] 获取默认总结失败: {str(e)}")
        return render_template('summary.html', error=str(e)), 500


# ---------- API 路由 ----------

@app.route('/api/summary', methods=['POST'])
def api_generate_summary():
    """API：手动触发 AI 总结生成"""
    try:
        range_key = request.json.get('range', '1d')
        ref_date = request.json.get('date')
        ref_date_str = ref_date.replace('-', '')[:8] if ref_date else None

        if range_key == '1d':
            success = _generate_summary_for_range('1d', '每日', 1, ref_date=ref_date_str)
        elif range_key == '3d':
            success = _generate_merged_summary_for_range('3d', '近3天', 3, ref_date=ref_date_str)
        elif range_key == '1w':
            success = _generate_merged_summary_for_range('1w', '近1周', 7, ref_date=ref_date_str)
        else:
            return jsonify({'success': False, 'message': '无效的 range 参数'})

        if success:
            return jsonify({'success': True, 'message': f'{range_key} 总结生成成功'})
        else:
            return jsonify({'success': False, 'message': '生成失败，请检查日志'})
    except Exception as e:
        logger.error(f"❌ [API] 生成总结失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/summary/status')
def api_summary_status():
    """API：获取 AI 总结状态"""
    try:
        from database import get_ai_summary_status
        status = get_ai_summary_status()
        return jsonify({'success': True, 'data': status})
    except Exception as e:
        logger.error(f"❌ [API] 获取总结状态失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# ---------- 管理后台 API 路由 ----------

@app.route('/api/admin/login', methods=['POST'])
def api_admin_login():
    """管理员登录"""
    from database import verify_admin_password
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')

    if verify_admin_password(username, password):
        session['admin'] = username
        return jsonify({'success': True, 'message': '登录成功'})
    return jsonify({'success': False, 'message': '用户名或密码错误'})


@app.route('/api/admin/logout')
def api_admin_logout():
    """管理员登出"""
    session.pop('admin', None)
    return jsonify({'success': True, 'message': '已退出'})


@app.route('/api/admin/check')
def api_admin_check():
    """检查是否已登录"""
    is_admin = session.get('admin') is not None
    return jsonify({'is_admin': is_admin})


@app.route('/api/admin/change_password', methods=['POST'])
def api_admin_change_password():
    """修改管理员密码"""
    from database import change_admin_password
    if not session.get('admin'):
        return jsonify({'success': False, 'message': '未登录'})

    data = request.json
    result = change_admin_password(
        username=session['admin'],
        old_password=data.get('old_password', ''),
        new_password=data.get('new_password', '')
    )
    return jsonify(result)


# ---------- 频道管理 API ----------

@app.route('/api/admin/channels')
def api_get_channels():
    """获取所有频道列表"""
    channels = get_channels()
    return jsonify({'success': True, 'data': channels})


@app.route('/api/admin/channels/add', methods=['POST'])
def api_add_channel():
    """添加频道"""
    data = request.json
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'success': False, 'message': '请输入频道 URL'})
    result = add_channel(url)
    return jsonify(result)


@app.route('/api/admin/channels/remove', methods=['POST'])
def api_remove_channel():
    """删除频道"""
    from database import remove_channel
    data = request.json
    channel_id = data.get('id', '')
    result = remove_channel(channel_id)
    return jsonify(result)


@app.route('/api/admin/channels/toggle', methods=['POST'])
def api_toggle_channel():
    """启用/禁用频道"""
    from database import toggle_channel
    data = request.json
    channel_id = data.get('id', '')
    enabled = data.get('enabled', True)
    result = toggle_channel(channel_id, enabled)
    return jsonify(result)


# ---------- 系统设置 API ----------

@app.route('/api/admin/settings')
def api_get_settings():
    """获取所有系统设置"""
    settings = get_all_settings()
    return jsonify({'success': True, 'data': settings})


@app.route('/api/admin/settings/update', methods=['POST'])
def api_update_settings():
    """更新系统设置"""
    data = request.json
    key = data.get('key', '')
    value = data.get('value', '')

    if not key:
        return jsonify({'success': False, 'message': '缺少设置键名'})

    success = set_setting(key, str(value))

    # 如果修改的是抓取间隔，重新调度任务
    if success and key == 'scrape_interval_minutes':
        interval = get_scrape_interval_minutes()
        reschedule_scrape_job(interval)

    return jsonify({'success': success, 'message': '设置已更新' if success else '更新失败'})


@app.route('/api/admin/settings/get/<key>')
def api_get_setting(key):
    """获取单个设置值"""
    default = request.args.get('default', '')
    value = get_setting(key, default)
    return jsonify({'success': True, 'data': {key: value}})


# ---------- 抓取控制 API ----------

@app.route('/api/admin/scrape/trigger', methods=['POST'])
def api_trigger_scrape():
    """手动触发立即抓取"""
    logger.info("🔄 [API] 手动触发抓取...")
    try:
        total = scrape_all_channels(save_news)
        return jsonify({'success': True, 'message': f'抓取完成，新增 {total} 条新闻', 'count': total})
    except Exception as e:
        logger.error(f"❌ [API] 手动抓取失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/admin/scrape/interval')
def api_get_scrape_interval():
    """获取当前抓取间隔"""
    interval = get_scrape_interval_minutes()
    return jsonify({'success': True, 'data': {'interval_minutes': interval}})


@app.route('/api/admin/scrape/interval', methods=['POST'])
def api_set_scrape_interval():
    """设置抓取间隔"""
    data = request.json
    try:
        interval = int(data.get('interval_minutes', 30))
        interval = max(1, min(interval, 1440))  # 限制 1 分钟 ~ 24 小时
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': '无效的间隔值'})

    # 保存到数据库
    set_setting('scrape_interval_minutes', str(interval))

    # 重新调度任务
    reschedule_scrape_job(interval)

    return jsonify({'success': True, 'message': f'抓取间隔已设为 {interval} 分钟'})


# ---------- 新闻数据 API ----------

@app.route('/api/news')
def api_get_news():
    """获取新闻列表"""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    tag = request.args.get('tag')

    session = get_session()
    try:
        query = session.query(FinanceNews)
        if tag:
            query = query.filter(FinanceNews.tags.like(f'%{tag}%'))
        news_list = query.order_by(
            FinanceNews.published_time.desc()
        ).limit(limit).offset(offset).all()

        total = query.count()

        return jsonify({
            'success': True,
            'data': [news_to_dict(n) for n in news_list],
            'total': total,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.error(f"❌ [API] 获取新闻失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        session.close()


@app.route('/api/news/<news_id>')
def api_get_news_detail(news_id):
    """获取新闻详情"""
    session = get_session()
    try:
        news = session.query(FinanceNews).filter(FinanceNews.id == news_id).first()
        if not news:
            return jsonify({'success': False, 'message': '新闻不存在'}), 404
        return jsonify({'success': True, 'data': news_to_dict(news)})
    except Exception as e:
        logger.error(f"❌ [API] 获取新闻详情失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        session.close()


@app.route('/api/news/search')
def api_search_news():
    """搜索新闻"""
    keyword = request.args.get('q', '').strip()
    limit = request.args.get('limit', 50, type=int)

    if not keyword:
        return jsonify({'success': False, 'message': '请输入搜索关键词'})

    session = get_session()
    try:
        results = session.query(FinanceNews).filter(
            (FinanceNews.title.like(f'%{keyword}%')) |
            (FinanceNews.content.like(f'%{keyword}%')) |
            (FinanceNews.tags.like(f'%{keyword}%'))
        ).order_by(FinanceNews.published_time.desc()).limit(limit).all()

        return jsonify({
            'success': True,
            'data': [news_to_dict(n) for n in results],
            'total': len(results),
            'keyword': keyword
        })
    except Exception as e:
        logger.error(f"❌ [API] 搜索新闻失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        session.close()


@app.route('/api/tags')
def api_get_tags():
    """获取所有标签"""
    session = get_session()
    try:
        news_list = session.query(FinanceNews).order_by(
            FinanceNews.published_time.desc()
        ).limit(1000).all()

        tag_counts = {}
        for n in news_list:
            if n.tags:
                for tag in n.tags.split(','):
                    tag = tag.strip()
                    if tag:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1

        sorted_tags = sorted(tag_counts.items(), key=lambda x: -x[1])
        return jsonify({
            'success': True,
            'data': [{'name': t, 'count': c} for t, c in sorted_tags]
        })
    except Exception as e:
        logger.error(f"❌ [API] 获取标签失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        session.close()


@app.route('/api/stats')
def api_get_stats():
    """获取统计数据"""
    try:
        stats = get_stats()
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        logger.error(f"❌ [API] 获取统计失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/db/info')
def api_db_info():
    """获取数据库信息"""
    from database import get_database_info
    try:
        info = get_database_info()
        return jsonify({'success': True, 'data': info})
    except Exception as e:
        logger.error(f"❌ [API] 获取数据库信息失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# ============ 文生图 API 路由 ============

@app.route('/api/tts', methods=['POST'])
def api_tts():
    """TTS 文字转语音（预留）"""
    return jsonify({'success': False, 'message': '功能开发中'})


@app.route('/api/asr', methods=['POST'])
def api_asr():
    """ASR 语音转文字（预留）"""
    return jsonify({'success': False, 'message': '功能开发中'})


# ============ 历史数据 API ============

@app.route('/api/news/history')
def api_news_history():
    """按日期获取当天历史新闻摘要"""
    date_str = request.args.get('date')
    if not date_str:
        local_now = datetime.utcnow() + timedelta(hours=8)
        date_str = local_now.strftime('%Y-%m-%d')

    session = get_session()
    try:
        start = datetime.strptime(date_str, '%Y-%m-%d')
        end = start + timedelta(days=1)
        # 转换为 UTC
        start_utc = start - timedelta(hours=8)
        end_utc = end - timedelta(hours=8)

        news_list = session.query(FinanceNews).filter(
            FinanceNews.published_time >= start_utc,
            FinanceNews.published_time < end_utc
        ).order_by(FinanceNews.published_time.desc()).all()

        return jsonify({
            'success': True,
            'data': [news_to_dict(n) for n in news_list],
            'total': len(news_list),
            'date': date_str
        })
    except Exception as e:
        logger.error(f"❌ [API] 获取历史新闻失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        session.close()


# ============ AI 状态 / 配置 API ============

@app.route('/api/ai/status')
def api_ai_status():
    """获取 AI 配置状态（供管理后台使用）"""
    try:
        import config as app_config
        api_key = getattr(app_config, 'AI_API_KEY', '') or os.getenv('AI_API_KEY', '')
        base_url = getattr(app_config, 'AI_BASE_URL', '') or os.getenv('AI_BASE_URL', '')
        model = getattr(app_config, 'AI_MODEL', '') or os.getenv('AI_MODEL', '')

        # 测试 API 连接
        connected = False
        try:
            from ai_summary import test_api_connection
            connected = test_api_connection()
        except Exception:
            pass

        # 获取缓存状态
        from database import get_ai_summary_status
        summary_status = get_ai_summary_status()
        summary_cached = any(v.get('cached') for v in summary_status.values())

        return jsonify({
            'success': True,
            'data': {
                'configured': bool(api_key),
                'base_url': base_url or '-',
                'model': model or '-',
                'connected': connected,
                'summary_cached': summary_cached,
                'summaries': summary_status
            }
        })
    except Exception as e:
        logger.error(f"❌ [API] 获取 AI 状态失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/ai/summary')
def api_ai_summary_get():
    """获取指定范围的 AI 总结"""
    range_key = request.args.get('range', '1d')
    try:
        summary = get_latest_ai_summary(range_key)
        return jsonify(summary)
    except Exception as e:
        logger.error(f"❌ [API] 获取 AI 总结失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/ai/summary/refresh', methods=['POST'])
def api_ai_summary_refresh():
    """手动刷新 AI 总结"""
    try:
        range_key = request.json.get('range', '1d')
        ref_date = request.json.get('date')
        ref_date_str = ref_date.replace('-', '')[:8] if ref_date else None

        if range_key == '1d':
            success = _generate_summary_for_range('1d', '每日', 1, ref_date=ref_date_str)
            news_count = _get_range_news_count(1, ref_date_str)
        elif range_key == '3d':
            success = _generate_merged_summary_for_range('3d', '近3天', 3, ref_date=ref_date_str)
            news_count = _get_range_news_count(3, ref_date_str)
        elif range_key == '1w':
            success = _generate_merged_summary_for_range('1w', '近1周', 7, ref_date=ref_date_str)
            news_count = _get_range_news_count(7, ref_date_str)
        else:
            return jsonify({'success': False, 'message': '无效的 range 参数'})

        return jsonify({
            'success': success,
            'message': f'{range_key} 总结生成成功' if success else '生成失败',
            'data': {
                'range': range_key,
                'news_count': news_count if success else 0
            }
        })
    except Exception as e:
        logger.error(f"❌ [API] 刷新 AI 总结失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/cleanup', methods=['POST'])
def api_cleanup():
    """手动执行数据清理"""
    logger.info("🧹 [API] 手动触发数据清理...")
    try:
        deleted = cleanup_old_data()
        return jsonify({'success': True, 'message': str(deleted)})
    except Exception as e:
        logger.error(f"❌ [API] 清理失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


# ============ AI 模型 API ============

@app.route('/api/ai/models')
def api_ai_models():
    """获取可用的 AI 模型列表"""
    try:
        models = list_available_models()
        return jsonify({'success': True, 'data': models})
    except Exception as e:
        logger.error(f"❌ [API] 获取模型列表失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/ai/analysis', methods=['POST'])
def api_ai_analysis():
    """AI 新闻分析"""
    try:
        data = request.json
        news_ids = data.get('news_ids', [])
        prompt = data.get('prompt', '请综合分析以下财经新闻')

        session = get_session()
        try:
            news_list = session.query(FinanceNews).filter(
                FinanceNews.id.in_(news_ids)
            ).all()
        finally:
            session.close()

        if not news_list:
            return jsonify({'success': False, 'message': '未找到指定的新闻'})

        # 将 ORM 对象转为字典（ai_summary 模块需要 dict 类型）
        news_dicts = _news_orm_to_dict_list(news_list)

        result = generate_news_analysis(news_dicts, prompt)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"❌ [API] AI 分析失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# ============ Flask Session 密钥 ============

def _ensure_secret_key():
    """确保 Flask session 密钥已设置"""
    if 'SECRET_KEY' not in session:
        secret = get_setting('flask_secret_key', '')
        if not secret:
            secret = hashlib.sha256(os.urandom(32)).hexdigest()
            set_setting('flask_secret_key', secret)
        app.secret_key = secret


# ============ 任务调度配置 ============

def setup_scheduled_jobs():
    """配置并启动所有定时任务"""

    # 清理任务：每天凌晨 3:00 执行
    scheduler.add_job(
        cleanup_task,
        CronTrigger(hour=3, minute=0),
        id='cleanup',
        name='数据清理',
        replace_existing=True
    )

    # 统计任务：每小时执行一次
    scheduler.add_job(
        stats_task,
        IntervalTrigger(hours=1),
        id='stats',
        name='数据统计',
        replace_existing=True
    )

    # 抓取任务：从数据库获取间隔，默认为 30 分钟
    interval = get_scrape_interval_minutes()
    scheduler.add_job(
        scrape_telegram_task,
        IntervalTrigger(minutes=interval),
        id='tg_scrape',
        name='TG 频道抓取',
        replace_existing=True
    )
    logger.info(f"✅ [Scheduler] 抓取任务已启动，间隔 {interval} 分钟")

    # AI 总结任务：每天 9:00 生成昨日总结
    scheduler.add_job(
        ai_summary_task,
        CronTrigger(hour=9, minute=0),
        id='ai_summary',
        name='AI 每日总结',
        replace_existing=True
    )

    # AI 近 3 天总结：每天 9:30
    scheduler.add_job(
        ai_summary_task_3d,
        CronTrigger(hour=9, minute=30),
        id='ai_summary_3d',
        name='AI 近3天总结',
        replace_existing=True
    )

    # AI 近 1 周总结：每周一 10:00
    scheduler.add_job(
        ai_summary_task_1w,
        CronTrigger(day_of_week='mon', hour=10, minute=0),
        id='ai_summary_1w',
        name='AI 近1周总结',
        replace_existing=True
    )

    logger.info("✅ [Scheduler] 所有定时任务配置完成")
    logger.info(f"📋 [Scheduler] 当前任务列表:")
    for job in scheduler.get_jobs():
        logger.info(f"   - {job.name} ({job.id}): {job.trigger}")


# ============ 应用入口 ============

if __name__ == '__main__':
    print("=" * 60)
    print("📈 caijing18 财经新闻聚合平台")
    print("=" * 60)

    # 初始化数据库
    init_database()
    print("✅ [启动] 数据库初始化完成")

    # 确保密钥
    _ensure_secret_key()

    # 同步配置中的频道到数据库
    added = sync_config_channels_to_db()

    # 配置定时任务
    setup_scheduled_jobs()

    # 启动时立即执行一次抓取（异步执行）
    print("⏳ [启动] 正在执行首次频道抓取...")
    try:
        total = scrape_all_channels(save_news)
        print(f"✅ [启动] 首次抓取完成，新增 {total} 条新闻")
    except Exception as e:
        print(f"⚠️ [启动] 首次抓取失败: {str(e)}")

    # 启动 Web 服务
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    print(f"🌐 [启动] Web 服务: http://{host}:{port}")
    print(f"⏰ [启动] 抓取间隔: {get_scrape_interval_minutes()} 分钟")
    print("=" * 60)

    app.run(host=host, port=port, debug=debug)
