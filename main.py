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
    get_ai_summary_by_date, get_ai_summaries_by_date_range
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

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())


# ============ 定时任务函数 ============

def cleanup_task():
    """定时清理任务：删除 7 天前的数据"""
    logger.info("=" * 60)
    logger.info(f"🧹 [Task] 数据清理任务启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    try:
        deleted_count = cleanup_old_data()
        logger.info(f"✅ [Task] 清理完成，删除 {deleted_count} 条过期记录")
    except Exception as e:
        logger.error(f"❌ [Task] 清理失败: {str(e)}")
    logger.info("=" * 60)


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
    生成指定时间范围的 AI 总结（基于原始新闻数据）

    用于 1天总结：直接从该天的所有新闻生成（不限制每标签条数）
    3天/7天总结：由 _generate_merged_summary_for_range 处理

    Args:
        range_key: 范围键值 '1d'/'3d'/'1w'
        range_label: 范围描述 '今日'/'近3天'/'近1周'
        days: 天数 1/3/7
        top_per_tag: 每个标签最多取多少条（1天总结不限制，默认9999≈全部）
        ref_date: 参考日期 YYYYMMDD，None 则用今天
    """
    logger.info("=" * 60)
    logger.info(f"🤖 [AI] 生成 {range_label} AI 总结启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    try:
        session = get_session()
        try:
            start_time, date_label, _ = _get_date_range(days, ref_date)
            end_time = start_time + timedelta(days=days)

            news_query = session.query(FinanceNews).filter(
                FinanceNews.created_time >= start_time,
                FinanceNews.created_time < end_time
            ).order_by(FinanceNews.published_time.desc()).all()

            if not news_query:
                logger.info(f"⏭️ [AI] {range_label} 没有新闻数据，跳过")
                return False

            # 按标签分组（不限条数）
            tag_groups = {}
            for news in news_query:
                tags = news.tags.split(',') if news.tags else ['财经']
                for tag in tags:
                    tag = tag.strip()
                    if not tag:
                        continue
                    if tag not in tag_groups:
                        tag_groups[tag] = []
                    if len(tag_groups[tag]) < top_per_tag:
                        tag_groups[tag].append({
                            'title': news.title,
                            'content': news.content,
                            'tags': tags,
                            'source': news.source,
                            'url': news.url,
                            'published_at': news.published_time.isoformat() if news.published_time else None
                        })

            # 合并所有标签下的新闻（去重），保持分类结构
            seen_urls = set()
            news_items = []
            categorized_news = {}
            for tag in sorted(tag_groups.keys()):
                tag_key = tag
                categorized_news[tag_key] = []
                for item in tag_groups[tag]:
                    if item['url'] not in seen_urls:
                        seen_urls.add(item['url'])
                        categorized_news[tag_key].append(item)
                        news_items.append(item)

            total_raw = len(news_query)
            logger.info(
                f"📝 [AI] {range_label} 原始 {total_raw} 条 → "
                f"按标签去重后 {len(news_items)} 条 "
                f"（{len(categorized_news)} 个分类）"
            )

            if not news_items:
                logger.info(f"⏭️ [AI] {range_label} 没有新闻数据，跳过")
                return False

            # 生成按分类组织的总结
            summary = generate_daily_summary(
                news_items, time_range=range_label,
                categorized_news=categorized_news,
                date_label=date_label
            )

            if summary:
                save_ai_summary(range_key, summary, len(news_items), date_label=date_label)
                logger.info(
                    f"✅ [AI] {range_label} 总结生成并持久化成功，"
                    f"输入 {len(news_items)} 条新闻，日期 {date_label}"
                )
                return True
            else:
                logger.warning(f"⚠️ [AI] {range_label} 总结生成失败")
                return False

        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ [AI] {range_label} 总结任务失败: {str(e)}")
        return False


def _generate_merged_summary_for_range(
    range_key: str, range_label: str, days: int,
    ref_date: str = None
):
    """
    基于多日每日总结(1d)生成综合总结（用于 3天/7天）

    策略：
    1. 获取指定日期范围内每天的 1d 总结
    2. 如果某天没有每日总结，则先为该天生成
    3. 将所有每日总结合并，交由 AI 生成综合总结
    """
    logger.info("=" * 60)
    logger.info(f"🤖 [AI] 生成 {range_label} 综合总结（基于每日总结合成）")
    logger.info("=" * 60)

    try:
        # 确定日期范围（本地日期）
        if ref_date:
            local_ref = datetime.strptime(ref_date, '%Y%m%d')
        else:
            local_ref = datetime.utcnow() + timedelta(hours=8)
            local_ref = local_ref.replace(hour=0, minute=0, second=0, microsecond=0)

        # 生成每天的日期标签 YYYY-MM-DD
        daily_summaries = []
        for i in range(days):
            day = local_ref - timedelta(days=i)
            day_label = day.strftime('%Y-%m-%d')

            # 尝试从数据库获取该天的1d总结
            summary = get_ai_summary_by_date('1d', day_label)

            if summary and summary.get('content'):
                daily_summaries.append(summary)
            else:
                # 没有现成的每日总结，则需要先生成
                day_str = day.strftime('%Y%m%d')
                logger.info(f"📝 [AI] 未找到 {day_label} 的每日总结，正在先生成...")
                generated = _generate_summary_for_range('1d', '今日', 1, ref_date=day_str)
                if generated:
                    summary = get_ai_summary_by_date('1d', day_label)
                    if summary and summary.get('content'):
                        daily_summaries.append(summary)

        # 按日期升序排列（最早的在前）
        daily_summaries.sort(key=lambda x: x.get('date_label', ''))

        if not daily_summaries:
            logger.warning(f"⏭️ [AI] {range_label} 没有可用的每日总结，跳过")
            return False

        logger.info(f"📚 [AI] 已收集 {len(daily_summaries)} 天每日总结")

        # 日期范围标签
        if ref_date:
            date_label = f"{ref_date[:4]}-{ref_date[4:6]}-{ref_date[6:8]}"
        else:
            date_label = local_ref.strftime('%Y-%m-%d')

        # 调用 AI 生成综合总结
        merged = generate_merged_summary(
            daily_summaries,
            time_range=range_label,
            date_label=date_label
        )

        if merged:
            total_count = sum(s.get('news_count', 0) for s in daily_summaries)
            save_ai_summary(range_key, merged, total_count, date_label=date_label)
            logger.info(f"✅ [AI] {range_label} 综合总结生成成功，基于 {len(daily_summaries)} 天每日总结")
            return True
        else:
            logger.warning(f"⚠️ [AI] {range_label} 综合总结生成失败")
            return False

    except Exception as e:
        logger.error(f"❌ [AI] {range_label} 综合总结任务失败: {str(e)}")
        return False


# ============ 定时 AI 总结任务 ============

def ai_summary_task():
    """定时 AI 总结任务：生成今日总结"""
    today_str = datetime.now().strftime('%Y%m%d')
    return _generate_summary_for_range('1d', '今日', 1, ref_date=today_str)


def ai_summary_task_3d():
    """定时 AI 总结任务：生成近3天综合总结（基于3天每日总结）"""
    today_str = datetime.now().strftime('%Y%m%d')
    return _generate_merged_summary_for_range('3d', '近3天', 3, ref_date=today_str)


def ai_summary_task_1w():
    """定时 AI 总结任务：生成近1周综合总结（基于7天每日总结）"""
    today_str = datetime.now().strftime('%Y%m%d')
    return _generate_merged_summary_for_range('1w', '近1周', 7, ref_date=today_str)


# ============ 辅助函数：将 ORM 对象转换为字典 ============

def news_to_dict(news):
    """将 FinanceNews 对象转换为字典"""
    return {
        'id': news.id,
        'title': news.title,
        'content': news.content,
        'tags': news.tags.split(',') if news.tags else [],
        'created_at': news.created_time.isoformat() if news.created_time else None,
        'published_at': news.published_time.isoformat() if news.published_time else None,
        'source': news.source,
        'url': news.url,
    }


# ============ Flask 路由 ============

# ---------- 页面路由 ----------

@app.route('/')
def index():
    """主页"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"❌ [Web] 获取主页失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/summary/<date>/<int:range_days>')
def summary_page_date_range(date, range_days):
    """
    AI 总结独立页面（带日期和范围）
    /summary/20260616/1  - 当日总结
    /summary/20260616/3  - 近三天总结
    /summary/20260616/7  - 近一周总结
    """
    try:
        # 验证日期格式
        if not date or len(date) != 8 or not date.isdigit():
            return render_template('summary.html', error="日期格式无效，请使用 YYYYMMDD 格式")

        if range_days not in [1, 3, 7]:
            return render_template('summary.html', error="天数格式无效，请使用 1、3 或 7")

        range_map = {1: '1d', 3: '3d', 7: '1w'}
        range_key = range_map[range_days]

        date_label = f"{date[:4]}-{date[4:6]}-{date[6:8]}"

        # 尝试从数据库获取已缓存的总结
        summary = get_ai_summary_by_date(range_key, date_label)

        if summary:
            return render_template('summary.html', summary=summary)

        # 没有缓存，根据范围生成
        if range_days == 1:
            # 1天总结：从当天所有新闻生成
            success = _generate_summary_for_range('1d', '今日', 1, ref_date=date)
        else:
            # 3天/7天总结：基于每日总结合成
            range_names = {3: '近3天', 7: '近1周'}
            success = _generate_merged_summary_for_range(range_key, range_names[range_days], range_days, ref_date=date)

        if success:
            summary = get_ai_summary_by_date(range_key, date_label)
            if summary:
                return render_template('summary.html', summary=summary)

        return render_template('summary.html', error="生成总结失败，请稍后再试")

    except Exception as e:
        logger.error(f"❌ [Web] 生成总结失败: {str(e)}")
        return render_template('summary.html', error=f"生成失败: {str(e)}")


@app.route('/summary/<path:fallback>')
def summary_page_fallback(fallback):
    """
    AI 总结页面（统一 fallback 处理器）
    /summary/1   - 当天1天
    /summary/3   - 当天三天
    /summary/7   - 当天一周
    /summary/20260616  - 指定日期当天总结（默认1天）
    /summary/20260616  - 指定日期（旧格式日期数字，匹配 path）
    """
    try:
        # fallback 是一个字符串，需要判断是日期还是范围
        # 日期格式: 8位数字 YYYYMMDD
        # 范围格式: 1, 3, 7 之一

        local_now = datetime.utcnow() + timedelta(hours=8)
        today_str = local_now.strftime('%Y%m%d')

        if fallback in ['1', '3', '7']:
            # 范围简写模式：使用当天日期
            range_days = int(fallback)
            date_str = today_str
        elif len(fallback) == 8 and fallback.isdigit():
            # 日期模式：默认1天
            range_days = 1
            date_str = fallback
        else:
            return render_template('summary.html', error="无效的路径，请使用 /summary/1 、 /summary/3 、 /summary/7 或 /summary/YYYYMMDD[/天数]")

        # 验证日期合理性
        y = int(date_str[:4])
        if y < 2000 or y > 2100:
            date_str = today_str

        range_map = {1: '1d', 3: '3d', 7: '1w'}
        range_key = range_map[range_days]
        date_label = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

        # 尝试从数据库获取已缓存的总结
        summary = get_ai_summary_by_date(range_key, date_label)

        if summary:
            return render_template('summary.html', summary=summary)

        # 没有缓存，根据范围生成
        range_names = {1: '今日', 3: '近3天', 7: '近1周'}
        if range_days == 1:
            success = _generate_summary_for_range('1d', '今日', 1, ref_date=date_str)
        else:
            success = _generate_merged_summary_for_range(range_key, range_names[range_days], range_days, ref_date=date_str)

        if success:
            summary = get_ai_summary_by_date(range_key, date_label)
            if summary:
                return render_template('summary.html', summary=summary)

        return render_template('summary.html', error="生成总结失败，请稍后再试")

    except Exception as e:
        logger.error(f"❌ [Web] 生成总结失败: {str(e)}")
        return render_template('summary.html', error=f"生成失败: {str(e)}")


@app.route('/summary')
def summary_page_default():
    """AI 总结页面（默认今天/1天）"""
    try:
        local_now = datetime.utcnow() + timedelta(hours=8)
        date_label = local_now.strftime('%Y-%m-%d')

        summary = get_ai_summary_by_date('1d', date_label)

        if summary:
            return render_template('summary.html', summary=summary)

        # 没有则生成
        date_str = local_now.strftime('%Y%m%d')
        success = _generate_summary_for_range('1d', '今日', 1, ref_date=date_str)

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
            return jsonify({"error": "无效的 range, 请使用 1d/3d/1w"}), 400

        if success:
            if ref_date:
                dl = ref_date
            else:
                dl = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d')
            summary = get_ai_summary_by_date(range_key, dl)
            return jsonify({"success": True, "data": summary})
        return jsonify({"error": "生成失败"}), 500

    except Exception as e:
        logger.error(f"❌ [API] 生成总结失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/summary', methods=['GET'])
def api_get_summary():
    """API：获取 AI 总结"""
    try:
        range_key = request.args.get('range', '1d')
        date_label = request.args.get('date')
        if not date_label:
            date_label = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d')
        summary = get_ai_summary_by_date(range_key, date_label)
        if summary:
            return jsonify({"success": True, "data": summary})
        return jsonify({"success": False, "error": "暂无总结"}), 404
    except Exception as e:
        logger.error(f"❌ [API] 获取总结失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/news', methods=['GET'])
def get_news():
    """获取新闻列表（分页）"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = request.args.get('limit', per_page, type=int)  # 兼容 limit 参数

        session = get_session()
        try:
            # 获取总数
            total = session.query(FinanceNews).count()

            # 获取分页数据
            offset = (page - 1) * per_page
            articles = session.query(FinanceNews).order_by(
                FinanceNews.published_time.desc()
            ).limit(per_page).offset(offset).all()

            return jsonify({
                'success': True,
                'data': [news_to_dict(a) for a in articles],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            })
        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ [API] 获取新闻失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/search', methods=['GET'])
def search_news():
    """按关键词搜索新闻"""
    try:
        keyword = request.args.get('keyword', '', type=str)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = request.args.get('limit', per_page, type=int)

        if not keyword:
            return jsonify({"error": "keyword required"}), 400

        session = get_session()
        try:
            # 构建查询
            query = session.query(FinanceNews).filter(
                (FinanceNews.title.ilike(f'%{keyword}%')) |
                (FinanceNews.content.ilike(f'%{keyword}%')) |
                (FinanceNews.tags.ilike(f'%{keyword}%'))
            )

            # 获取总数
            total = query.count()

            # 获取分页数据
            offset = (page - 1) * per_page
            articles = query.order_by(
                FinanceNews.published_time.desc()
            ).limit(per_page).offset(offset).all()

            return jsonify({
                'success': True,
                'data': [news_to_dict(a) for a in articles],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            })
        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ [API] 搜索失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/news/by-tag', methods=['GET'])
def get_news_by_tag():
    """按标签筛选新闻"""
    try:
        tag = request.args.get('tag', '', type=str)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = request.args.get('limit', per_page, type=int)

        if not tag:
            return jsonify({"error": "tag required"}), 400

        session = get_session()
        try:
            # 构建查询
            query = session.query(FinanceNews).filter(
                FinanceNews.tags.ilike(f'%{tag}%')
            )

            # 获取总数
            total = query.count()

            # 获取分页数据
            offset = (page - 1) * per_page
            articles = query.order_by(
                FinanceNews.published_time.desc()
            ).limit(per_page).offset(offset).all()

            return jsonify({
                'success': True,
                'data': [news_to_dict(a) for a in articles],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            })
        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ [API] 按标签筛选失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/filter', methods=['GET'])
def filter_news():
    """多条件组合筛选"""
    try:
        tags = request.args.get('tags', '', type=str)
        start_date = request.args.get('start_date', '', type=str)
        end_date = request.args.get('end_date', '', type=str)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = request.args.get('limit', per_page, type=int)

        session = get_session()
        try:
            # 开始构建查询
            query = session.query(FinanceNews)

            # 按标签筛选
            if tags:
                tag_list = [t.strip() for t in tags.split(',')]
                tag_conditions = [FinanceNews.tags.ilike(f'%{tag}%') for tag in tag_list]
                from sqlalchemy import or_
                query = query.filter(or_(*tag_conditions))

            # 按开始日期筛选
            if start_date:
                from datetime import datetime as dt
                start_dt = dt.fromisoformat(start_date)
                query = query.filter(FinanceNews.created_time >= start_dt)

            # 按结束日期筛选
            if end_date:
                from datetime import datetime as dt
                end_dt = dt.fromisoformat(end_date)
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(FinanceNews.created_time <= end_dt)

            # 获取总数
            total = query.count()

            # 获取分页数据
            offset = (page - 1) * per_page
            articles = query.order_by(
                FinanceNews.published_time.desc()
            ).limit(per_page).offset(offset).all()

            return jsonify({
                'success': True,
                'data': [news_to_dict(a) for a in articles],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            })
        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ [API] 多条件筛选失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/tags', methods=['GET'])
def get_all_tags():
    """获取所有可用标签"""
    try:
        session = get_session()
        try:
            # 获取所有包含标签的新闻
            articles = session.query(FinanceNews).filter(
                FinanceNews.tags.isnot(None)
            ).all()

            all_tags = set()
            for article in articles:
                if article.tags:
                    tags = article.tags.split(',')
                    all_tags.update([t.strip() for t in tags if t.strip()])

            return jsonify({
                'success': True,
                'data': sorted(list(all_tags))
            })
        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ [API] 获取标签失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_api_stats():
    """获取统计信息"""
    try:
        stats = get_stats()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"❌ [API] 获取统计信息失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/cleanup', methods=['POST'])
def trigger_cleanup():
    """手动触发数据清理"""
    try:
        deleted_count = cleanup_old_data()
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} records'
        })
    except Exception as e:
        logger.error(f"❌ [API] 手动清理失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'success': True,
        'message': 'Service is running',
        'timestamp': datetime.now().isoformat()
    })


# ============ 管理员 API ============

# Flask 密钥（用于 session）
app.secret_key = os.getenv('FLASK_SECRET_KEY', hashlib.sha256(b'caijing18_admin').hexdigest())

def admin_required():
    """检查管理员是否已登录"""
    if not session.get('admin_logged_in'):
        return False
    return True

@app.route('/admin')
def admin_page():
    """管理后台页面"""
    try:
        return render_template('admin.html')
    except Exception as e:
        logger.error(f"❌ [Admin] 页面加载失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/check', methods=['GET'])
def admin_check():
    """检查管理登录状态"""
    try:
        return jsonify({
            'logged_in': session.get('admin_logged_in', False),
            'username': session.get('admin_username', '')
        })
    except Exception as e:
        logger.error(f"❌ [Admin] check失败: {str(e)}")
        return jsonify({'logged_in': False, 'username': ''})

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """管理员登录"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')

        from database import verify_admin_password
        if verify_admin_password(username, password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return jsonify({'success': True, 'message': '登录成功'})
        else:
            return jsonify({'success': False, 'message': '用户名或密码错误'})
    except Exception as e:
        logger.error(f"❌ [Admin] 登录失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    """管理员退出"""
    session.clear()
    return jsonify({'success': True, 'message': '已退出'})

@app.route('/api/admin/channels', methods=['GET'])
def admin_get_channels():
    """获取频道列表"""
    if not admin_required():
        return jsonify({'success': False, 'message': '未登录', 'need_login': True}), 401
    try:
        from database import get_channels
        channels = get_channels()
        return jsonify({'success': True, 'data': channels})
    except Exception as e:
        logger.error(f"❌ [Admin] 获取频道失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/admin/channels', methods=['POST'])
def admin_add_channel():
    """添加频道"""
    if not admin_required():
        return jsonify({'success': False, 'message': '未登录', 'need_login': True}), 401
    try:
        from database import add_channel
        url = request.json.get('url', '').strip()
        if not url:
            return jsonify({'success': False, 'message': 'URL不能为空'})
        result = add_channel(url)
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ [Admin] 添加频道失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/admin/channels/<channel_id>', methods=['DELETE'])
def admin_remove_channel(channel_id):
    """删除频道"""
    if not admin_required():
        return jsonify({'success': False, 'message': '未登录', 'need_login': True}), 401
    try:
        from database import remove_channel
        result = remove_channel(channel_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ [Admin] 删除频道失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/admin/channels/<channel_id>/toggle', methods=['POST'])
def admin_toggle_channel(channel_id):
    """启用/禁用频道"""
    if not admin_required():
        return jsonify({'success': False, 'message': '未登录', 'need_login': True}), 401
    try:
        from database import toggle_channel
        enabled = request.json.get('enabled', True)
        result = toggle_channel(channel_id, enabled)
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ [Admin] 切换频道状态失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/admin/scrape', methods=['POST'])
def admin_scrape():
    """手动触发抓取"""
    if not admin_required():
        return jsonify({'success': False, 'message': '未登录', 'need_login': True}), 401
    try:
        total = scrape_all_channels(save_news)
        return jsonify({'success': True, 'data': {'count': total}})
    except Exception as e:
        logger.error(f"❌ [Admin] 手动抓取失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/change-password', methods=['POST'])
def admin_change_password():
    """修改管理员密码"""
    if not admin_required():
        return jsonify({'success': False, 'message': '未登录', 'need_login': True}), 401
    try:
        from database import change_admin_password
        data = request.json
        username = session.get('admin_username', 'admin')
        result = change_admin_password(
            username,
            data.get('old_password', ''),
            data.get('new_password', '')
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ [Admin] 修改密码失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# ============ AI 状态 API ============

@app.route('/api/ai/status', methods=['GET'])
def ai_status():
    """获取 AI 服务状态"""
    try:
        ai_configured = bool(os.getenv('AI_API_KEY', ''))
        ai_base_url = os.getenv('AI_BASE_URL', '')
        ai_model = os.getenv('AI_MODEL', '')
        
        # 检查是否有缓存的总结
        summary_cached = False
        summaries = {}
        for rk in ['1d', '3d', '1w']:
            summary = get_latest_ai_summary(rk)
            summaries[rk] = {
                'cached': summary is not None,
                'news_count': summary.get('news_count', 0) if summary else 0,
                'generated_at': summary.get('generated_at') if summary else None
            }
            if summary:
                summary_cached = True
        
        # 检测 AI API 连接
        connected = False
        if ai_configured:
            try:
                from ai_summary import generate_news_analysis
                connected = True  # 如果导入成功则认为可连接
            except:
                connected = False
        
        return jsonify({
            'success': True,
            'data': {
                'configured': ai_configured,
                'base_url': ai_base_url,
                'model': ai_model,
                'connected': connected,
                'summary_cached': summary_cached,
                'summaries': summaries
            }
        })
    except Exception as e:
        logger.error(f"❌ [API] AI状态查询失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/ai/summary/refresh', methods=['POST'])
def api_ai_summary_refresh():
    """API：手动刷新 AI 总结"""
    try:
        range_key = request.json.get('range', '1d')
        ref_date_str = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y%m%d')
        
        if range_key == '1d':
            success = _generate_summary_for_range('1d', '今日', 1, ref_date=ref_date_str)
        elif range_key == '3d':
            success = _generate_merged_summary_for_range('3d', '近3天', 3, ref_date=ref_date_str)
        elif range_key == '1w':
            success = _generate_merged_summary_for_range('1w', '近1周', 7, ref_date=ref_date_str)
        else:
            return jsonify({"error": "无效的 range"}), 400
        
        if success:
            date_label = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d')
            summary = get_ai_summary_by_date(range_key, date_label)
            return jsonify({"success": True, "data": summary})
        return jsonify({"error": "生成失败"}), 500
    except Exception as e:
        logger.error(f"❌ [API] 刷新总结失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ============ 错误处理 ============

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(error):
    logger.error(f"❌ [Web] 服务器错误: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500


# ============ 主程序 ============

def main():
    """程序入口"""
    logger.info("=" * 60)
    logger.info("🚀 [Main] caijing18 财经新闻聚合平台启动")
    logger.info("=" * 60)

    # 初始化数据库
    logger.info("📦 [Main] 初始化数据库...")
    try:
        init_database()
        logger.info("✅ [Main] 数据库初始化完成")
    except Exception as e:
        logger.error(f"❌ [Main] 数据库初始化失败: {str(e)}")
        sys.exit(1)

    # 添加定时任务
    logger.info("⏰ [Main] 添加定时任务...")
    try:
        # 每天 03:00 执行数据清理
        scheduler.add_job(
            cleanup_task,
            trigger=CronTrigger(hour=3, minute=0),
            id='cleanup_job',
            name='Daily cleanup task',
            replace_existing=True
        )
        logger.info("✅ [Main] 数据清理任务 - 每天 03:00 执行")

        # 每小时执行统计
        scheduler.add_job(
            stats_task,
            trigger=CronTrigger(minute=0),
            id='stats_job',
            name='Hourly stats task',
            replace_existing=True
        )
        logger.info("✅ [Main] 统计任务 - 每小时 00 分执行")

        # 每天 08:00 生成每日 AI 总结
        scheduler.add_job(
            ai_summary_task,
            trigger=CronTrigger(hour=8, minute=0),
            id='ai_summary_daily',
            name='Daily AI summary',
            replace_existing=True
        )
        logger.info("✅ [Main] AI 每日新闻总结 - 每天 08:00 执行")

        # 每天 08:30 生成近 3 天综合总结
        scheduler.add_job(
            ai_summary_task_3d,
            trigger=CronTrigger(hour=8, minute=30),
            id='ai_summary_3d',
            name='3-day AI summary',
            replace_existing=True
        )
        logger.info("✅ [Main] AI 近3天综合总结 - 每天 08:30 执行")

        # 每天 09:00 生成近 1 周综合总结
        scheduler.add_job(
            ai_summary_task_1w,
            trigger=CronTrigger(hour=9, minute=0),
            id='ai_summary_1w',
            name='1-week AI summary',
            replace_existing=True
        )
        logger.info("✅ [Main] AI 近1周综合总结 - 每天 09:00 执行")

        # 每隔 30 分钟抓取 Telegram 频道
        scheduler.add_job(
            scrape_telegram_task,
            trigger=CronTrigger(minute='*/30'),
            id='tg_scrape',
            name='Telegram scrape',
            replace_existing=True
        )
        logger.info("✅ [Main] Telegram 频道抓取 - 每 30 分钟执行")
    except Exception as e:
        logger.error(f"❌ [Main] 添加定时任务失败: {str(e)}")
    finally:
        logger.info("✅ [Main] 定时任务配置完成")

    # 启动 Flask 服务器
    logger.info("=" * 60)
    logger.info("🌐 [Main] 启动 Flask Web 服务器...")
    logger.info("端口: 5000")
    logger.info("访问地址: http://localhost:5000")
    logger.info("=" * 60)

    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False
        )
    except Exception as e:
        logger.error(f"❌ [Main] Flask 启动失败: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
