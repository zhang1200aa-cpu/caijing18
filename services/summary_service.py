"""
AI 总结相关业务逻辑
"""
import logging
from datetime import datetime, timedelta
from database import FinanceNews, save_ai_summary
from db import session_scope_readonly
from .news_service import news_to_dict
from ai_summary import generate_daily_summary, generate_merged_summary

logger = logging.getLogger(__name__)


def get_date_range(days: int, ref_date: str = None):
    """
    获取日期范围（使用 UTC 时间，与数据库 datetime.utcnow 保持一致）

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


def get_news_dicts_in_range(days: int, ref_date: str = None):
    """
    获取指定范围内的新闻（已转成 dict 列表）

    Returns:
        (dict_list, date_label, news_count)
    """
    start_time, date_label, _ = get_date_range(days, ref_date)

    with session_scope_readonly() as session:
        news_list = session.query(FinanceNews).filter(
            FinanceNews.created_time >= start_time
        ).order_by(FinanceNews.published_time.desc()).all()

    dicts = [news_to_dict(n) for n in news_list]
    return dicts, date_label, len(dicts)


def get_range_news_count(days: int, ref_date: str = None) -> int:
    """获取指定范围内的新闻数量"""
    start_time, _, _ = get_date_range(days, ref_date)
    with session_scope_readonly() as session:
        count = session.query(FinanceNews).filter(
            FinanceNews.created_time >= start_time
        ).count()
        return count


def generate_summary_for_range(
    range_key: str, range_label: str, days: int,
    top_per_tag: int = 9999, ref_date: str = None
):
    """
    生成指定范围的基础 AI 总结（1d）
    返回 bool 是否成功
    """
    news_dicts, date_label, total_count = get_news_dicts_in_range(days, ref_date)

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


def generate_merged_summary_for_range(
    range_key: str, range_label: str, days: int, ref_date: str = None
):
    """
    生成合并的 AI 总结（用于 3d/1w）
    先逐日生成每日总结，再综合生成合并总结
    返回 bool 是否成功
    """
    start_time, date_label, ref = get_date_range(days, ref_date)

    daily_summaries = []
    total_news_count = 0

    for day_offset in range(days):
        day_start = start_time + timedelta(days=day_offset)
        day_end = day_start + timedelta(days=1)

        with session_scope_readonly() as session:
            day_news = session.query(FinanceNews).filter(
                FinanceNews.created_time >= day_start,
                FinanceNews.created_time < day_end
            ).order_by(FinanceNews.published_time.desc()).all()

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