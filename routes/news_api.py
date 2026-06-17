"""
新闻相关 API 路由
"""
import logging
from flask import Blueprint, jsonify, request
from services import news_to_dict, get_news_list, get_news_detail, search_news, get_tags, get_stats

logger = logging.getLogger(__name__)

news_api_bp = Blueprint('news_api', __name__, url_prefix='/api')


@news_api_bp.route('/news')
def api_get_news():
    """获取新闻列表"""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    tag = request.args.get('tag')
    try:
        data_list, total = get_news_list(limit=limit, offset=offset, tag=tag)
        return jsonify({
            'success': True,
            'data': data_list,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.error(f"❌ [API] 获取新闻失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@news_api_bp.route('/news/<news_id>')
def api_get_news_detail(news_id):
    """获取新闻详情"""
    try:
        data = get_news_detail(news_id)
        if not data:
            return jsonify({'success': False, 'message': '新闻不存在'}), 404
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"❌ [API] 获取新闻详情失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@news_api_bp.route('/news/search')
def api_search_news():
    """搜索新闻"""
    keyword = request.args.get('q', '').strip()
    limit = request.args.get('limit', 50, type=int)
    if not keyword:
        return jsonify({'success': False, 'message': '请输入搜索关键词'})
    try:
        results = search_news(keyword, limit=limit)
        return jsonify({
            'success': True,
            'data': results,
            'total': len(results),
            'keyword': keyword
        })
    except Exception as e:
        logger.error(f"❌ [API] 搜索新闻失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@news_api_bp.route('/tags')
def api_get_tags():
    """获取所有标签"""
    try:
        tags = get_tags()
        return jsonify({'success': True, 'data': tags})
    except Exception as e:
        logger.error(f"❌ [API] 获取标签失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@news_api_bp.route('/stats')
def api_get_stats():
    """获取统计数据"""
    try:
        stats = get_stats()
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        logger.error(f"❌ [API] 获取统计失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})