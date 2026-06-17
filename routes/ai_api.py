"""
AI 相关 API 路由（总结、分析、状态）
"""
import logging
import re
from flask import Blueprint, jsonify, request
from services import (
    generate_summary_for_range,
    generate_merged_summary_for_range,
    get_range_news_count,
)
from database import (
    get_latest_ai_summary,
    get_ai_summary_by_date,
    get_ai_summary_status,
    get_setting,
    set_setting,
    get_all_settings,
)
import config

logger = logging.getLogger(__name__)

ai_api_bp = Blueprint('ai_api', __name__, url_prefix='/api')


@ai_api_bp.route('/summary', methods=['POST'])
def api_generate_summary():
    """API：手动触发 AI 总结生成"""
    try:
        range_key = request.json.get('range', '1d')
        ref_date = request.json.get('date')
        ref_date_str = ref_date.replace('-', '')[:8] if ref_date else None

        if range_key == '1d':
            success = generate_summary_for_range('1d', '每日', 1, ref_date=ref_date_str)
        elif range_key == '3d':
            success = generate_merged_summary_for_range('3d', '近3天', 3, ref_date=ref_date_str)
        elif range_key == '1w':
            success = generate_merged_summary_for_range('1w', '近1周', 7, ref_date=ref_date_str)
        else:
            return jsonify({'success': False, 'message': '无效的 range 参数'})

        if success:
            return jsonify({'success': True, 'message': f'{range_key} 总结生成成功'})
        else:
            return jsonify({'success': False, 'message': '生成失败，请检查日志'})
    except Exception as e:
        logger.error(f"❌ [API] 生成总结失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@ai_api_bp.route('/summary/status')
def api_summary_status():
    """API：获取 AI 总结状态"""
    try:
        status = get_ai_summary_status()
        return jsonify({'success': True, 'data': status})
    except Exception as e:
        logger.error(f"❌ [API] 获取总结状态失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@ai_api_bp.route('/ai/analysis', methods=['POST'])
def api_ai_analysis():
    """AI 新闻分析"""
    from database import FinanceNews
    from db import session_scope_readonly
    from services.news_service import news_to_dict
    from ai_summary import generate_news_analysis

    try:
        data = request.json
        news_ids = data.get('news_ids', [])
        news_id = data.get('news_id')
        if news_id:
            news_ids = [news_id]

        with session_scope_readonly() as session:
            news_objs = session.query(FinanceNews).filter(
                FinanceNews.id.in_(news_ids)
            ).all()

        if not news_objs:
            return jsonify({'success': False, 'message': '未找到指定的新闻'})
        news_dicts = [news_to_dict(n) for n in news_objs]
        result = generate_news_analysis(news_dicts[0]) if news_dicts else None
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"❌ [API] AI 分析失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@ai_api_bp.route('/ai/status')
def api_ai_status():
    """AI 系统状态"""
    try:
        from ai_summary import AIClient
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


@ai_api_bp.route('/admin/ai/settings', methods=['POST'])
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
        # 尝试测试连接
        from ai_summary import AIClient
        client = AIClient()
        connected = client.test_connection()
        logger.info(f"✅ [API] AI 设置已更新，连接测试: {'成功' if connected else '失败'}")
        return jsonify({
            'success': True,
            'message': 'AI 设置已更新',
            'connected': connected
        })
    except Exception as e:
        logger.error(f"❌ [API] AI 设置更新失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@ai_api_bp.route('/admin/ai/test', methods=['POST'])
def api_test_ai_connection():
    """测试 AI API 连接"""
    try:
        data = request.json or {}
        # 支持临时测试（不保存）和保存后测试
        api_key = data.get('api_key', '')
        base_url = data.get('base_url', '')
        model = data.get('model', '')
        
        from ai_summary import AIClient
        # 临时替换配置测试
        import config as app_config
        old_key = app_config.AI_API_KEY
        old_url = app_config.AI_BASE_URL
        old_model = app_config.AI_MODEL
        try:
            if api_key:
                app_config.AI_API_KEY = api_key
            if base_url:
                app_config.AI_BASE_URL = base_url
            if model:
                app_config.AI_MODEL = model
            client = AIClient()
            connected = client.test_connection()
            return jsonify({
                'success': True,
                'connected': connected,
                'message': '✅ 连接测试成功' if connected else '❌ 连接测试失败，请检查 API Key、Base URL 或模型名称'
            })
        finally:
            app_config.AI_API_KEY = old_key
            app_config.AI_BASE_URL = old_url
            app_config.AI_MODEL = old_model
    except Exception as e:
        logger.error(f"❌ [API] AI 连接测试失败: {str(e)}")
        return jsonify({'success': False, 'connected': False, 'message': f'❌ 测试失败: {str(e)}'})


@ai_api_bp.route('/ai/summary')
def api_get_ai_summary():
    """获取 AI 总结"""
    try:
        range_key = request.args.get('range', '1d')
        summary = get_latest_ai_summary(range_key)
        if summary.get('success'):
            s = summary['data']
            content = s['content']
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


@ai_api_bp.route('/ai/summary/refresh', methods=['POST'])
def api_refresh_ai_summary():
    """刷新 AI 总结"""
    try:
        data = request.json or {}
        range_key = data.get('range', '1d')
        ref_date = data.get('date')
        ref_date_str = ref_date.replace('-', '')[:8] if ref_date else None

        if range_key == '1d':
            success = generate_summary_for_range('1d', '每日', 1, ref_date=ref_date_str)
            news_count = get_range_news_count(1, ref_date_str)
        elif range_key == '3d':
            success = generate_merged_summary_for_range('3d', '近3天', 3, ref_date=ref_date_str)
            news_count = get_range_news_count(3, ref_date_str)
        elif range_key == '1w':
            success = generate_merged_summary_for_range('1w', '近1周', 7, ref_date=ref_date_str)
            news_count = get_range_news_count(3, ref_date_str)
        else:
            return jsonify({'success': False, 'message': '无效的 range 参数'})

        if success:
            return jsonify({'success': True, 'data': {'news_count': news_count}})
        else:
            return jsonify({'success': False, 'message': '生成失败，请检查日志或 API 配置'})
    except Exception as e:
        logger.error(f"❌ [API] 刷新 AI 总结失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})