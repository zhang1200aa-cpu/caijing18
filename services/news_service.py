"""
新闻相关业务逻辑
"""
import logging
from datetime import datetime, timedelta
from database import FinanceNews
from db import session_scope, session_scope_readonly
from ai_summary import generate_news_analysis

logger = logging.getLogger(__name__)


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


def get_news_list(limit=100, offset=0, tag=None):
    """获取新闻列表"""
    with session_scope_readonly() as session:
        query = session.query(FinanceNews)
        if tag:
            query = query.filter(FinanceNews.tags.like(f'%{tag}%'))
        total = query.count()
        news_list = query.order_by(
            FinanceNews.published_time.desc()
        ).limit(limit).offset(offset).all()
        return [news_to_dict(n) for n in news_list], total


def get_news_detail(news_id):
    """获取新闻详情"""
    with session_scope_readonly() as session:
        news = session.query(FinanceNews).filter(FinanceNews.id == news_id).first()
        if not news:
            return None
        return news_to_dict(news)


def search_news(keyword, limit=50):
    """搜索新闻"""
    with session_scope_readonly() as session:
        results = session.query(FinanceNews).filter(
            FinanceNews.title.like(f'%{keyword}%')
        ).order_by(FinanceNews.published_time.desc()).limit(limit).all()
        return [news_to_dict(n) for n in results]


def get_tags(limit=1000):
    """获取所有标签及其计数"""
    with session_scope_readonly() as session:
        news_list = session.query(FinanceNews).order_by(
            FinanceNews.published_time.desc()
        ).limit(limit).all()
        tag_counts = {}
        for n in news_list:
            if n.tags:
                for tag in n.tags.split(','):
                    tag = tag.strip()
                    if tag:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
        sorted_tags = sorted(tag_counts.items(), key=lambda x: -x[1])
        return [{'name': t, 'count': c} for t, c in sorted_tags]


def get_stats():
    """获取统计数据"""
    from database import get_stats as db_get_stats
    return db_get_stats()


def ai_analysis(news_ids):
    """AI 新闻分析"""
    with session_scope_readonly() as session:
        news_objs = session.query(FinanceNews).filter(
            FinanceNews.id.in_(news_ids)
        ).all()
    if not news_objs:
        return None, '未找到指定的新闻'
    news_dicts = [news_to_dict(n) for n in news_objs]
    result = generate_news_analysis(news_dicts[0])
    return result, None