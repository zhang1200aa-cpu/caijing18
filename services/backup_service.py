"""
备份与恢复服务
提供数据库备份、JSON 导出、数据库恢复、JSON 导入等功能
"""
import os
import json
import shutil
import hashlib
import logging
from datetime import datetime
from typing import Optional
import config

logger = logging.getLogger(__name__)

# 备份目录
BACKUP_DIR = os.path.join(config.APP_DATA_DIR, 'backups')

def _ensure_backup_dir():
    """确保备份目录存在"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR, exist_ok=True)

def list_backups() -> list:
    """列出所有备份文件"""
    _ensure_backup_dir()
    backups = []
    try:
        for f in os.listdir(BACKUP_DIR):
            if f.endswith('.db') or f.endswith('.json'):
                filepath = os.path.join(BACKUP_DIR, f)
                stat = os.stat(filepath)
                size_mb = stat.st_size / (1024 * 1024)
                backups.append({
                    'filename': f,
                    'size_bytes': stat.st_size,
                    'size_mb': round(size_mb, 2),
                    'created_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'type': '数据库备份' if f.endswith('.db') else 'JSON 导出'
                })
        # 按创建时间倒序排列
        backups.sort(key=lambda x: x['created_at'], reverse=True)
    except Exception as e:
        logger.error(f"列出备份文件失败: {e}")
    return backups

def create_db_backup() -> dict:
    """创建数据库文件备份（复制 .db 文件）"""
    _ensure_backup_dir()
    try:
        if not os.path.exists(config.DB_PATH):
            return {'success': False, 'message': '数据库文件不存在'}
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'finance_data_{timestamp}.db'
        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        
        shutil.copy2(config.DB_PATH, backup_path)
        
        size_mb = os.path.getsize(backup_path) / (1024 * 1024)
        logger.info(f"✅ 数据库备份完成: {backup_filename} ({size_mb:.2f} MB)")
        
        return {
            'success': True,
            'message': f'备份成功: {backup_filename} ({size_mb:.2f} MB)',
            'data': {
                'filename': backup_filename,
                'size_mb': round(size_mb, 2),
                'path': backup_path
            }
        }
    except Exception as e:
        logger.error(f"创建数据库备份失败: {e}")
        return {'success': False, 'message': f'备份失败: {str(e)}'}

def restore_from_db_backup(backup_filename: str) -> dict:
    """从数据库备份文件恢复"""
    _ensure_backup_dir()
    try:
        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        if not os.path.exists(backup_path):
            return {'success': False, 'message': '备份文件不存在'}
        
        if not backup_filename.endswith('.db'):
            return {'success': False, 'message': '无效的备份文件格式'}
        
        # 备份当前数据库（以防万一）
        if os.path.exists(config.DB_PATH):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pre_restore_backup = os.path.join(
                BACKUP_DIR, 
                f'pre_restore_{timestamp}.db'
            )
            shutil.copy2(config.DB_PATH, pre_restore_backup)
            logger.info(f"💾 恢复前已备份当前数据库: pre_restore_{timestamp}.db")
        
        # 复制备份文件到数据库路径
        shutil.copy2(backup_path, config.DB_PATH)
        
        logger.info(f"✅ 数据库已从 {backup_filename} 恢复")
        
        return {
            'success': True,
            'message': f'数据库已从 {backup_filename} 恢复成功'
        }
    except Exception as e:
        logger.error(f"恢复数据库失败: {e}")
        return {'success': False, 'message': f'恢复失败: {str(e)}'}

def export_to_json() -> dict:
    """将所有表数据导出为 JSON 文件"""
    from database import get_session, FinanceNews, AISummary, Channel, Settings, Admin, SummaryTemplate
    
    _ensure_backup_dir()
    session = get_session()
    try:
        # 导出新闻数据
        news_list = []
        for n in session.query(FinanceNews).all():
            news_list.append({
                'id': n.id,
                'title': n.title,
                'content': n.content,
                'source': n.source,
                'published_time': n.published_time.isoformat() if n.published_time else None,
                'created_time': n.created_time.isoformat() if n.created_time else None,
                'tags': n.tags,
                'url': n.url,
                'message_id': n.message_id
            })
        
        # 导出 AI 总结
        summaries = []
        for s in session.query(AISummary).all():
            summaries.append({
                'id': s.id,
                'range_key': s.range_key,
                'date_label': s.date_label,
                'content': s.content,
                'news_count': s.news_count,
                'generated_at': s.generated_at.isoformat() if s.generated_at else None,
                'is_composite': s.is_composite
            })
        
        # 导出频道
        channels = []
        for c in session.query(Channel).all():
            channels.append({
                'id': c.id,
                'url': c.url,
                'name': c.name,
                'enabled': c.enabled,
                'scrape_depth': c.scrape_depth,
                'created_at': c.created_at.isoformat() if c.created_at else None
            })
        
        # 导出设置
        settings = {}
        for s in session.query(Settings).all():
            settings[s.key] = s.value
        
        # 导出管理员（不包含密码哈希）
        admins = []
        for a in session.query(Admin).all():
            admins.append({
                'id': a.id,
                'username': a.username,
                'created_at': a.created_at.isoformat() if a.created_at else None
            })
        
        # 导出提示词模板
        templates = []
        for t in session.query(SummaryTemplate).all():
            templates.append({
                'id': t.id,
                'name': t.name,
                'category': t.category,
                'system_prompt': t.system_prompt,
                'user_prompt': t.user_prompt,
                'is_default': t.is_default,
                'created_at': t.created_at.isoformat() if t.created_at else None,
                'updated_at': t.updated_at.isoformat() if t.updated_at else None
            })
        
        export_data = {
            'export_time': datetime.now().isoformat(),
            'version': '1.0',
            'stats': {
                'news_count': len(news_list),
                'summaries_count': len(summaries),
                'channels_count': len(channels),
                'settings_count': len(settings),
                'admins_count': len(admins),
                'templates_count': len(templates)
            },
            'data': {
                'finance_news': news_list,
                'ai_summaries': summaries,
                'channels': channels,
                'settings': settings,
                'admins': admins,
                'summary_templates': templates
            }
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_filename = f'finance_data_export_{timestamp}.json'
        json_path = os.path.join(BACKUP_DIR, json_filename)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        size_mb = os.path.getsize(json_path) / (1024 * 1024)
        logger.info(f"✅ JSON 导出完成: {json_filename} ({size_mb:.2f} MB)")
        
        return {
            'success': True,
            'message': f'导出成功: {json_filename} ({size_mb:.2f} MB)',
            'data': {
                'filename': json_filename,
                'size_mb': round(size_mb, 2),
                'stats': export_data['stats']
            }
        }
    except Exception as e:
        logger.error(f"JSON 导出失败: {e}")
        return {'success': False, 'message': f'导出失败: {str(e)}'}
    finally:
        session.close()

def import_from_json(json_filename: str, options: dict = None) -> dict:
    """从 JSON 文件导入数据
    options: 控制导入哪些表，如 {'finance_news': True, 'settings': True}
    """
    from database import get_session, FinanceNews, AISummary, Channel, Settings, Admin, SummaryTemplate, now_bj
    
    _ensure_backup_dir()
    json_path = os.path.join(BACKUP_DIR, json_filename)
    if not os.path.exists(json_path):
        return {'success': False, 'message': '导入文件不存在'}
    
    if options is None:
        options = {'finance_news': True, 'ai_summaries': True, 'channels': True, 
                   'settings': True, 'summary_templates': True}
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            export_data = json.load(f)
    except Exception as e:
        return {'success': False, 'message': f'读取文件失败: {str(e)}'}
    
    data = export_data.get('data', {})
    session = get_session()
    results = {}
    
    try:
        # 导入新闻
        if options.get('finance_news') and data.get('finance_news'):
            count = 0
            for item in data['finance_news']:
                existing = session.query(FinanceNews).filter(FinanceNews.id == item['id']).first()
                if not existing:
                    news = FinanceNews(
                        id=item['id'],
                        title=item['title'],
                        content=item['content'],
                        source=item.get('source'),
                        tags=item.get('tags'),
                        url=item.get('url'),
                        message_id=item.get('message_id'),
                        published_time=datetime.fromisoformat(item['published_time']) if item.get('published_time') else now_bj(),
                        created_time=datetime.fromisoformat(item['created_time']) if item.get('created_time') else now_bj()
                    )
                    session.add(news)
                    count += 1
            session.commit()
            results['finance_news'] = f'导入了 {count} 条新闻（跳过已存在的）'
        
        # 导入 AI 总结
        if options.get('ai_summaries') and data.get('ai_summaries'):
            count = 0
            for item in data['ai_summaries']:
                existing = session.query(AISummary).filter(AISummary.id == item['id']).first()
                if not existing:
                    summary = AISummary(
                        id=item['id'],
                        range_key=item['range_key'],
                        date_label=item['date_label'],
                        content=item['content'],
                        news_count=item.get('news_count', 0),
                        is_composite=item.get('is_composite', False),
                        generated_at=datetime.fromisoformat(item['generated_at']) if item.get('generated_at') else now_bj()
                    )
                    session.add(summary)
                    count += 1
            session.commit()
            results['ai_summaries'] = f'导入了 {count} 条 AI 总结'
        
        # 导入频道
        if options.get('channels') and data.get('channels'):
            count = 0
            for item in data['channels']:
                existing = session.query(Channel).filter(Channel.id == item['id']).first()
                if not existing:
                    channel = Channel(
                        id=item['id'],
                        url=item['url'],
                        name=item['name'],
                        enabled=item.get('enabled', True),
                        scrape_depth=item.get('scrape_depth', 1000),
                        created_at=datetime.fromisoformat(item['created_at']) if item.get('created_at') else now_bj()
                    )
                    session.add(channel)
                    count += 1
            session.commit()
            results['channels'] = f'导入了 {count} 个频道'
        
        # 导入设置
        if options.get('settings') and data.get('settings'):
            count = 0
            for key, value in data['settings'].items():
                existing = session.query(Settings).filter(Settings.key == key).first()
                if existing:
                    existing.value = str(value)
                else:
                    setting = Settings(key=key, value=str(value))
                    session.add(setting)
                count += 1
            session.commit()
            results['settings'] = f'导入了 {count} 项设置'
        
        # 导入提示词模板
        if options.get('summary_templates') and data.get('summary_templates'):
            count = 0
            for item in data['summary_templates']:
                existing = session.query(SummaryTemplate).filter(SummaryTemplate.id == item['id']).first()
                if not existing:
                    template = SummaryTemplate(
                        id=item['id'],
                        name=item['name'],
                        category=item.get('category', 'general'),
                        system_prompt=item['system_prompt'],
                        user_prompt=item.get('user_prompt', ''),
                        is_default=item.get('is_default', False),
                        created_at=datetime.fromisoformat(item['created_at']) if item.get('created_at') else now_bj(),
                        updated_at=datetime.fromisoformat(item['updated_at']) if item.get('updated_at') else now_bj()
                    )
                    session.add(template)
                    count += 1
            session.commit()
            results['summary_templates'] = f'导入了 {count} 个提示词模板'
        
        logger.info(f"✅ JSON 导入完成: {json_filename}")
        return {
            'success': True,
            'message': '导入完成',
            'data': results
        }
    except Exception as e:
        session.rollback()
        logger.error(f"JSON 导入失败: {e}")
        return {'success': False, 'message': f'导入失败: {str(e)}'}
    finally:
        session.close()

def delete_backup(filename: str) -> dict:
    """删除指定的备份文件"""
    _ensure_backup_dir()
    try:
        filepath = os.path.join(BACKUP_DIR, filename)
        if not os.path.exists(filepath):
            return {'success': False, 'message': '文件不存在'}
        os.remove(filepath)
        logger.info(f"🗑️ 已删除备份文件: {filename}")
        return {'success': True, 'message': f'已删除: {filename}'}
    except Exception as e:
        logger.error(f"删除备份文件失败: {e}")
        return {'success': False, 'message': f'删除失败: {str(e)}'}

def delete_old_backups(keep_count: int = 10) -> int:
    """清理旧备份，只保留最新的 keep_count 个文件"""
    _ensure_backup_dir()
    try:
        all_files = []
        for f in os.listdir(BACKUP_DIR):
            if f.endswith('.db') or f.endswith('.json'):
                filepath = os.path.join(BACKUP_DIR, f)
                mtime = os.path.getmtime(filepath)
                all_files.append((f, mtime))
        
        # 按修改时间倒序排列（最新的在前面）
        all_files.sort(key=lambda x: x[1], reverse=True)
        
        # 删除超出 keep_count 的旧文件
        deleted = 0
        for f, _ in all_files[keep_count:]:
            try:
                os.remove(os.path.join(BACKUP_DIR, f))
                deleted += 1
                logger.info(f"🗑️ 已清理旧备份: {f}")
            except Exception as e:
                logger.error(f"❌ 清理 {f} 失败: {e}")
        
        if deleted > 0:
            logger.info(f"✅ 清理完成，共删除 {deleted} 个旧备份文件")
        return deleted
    except Exception as e:
        logger.error(f"❌ 清理旧备份失败: {e}")
        return 0


def get_backup_download_path(filename: str) -> Optional[str]:
    """获取备份文件的完整路径"""
    _ensure_backup_dir()
    filepath = os.path.join(BACKUP_DIR, filename)
    if os.path.exists(filepath):
        return filepath
    return None
