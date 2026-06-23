#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 总结服务 - 重构版
支持: 当日总结、昨日总结、三日总结、一周总结、搜索结果总结
其中三日/一周总结基于每日总结再总结生成
新增: 按日期查看历史总结
"""
import json
import logging
import hashlib
import threading
from datetime import datetime, timedelta, timezone
from database import now_bj
from typing import Optional, List

import requests
from database import (
    get_session, get_news_by_time_range, search_news_by_text,
    get_setting, set_setting, AISummary, FinanceNews
)
import config

logger = logging.getLogger(__name__)

# ---------- 并发控制：每个生成任务使用独立锁，防止多人同时调用导致 AI 回答不一致 ----------
_gen_locks = {}
_gen_locks_lock = threading.Lock()

def _get_lock_for_key(key: str) -> threading.Lock:
    """获取或创建指定 key 的线程锁"""
    with _gen_locks_lock:
        if key not in _gen_locks:
            _gen_locks[key] = threading.Lock()
        return _gen_locks[key]

# 北京时区偏移 +8 小时
BJT = timezone(timedelta(hours=8))

# ---------- 日期工具函数 ----------

def now_bj() -> datetime:
    """返回当前北京时间"""
    return datetime.now(BJT)

def today_str() -> str:
    """返回今天的日期字符串 YYYY-MM-DD"""
    return now_bj().strftime('%Y-%m-%d')

def yesterday_str() -> str:
    """返回昨天的日期字符串 YYYY-MM-DD"""
    return (now_bj() - timedelta(days=1)).strftime('%Y-%m-%d')

def three_days_ago_str() -> str:
    """返回三天前的日期字符串"""
    return (now_bj() - timedelta(days=3)).strftime('%Y-%m-%d')

def week_ago_str() -> str:
    """返回一周前的日期字符串"""
    return (now_bj() - timedelta(days=7)).strftime('%Y-%m-%d')

def range_start_str(days: int) -> str:
    """返回包含今天在内的 N 天范围起始日期。"""
    return (now_bj() - timedelta(days=days - 1)).strftime('%Y-%m-%d')

def get_summary_context() -> str:
    """读取管理后台配置的 AI 总结上下文。"""
    return (get_setting('ai_summary_context') or '').strip()

def with_summary_context(system_prompt: str) -> str:
    context = get_summary_context()
    if not context:
        return system_prompt
    return (
        f"{system_prompt}\n\n"
        "以下是用户在管理后台配置的长期上下文，请在总结时结合使用；"
        "若与新闻事实冲突，以新闻事实为准：\n"
        f"{context}"
    )

# ---------- AI 调用 ----------

def call_ai(system_prompt: str, user_content: str, max_retries: int = 3) -> Optional[str]:
    """调用 OpenAI 兼容接口的 AI 总结"""
    api_key = get_setting('ai_api_key') or config.AI_API_KEY
    base_url = get_setting('ai_base_url') or config.AI_BASE_URL
    model = get_setting('ai_model') or config.AI_MODEL

    if not api_key or not base_url:
        logger.error("❌ [AI] API Key 或 Base URL 未配置")
        return None

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_content}
        ],
        'temperature': 0.3,
        'max_tokens': 4096
    }

    # 兼容 DeepSeek 等使用 /chat/completions 的接口
    api_url = base_url.rstrip('/')
    if not api_url.endswith('/chat/completions'):
        api_url += '/chat/completions'

    for attempt in range(max_retries):
        try:
            logger.info(f"🤖 [AI] 调用 {model} (尝试 {attempt+1}/{max_retries})...")
            resp = requests.post(api_url, headers=headers, json=payload, timeout=120)
            if resp.status_code == 200:
                result = resp.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                if content:
                    logger.info(f"✅ [AI] 调用成功，返回 {len(content)} 字符")
                    return content
                else:
                    logger.warning(f"⚠️ [AI] 返回内容为空")
            else:
                logger.warning(f"⚠️ [AI] HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"❌ [AI] 调用异常 (尝试 {attempt+1}): {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(3)

    logger.error("❌ [AI] 所有重试均失败")
    return None


# ---------- 提示词模板 ----------

SYSTEM_PROMPT_TODAY_QA = """你是一个专业的财经新闻分析师。请基于提供的今日财经新闻，回答用户提出的问题。

要求：
1. 严格基于提供的今日新闻内容进行分析和回答
2. 不要编造新闻中没有的信息
3. 如果新闻内容不足以回答用户问题，请明确说明
4. 用专业的财经分析语言
5. 使用中文输出，Markdown 格式
6. 引用相关新闻要点来支持你的分析

输出格式：
## 💡 分析回答

[直接回答用户问题，基于今日新闻进行分析]

### 📰 相关新闻要点
1. [相关新闻要点一]
2. [相关新闻要点二]
...

---

*回答基于今日 {news_count} 条财经新闻生成*"""

SYSTEM_PROMPT_DAILY = """你是一个专业的财经新闻分析师。请根据提供的新闻数据，生成一份结构化的财经新闻总结报告。

要求：
1. 按重要性排序，列出最重要的 3-5 个核心主题
2. 每个主题下概括关键事件和影响
3. 提供市场整体趋势分析（如果有足够信息）
4. 用专业的财经分析语言
5. 使用中文输出，Markdown 格式

输出格式：
## 📊 核心主题

### 1. [主题标题]
[分析内容]

### 2. [主题标题]
[分析内容]

...

## 📈 市场趋势
[整体趋势分析]

---

*报告基于 {news_count} 条财经新闻生成*"""

SYSTEM_PROMPT_COMPOSITE = """你是一个专业的财经新闻分析师。下面是过去几天每日财经新闻总结的集合，请基于这些每日总结，生成一份综合性、高质量的阶段性总结报告。

要求：
1. 分析过去 {period_days} 天的财经整体走势
2. 提炼出最重要的持续性主题和趋势
3. 指出关键转折点或重大事件
4. 提供市场展望
5. 使用专业的财经分析语言
6. 使用中文输出，Markdown 格式

输出格式：
## 🔍 阶段性总结（过去 {period_days} 天）

### 📋 总体趋势
[整体趋势分析]

### 🏆 重要主题
1. [主题一]
2. [主题二]
...

### 🔮 市场展望
[展望分析]

---

*本报告基于每日 AI 总结综合生成*"""


# ---------- 提示词持久化（管理后台可编辑）----------

def get_summary_prompts() -> dict:
    """从数据库获取自定义提示词，如未设置则返回默认值"""
    daily = get_setting('summary_prompt_daily', '')
    composite = get_setting('summary_prompt_composite', '')
    todayqa = get_setting('summary_prompt_todayqa', '')
    return {
        'daily': daily if daily else SYSTEM_PROMPT_DAILY,
        'composite': composite if composite else SYSTEM_PROMPT_COMPOSITE,
        'todayqa': todayqa if todayqa else SYSTEM_PROMPT_TODAY_QA,
        'daily_default': SYSTEM_PROMPT_DAILY,
        'composite_default': SYSTEM_PROMPT_COMPOSITE,
        'todayqa_default': SYSTEM_PROMPT_TODAY_QA,
        'has_custom_daily': bool(daily),
        'has_custom_composite': bool(composite),
        'has_custom_todayqa': bool(todayqa),
    }


def set_summary_prompts(daily: str = None, composite: str = None, todayqa: str = None) -> dict:
    """保存自定义提示词到数据库"""
    if daily is not None:
        set_setting('summary_prompt_daily', daily.strip())
    if composite is not None:
        set_setting('summary_prompt_composite', composite.strip())
    if todayqa is not None:
        set_setting('summary_prompt_todayqa', todayqa.strip())
    logger.info("✅ [提示词] 自定义提示词已保存")
    return {'success': True, 'message': '提示词已保存'}


def reset_summary_prompt(prompt_type: str) -> dict:
    """重置特定提示词为默认值（从数据库删除）"""
    if prompt_type == 'daily':
        set_setting('summary_prompt_daily', '')
        return {'success': True, 'message': '每日总结提示词已恢复默认'}
    elif prompt_type == 'composite':
        set_setting('summary_prompt_composite', '')
        return {'success': True, 'message': '复合总结提示词已恢复默认'}
    elif prompt_type == 'todayqa':
        set_setting('summary_prompt_todayqa', '')
        return {'success': True, 'message': '当日财经分析提示词已恢复默认'}
    return {'success': False, 'message': '未知的提示词类型'}


def _get_active_daily_prompt() -> str:
    """获取当前生效的每日提示词（优先使用数据库自定义版）"""
    custom = get_setting('summary_prompt_daily', '')
    return custom if custom else SYSTEM_PROMPT_DAILY


def _get_active_composite_prompt() -> str:
    """获取当前生效的复合提示词（优先使用数据库自定义版）"""
    custom = get_setting('summary_prompt_composite', '')
    return custom if custom else SYSTEM_PROMPT_COMPOSITE


def _get_active_todayqa_prompt() -> str:
    """获取当前生效的当日财经分析提示词（优先使用数据库自定义版）"""
    custom = get_setting('summary_prompt_todayqa', '')
    return custom if custom else SYSTEM_PROMPT_TODAY_QA


# ---------- 获取新闻数据 ----------

def get_daily_news(date_str: str, limit: int = 0) -> list:
    """获取某一天的新闻（按北京时间），limit=0 表示不限制数量"""
    # 将日期字符串转为北京时间的起止
    year, month, day = date_str.split('-')
    
    # 当天 00:00:00 至 次日 00:00:00（北京时间，数据库已存储北京时间）
    start_dt = datetime(int(year), int(month), int(day), 0, 0, 0)
    end_dt = datetime(int(year), int(month), int(day), 23, 59, 59)
    
    if limit > 0:
        return get_news_by_time_range(start_dt, end_dt, limit=limit)
    return get_news_by_time_range(start_dt, end_dt, limit=50000)


def get_search_news(keyword: str, limit: int = 100) -> list:
    """搜索新闻"""
    return search_news_by_text(keyword, limit=limit)


def get_daily_summaries_for_range(start_date_str: str, end_date_str: str) -> list:
    """获取指定日期范围内已有的每日总结（用于合成三日/一周总结）"""
    session = get_session()
    try:
        rows = session.query(AISummary).filter(
            AISummary.range_key.in_(['today', 'yesterday']),
            AISummary.date_label >= start_date_str,
            AISummary.date_label <= end_date_str,
            AISummary.is_composite == False
        ).order_by(AISummary.date_label.asc(), AISummary.generated_at.desc()).all()
        summaries = []
        seen_dates = set()
        for row in rows:
            if row.date_label in seen_dates:
                continue
            summaries.append(row)
            seen_dates.add(row.date_label)
        return summaries
    except Exception as e:
        logger.error(f"获取每日总结列表失败: {e}")
        return []
    finally:
        session.close()


# ---------- 总结持久化 ----------

def save_summary(range_key: str, date_label: str, content: str, news_count: int, is_composite: bool = False) -> bool:
    """保存或更新 AI 总结"""
    session = get_session()
    try:
        # 生成唯一 ID
        unique_id = hashlib.md5(f"{range_key}:{date_label}".encode()).hexdigest()[:16]
        
        existing = session.query(AISummary).filter(
            AISummary.range_key == range_key,
            AISummary.date_label == date_label
        ).first()
        
        if existing:
            existing.content = content
            existing.news_count = news_count
            existing.generated_at = now_bj()
            existing.is_composite = is_composite
        else:
            summary = AISummary(
                id=unique_id,
                range_key=range_key,
                date_label=date_label,
                content=content,
                news_count=news_count,
                generated_at=now_bj(),
                is_composite=is_composite
            )
            session.add(summary)
        
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"保存总结失败: {e}")
        return False
    finally:
        session.close()


def get_summary(range_key: str, date_label: str) -> Optional[dict]:
    """获取已缓存的总结"""
    session = get_session()
    try:
        summary = session.query(AISummary).filter(
            AISummary.range_key == range_key,
            AISummary.date_label == date_label
        ).first()
        if summary:
            return {
                'content': summary.content,
                'news_count': summary.news_count,
                'generated_at': summary.generated_at.strftime('%Y-%m-%d %H:%M:%S') if summary.generated_at else None,
                'is_composite': summary.is_composite,
                'range_key': summary.range_key,
                'date_label': summary.date_label
            }
        return None
    except Exception as e:
        logger.error(f"获取总结失败: {e}")
        return None
    finally:
        session.close()


# ---------- 按日期获取历史总结（新增）----------

def get_summary_by_date(date_str: str) -> Optional[dict]:
    """
    按日期获取历史总结（不区分 today/yesterday，只要 date_label 匹配即可）
    先查 is_composite=False 的每日总结，再查合成总结
    日期格式：YYYY-MM-DD 或 YYYYMMDD
    """
    # 统一日期格式
    date_clean = date_str.replace('-', '')
    if len(date_clean) == 8:
        date_formatted = f"{date_clean[:4]}-{date_clean[4:6]}-{date_clean[6:8]}"
    else:
        date_formatted = date_str
    
    session = get_session()
    try:
        # 查询所有匹配 date_label 的总结（优先每日总结，再合成总结）
        summaries = session.query(AISummary).filter(
            AISummary.date_label == date_formatted,
            AISummary.is_composite == False
        ).order_by(AISummary.generated_at.desc()).all()
        
        if not summaries:
            # 再查合成总结
            summaries = session.query(AISummary).filter(
                AISummary.date_label == date_formatted,
                AISummary.is_composite == True
            ).order_by(AISummary.generated_at.desc()).all()
        
        if not summaries:
            return None
        
        # 取第一条
        s = summaries[0]
        return {
            'content': s.content,
            'news_count': s.news_count,
            'generated_at': s.generated_at.strftime('%Y-%m-%d %H:%M:%S') if s.generated_at else None,
            'is_composite': s.is_composite,
            'range_key': s.range_key,
            'date_label': s.date_label
        }
    except Exception as e:
        logger.error(f"获取历史总结失败: {e}")
        return None
    finally:
        session.close()


def get_summary_list_by_date_range(start_date: str, end_date: str, limit: int = 100) -> list:
    """
    获取指定日期范围内的所有历史总结
    返回按日期排序的总结列表
    """
    session = get_session()
    try:
        # 查询所有非合成的每日总结（today/yesterday）
        rows = session.query(AISummary).filter(
            AISummary.range_key.in_(['today', 'yesterday']),
            AISummary.date_label >= start_date,
            AISummary.date_label <= end_date,
            AISummary.is_composite == False
        ).order_by(AISummary.date_label.desc(), AISummary.generated_at.desc()).all()
        
        seen_dates = set()
        result = []
        for s in rows:
            if s.date_label in seen_dates:
                continue
            seen_dates.add(s.date_label)
            result.append({
                'content': s.content,
                'news_count': s.news_count,
                'generated_at': s.generated_at.strftime('%Y-%m-%d %H:%M:%S') if s.generated_at else None,
                'is_composite': s.is_composite,
                'range_key': s.range_key,
                'date_label': s.date_label
            })
            if len(result) >= limit:
                break
        return result
    except Exception as e:
        logger.error(f"获取历史总结列表失败: {e}")
        return []
    finally:
        session.close()


# ---------- 核心总结生成函数 ----------

def generate_today_summary(force: bool = False) -> dict:
    """生成当日总结"""
    lock_key = 'today'
    lock = _get_lock_for_key(lock_key)
    
    with lock:
        date_label = today_str()
        
        if not force:
            existing = get_summary('today', date_label)
            if existing:
                return {'success': True, 'data': existing, 'cached': True}
        
        news_list = get_daily_news(date_label)
        if not news_list:
            logger.warning(f"⚠️ [今日总结] {date_label} 没有新闻数据")
            return {'success': False, 'message': '没有新闻数据可总结'}
        
        # 准备新闻文本
        news_text = ""
        for i, news in enumerate(news_list, 1):
            title = news.get('title', '')
            content = news.get('content', '')[:300]
            tags = news.get('tags', '')
            source = news.get('source', '')
            news_text += f"{i}. [{tags}] {title}\n   {content}\n"
        
        # 使用数据库中自定义的提示词（如有）
        active_daily_prompt = _get_active_daily_prompt()
        system_prompt = with_summary_context(active_daily_prompt.format(news_count=len(news_list)))
        
        user_prompt = f"以下是今日（{date_label}）的财经新闻，请生成总结：\n\n{news_text}"
        
        content = call_ai(system_prompt, user_prompt)
        if not content:
            return {'success': False, 'message': 'AI 调用失败'}
        
        save_summary('today', date_label, content, len(news_list), is_composite=False)
        
        return {
            'success': True,
            'data': {
                'content': content,
                'news_count': len(news_list),
                'generated_at': now_bj().strftime('%Y-%m-%d %H:%M:%S'),
                'is_composite': False,
                'range_key': 'today',
                'date_label': date_label
            },
            'cached': False
        }


def generate_yesterday_summary(force: bool = False) -> dict:
    """生成昨日总结"""
    lock_key = 'yesterday'
    lock = _get_lock_for_key(lock_key)
    
    with lock:
        date_label = yesterday_str()
        
        if not force:
            existing = get_summary('yesterday', date_label)
            if existing:
                return {'success': True, 'data': existing, 'cached': True}
        
        news_list = get_daily_news(date_label)
        if not news_list:
            logger.warning(f"⚠️ [昨日总结] {date_label} 没有新闻数据")
            return {'success': False, 'message': '没有新闻数据可总结'}
        
        news_text = ""
        for i, news in enumerate(news_list, 1):
            title = news.get('title', '')
            content = news.get('content', '')[:300]
            tags = news.get('tags', '')
            source = news.get('source', '')
            news_text += f"{i}. [{tags}] {title}\n   {content}\n"
        
        # 使用数据库中自定义的提示词（如有）
        active_daily_prompt = _get_active_daily_prompt()
        system_prompt = with_summary_context(active_daily_prompt.format(news_count=len(news_list)))
        user_prompt = f"以下是昨日（{date_label}）的财经新闻，请生成总结：\n\n{news_text}"
        
        content = call_ai(system_prompt, user_prompt)
        if not content:
            return {'success': False, 'message': 'AI 调用失败'}
        
        save_summary('yesterday', date_label, content, len(news_list), is_composite=False)
        
        return {
            'success': True,
            'data': {
                'content': content,
                'news_count': len(news_list),
                'generated_at': now_bj().strftime('%Y-%m-%d %H:%M:%S'),
                'is_composite': False,
                'range_key': 'yesterday',
                'date_label': date_label
            },
            'cached': False
        }


def generate_3d_summary(force: bool = False) -> dict:
    """生成三日总结（基于每日总结再总结）"""
    lock_key = '3d'
    lock = _get_lock_for_key(lock_key)
    
    with lock:
        today = today_str()
        three_days_ago = range_start_str(3)
        
        # 使用固定 range_key + date_label
        range_key = '3d'
        date_label = f"{three_days_ago}_to_{today}"
        
        if not force:
            existing = get_summary(range_key, date_label)
            if existing:
                return {'success': True, 'data': existing, 'cached': True}
        
        # 获取这3天的每日总结
        daily_summaries = get_daily_summaries_for_range(three_days_ago, today)
        
        if not daily_summaries:
            return {'success': False, 'message': '没有可用于合成三天总结的每日总结，请先生成今日/昨日总结'}
        
        # 已有每日总结，基于每日总结再总结
        summaries_text = ""
        total_news = 0
        for s in daily_summaries:
            summaries_text += f"\n--- {s.date_label} 总结 ---\n{s.content}\n"
            total_news += s.news_count or 0
        
        # 使用数据库中自定义的复合提示词（如有）
        active_composite_prompt = _get_active_composite_prompt()
        system_prompt = with_summary_context(active_composite_prompt.format(period_days=3))
        user_prompt = f"以下是过去3天（{three_days_ago} 至 {today}）的每日财经总结，请综合生成一份三日总结报告：\n\n{summaries_text}"
        
        content = call_ai(system_prompt, user_prompt)
        if not content:
            return {'success': False, 'message': 'AI 调用失败'}
        
        save_summary(range_key, date_label, content, total_news, is_composite=True)
        
        return {
            'success': True,
            'data': {
                'content': content,
                'news_count': total_news,
                'generated_at': now_bj().strftime('%Y-%m-%d %H:%M:%S'),
                'is_composite': True,
                'range_key': range_key,
                'date_label': date_label
            },
            'cached': False
        }


def generate_1w_summary(force: bool = False) -> dict:
    """生成一周总结（基于每日总结再总结）"""
    lock_key = '1w'
    lock = _get_lock_for_key(lock_key)
    
    with lock:
        today = today_str()
        week_ago = range_start_str(7)
        
        range_key = '1w'
        date_label = f"{week_ago}_to_{today}"
        
        if not force:
            existing = get_summary(range_key, date_label)
            if existing:
                return {'success': True, 'data': existing, 'cached': True}
        
        # 获取这7天的每日总结
        daily_summaries = get_daily_summaries_for_range(week_ago, today)
        
        if not daily_summaries:
            return {'success': False, 'message': '没有可用于合成一周总结的每日总结，请先生成每日总结'}
        
        summaries_text = ""
        total_news = 0
        for s in daily_summaries:
            summaries_text += f"\n--- {s.date_label} 总结 ---\n{s.content}\n"
            total_news += s.news_count or 0
        
        # 使用数据库中自定义的复合提示词（如有）
        active_composite_prompt = _get_active_composite_prompt()
        system_prompt = with_summary_context(active_composite_prompt.format(period_days=7))
        user_prompt = f"以下是过去一周（{week_ago} 至 {today}）的每日财经总结，请综合生成一份一周总结报告：\n\n{summaries_text}"
        
        content = call_ai(system_prompt, user_prompt)
        if not content:
            return {'success': False, 'message': 'AI 调用失败'}
        
        save_summary(range_key, date_label, content, total_news, is_composite=True)
        
        return {
            'success': True,
            'data': {
                'content': content,
                'news_count': total_news,
                'generated_at': now_bj().strftime('%Y-%m-%d %H:%M:%S'),
                'is_composite': True,
                'range_key': range_key,
                'date_label': date_label
            },
            'cached': False
        }


def get_today_qa_hours_setting() -> int:
    """获取后台配置的当日财经分析时间范围（小时数），默认24小时"""
    try:
        val = get_setting('today_qa_hours', '24')
        hours = int(val)
        if hours < 1:
            hours = 1
        if hours > 720:  # 上限30天
            hours = 720
        return hours
    except (ValueError, TypeError):
        return 24


def generate_today_qa(question: str) -> dict:
    """基于可配置时间范围内的新闻回答用户问题"""
    date_label = today_str()
    range_key = 'todayqa'
    question_hash = hashlib.md5(question.encode()).hexdigest()[:16]
    cache_key = f"todayqa:{date_label}:{question_hash}"
    
    # 使用问题哈希作为锁 key，相同问题串行，不同问题可并发
    lock = _get_lock_for_key(cache_key)
    
    with lock:
        # 读取后台配置的时间范围（小时数）
        hours = get_today_qa_hours_setting()
        now = now_bj()
        start_time = now - timedelta(hours=hours)
        
        logger.info(f"📡 [当日财经分析] 时间范围: 过去 {hours} 小时 (从 {start_time.strftime('%Y-%m-%d %H:%M')} 至 {now.strftime('%Y-%m-%d %H:%M')})")
        
        # 根据配置的时间范围获取新闻
        news_list = get_news_by_time_range(start_time, now, limit=50000)
        if not news_list:
            logger.warning(f"⚠️ [当日财经分析] 过去 {hours} 小时内没有新闻数据")
            return {'success': False, 'message': f'过去 {hours} 小时内暂无新闻数据，无法进行分析'}
        
        # 准备新闻文本（取所有新闻）
        news_text = ""
        for i, news in enumerate(news_list, 1):
            title = news.get('title', '')
            content = news.get('content', '')[:300]
            tags = news.get('tags', '')
            source = news.get('source', '')
            news_text += f"{i}. [{tags}] {title}\n   {content}\n"
        
        active_todayqa_prompt = _get_active_todayqa_prompt()
        system_prompt = with_summary_context(active_todayqa_prompt.format(news_count=len(news_list)))
        
        time_desc = f"过去 {hours} 小时" if hours <= 24 else f"过去 {hours//24} 天"
        user_prompt = f"当前时间：{now.strftime('%Y-%m-%d %H:%M')}\n\n分析的新闻时间范围：{start_time.strftime('%Y-%m-%d %H:%M')} 至 {now.strftime('%Y-%m-%d %H:%M')}（{time_desc}）\n\n共 {len(news_list)} 条财经新闻。\n\n新闻列表：\n{news_text}\n\n用户问题：{question}\n\n请基于以上新闻内容，回答用户的问题。"
        
        content = call_ai(system_prompt, user_prompt)
        if not content:
            return {'success': False, 'message': 'AI 调用失败'}
        
        return {
            'success': True,
            'data': {
                'content': content,
                'news_count': len(news_list),
                'generated_at': now.strftime('%Y-%m-%d %H:%M:%S'),
                'range_key': range_key,
                'question': question,
                'time_range_hours': hours
            },
            'cached': False
        }


def generate_search_summary(keyword: str, force: bool = False) -> dict:
    """生成搜索结果总结"""
    lock_key = 'search:' + hashlib.md5(keyword.encode()).hexdigest()[:16]
    lock = _get_lock_for_key(lock_key)
    
    with lock:
        range_key = 'search'
        date_label = f"search:{keyword}"
        
        if not force:
            existing = get_summary(range_key, date_label)
            if existing:
                return {'success': True, 'data': existing, 'cached': True}
        
        news_list = get_search_news(keyword)
        if not news_list:
            logger.warning(f"⚠️ [搜索总结] 关键词 '{keyword}' 没有搜索结果")
            return {'success': False, 'message': '没有找到相关新闻'}
        
        news_text = ""
        for i, news in enumerate(news_list[:80], 1):
            title = news.get('title', '')
            content = news.get('content', '')[:250]
            tags = news.get('tags', '')
            source = news.get('source', '')
            news_text += f"{i}. [{tags}] {title}\n   {content}\n"
        
        # 搜索总结也使用自定义的每日提示词（如有），因为它是基于原始新闻的
        active_daily_prompt = _get_active_daily_prompt()
        system_prompt_text = active_daily_prompt.format(news_count=len(news_list))
        # 替换为搜索总结专属格式
        system_prompt = with_summary_context(f"""你是一个专业的财经新闻分析师。请根据搜索关键词 "{keyword}" 的结果，生成一份聚焦式总结。

要求：
1. 分析搜索结果的共性主题和趋势
2. 提炼关键信息，去除冗余
3. 用专业的财经分析语言
4. 使用中文输出，Markdown 格式

输出格式：
## 🔎 搜索结果总结: {keyword}

### 📋 核心发现
[分析内容]

### 🏆 要点梳理
1. [要点一]
2. [要点二]
...

---

*基于 {len(news_list)} 条搜索结果生成*""")
        user_prompt = f"以下是关键词 '{keyword}' 的搜索结果，请生成总结：\n\n{news_text}"
        
        content = call_ai(system_prompt, user_prompt)
        if not content:
            return {'success': False, 'message': 'AI 调用失败'}
        
        save_summary(range_key, date_label, content, len(news_list), is_composite=False)
        
        return {
            'success': True,
            'data': {
                'content': content,
                'news_count': len(news_list),
                'generated_at': now_bj().strftime('%Y-%m-%d %H:%M:%S'),
                'is_composite': False,
                'range_key': range_key,
                'date_label': date_label
            },
            'cached': False
        }


def get_summary_schedule() -> dict:
    """获取总结定时配置"""
    default_today = {'time': '20:00', 'enabled': True}
    default_yesterday = {'time': '08:00', 'enabled': True}
    default_3d = {'time': '20:30', 'enabled': True}
    default_1w = {'day': 'fri', 'time': '21:00', 'enabled': True}
    
    today_time = get_setting('summary_schedule_today_time', default_today['time'])
    today_enabled = get_setting('summary_schedule_today_enabled', 'true')
    yesterday_time = get_setting('summary_schedule_yesterday_time', default_yesterday['time'])
    yesterday_enabled = get_setting('summary_schedule_yesterday_enabled', 'true')
    time_3d = get_setting('summary_schedule_3d_time', default_3d['time'])
    enabled_3d = get_setting('summary_schedule_3d_enabled', 'true')
    week_day = get_setting('summary_schedule_1w_day', default_1w['day'])
    time_1w = get_setting('summary_schedule_1w_time', default_1w['time'])
    enabled_1w = get_setting('summary_schedule_1w_enabled', 'true')
    
    return {
        'today': {
            'time': today_time,
            'enabled': today_enabled == 'true',
        },
        'yesterday': {
            'time': yesterday_time,
            'enabled': yesterday_enabled == 'true',
        },
        '3d': {
            'time': time_3d,
            'enabled': enabled_3d == 'true',
        },
        '1w': {
            'day': week_day,
            'time': time_1w,
            'enabled': enabled_1w == 'true',
        }
    }


def set_summary_schedule(schedule: dict) -> dict:
    """保存总结定时配置"""
    if 'today' in schedule:
        today = schedule['today']
        if 'time' in today:
            set_setting('summary_schedule_today_time', today['time'])
        if 'enabled' in today:
            set_setting('summary_schedule_today_enabled', 'true' if today['enabled'] else 'false')
    if 'yesterday' in schedule:
        sy = schedule['yesterday']
        if 'time' in sy:
            set_setting('summary_schedule_yesterday_time', sy['time'])
        if 'enabled' in sy:
            set_setting('summary_schedule_yesterday_enabled', 'true' if sy['enabled'] else 'false')
    if '3d' in schedule:
        s3d = schedule['3d']
        if 'time' in s3d:
            set_setting('summary_schedule_3d_time', s3d['time'])
        if 'enabled' in s3d:
            set_setting('summary_schedule_3d_enabled', 'true' if s3d['enabled'] else 'false')
    if '1w' in schedule:
        s1w = schedule['1w']
        if 'day' in s1w:
            set_setting('summary_schedule_1w_day', s1w['day'])
        if 'time' in s1w:
            set_setting('summary_schedule_1w_time', s1w['time'])
        if 'enabled' in s1w:
            set_setting('summary_schedule_1w_enabled', 'true' if s1w['enabled'] else 'false')
    return {'success': True, 'message': '总结定时配置已保存'}
