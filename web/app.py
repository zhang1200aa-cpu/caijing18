from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from database import (
    get_all_news, search_news, get_news_by_tag, 
    get_stats, cleanup_old_data
)
from tagger import tagger

app = Flask(__name__, template_folder='templates')
CORS(app)

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/news', methods=['GET'])
def get_news():
    """获取新闻列表"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    offset = (page - 1) * limit
    
    news_list = get_all_news(limit=limit, offset=offset)
    
    return jsonify({
        'code': 0,
        'data': [
            {
                'id': news.id,
                'title': news.title,
                'content': news.content[:200] + '...' if len(news.content) > 200 else news.content,
                'full_content': news.content,
                'tags': tagger.parse_tags(news.tags),
                'time': news.published_time.isoformat(),
                'source': news.source
            }
            for news in news_list
        ],
        'total': len(news_list)
    })
@app.route('/api/search', methods=['GET'])
def search():
    """搜索新闻"""
    keyword = request.args.get('keyword', '', type=str).strip()
    
    if not keyword or len(keyword) < 2:
        return jsonify({'code': 1, 'message': '搜索词长度至少2个字符'}), 400
    
    results = search_news(keyword, limit=100)
    
    return jsonify({
        'code': 0,
        'keyword': keyword,
        'total': len(results),
        'data': [
            {
                'id': news.id,
                'title': news.title,
                'content': news.content[:200] + '...',
                'full_content': news.content,
                'tags': tagger.parse_tags(news.tags),
                'time': news.published_time.isoformat(),
                'source': news.source
            }
            for news in results
        ]
    })

@app.route('/api/tags', methods=['GET'])
def get_tags():
    """获取所有可用标签"""
    tags = list(config.FINANCE_KEYWORDS.keys())
    return jsonify({
        'code': 0,
        'tags': tags
    })

@app.route('/api/news/by-tag', methods=['GET'])
def news_by_tag():
    """按标签获取新闻"""
    tag = request.args.get('tag', '', type=str).strip()
    
    if not tag:
        return jsonify({'code': 1, 'message': '标签不能为空'}), 400
    
    results = get_news_by_tag(tag, limit=100)
    
    return jsonify({
        'code': 0,
        'tag': tag,
        'total': len(results),
        'data': [
            {
                'id': news.id,
                'title': news.title,
                'content': news.content[:200] + '...',
                'full_content': news.content,
                'tags': tagger.parse_tags(news.tags),
                'time': news.published_time.isoformat(),
                'source': news.source
            }
            for news in results
        ]
    })

@app.route('/api/stats', methods=['GET'])
def stats():
    """获取统计信息"""
    stats_data = get_stats()
    
    return jsonify({
        'code': 0,
        'stats': {
            'total': stats_data['total'],
            'today': stats_data['today'],
            'retention_days': config.DATA_RETENTION_DAYS,
            'similarity_threshold': config.SIMILARITY_THRESHOLD
        }
    })

@app.route('/api/filter', methods=['GET'])
def filter_news():
    """按日期和标签筛选"""
    start_date = request.args.get('start_date', type=str)
    end_date = request.args.get('end_date', type=str)
    tags = request.args.getlist('tags')
    
    from database import get_session, FinanceNews
    session = get_session()
    
    try:
        query = session.query(FinanceNews)
        
        if start_date:
            start = datetime.fromisoformat(start_date)
            query = query.filter(FinanceNews.published_time >= start)
        
        if end_date:
            end = datetime.fromisoformat(end_date)
            query = query.filter(FinanceNews.published_time <= end)
        
        results = query.order_by(FinanceNews.published_time.desc()).all()
        
        # 标签过滤
        if tags:
            filtered = []
            for news in results:
                news_tags = tagger.parse_tags(news.tags)
                if any(tag in news_tags for tag in tags):
                    filtered.append(news)
            results = filtered
        
        return jsonify({
            'code': 0,
            'total': len(results),
            'data': [
                {
                    'id': news.id,
                    'title': news.title,
                    'content': news.content[:200] + '...',
                    'full_content': news.content,
                    'tags': tagger.parse_tags(news.tags),
                    'time': news.published_time.isoformat(),
                    'source': news.source
                }
                for news in results
            ]
        })
    finally:
        session.close()

@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    """手动清理过期数据"""
    try:
        cleanup_old_data()
        return jsonify({
            'code': 0,
            'message': '数据清理完成'
        })
    except Exception as e:
        return jsonify({
            'code': 1,
            'message': f'清理失败: {str(e)}'
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'code': 404, 'message': '接口不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'code': 500, 'message': '服务器错误'}), 500

if __name__ == '__main__':
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG)
