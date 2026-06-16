#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主程序入口
- 启动 Flask Web 服务器
- 定时任务管理（数据清理、统计）
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

# 加载环境变量
load_dotenv()

# ============ 日志配置 ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# ============ 导入项目模块 ============
from database import init_database, get_session, cleanup_old_data, get_stats, FinanceNews

# ============ Flask 应用配置 ============
app = Flask(__name__, template_folder='web/templates')
app.config['JSON_AS_ASCII'] = False
app.config['JSON_SORT_KEYS'] = False

# ============ 定时任务调度器 ============
scheduler = BackgroundScheduler()
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

# ============ 定时任务函数 ============

def cleanup_task():
    """定时清理任务：删除 7 天前的数据"""
    logger.info("=" * 60)
    logger.info(f"🧹 [Task] 数据清理任务启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    try:
        deleted_count = cleanup_old_data()
        logger.info(f"✅ [Task] 清理完成，删除 {deleted_count} 条过期记录")
    except Exception as e:
        logger.error(f"❌ [Task] 清理失败: {str(e)}")
    logger.info("=" * 60)

def stats_task():
    """定时统计任务：生成统计信息"""
    logger.info(f"📊 [Task] 统计任务执行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        stats = get_stats()
        logger.info(f"✅ [Task] 统计信息: {stats}")
    except Exception as e:
        logger.error(f"❌ [Task] 统计失败: {str(e)}")

# ============ 辅助函数：将 ORM 对象转换为字典 ============

def news_to_dict(news):
    """将 FinanceNews 对象转换为字典"""
    return {
        'id': news.id,
        'title': news.title,
        'content': news.content,
        'tags': news.tags.split(',') if news.tags else [],
        'created_at': news.created_time.isoformat() if news.created_time else None,
        'published_at': news.published_time.isoformat() if news.published_time else None,
        'source': news.source,
        'url': news.url,
    }

# ============ Flask 路由 ============

@app.route('/')
def index():
    """主页"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"❌ [Web] 获取主页失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/news', methods=['GET'])
def get_news():
    """获取新闻列表（分页）"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = request.args.get('limit', per_page, type=int)  # 兼容 limit 参数
        
        session = get_session()
        try:
            # 获取总数
            total = session.query(FinanceNews).count()
            
            # 获取分页数据
            offset = (page - 1) * per_page
            articles = session.query(FinanceNews).order_by(
                FinanceNews.published_time.desc()
            ).limit(per_page).offset(offset).all()
            
            return jsonify({
                'success': True,
                'data': [news_to_dict(a) for a in articles],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            })
        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ [API] 获取新闻失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search_news():
    """按关键词搜索新闻"""
    try:
        keyword = request.args.get('keyword', '', type=str)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = request.args.get('limit', per_page, type=int)
        
        if not keyword:
            return jsonify({"error": "keyword required"}), 400
        
        session = get_session()
        try:
            # 构建查询
            query = session.query(FinanceNews).filter(
                (FinanceNews.title.ilike(f'%{keyword}%')) |
                (FinanceNews.content.ilike(f'%{keyword}%')) |
                (FinanceNews.tags.ilike(f'%{keyword}%'))
            )
            
            # 获取总数
            total = query.count()
            
            # 获取分页数据
            offset = (page - 1) * per_page
            articles = query.order_by(
                FinanceNews.published_time.desc()
            ).limit(per_page).offset(offset).all()
            
            return jsonify({
                'success': True,
                'data': [news_to_dict(a) for a in articles],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            })
        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ [API] 搜索失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/news/by-tag', methods=['GET'])
def get_news_by_tag():
    """按标签筛选新闻"""
    try:
        tag = request.args.get('tag', '', type=str)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = request.args.get('limit', per_page, type=int)
        
        if not tag:
            return jsonify({"error": "tag required"}), 400
        
        session = get_session()
        try:
            # 构建查询
            query = session.query(FinanceNews).filter(
                FinanceNews.tags.ilike(f'%{tag}%')
            )
            
            # 获取总数
            total = query.count()
            
            # 获取分页数据
            offset = (page - 1) * per_page
            articles = query.order_by(
                FinanceNews.published_time.desc()
            ).limit(per_page).offset(offset).all()
            
            return jsonify({
                'success': True,
                'data': [news_to_dict(a) for a in articles],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            })
        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ [API] 按标签筛选失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/filter', methods=['GET'])
def filter_news():
    """多条件组合筛选"""
    try:
        tags = request.args.get('tags', '', type=str)
        start_date = request.args.get('start_date', '', type=str)
        end_date = request.args.get('end_date', '', type=str)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = request.args.get('limit', per_page, type=int)
        
        session = get_session()
        try:
            # 开始构建查询
            query = session.query(FinanceNews)
            
            # 按标签筛选
            if tags:
                tag_list = [t.strip() for t in tags.split(',')]
                tag_conditions = [FinanceNews.tags.ilike(f'%{tag}%') for tag in tag_list]
                from sqlalchemy import or_
                query = query.filter(or_(*tag_conditions))
            
            # 按开始日期筛选
            if start_date:
                from datetime import datetime as dt
                start_dt = dt.fromisoformat(start_date)
                query = query.filter(FinanceNews.created_time >= start_dt)
            
            # 按结束日期筛选
            if end_date:
                from datetime import datetime as dt
                end_dt = dt.fromisoformat(end_date)
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.filter(FinanceNews.created_time <= end_dt)
            
            # 获取总数
            total = query.count()
            
            # 获取分页数据
            offset = (page - 1) * per_page
            articles = query.order_by(
                FinanceNews.published_time.desc()
            ).limit(per_page).offset(offset).all()
            
            return jsonify({
                'success': True,
                'data': [news_to_dict(a) for a in articles],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            })
        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ [API] 多条件筛选失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tags', methods=['GET'])
def get_all_tags():
    """获取所有可用标签"""
    try:
        session = get_session()
        try:
            # 获取所有包含标签的新闻
            articles = session.query(FinanceNews).filter(
                FinanceNews.tags.isnot(None)
            ).all()
            
            all_tags = set()
            for article in articles:
                if article.tags:
                    tags = article.tags.split(',')
                    all_tags.update([t.strip() for t in tags if t.strip()])
            
            return jsonify({
                'success': True,
                'data': sorted(list(all_tags))
            })
        finally:
            session.close()
    except Exception as e:
        logger.error(f"❌ [API] 获取标签失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_api_stats():
    """获取统计信息"""
    try:
        stats = get_stats()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"❌ [API] 获取统计信息失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cleanup', methods=['POST'])
def trigger_cleanup():
    """手动触发数据清理"""
    try:
        deleted_count = cleanup_old_data()
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} records'
        })
    except Exception as e:
        logger.error(f"❌ [API] 手动清理失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'success': True,
        'message': 'Service is running',
        'timestamp': datetime.now().isoformat()
    })

# ============ 错误处理 ============

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"❌ [Web] 服务器错误: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500

# ============ 主程序 ============

def main():
    """程序入口"""
    logger.info("=" * 60)
    logger.info("🚀 [Main] caijing18 财经新闻聚合平台启动")
    logger.info("=" * 60)
    
    # 初始化数据库
    logger.info("📦 [Main] 初始化数据库...")
    try:
        init_database()
        logger.info("✅ [Main] 数据库初始化完成")
    except Exception as e:
        logger.error(f"❌ [Main] 数据库初始化失败: {str(e)}")
        sys.exit(1)
    
    # 添加定时任务
    logger.info("⏰ [Main] 添加定时任务...")
    try:
        # 每天 03:00 执行数据清理
        scheduler.add_job(
            cleanup_task,
            trigger=CronTrigger(hour=3, minute=0),
            id='cleanup_job',
            name='Daily cleanup task',
            replace_existing=True
        )
        logger.info("✅ [Main] 数据清理任务 - 每天 03:00 执行")
        
        # 每小时执行统计
        scheduler.add_job(
            stats_task,
            trigger=CronTrigger(minute=0),
            id='stats_job',
            name='Hourly stats task',
            replace_existing=True
        )
        logger.info("✅ [Main] 统计任务 - 每小时 00 分执行")
    except Exception as e:
        logger.error(f"❌ [Main] 添加定时任务失败: {str(e)}")
    
    # 启动 Flask 服务器
    logger.info("=" * 60)
    logger.info("🌐 [Main] 启动 Flask Web 服务器...")
    logger.info("=" * 60)
    
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False
        )
    except Exception as e:
        logger.error(f"❌ [Main] Flask 启动失败: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
