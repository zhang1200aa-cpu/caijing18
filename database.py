#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型与操作
"""
from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, Integer, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os
import hashlib
import json
import config

Base = declarative_base()

class FinanceNews(Base):
    __tablename__ = 'finance_news'
    
    id = Column(String, primary_key=True, unique=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(100), default='Financial_Express')
    published_time = Column(DateTime, nullable=False)
    created_time = Column(DateTime, default=datetime.utcnow)
    tags = Column(String(200))  # JSON格式标签
    url = Column(String(500))
    message_id = Column(String(100))
    
    __table_args__ = (
        Index('idx_published_time', 'published_time'),
        Index('idx_created_time', 'created_time'),
        Index('idx_tags', 'tags'),
    )

class Admin(Base):
    """管理员账户"""
    __tablename__ = 'admins'
    
    id = Column(String(64), primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Channel(Base):
    """订阅的 Telegram 频道"""
    __tablename__ = 'channels'
    
    id = Column(String(64), primary_key=True)
    url = Column(String(500), nullable=False)
    name = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AISummary(Base):
    """AI 总结持久化存储"""
    __tablename__ = 'ai_summaries'
    
    id = Column(String(64), primary_key=True)
    range_key = Column(String(10), nullable=False, index=True)  # 1d, 3d, 1w
    date_label = Column(String(20), nullable=False)  # 如 2026-06-16
    content = Column(Text, nullable=False)
    news_count = Column(Integer, default=0)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_range_date', 'range_key', 'date_label'),
    )

class Settings(Base):
    """系统设置（key-value 持久化存储）"""
    __tablename__ = 'settings'
    
    key = Column(String(100), primary_key=True)
    value = Column(String(500), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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

def add_channel(url: str) -> dict:
    """添加 TG 频道订阅"""
    # 从 URL 提取频道名
    name = url.rstrip('/').split('/')[-1]
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
            enabled=True
        )
        session.add(channel)
        session.commit()
        return {'success': True, 'message': f'已添加频道: {name}', 'data': {
            'id': channel_id, 'url': url, 'name': name, 'enabled': True
        }}
    except Exception as e:
        session.rollback()
        return {'success': False, 'message': str(e)}
    finally:
        session.close()

def remove_channel(channel_id: str) -> dict:
    """删除 TG 频道订阅"""
    session = get_session()
    try:
        channel = session.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return {'success': False, 'message': '频道不存在'}
        session.delete(channel)
        session.commit()
        return {'success': True, 'message': f'已删除频道: {channel.name}'}
    except Exception as e:
        session.rollback()
        return {'success': False, 'message': str(e)}
    finally:
        session.close()

def toggle_channel(channel_id: str, enabled: bool) -> dict:
    """启用/禁用 TG 频道"""
    session = get_session()
    try:
        channel = session.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return {'success': False, 'message': '频道不存在'}
        channel.enabled = enabled
        session.commit()
        return {'success': True, 'message': f'已{"启用" if enabled else "禁用"}频道: {channel.name}'}
    except Exception as e:
        session.rollback()
        return {'success': False, 'message': str(e)}
    finally:
        session.close()


# ============ 系统设置（key-value） ============

def get_setting(key: str, default=None):
    """获取系统设置值"""
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
    """设置系统设置值"""
    session = get_session()
    try:
        setting = session.query(Settings).filter(Settings.key == key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            setting = Settings(key=key, value=value)
            session.add(setting)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"❌ [数据库] 保存设置失败: {e}")
        return False
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


# ============ 数据库操作 ============

def get_session():
    """获取数据库会话"""
    _ensure_initialized()
    return _SessionLocal()

def cleanup_old_data():
    """删除7天前的数据"""
    session = get_session()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=config.DATA_RETENTION_DAYS)
        deleted = session.query(FinanceNews).filter(
            FinanceNews.created_time < cutoff_date
        ).delete()
        session.commit()
        print(f"✅ [数据清理] 删除了 {deleted} 条过期数据 ({config.DATA_RETENTION_DAYS}天前)")
        return deleted
    except Exception as e:
        print(f"❌ [数据清理] 错误: {e}")
        session.rollback()
        return 0
    finally:
        session.close()

def save_news(news_id, title, content, tags, url=None, message_id=None):
    """保存新闻"""
    session = get_session()
    try:
        news = FinanceNews(
            id=news_id,
            title=title,
            content=content,
            tags=tags,
            url=url,
            message_id=message_id,
            published_time=datetime.utcnow()
        )
        session.add(news)
        session.commit()
        print(f"✅ [数据库] 保存新闻: {news_id}")
        return True
    except Exception as e:
        print(f"❌ [数据库] 保存失败: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def get_all_news(limit=100, offset=0):
    """获取所有新闻"""
    session = get_session()
    try:
        news = session.query(FinanceNews).order_by(
            FinanceNews.published_time.desc()
        ).limit(limit).offset(offset).all()
        return news
    except Exception as e:
        print(f"❌ [数据库] 查询失败: {e}")
        return []
    finally:
        session.close()

def search_news(keyword, limit=50):
    """搜索新闻"""
    session = get_session()
    try:
        results = session.query(FinanceNews).filter(
            (FinanceNews.title.like(f'%{keyword}%')) |
            (FinanceNews.content.like(f'%{keyword}%')) |
            (FinanceNews.tags.like(f'%{keyword}%'))
        ).order_by(FinanceNews.published_time.desc()).limit(limit).all()
        return results
    except Exception as e:
        print(f"❌ [数据库] 搜索失败: {e}")
        return []
    finally:
        session.close()

def get_news_by_tag(tag, limit=50):
    """按标签获取新闻"""
    session = get_session()
    try:
        results = session.query(FinanceNews).filter(
            FinanceNews.tags.like(f'%{tag}%')
        ).order_by(FinanceNews.published_time.desc()).limit(limit).all()
        return results
    except Exception as e:
        print(f"❌ [数据库] 按标签查询失败: {e}")
        return []
    finally:
        session.close()

def get_stats():
    """获取统计信息"""
    session = get_session()
    try:
        total = session.query(FinanceNews).count()
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today = session.query(FinanceNews).filter(
            FinanceNews.created_time >= today_start
        ).count()
        channels = session.query(Channel).count()
        return {'total': total, 'today': today, 'channels': channels}
    except Exception as e:
        print(f"❌ [数据库] 统计失败: {e}")
        return {'total': 0, 'today': 0, 'channels': 0}
    finally:
        session.close()

def get_database_info():
    """获取数据库信息"""
    session = get_session()
    try:
        total = session.query(FinanceNews).count()
        oldest = session.query(FinanceNews).order_by(
            FinanceNews.created_time.asc()
        ).first()
        newest = session.query(FinanceNews).order_by(
            FinanceNews.created_time.desc()
        ).first()
        
        return {
            'total': total,
            'db_path': config.DB_PATH,
            'data_dir': config.APP_DATA_DIR,
            'oldest_news': oldest.created_time.isoformat() if oldest else None,
            'newest_news': newest.created_time.isoformat() if newest else None,
            'db_size_mb': os.path.getsize(config.DB_PATH) / (1024 * 1024) if os.path.exists(config.DB_PATH) else 0
        }
    except Exception as e:
        print(f"❌ [数据库] 获取信息失败: {e}")
        return {}
    finally:
        session.close()


# ============ AI 总结持久化存储 ============

def save_ai_summary(range_key: str, content: str, news_count: int, date_label: str = None):
    """
    保存 AI 总结到数据库
    
    Args:
        range_key: 范围键值 '1d'/'3d'/'1w'
        content: 总结内容
        news_count: 新闻数量
        date_label: 日期标签 YYYY-MM-DD，None 则用当天
    """
    session = get_session()
    try:
        if date_label is None:
            date_label = datetime.now().strftime('%Y-%m-%d')
        summary_id = hashlib.md5(f"{range_key}_{date_label}".encode()).hexdigest()[:16]
        
        # 查找旧的同 range 同日期记录
        existing = session.query(AISummary).filter(
            AISummary.id == summary_id
        ).first()
        if existing:
            existing.content = content
            existing.news_count = news_count
            existing.generated_at = datetime.utcnow()
        else:
            summary = AISummary(
                id=summary_id,
                range_key=range_key,
                date_label=date_label,
                content=content,
                news_count=news_count,
                generated_at=datetime.utcnow()
            )
            session.add(summary)
        session.commit()
        print(f"✅ [AI 总结] 已保存 {range_key} 总结到数据库 ({date_label})")
        return True
    except Exception as e:
        print(f"❌ [AI 总结] 保存失败: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def get_latest_ai_summary(range_key: str = '1d') -> dict:
    """获取最新指定范围的 AI 总结（优先当天，若无则取最新）"""
    session = get_session()
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 先找当天的
        summary = session.query(AISummary).filter(
            AISummary.range_key == range_key,
            AISummary.date_label == today
        ).order_by(AISummary.generated_at.desc()).first()
        
        # 没有则取最新
        if not summary:
            summary = session.query(AISummary).filter(
                AISummary.range_key == range_key
            ).order_by(AISummary.generated_at.desc()).first()
        
        if not summary:
            return {'success': False, 'message': '暂无总结'}
        
        return {
            'success': True,
            'data': {
                'range_key': summary.range_key,
                'date_label': summary.date_label,
                'content': summary.content,
                'news_count': summary.news_count,
                'generated_at': summary.generated_at.isoformat() if summary.generated_at else None
            }
        }
    except Exception as e:
        print(f"❌ [AI 总结] 获取失败: {e}")
        return {'success': False, 'message': str(e)}
    finally:
        session.close()

def get_ai_summary_status() -> dict:
    """获取 AI 总结状态（各 range 的缓存情况）"""
    session = get_session()
    try:
        from sqlalchemy import func
        # 获取所有 range_key 中最新的一条记录
        subquery = session.query(
            AISummary.range_key,
            func.max(AISummary.generated_at).label('max_generated')
        ).group_by(AISummary.range_key).subquery()
        
        summaries = session.query(AISummary).join(
            subquery,
            (AISummary.range_key == subquery.c.range_key) &
            (AISummary.generated_at == subquery.c.max_generated)
        ).all()
        
        result = {}
        for s in summaries:
            result[s.range_key] = {
                'cached': True,
                'news_count': s.news_count,
                'generated_at': s.generated_at.isoformat() if s.generated_at else None,
                'date_label': s.date_label
            }
        
        # 确保所有 range 都有记录
        for rk in ['1d', '3d', '1w']:
            if rk not in result:
                result[rk] = {'cached': False, 'news_count': 0, 'generated_at': None, 'date_label': None}
        
        return result
    except Exception as e:
        print(f"❌ [AI 总结] 获取状态失败: {e}")
        return {}
    finally:
        session.close()
