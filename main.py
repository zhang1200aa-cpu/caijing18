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
app = Flask(__name__, template_folder='web/templates', static_folder='web/static', static_url_path='/static')
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
            local_ref = datetime.strptime(ref_date, '%Y%m%d')
            local_ref = local_ref.replace(hour=0, minute=0, second=0, microsecond=0)
            ref = local_ref - timedelta(hours=8)
        except ValueError:
            ref = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        local_now = datetime.utcnow() + timedelta(hours=8)
        local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        ref = local_midnight - timedelta(hours=8)

    start_time = ref - timedelta(days=days - 1)
    start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)

    if ref_date:
        date_label = f"{ref_date[:4]}-{ref_date[4:6]}-{ref_date[6:8]}"
    else:
        local_now = datetime.utcnow() + timedelta(hours=8)
        date_label = local_now.strftime('%Y-%m-%d')

    return start_time, date_label, ref


def news_to_dict(news):
    """将 FinanceNews ORM 对象转为 dict"""
    tags = news.tags.split(',') if news.tags else []
    return {
        'id': news.id,
        'title': news.title,
        'content': news.content,
        'tags': tags,
        'source': news.source or 'Telegram',
        'url': news.url,
        'published_time': news.published_time.isoformat() if news.published_time else None,
        'created_time': news.created_time.isoformat() if news.created_time else None,
    }


def _get_news_dicts_in_range(days: int, ref_date: str = None):
    """
    获取指定范围内的新闻（已转成 dict 列表）

    Args:
        days: 往前推的天数
        ref_date: 参考日期 YYYYMMDD

    Returns:
        (dict_list, date_label, news_count)
    """
    start_time, date_label, _ = _get_date_range(days, ref_date)

    session_db = get_session()
    try:
        news_list = session_db.query(FinanceNews).filter(
            FinanceNews.created_time >= start_time
        ).order_by(FinanceNews.published_time.desc()).all()
    finally:
        session_db.close()

    dicts = [news_to_dict(n) for n in news_list]
    return dicts, date_label, len(dicts)


def _get_range_news_count(days: int, ref_date: str = None) -> int:
    """获取指定范围内的新闻数量"""
    start_time, _, _ = _get_date_range(days, ref_date)
    session_db = get_session()
    try:
        count = session_db.query(FinanceNews).filter(
            FinanceNews.created_time >= start_time
        ).count()
        return count
    except Exception as e:
        logger.error(f"❌ 统计新闻数量失败: {str(e)}")
        return 0
    finally:
        session_db.close()


def _generate_summary_for_range(
    range_key: str, range_label: str, days: int,
    top_per_tag: int = 9999, ref_date: str = None
):
    """
    生成指定范围的基础 AI 总结（1d）

    Args:
        range_key: 范围键值 '1d'/'3d'/'1w'
        range_label: 友好名称
        days: 天数
        ref_date: 参考日期 YYYYMMDD

    Returns:
        bool 是否成功
    """
    news_dicts, date_label, total_count = _get_news_dicts_in_range(days, ref_date)

    if not news_dicts:
        logger.warning(f"⚠️ [AI] {range_label}总结: 无新闻数据，跳过生成")
        return False

    logger.info(f"🤖 [AI] {range_label}总结: 共 {total_count} 条新闻，开始生成...")

    result = generate_daily_summary(
        news_items=news_dicts,
        time_range=range_label,
        date_label=date_label,
    )

    if result:
        logger.info(f"✅ [AI] {range_label}总结生成成功，长度 {len(result)} 字符")
        save_ai_summary(
            range_key=range_key,
            content=result,
            news_count=total_count,
            date_label=date_label
        )
        return True
    else:
        logger.warning(f"⚠️ [AI] {range_label}总结生成失败")
        return False


def _generate_merged_summary_for_range(
    range_key: str, range_label: str, days: int, ref_date: str = None
):
    """
    生成合并的 AI 总结（用于 3d/1w）
    先逐日生成每日总结，再综合生成合并总结

    Args:
        range_key: 范围键值 '3d'/'1w'
        range_label: 友好名称
        days: 天数
        ref_date: 参考日期 YYYYMMDD

    Returns:
        bool 是否成功
    """
    start_time, date_label, ref = _get_date_range(days, ref_date)

    daily_summaries = []
    total_news_count = 0

    for day_offset in range(days):
        day_start = start_time + timedelta(days=day_offset)
        day_end = day_start + timedelta(days=1)

        session_db = get_session()
        try:
            day_news = session_db.query(FinanceNews).filter(
                FinanceNews.created_time >= day_start,
                FinanceNews.created_time < day_end
            ).order_by(FinanceNews.published_time.desc()).all()
        finally:
            session_db.close()

        if not day_news:
            continue

        day_dicts = [news_to_dict(n) for n in day_news]

        local_day = datetime.utcnow() + timedelta(hours=8) - timedelta(days=days - 1 - day_offset)
        day_date_label = local_day.strftime('%Y-%m-%d')

        day_result = generate_daily_summary(
            news_items=day_dicts,
            time_range="每日",
            date_label=day_date_label,
        )

        if day_result:
            daily_summaries.append({
                'date_label': day_date_label,
                'content': day_result,
                'news_count': len(day_dicts)
            })
            total_news_count += len(day_dicts)
            logger.info(f"✅ [AI] 第{day_offset+1}天({day_date_label})每日总结生成完成")
        else:
            logger.warning(f"⚠️ [AI] 第{day_offset+1}天({day_date_label})每日总结生成失败，跳过")

    if not daily_summaries:
        logger.warning(f"⚠️ [AI] {range_label}总结: 没有任何一天的每日总结生成成功，跳过")
        return False

    logger.info(f"🤖 [AI] {range_label}综合总结: 基于 {len(daily_summaries)} 天的每日总结，共 {total_news_count} 条新闻，开始生成...")

    result = generate_merged_summary(
        daily_summaries=daily_summaries,
        time_range=range_label,
        date_label=date_label,
    )

    if result:
        logger.info(f"✅ [AI] {range_label}综合总结生成成功，长度 {len(result)} 字符")
        save_ai_summary(
            range_key=range_key,
            content=result,
            news_count=total_news_count,
            date_label=date_label
        )
        return True
    else:
        logger.warning(f"⚠️ [AI] {range_label}综合总结生成失败")
        return False


# ============ 抓取间隔调度 ============

def get_scrape_interval_minutes():
    """获取抓取间隔（分钟）"""
    interval_str = get_setting('scrape_interval_minutes', '30')
    try:
        return max(1, int(interval_str))
    except (ValueError, TypeError):
        return 30


def reschedule_scrape_job(interval: int):
    """重新调度抓取任务"""
    scheduler.reschedule_job(
        'tg_scrape',
        trigger=IntervalTrigger(minutes=interval)
    )
    logger.info(f"✅ [Scheduler] 抓取间隔已更新为 {interval} 分钟")


def sync_config_channels_to_db():
    """从配置中同步频道到数据库"""
    from config import TG_CHANNEL_URLS
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


# ============ Flask 路由 ============

@app.route('/')
def index():
    """首页：管理面板"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"❌ [Web] 加载首页失败: {str(e)}")
        return f"<h1>caijing18</h1><p>财经新闻聚合平台</p><p>错误: {str(e)}</p>"


@app.route('/summary')
@app.route('/summary/<range_key>')
def summary_page(range_key='1d'):
    """AI 总结页面"""
    date_str = request.args.get('date')
    try:
        if date_str:
            summary = get_ai_summary_by_date(range_key, date_str)
            if summary:
                return render_template('summary.html', summary=summary)
            return render_template('summary.html', error="该日期无总结数据")
        else:
            summary = get_latest_ai_summary(range_key)
            if summary:
                return render_template('summary.html', summary=summary)
        return render_template('summary.html', error="暂无今日总结，请稍后再试")
    except Exception as e:
        logger.error(f"❌ [Web] 获取默认总结失败: {str(e)}")
        return render_template('summary.html', error=str(e)), 500


# ============ API 路由 ============

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
    if success and key == 'scrape_interval_minutes':
        interval = get_scrape_interval_minutes()
        reschedule_scrape_job(interval)
    return jsonify({'success': success, 'message': '设置已更新' if success else '更新失败'})


@app.route('/api/admin/scrape/trigger', methods=['POST'])
def api_trigger_scrape():
    """手动触发立即抓取"""
    logger.info("🔄 [API] 手动触发抓取...")
    try:
        # 先检查是否有已配置的频道
        from database import get_enabled_channels
        db_channels = get_enabled_channels()
        from config import TG_CHANNEL_URLS
        if not db_channels and not TG_CHANNEL_URLS:
            return jsonify({
                'success': False,
                'message': '⚠️ 未绑定任何 Telegram 频道，请先添加频道',
                'need_channel': True
            })
        total = scrape_all_channels(save_news)
        message = f'抓取完成，新增 {total} 条新闻'
        if total == 0 and (not db_channels or len(db_channels) == 0):
            message = '⚠️ 没有可用的频道，请在管理后台添加 Telegram 频道后重试'
        elif total == 0:
            message = '没有新消息'
        return jsonify({'success': True, 'message': message, 'count': total})
    except Exception as e:
        logger.error(f"❌ [API] 手动抓取失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/news')
def api_get_news():
    """获取新闻列表"""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    tag = request.args.get('tag')
    session_db = get_session()
    try:
        query = session_db.query(FinanceNews)
        if tag:
            query = query.filter(FinanceNews.tags.like(f'%{tag}%'))
        news_list = query.order_by(FinanceNews.published_time.desc()).limit(limit).offset(offset).all()
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
        session_db.close()


@app.route('/api/news/<news_id>')
def api_get_news_detail(news_id):
    """获取新闻详情"""
    session_db = get_session()
    try:
        news = session_db.query(FinanceNews).filter(FinanceNews.id == news_id).first()
        if not news:
            return jsonify({'success': False, 'message': '新闻不存在'}), 404
        return jsonify({'success': True, 'data': news_to_dict(news)})
    except Exception as e:
        logger.error(f"❌ [API] 获取新闻详情失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        session_db.close()


@app.route('/api/news/search')
def api_search_news():
    """搜索新闻"""
    keyword = request.args.get('q', '').strip()
    limit = request.args.get('limit', 50, type=int)
    if not keyword:
        return jsonify({'success': False, 'message': '请输入搜索关键词'})
    session_db = get_session()
    try:
        results = session_db.query(FinanceNews).filter(
            FinanceNews.title.like(f'%{keyword}%')
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
        session_db.close()


@app.route('/api/tags')
def api_get_tags():
    """获取所有标签"""
    session_db = get_session()
    try:
        news_list = session_db.query(FinanceNews).order_by(
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
        session_db.close()


@app.route('/api/stats')
def api_get_stats():
    """获取统计数据"""
    try:
        stats = get_stats()
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        logger.error(f"❌ [API] 获取统计失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/ai/analysis', methods=['POST'])
def api_ai_analysis():
    """AI 新闻分析"""
    try:
        data = request.json
        news_ids = data.get('news_ids', [])
        news_id = data.get('news_id')
        if news_id:
            news_ids = [news_id]
        session_db = get_session()
        try:
            news_objs = session_db.query(FinanceNews).filter(FinanceNews.id.in_(news_ids)).all()
        finally:
            session_db.close()
        if not news_objs:
            return jsonify({'success': False, 'message': '未找到指定的新闻'})
        news_dicts = [news_to_dict(n) for n in news_objs]
        # Use single item analysis for each, or combine
        result = generate_news_analysis(news_dicts[0]) if news_dicts else None
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"❌ [API] AI 分析失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/ai/status')
def api_ai_status():
    """AI 系统状态"""
    try:
        from ai_summary import AIClient
        from database import get_ai_summary_status
        # 优先使用数据库中的设置，其次使用 config 中的环境变量
        db_settings = get_all_settings()
        api_key = db_settings.get('ai_api_key', '') or config.AI_API_KEY
        base_url = db_settings.get('ai_base_url', '') or config.AI_BASE_URL
        model = db_settings.get('ai_model', '') or config.AI_MODEL
        client = AIClient()
        connected = client.test_connection()
        status = get_ai_summary_status()
        summary_cached = any(v.get('cached') for v in status.values())
        return jsonify({
            'success': True,
            'data': {
                'configured': bool(api_key),
                'api_key': '****' + api_key[-4:] if api_key else '',
                'base_url': base_url,
                'model': model,
                'connected': connected,
                'summary_cached': summary_cached,
                'summaries': status
            }
        })
    except Exception as e:
        logger.error(f"❌ [API] AI 状态查询失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/admin/ai/settings', methods=['POST'])
def api_update_ai_settings():
    """更新 AI 设置"""
    try:
        data = request.json
        api_key = data.get('api_key', '')
        base_url = data.get('base_url', '')
        model = data.get('model', '')
        if api_key:
            set_setting('ai_api_key', api_key)
        if base_url:
            set_setting('ai_base_url', base_url)
        if model:
            set_setting('ai_model', model)
        logger.info(f"✅ [API] AI 设置已更新")
        return jsonify({'success': True, 'message': 'AI 设置已更新'})
    except Exception as e:
        logger.error(f"❌ [API] AI 设置更新失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/ai/summary')
def api_get_ai_summary():
    """获取 AI 总结"""
    try:
        range_key = request.args.get('range', '1d')
        summary = get_latest_ai_summary(range_key)
        if summary.get('success'):
            s = summary['data']
            # Render content with markdown-like conversion
            content = s['content']
            import re
            content = re.sub(r'^### ', '<h3>', content, flags=re.MULTILINE)
            content = re.sub(r'^#### ', '<h4>', content, flags=re.MULTILINE)
            content = re.sub(r'^- ', '<li>', content, flags=re.MULTILINE)
            content = content.replace('\n', '<br>')
            return jsonify({
                'success': True,
                'data': {
                    'content': content,
                    'news_count': s.get('news_count', 0),
                    'generated_at': s.get('generated_at')
                }
            })
        return jsonify({'success': False, 'message': '暂无总结'})
    except Exception as e:
        logger.error(f"❌ [API] 获取 AI 总结失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/ai/summary/refresh', methods=['POST'])
def api_refresh_ai_summary():
    """刷新 AI 总结"""
    try:
        data = request.json or {}
        range_key = data.get('range', '1d')
        ref_date = data.get('date')
        ref_date_str = ref_date.replace('-', '')[:8] if ref_date else None

        if range_key == '1d':
            success = _generate_summary_for_range('1d', '每日', 1, ref_date=ref_date_str)
            news_count = _get_range_news_count(1, ref_date_str)
        elif range_key == '3d':
            success = _generate_merged_summary_for_range('3d', '近3天', 3, ref_date=ref_date_str)
            news_count = _get_range_news_count(3, ref_date_str)
        elif range_key == '1w':
            success = _generate_merged_summary_for_range('1w', '近1周', 7, ref_date=ref_date_str)
            news_count = _get_range_news_count(3, ref_date_str)
        else:
            return jsonify({'success': False, 'message': '无效的 range 参数'})

        if success:
            return jsonify({'success': True, 'data': {'news_count': news_count}})
        else:
            return jsonify({'success': False, 'message': '生成失败，请检查日志或 API 配置'})
    except Exception as e:
        logger.error(f"❌ [API] 刷新 AI 总结失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/admin/cleanup', methods=['POST'])
def api_admin_cleanup():
    """清理重复/旧数据"""
    try:
        deleted = cleanup_old_data()
        return jsonify({'success': True, 'count': deleted})
    except Exception as e:
        logger.error(f"❌ [API] 清理失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/admin/settings/interval', methods=['POST'])
def api_update_interval():
    """更新抓取间隔"""
    try:
        data = request.json
        interval = int(data.get('interval', 30))
        if interval < 1:
            return jsonify({'success': False, 'message': '间隔必须大于 0'})
        set_setting('scrape_interval_minutes', str(interval))
        reschedule_scrape_job(interval)
        return jsonify({'success': True, 'message': f'抓取间隔已更新为 {interval} 分钟'})
    except Exception as e:
        logger.error(f"❌ [API] 更新间隔失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/admin/change-password', methods=['POST'])
def api_change_password():
    """修改管理员密码"""
    try:
        from database import verify_admin_password, set_setting as db_set
        data = request.json
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')

        if not old_password or not new_password:
            return jsonify({'success': False, 'message': '请填写原密码和新密码'})
        if len(new_password) < 4:
            return jsonify({'success': False, 'message': '新密码至少 4 位'})

        if not verify_admin_password('admin', old_password):
            return jsonify({'success': False, 'message': '原密码错误'})

        import hashlib
        new_hash = hashlib.sha256(new_password.encode()).hexdigest()
        db_set('admin_password', new_hash)
        return jsonify({'success': True, 'message': '密码修改成功'})
    except Exception as e:
        logger.error(f"❌ [API] 修改密码失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# ============ Session 密钥 ============

def _ensure_secret_key():
    """确保 Flask session 密钥已设置"""
    secret = get_setting('flask_secret_key', '')
    if not secret:
        secret = hashlib.sha256(os.urandom(32)).hexdigest()
        set_setting('flask_secret_key', secret)
    app.secret_key = secret


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
    print("=" * 60)
    print("📈 caijing18 财经新闻聚合平台")
    print("=" * 60)
    init_database()
    print("✅ [启动] 数据库初始化完成")
    _ensure_secret_key()
    sync_config_channels_to_db()
    setup_scheduled_jobs()
    print("⏳ [启动] 正在执行首次频道抓取...")
    try:
        total = scrape_all_channels(save_news)
        print(f"✅ [启动] 首次抓取完成，新增 {total} 条新闻")
    except Exception as e:
        print(f"⚠️ [启动] 首次抓取失败: {str(e)}")
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    print(f"🌐 [启动] Web 服务: http://{host}:{port}")
    print("=" * 60)
    app.run(host=host, port=port, debug=debug)
