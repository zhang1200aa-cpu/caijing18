"""
AI 总结相关 API 路由（重构版）
支持：当日总结、昨日总结、三日总结、一周总结、搜索结果总结
"""
import logging
from flask import Blueprint, jsonify, request
from services.summary_service import (
    generate_today_summary,
    generate_yesterday_summary,
    generate_3d_summary,
    generate_1w_summary,
    generate_search_summary,
    generate_today_qa,
)
from database import get_setting, set_setting, get_all_settings

logger = logging.getLogger(__name__)

ai_api_bp = Blueprint('ai_api', __name__, url_prefix='/api')


@ai_api_bp.route('/summary/today', methods=['GET', 'POST'])
def api_today_summary():
    """获取当日总结"""
    force = request.method == 'POST' and request.json and request.json.get('force', False)
    result = generate_today_summary(force=force)
    return jsonify(result)


@ai_api_bp.route('/summary/yesterday', methods=['GET', 'POST'])
def api_yesterday_summary():
    """获取昨日总结"""
    force = request.method == 'POST' and request.json and request.json.get('force', False)
    result = generate_yesterday_summary(force=force)
    return jsonify(result)


@ai_api_bp.route('/summary/3d', methods=['GET', 'POST'])
def api_3day_summary():
    """获取三日总结"""
    force = request.method == 'POST' and request.json and request.json.get('force', False)
    result = generate_3d_summary(force=force)
    return jsonify(result)


@ai_api_bp.route('/summary/1w', methods=['GET', 'POST'])
def api_1week_summary():
    """获取一周总结"""
    force = request.method == 'POST' and request.json and request.json.get('force', False)
    result = generate_1w_summary(force=force)
    return jsonify(result)


@ai_api_bp.route('/summary/today-qa', methods=['POST'])
def api_today_qa():
    """当日财经分析：基于今日新闻回答用户问题"""
    data = request.json or {}
    question = data.get('question', '').strip()
    if not question:
        return jsonify({'success': False, 'message': '请输入你的问题'})
    result = generate_today_qa(question)
    return jsonify(result)


@ai_api_bp.route('/summary/search', methods=['POST'])
def api_search_summary():
    """获取搜索结果总结"""
    data = request.json or {}
    keyword = data.get('keyword', '').strip()
    force = data.get('force', False)
    if not keyword:
        return jsonify({'success': False, 'message': '请输入搜索关键词'})
    result = generate_search_summary(keyword, force=force)
    return jsonify(result)


@ai_api_bp.route('/summary/all')
def api_all_summaries():
    """获取所有总结的概览（用于主页展示）"""
    try:
        summaries = {}
        today = generate_today_summary()
        if today.get('success'):
            summaries['today'] = today['data']
        yesterday = generate_yesterday_summary()
        if yesterday.get('success'):
            summaries['yesterday'] = yesterday['data']
        # 也获取 3d 和 1w 总结
        for key, func in [('3d', generate_3d_summary), ('1w', generate_1w_summary)]:
            result = func()
            if result.get('success'):
                summaries[key] = result['data']
        return jsonify({
            'success': True,
            'data': summaries
        })
    except Exception as e:
        logger.error(f"❌ [API] 获取所有总结失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@ai_api_bp.route('/ai/status')
def api_ai_status():
    """AI 系统状态"""
    try:
        db_settings = get_all_settings()
        api_key = db_settings.get('ai_api_key', '') or getattr(__import__('config'), 'AI_API_KEY', '')
        base_url = db_settings.get('ai_base_url', '') or getattr(__import__('config'), 'AI_API_URL', '')
        model = db_settings.get('ai_model', '') or getattr(__import__('config'), 'AI_MODEL', '')
        summary_context = db_settings.get('ai_summary_context', '')

        # 测试连接
        connected = False
        if api_key:
            try:
                from services.summary_service import call_ai
                result = call_ai('ping', 'ping')
                connected = result is not None
            except Exception:
                connected = False

        return jsonify({
            'success': True,
            'data': {
                'configured': bool(api_key),
                'api_key': '****' + api_key[-4:] if api_key else '',
                'base_url': base_url,
                'model': model,
                'summary_context': summary_context,
                'connected': connected,
            }
        })
    except Exception as e:
        logger.error(f"❌ [API] AI 状态查询失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@ai_api_bp.route('/ai/settings', methods=['POST'])
@ai_api_bp.route('/admin/ai/settings', methods=['POST'])
def api_update_ai_settings():
    """更新 AI 设置"""
    try:
        data = request.json
        api_key = data.get('api_key', '')
        base_url = data.get('base_url', '')
        model = data.get('model', '')
        summary_context = data.get('summary_context')
        if api_key:
            set_setting('ai_api_key', api_key)
        if base_url:
            set_setting('ai_base_url', base_url)
        if model:
            set_setting('ai_model', model)
        if summary_context is not None:
            set_setting('ai_summary_context', summary_context)
        logger.info(f"✅ [API] AI 设置已更新")
        return jsonify({'success': True, 'message': 'AI 设置已更新'})
    except Exception as e:
        logger.error(f"❌ [API] AI 设置更新失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@ai_api_bp.route('/settings/today-qa-hours')
def api_today_qa_hours():
    """获取今日分析时间范围设置（公开接口，供前端展示）"""
    try:
        from services.summary_service import get_today_qa_hours_setting
        hours = get_today_qa_hours_setting()
        return jsonify({'success': True, 'data': {'today_qa_hours': hours}})
    except Exception as e:
        logger.error(f"❌ [API] 获取今日分析时间范围失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@ai_api_bp.route('/ai/test', methods=['POST'])
@ai_api_bp.route('/admin/ai/test', methods=['POST'])
def api_test_ai_connection():
    """测试 AI API 连接"""
    try:
        from services.summary_service import call_ai
        result = call_ai('测试连接', '请回复OK以确认连接正常。')
        connected = result is not None
        return jsonify({
            'success': True,
            'connected': connected,
            'message': '✅ 连接测试成功' if connected else '❌ 连接测试失败，请检查 API 配置'
        })
    except Exception as e:
        logger.error(f"❌ [API] AI 连接测试失败: {str(e)}")
        return jsonify({'success': False, 'connected': False, 'message': f'❌ 测试失败: {str(e)}'})
