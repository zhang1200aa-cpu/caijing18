"""
管理员相关 API 路由
"""
import hashlib
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, session
from database import (
    get_channels, add_channel, remove_channel, toggle_channel,
    get_all_settings, set_setting, verify_admin_password,
    change_admin_password, cleanup_old_data, get_enabled_channels,
    now_bj
)
import config
from config import TG_CHANNEL_URLS
from tg_scraper import scrape_all_channels, scrape_channel_history
from database import save_news
from services import get_scrape_interval_minutes, reschedule_scrape_job, get_summary_schedule, update_summary_schedule
from services.summary_service import get_summary_prompts, set_summary_prompts, reset_summary_prompt

logger = logging.getLogger(__name__)

admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')


def login_required(f):
    """简单的登录装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('admin') is None:
            return jsonify({'success': False, 'message': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated


@admin_api_bp.route('/login', methods=['POST'])
def api_admin_login():
    """管理员登录"""
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')
    if verify_admin_password(username, password):
        session['admin'] = username
        return jsonify({'success': True, 'message': '登录成功'})
    return jsonify({'success': False, 'message': '用户名或密码错误'})


@admin_api_bp.route('/logout')
def api_admin_logout():
    """管理员登出"""
    session.pop('admin', None)
    return jsonify({'success': True, 'message': '已退出'})


@admin_api_bp.route('/check')
def api_admin_check():
    """检查是否已登录"""
    is_admin = session.get('admin') is not None
    return jsonify({'is_admin': is_admin})


@admin_api_bp.route('/channels')
def api_get_channels():
    """获取所有频道列表"""
    channels = get_channels()
    return jsonify({'success': True, 'data': channels})


def _update_history_scrape_status(channel_name: str, status: str, count: int = None):
    """Update channel history scrape status in DB"""
    from database import get_session, Channel
    session = get_session()
    try:
        channel = session.query(Channel).filter(Channel.name == channel_name).first()
        if channel:
            channel.history_scrape_status = status
            if count is not None:
                channel.history_scrape_count = count
            if status in ('done', 'failed'):
                channel.last_history_scrape_at = now_bj()
            session.commit()
    except Exception as e:
        logger.error(f"更新历史回填状态失败: {e}")
    finally:
        session.close()


@admin_api_bp.route('/channels/add', methods=['POST'])
def api_add_channel():
    """添加频道"""
    data = request.json
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'success': False, 'message': '请输入频道 URL'})
    scrape_depth = data.get('scrape_depth', 1000)
    try:
        scrape_depth = int(scrape_depth)
        if scrape_depth < 0:
            scrape_depth = 0
    except (ValueError, TypeError):
        scrape_depth = 1000
    result = add_channel(url, scrape_depth=scrape_depth)
    
    # 如果添加成功且 scrape_depth > 0, 异步触发历史消息回填
    if result.get('success') and scrape_depth > 0:
        try:
            channel_name = url.rstrip('/').split('/')[-1]
            logger.info(f"📡 [API] 频道绑定成功，后台异步回填 {scrape_depth} 条历史消息...")
            
            # Mark as pending in DB
            _update_history_scrape_status(channel_name, 'pending')
            
            # 异步执行历史回填，避免 HTTP 请求超时
            import threading
            def _progress_callback(current, total):
                """进度回调：实时更新数据库中的回填条数"""
                _update_history_scrape_status(channel_name, 'running', current)

            def _do_history_scrape():
                """在后台线程中执行历史回填"""
                try:
                    _update_history_scrape_status(channel_name, 'running')
                    logger.info(f"📡 [历史回填] [{channel_name}] 开始后台回填 {scrape_depth} 条...")
                    count = scrape_channel_history(url, save_callback=save_news, max_count=scrape_depth, progress_callback=_progress_callback)
                    logger.info(f"✅ [历史回填] [{channel_name}] 后台回填完成，新增 {count} 条")
                    _update_history_scrape_status(channel_name, 'done', count)
                except Exception as e:
                    logger.error(f"❌ [历史回填] [{channel_name}] 后台回填失败: {e}", exc_info=True)
                    _update_history_scrape_status(channel_name, 'failed')
            
            thread = threading.Thread(target=_do_history_scrape, daemon=True)
            thread.start()
            
            result['history_async'] = True
            result['message'] += '，历史消息正在后台回填中（约 ' + str(scrape_depth) + ' 条）'
            result['history_status'] = 'running'
        except Exception as e:
            logger.error(f"❌ [API] 触发历史回填失败: {e}")
            result['history_async_error'] = str(e)
    
    return jsonify(result)


@admin_api_bp.route('/channels/remove', methods=['POST'])
def api_remove_channel():
    """删除频道"""
    data = request.json
    channel_id = data.get('id', '')
    result = remove_channel(channel_id)
    return jsonify(result)


@admin_api_bp.route('/channels/toggle', methods=['POST'])
def api_toggle_channel():
    """启用/禁用频道"""
    data = request.json
    channel_id = data.get('id', '')
    enabled = data.get('enabled', True)
    result = toggle_channel(channel_id, enabled)
    return jsonify(result)


@admin_api_bp.route('/settings')
@login_required
def api_get_settings():
    """获取所有系统设置"""
    settings = get_all_settings()
    return jsonify({'success': True, 'data': settings})


@admin_api_bp.route('/settings/update', methods=['POST'])
@login_required
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


@admin_api_bp.route('/scrape/trigger', methods=['POST'])
def api_trigger_scrape():
    """手动触发立即抓取"""
    logger.info("🔄 [API] 手动触发抓取...")
    try:
        db_channels = get_enabled_channels()
        if not db_channels and not TG_CHANNEL_URLS:
            return jsonify({
                'success': False,
                'message': '⚠️ 未绑定任何 Telegram 频道，请先添加频道',
                'need_channel': True
            })
        total, _ = scrape_all_channels(save_news)
        message = f'抓取完成，新增 {total} 条新闻'
        if total == 0 and (not db_channels or len(db_channels) == 0):
            message = '⚠️ 没有可用的频道，请在管理后台添加 Telegram 频道后重试'
        elif total == 0:
            message = '没有新消息'
        return jsonify({'success': True, 'message': message, 'count': total})
    except Exception as e:
        logger.error(f"❌ [API] 手动抓取失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@admin_api_bp.route('/cleanup', methods=['POST'])
def api_admin_cleanup():
    """清理重复/旧数据"""
    try:
        deleted = cleanup_old_data()
        return jsonify({'success': True, 'count': deleted})
    except Exception as e:
        logger.error(f"❌ [API] 清理失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@admin_api_bp.route('/settings/interval', methods=['POST'])
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


@admin_api_bp.route('/change-password', methods=['POST'])
def api_change_password():
    """修改管理员密码"""
    try:
        data = request.json
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')

        if not old_password or not new_password:
            return jsonify({'success': False, 'message': '请填写原密码和新密码'})
        if len(new_password) < 4:
            return jsonify({'success': False, 'message': '新密码至少 4 位'})

        if not verify_admin_password('admin', old_password):
            return jsonify({'success': False, 'message': '原密码错误'})

        result = change_admin_password('admin', old_password, new_password)
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ [API] 修改密码失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@admin_api_bp.route('/check-channels')
def api_check_channels():
    """检查系统是否有可用频道（用于首次启动检测）"""
    try:
        db_channels = get_channels() or []
        has_channels = len(db_channels) > 0
        any_enabled = any(c.get('enabled', True) for c in db_channels)
        return jsonify({
            'success': True,
            'data': {
                'has_channels': has_channels,
                'any_enabled': any_enabled,
                'count': len(db_channels),
                'need_setup': not has_channels,
                'message': '⚠️ 首次使用请先添加 Telegram 频道' if not has_channels else '频道已配置'
            }
        })
    except Exception as e:
        logger.error(f"❌ [API] 频道检测失败: {str(e)}")
        return jsonify({'success': True, 'data': {'has_channels': False, 'need_setup': True, 'error': str(e)}})


@admin_api_bp.route('/channels/re-scrape', methods=['POST'])
def api_re_scrape_channel():
    """重新触发指定频道的历史消息回填"""
    data = request.json
    channel_id = data.get('id', '')
    if not channel_id:
        return jsonify({'success': False, 'message': '缺少频道 ID'})
    
    from database import get_session, Channel
    session = get_session()
    try:
        channel = session.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return jsonify({'success': False, 'message': '频道不存在'})
        
        url = channel.url
        scrape_depth = channel.scrape_depth or 1000
        channel_name = channel.name
        
        # 重置状态
        channel.history_scrape_status = 'pending'
        channel.history_scrape_count = 0
        session.commit()
        
        # 异步执行
        import threading
        def _do_re_scrape():
            try:
                from database import get_session as get_db_session
                sess = get_db_session()
                ch = sess.query(Channel).filter(Channel.id == channel_id).first()
                if ch:
                    ch.history_scrape_status = 'running'
                    sess.commit()
                sess.close()
                
                def _re_progress_callback(current, total):
                    """重新回填进度回调"""
                    sess = get_db_session()
                    ch = sess.query(Channel).filter(Channel.id == channel_id).first()
                    if ch:
                        ch.history_scrape_status = 'running'
                        ch.history_scrape_count = current
                        sess.commit()
                    sess.close()

                logger.info(f"📡 [重新回填] [{channel_name}] 开始回填 {scrape_depth} 条...")
                count = scrape_channel_history(url, save_callback=save_news, max_count=scrape_depth, progress_callback=_re_progress_callback)
                logger.info(f"✅ [重新回填] [{channel_name}] 完成，新增 {count} 条")
                
                sess = get_db_session()
                ch = sess.query(Channel).filter(Channel.id == channel_id).first()
                if ch:
                    ch.history_scrape_status = 'done' if count > 0 else 'failed'
                    ch.history_scrape_count = count
                    ch.last_history_scrape_at = now_bj()
                    sess.commit()
                sess.close()
            except Exception as e:
                logger.error(f"❌ [重新回填] [{channel_name}] 失败: {e}", exc_info=True)
                sess = get_db_session()
                ch = sess.query(Channel).filter(Channel.id == channel_id).first()
                if ch:
                    ch.history_scrape_status = 'failed'
                    sess.commit()
                sess.close()
        
        thread = threading.Thread(target=_do_re_scrape, daemon=True)
        thread.start()
        
        return jsonify({'success': True, 'message': f'已开始重新回填 {scrape_depth} 条历史消息'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        session.close()


@admin_api_bp.route('/site-name', methods=['GET'])
def api_get_site_name():
    """获取网站名称"""
    from database import get_setting
    name = get_setting('site_name', '财经新闻聚合')
    return jsonify({'success': True, 'data': {'site_name': name}})


@admin_api_bp.route('/site-name', methods=['POST'])
@login_required
def api_update_site_name():
    """更新网站名称"""
    from database import set_setting
    data = request.json
    name = data.get('site_name', '').strip()
    if not name:
        return jsonify({'success': False, 'message': '网站名称不能为空'})
    success = set_setting('site_name', name)
    return jsonify({'success': success, 'message': '网站名称已更新' if success else '更新失败'})


@admin_api_bp.route('/site-notice', methods=['GET'])
def api_get_site_notice():
    """获取公告内容"""
    from database import get_setting
    notice = get_setting('site_notice', '')
    return jsonify({'success': True, 'data': {'notice': notice}})


@admin_api_bp.route('/site-notice', methods=['POST'])
@login_required
def api_update_site_notice():
    """更新公告内容"""
    from database import set_setting
    data = request.json
    notice = data.get('notice', '').strip()
    success = set_setting('site_notice', notice)
    return jsonify({'success': success, 'message': '公告已更新' if success else '更新失败'})


@admin_api_bp.route('/summary-prompts', methods=['GET'])
@login_required
def api_get_summary_prompts():
    """获取 AI 总结提示词（含默认值）"""
    try:
        data = get_summary_prompts()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"❌ [API] 获取提示词失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@admin_api_bp.route('/summary-prompts', methods=['POST'])
@login_required
def api_update_summary_prompts():
    """更新 AI 总结提示词"""
    try:
        data = request.json
        daily = data.get('daily')
        composite = data.get('composite')
        todayqa = data.get('todayqa')
        result = set_summary_prompts(daily=daily, composite=composite, todayqa=todayqa)
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ [API] 更新提示词失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@admin_api_bp.route('/summary-prompts/todayqa', methods=['POST'])
@login_required
def api_update_todayqa_prompt():
    """单独更新当日财经分析提示词"""
    try:
        data = request.json
        todayqa = data.get('todayqa') or data.get('today_qa_prompt')
        result = set_summary_prompts(todayqa=todayqa)
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ [API] 更新当日财经分析提示词失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@admin_api_bp.route('/summary-prompts/reset', methods=['POST'])
@login_required
def api_reset_summary_prompt():
    """重置指定提示词为默认值"""
    try:
        data = request.json
        prompt_type = data.get('type', '')
        result = reset_summary_prompt(prompt_type)
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ [API] 重置提示词失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@admin_api_bp.route('/backup/list')
@login_required
def api_list_backups():
    """列出所有备份文件"""
    from services.backup_service import list_backups
    backups = list_backups()
    return jsonify({'success': True, 'data': backups})


@admin_api_bp.route('/backup/create-db', methods=['POST'])
@login_required
def api_create_db_backup():
    """创建数据库备份"""
    from services.backup_service import create_db_backup
    result = create_db_backup()
    return jsonify(result)


@admin_api_bp.route('/backup/export-json', methods=['POST'])
@login_required
def api_export_json():
    """导出所有数据为 JSON"""
    from services.backup_service import export_to_json
    result = export_to_json()
    return jsonify(result)


@admin_api_bp.route('/backup/restore-db', methods=['POST'])
@login_required
def api_restore_db():
    """从数据库备份恢复"""
    from services.backup_service import restore_from_db_backup
    data = request.json
    filename = data.get('filename', '')
    if not filename:
        return jsonify({'success': False, 'message': '请指定备份文件'})
    result = restore_from_db_backup(filename)
    return jsonify(result)


@admin_api_bp.route('/backup/import-json', methods=['POST'])
@login_required
def api_import_json():
    """从 JSON 文件导入数据"""
    from services.backup_service import import_from_json
    data = request.json
    filename = data.get('filename', '')
    if not filename:
        return jsonify({'success': False, 'message': '请指定导入文件'})
    options = data.get('options', None)
    result = import_from_json(filename, options)
    return jsonify(result)


@admin_api_bp.route('/backup/delete', methods=['POST'])
@login_required
def api_delete_backup():
    """删除备份文件"""
    from services.backup_service import delete_backup
    data = request.json
    filename = data.get('filename', '')
    if not filename:
        return jsonify({'success': False, 'message': '请指定文件名'})
    result = delete_backup(filename)
    return jsonify(result)


@admin_api_bp.route('/backup/download/<filename>')
@login_required
def api_download_backup(filename):
    """下载备份文件"""
    from services.backup_service import get_backup_download_path
    filepath = get_backup_download_path(filename)
    if not filepath:
        return jsonify({'success': False, 'message': '文件不存在'}), 404
    from flask import send_file
    return send_file(filepath, as_attachment=True, download_name=filename)


# 注意: api_get_system_config 已在下方定义
# 第一个定义已被移除，保留带 @login_required 的版本


@admin_api_bp.route('/summary-schedule')
@login_required
def api_get_summary_schedule():
    """获取定时总结时间配置"""
    try:
        data = get_summary_schedule()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"❌ [API] 获取总结时间失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@admin_api_bp.route('/summary-schedule', methods=['POST'])
@login_required
def api_update_summary_schedule():
    """更新定时总结时间配置"""
    try:
        data = request.json
        range_type = data.get('type', '')
        settings = data.get('settings', {})
        if not range_type:
            return jsonify({'success': False, 'message': '缺少总结类型'})
        result = update_summary_schedule(range_type, data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ [API] 更新总结时间失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@admin_api_bp.route('/backup-schedule')
@login_required
def api_get_backup_schedule():
    """获取自动备份时间配置"""
    try:
        from services import get_backup_schedule
        data = get_backup_schedule()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"❌ [API] 获取自动备份设置失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@admin_api_bp.route('/backup-schedule', methods=['POST'])
@login_required
def api_update_backup_schedule():
    """更新自动备份时间配置"""
    try:
        from services import update_backup_schedule
        data = request.json
        result = update_backup_schedule(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ [API] 更新自动备份设置失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
