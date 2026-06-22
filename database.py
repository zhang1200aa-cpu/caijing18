#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型与操作
"""
from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, Integer, Index, Boolean, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta, timezone
import os
import hashlib
import json
import config
import logging

logger_db = logging.getLogger('database')

# 北京时间 (UTC+8)
BJT = timezone(timedelta(hours=8))

def now_bj():
    """返回当前北京时间（naive datetime）"""
    return datetime.now(BJT).replace(tzinfo=None)

Base = declarative_base()

class FinanceNews(Base):
    __tablename__ = 'finance_news'
    
    id = Column(String, primary_key=True, unique=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(100), default='Financial_Express')
    published_time = Column(DateTime, nullable=False)
    created_time = Column(DateTime, default=now_bj)
    tags = Column(String(200))  # JSON格式标签
    url = Column(String(500))
    message_id = Column(String(100))
    
    __table_args__ = (
        Index('idx_published_time', 'published_time'),
        Index('idx_created_time', 'created_time'),
        Index('idx_tags', 'tags'),
    )

class SummaryTemplate(Base):
    """AI 总结提示词模板"""
    __tablename__ = 'summary_templates'
    
    id = Column(String(64), primary_key=True)
    name = Column(String(100), nullable=False)  # 模板名称
    category = Column(String(50), default='general')  # 分类：finance/tech/news/custom
    system_prompt = Column(Text, nullable=False)  # 系统提示词
    user_prompt = Column(Text, default='')  # 用户提示词（可选）
    is_default = Column(Boolean, default=False)  # 是否为当前默认
    created_at = Column(DateTime, default=now_bj)
    updated_at = Column(DateTime, default=now_bj, onupdate=now_bj)


class Admin(Base):
    """管理员账户"""
    __tablename__ = 'admins'
    
    id = Column(String(64), primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=now_bj)

class Channel(Base):
    """订阅的 Telegram 频道"""
    __tablename__ = 'channels'
    
    id = Column(String(64), primary_key=True)
    url = Column(String(500), nullable=False)
    name = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    scrape_depth = Column(Integer, default=1000)  # 历史抓取数量：绑定时初始抓取的条数
    history_scrape_status = Column(String(20), default='none')  # none/pending/running/done/failed
    history_scrape_count = Column(Integer, default=0)  # 已回填条数
    last_history_scrape_at = Column(DateTime, nullable=True)  # 上次回填时间
    created_at = Column(DateTime, default=now_bj)

class AISummary(Base):
    """AI 总结持久化存储"""
    __tablename__ = 'ai_summaries'
    
    id = Column(String(64), primary_key=True)
    range_key = Column(String(20), nullable=False, index=True)  # today, yesterday, 3d, 1w, search
    date_label = Column(String(20), nullable=False)  # 如 2026-06-17 或 search:关键词
    content = Column(Text, nullable=False)
    news_count = Column(Integer, default=0)
    generated_at = Column(DateTime, default=now_bj)
    # 新增: 用于标记是由每日总结合成的（3d/1w类型）
    is_composite = Column(Boolean, default=False)  # 是否为合成的（基于每日总结再总结）
    
    __table_args__ = (
        Index('idx_range_date', 'range_key', 'date_label'),
    )

class Settings(Base):
    """系统设置（key-value 持久化存储）"""
    __tablename__ = 'settings'
    
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=now_bj, onupdate=now_bj)


# ============ 数据库初始化（惰性） ============
_engine = None
_SessionLocal = None

def _ensure_initialized():
    """确保数据库已初始化（惰性加载）"""
    global _engine, _SessionLocal
    if _engine is not None:
        return
    
    # 确保数据目录存在
    db_dir = config.APP_DATA_DIR
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    # 创建引擎
    _engine = create_engine(
        config.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    
    # 创建所有表
    Base.metadata.create_all(_engine)
    _SessionLocal = sessionmaker(bind=_engine)
    
    print(f"✅ [数据库] 初始化成功: {config.DB_PATH}")

def init_database():
    """显式初始化数据库（可幂等调用）"""
    _ensure_initialized()
    
    # 自动创建默认管理员
    _create_default_admin()
    
    return _engine

def _create_default_admin():
    """自动创建默认管理员账户 admin/admin"""
    session = get_session()
    try:
        existing = session.query(Admin).filter(Admin.username == 'admin').first()
        if existing:
            return
        # 使用 bcrypt 或 SHA256 作为备用
        try:
            import bcrypt
            password_hash = bcrypt.hashpw(b'admin', bcrypt.gensalt()).decode()
        except ImportError:
            # 备用：SHA256
            password_hash = 'sha256$' + hashlib.sha256(b'admin').hexdigest()
        
        admin = Admin(
            id='admin_default',
            username='admin',
            password_hash=password_hash
        )
        session.add(admin)
        session.commit()
        print("✅ [数据库] 已创建默认管理员 admin/admin")
    except Exception as e:
        session.rollback()
        print(f"⚠️ [数据库] 创建管理员失败: {e}")
    finally:
        session.close()

def verify_admin_password(username: str, password: str) -> bool:
    """验证管理员密码"""
    session = get_session()
    try:
        admin = session.query(Admin).filter(Admin.username == username).first()
        if not admin:
            return False
        if admin.password_hash.startswith('sha256$'):
            expected = 'sha256$' + hashlib.sha256(password.encode()).hexdigest()
            return admin.password_hash == expected
        else:
            # bcrypt
            import bcrypt
            return bcrypt.checkpw(password.encode(), admin.password_hash.encode())
    except Exception:
        return False
    finally:
        session.close()

def change_admin_password(username: str, old_password: str, new_password: str) -> dict:
    """修改管理员密码"""
    if not verify_admin_password(username, old_password):
        return {'success': False, 'message': '原密码错误'}
    if len(new_password) < 4:
        return {'success': False, 'message': '新密码至少4位'}
    
    session = get_session()
    try:
        admin = session.query(Admin).filter(Admin.username == username).first()
        if not admin:
            return {'success': False, 'message': '用户不存在'}
        import bcrypt
        admin.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        session.commit()
        return {'success': True, 'message': '密码修改成功'}
    except Exception as e:
        session.rollback()
        return {'success': False, 'message': str(e)}
    finally:
        session.close()

def get_channels() -> list:
    """获取所有订阅的 TG 频道"""
    session = get_session()
    try:
        channels = session.query(Channel).all()
        return [{
            'id': c.id,
            'url': c.url,
            'name': c.name,
            'enabled': c.enabled,
            'scrape_depth': getattr(c, 'scrape_depth', 1000),
            'history_scrape_status': getattr(c, 'history_scrape_status', 'none'),
            'history_scrape_count': getattr(c, 'history_scrape_count', 0),
            'last_history_scrape_at': c.last_history_scrape_at.isoformat() if getattr(c, 'last_history_scrape_at', None) else None,
            'created_at': c.created_at.isoformat() if c.created_at else None
        } for c in channels]
    except Exception:
        return []
    finally:
        session.close()

def get_enabled_channels() -> list:
    """获取启用的 TG 频道"""
    session = get_session()
    try:
        channels = session.query(Channel).filter(Channel.enabled == True).all()
        return channels
    except Exception:
        return []
    finally:
        session.close()

def add_channel(url: str, scrape_depth: int = 1000) -> dict:
    """添加 TG 频道订阅"""
    url = url.strip() if url else ''
    if not url:
        return {'success': False, 'message': 'URL 不能为空'}
    # 从 URL 提取频道名
    name = url.rstrip('/').split('/')[-1]
    if not name:
        return {'success': False, 'message': '无法从 URL 提取频道名称'}
    channel_id = hashlib.md5(url.encode()).hexdigest()[:16]
    
    session = get_session()
    try:
        existing = session.query(Channel).filter(Channel.url == url).first()
        if existing:
            return {'success': False, 'message': '该频道已存在'}
        
        channel = Channel(
            id=channel_id,
            url=url,
            name=name,
            enabled=True,
            scrape_depth=scrape_depth
        )
        session.add(channel)
        session.commit()
        return {'success': True, 'message': f'已添加频道: {name}', 'data': {
            'id': channel_id, 'url': url, 'name': name, 'enabled': True, 'scrape_depth': scrape_depth
        }}
    except Exception as e:
        session.rollback()
        return {'success': False, 'message': str(e)}
    finally:
        session.close()

def remove_channel(channel_id: str) -> dict:
    """删除 TG 频道订阅及该频道下的所有新闻数据"""
    session = get_session()
    try:
        channel = session.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return {'success': False, 'message': '频道不存在'}
        
        channel_name = channel.name
        channel_url = channel.url
        
        # 删除该频道相关的所有新闻
        # 从 URL 提取频道名（避免从 tg_scraper 导入导致循环引用）
        url_channel_name = channel_url.rstrip('/').split('/')[-1]
        deleted_news = session.query(FinanceNews).filter(
            or_(
                FinanceNews.source == channel_name,
                FinanceNews.source == url_channel_name,
            )
        ).delete(synchronize_session='fetch')
        
        # 删除频道记录
        session.delete(channel)
        session.commit()
        
        logger_db.info(f"🗑️ 已删除频道 '{channel_name}' 及 {deleted_news} 条关联新闻")
        return {
            'success': True,
            'message': f'频道已删除，同时清理了 {deleted_news} 条关联新闻',
            'deleted_news': deleted_news
        }
    except Exception as e:
        session.rollback()
        return {'success': False, 'message': str(e)}
    finally:
        session.close()

def update_channel_scrape_depth(channel_id: str, scrape_depth: int) -> dict:
    """更新频道的历史抓取数量设置"""
    session = get_session()
    try:
        channel = session.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return {'success': False, 'message': '频道不存在'}
        channel.scrape_depth = scrape_depth
        session.commit()
        return {'success': True, 'message': f'历史抓取数量已更新为 {scrape_depth}'}
    except Exception as e:
        session.rollback()
        return {'success': False, 'message': str(e)}
    finally:
        session.close()

def toggle_channel(channel_id: str, enabled: bool) -> dict:
    """启用/禁用频道"""
    session = get_session()
    try:
        channel = session.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return {'success': False, 'message': '频道不存在'}
        channel.enabled = enabled
        session.commit()
        return {'success': True, 'message': '频道状态已更新'}
    except Exception as e:
        session.rollback()
        return {'success': False, 'message': str(e)}
    finally:
        session.close()

def get_all_settings() -> dict:
    """获取所有系统设置"""
    session = get_session()
    try:
        settings = session.query(Settings).all()
        return {s.key: s.value for s in settings}
    except Exception:
        return {}
    finally:
        session.close()

def get_setting(key: str, default=None) -> str:
    """获取单个设置值"""
    session = get_session()
    try:
        setting = session.query(Settings).filter(Settings.key == key).first()
        if setting:
            return setting.value
        return default
    except Exception:
        return default
    finally:
        session.close()

def set_setting(key: str, value: str) -> bool:
    """设置单个配置项"""
    session = get_session()
    try:
        setting = session.query(Settings).filter(Settings.key == key).first()
        if setting:
            setting.value = str(value)
            setting.updated_at = now_bj()
        else:
            setting = Settings(key=key, value=str(value))
            session.add(setting)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        logger_db.error(f"保存设置失败 {key}: {e}")
        return False
    finally:
        session.close()

def get_session():
    """获取数据库会话（惰性初始化）"""
    _ensure_initialized()
    return _SessionLocal()

def cleanup_old_data(days: int = 30) -> int:
    """清理旧数据（保留最近 N 天的新闻）"""
    session = get_session()
    try:
        cutoff = now_bj() - timedelta(days=days)
        deleted = session.query(FinanceNews).filter(FinanceNews.created_time < cutoff).delete()
        session.commit()
        if deleted:
            logger_db.info(f"🧹 清理了 {deleted} 条 {days} 天前的旧新闻")
        return deleted
    except Exception as e:
        session.rollback()
        logger_db.error(f"清理旧数据失败: {e}")
        return 0
    finally:
        session.close()

def save_news(news_id, title, content, tags, url, message_id=None, source=None) -> bool:
    """保存一条新闻到数据库"""
    session = get_session()
    try:
        existing = session.query(FinanceNews).filter(FinanceNews.id == news_id).first()
        if existing:
            logger_db.debug(f"新闻已存在，跳过: {news_id}")
            return False
        
        # 使用传入的 source，如果为 None 则使用 ORM 模型的默认值 'Financial_Express'
        now = now_bj()
        news = FinanceNews(
            id=news_id,
            title=title,
            content=content,
            source=source,
            tags=tags,
            url=url,
            message_id=message_id,
            published_time=now,
            created_time=now
        )
        session.add(news)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        logger_db.error(f"保存新闻失败: {e}")
        return False
    finally:
        session.close()


def get_stats() -> dict:
    """获取统计数据"""
    session = get_session()
    try:
        total = session.query(FinanceNews).count()
        # 获取今日数量（北京时间 0点之后）
        today_start = now_bj().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = session.query(FinanceNews).filter(
            FinanceNews.created_time >= today_start
        ).count()
        
        # 获取标签统计
        all_news = session.query(FinanceNews.tags).all()
        tag_set = set()
        for row in all_news:
            if row.tags:
                for tag in row.tags.split(','):
                    tag = tag.strip()
                    if tag:
                        tag_set.add(tag)
        
        # 获取来源统计
        source_counts = {}
        for row in session.query(FinanceNews.source).all():
            if row.source:
                source_counts[row.source] = source_counts.get(row.source, 0) + 1
        
        # 获取频道总数
        channel_count = session.query(Channel).count()
        
        return {
            'total': total,
            'today': today_count,
            'tag_count': len(tag_set),
            'sources': source_counts,
            'channels': channel_count,
            'retention_days': config.DATA_RETENTION_DAYS,
        }
    except Exception as e:
        logger_db.error(f"获取统计失败: {e}")
        return {'total': 0, 'today': 0, 'tag_count': 0, 'sources': {}, 'channels': 0}
    finally:
        session.close()


def get_news_by_time_range(start_time, end_time, limit: int = 500) -> list:
    """获取指定时间范围内的新闻"""
    session = get_session()
    try:
        news_list = session.query(FinanceNews).filter(
            FinanceNews.published_time >= start_time,
            FinanceNews.published_time <= end_time
        ).order_by(FinanceNews.published_time.desc()).limit(limit).all()
        result = []
        for n in news_list:
            result.append({
                'id': n.id,
                'title': n.title,
                'content': n.content,
                'source': n.source,
                'tags': n.tags,
                'url': n.url,
                'published_time': (n.published_time.isoformat() + '+08:00') if n.published_time else None,
                'created_time': (n.created_time.isoformat() + '+08:00') if n.created_time else None,
            })
        return result
    except Exception as e:
        logger_db.error(f"获取时间范围新闻失败: {e}")
        return []
    finally:
        session.close()

def search_news_by_text(keyword: str, limit: int = 100) -> list:
    """全文搜索新闻"""
    session = get_session()
    try:
        like_pattern = f'%{keyword}%'
        news_list = session.query(FinanceNews).filter(
            (FinanceNews.title.like(like_pattern)) |
            (FinanceNews.content.like(like_pattern))
        ).order_by(FinanceNews.published_time.desc()).limit(limit).all()
        result = []
        for n in news_list:
            result.append({
                'id': n.id,
                'title': n.title,
                'content': n.content[:200],
                'source': n.source,
                'tags': n.tags,
                'url': n.url,
                'published_time': (n.published_time.isoformat() + '+08:00') if n.published_time else None,
            })
        return result
    except Exception as e:
        logger_db.error(f"搜索新闻失败: {e}")
        return []
    finally:
        session.close()