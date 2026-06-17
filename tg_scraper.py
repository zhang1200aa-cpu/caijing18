#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram 公共频道爬虫 - 无需 Bot 管理员权限
通过解析 t.me/s/ChannelName 公开网页获取消息
从 config.TG_CHANNEL_URLS 读取频道 URL 配置
"""

import os
import re
import json
import time
import hashlib
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import config
from deduplicator import deduplicator

logger = logging.getLogger(__name__)

# 已处理的消息 ID 缓存文件
SEEN_FILE = os.path.join(config.APP_DATA_DIR, "tg_seen_messages.json")

def load_seen_messages():
    """加载已处理过的消息 ID 列表"""
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception as e:
            logger.warning(f"[Scraper] 读取已处理消息缓存失败: {e}")
    return set()

def save_seen_messages(seen):
    """保存已处理的消息 ID 列表"""
    try:
        os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
        with open(SEEN_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(seen)[-10000:], f, ensure_ascii=False)  # 只保留最近 10000 条
    except Exception as e:
        logger.warning(f"[Scraper] 保存已处理消息缓存失败: {e}")

def extract_links_from_text(text):
    """从文本中提取所有链接"""
    url_pattern = r'https?://[^\s<>"\'）)]+|t\.me/[^\s<>"\'）)]+'
    urls = re.findall(url_pattern, text)
    cleaned = []
    for url in urls:
        url = url.rstrip('.,;:!?）)】]\"\'')
        if url.startswith('t.me'):
            url = 'https://' + url
        cleaned.append(url)
    return cleaned

def generate_news_id(url_or_text, channel_name):
    """根据 URL 或文本内容 + 频道生成唯一 ID"""
    raw = f"{channel_name}:{url_or_text}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]

def get_channel_name_from_url(url):
    """从 URL 提取频道名，例如 https://t.me/s/Financial_Express -> Financial_Express"""
    name = url.rstrip('/').split('/')[-1]
    return name

def scrape_channel(channel_url, seen, save_callback, max_new=None, scrape_all_history=False):
    """
    抓取单个频道的公开页面
    save_callback: func(news_id, title, content, tags, url, message_id) -> bool
    max_new: 最多抓取多少条新消息（历史抓取时使用）
    scrape_all_history: 是否抓取历史消息（用于频道初始绑定时的回填）
    """
    channel_name = get_channel_name_from_url(channel_url)
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        
        base_url = channel_url.rstrip('/')
        before_param = None
        total_new = 0
        page_count = 0
        
        while True:
            if before_param:
                url = f"{base_url}?before={before_param}"
            else:
                url = channel_url
            
            logger.info(f"[Scraper] [{channel_name}] 抓取: {url}")
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"[Scraper] [{channel_name}] HTTP {resp.status_code}")
                break
            
            soup = BeautifulSoup(resp.text, 'lxml')
            messages = soup.select('.tgme_widget_message_wrap')
            
            if not messages:
                logger.warning(f"[Scraper] [{channel_name}] 页面中没有找到消息元素（可能被反爬）")
                break
            
            new_count = 0
            oldest_message_id = None
            
            for msg in messages:
                msg_div = msg.select_one('.tgme_widget_message')
                if not msg_div:
                    continue
                
                message_id = msg_div.get('data-post', '')
                if not message_id:
                    continue
                
                if message_id in seen:
                    continue
                
                text_div = msg.select_one('.tgme_widget_message_text.js-message_text')
                if not text_div:
                    continue
                
                text = text_div.get_text('\n', strip=True)
                if not text:
                    continue
                
                # 提取链接（如果有的话）
                links = extract_links_from_text(text)
                
                if links:
                    main_url = links[0]
                    news_id = generate_news_id(main_url, channel_name)
                else:
                    main_url = f"https://t.me/{message_id}"
                    news_id = generate_news_id(main_url + text[:100], channel_name)
                
                # 提取标题（取文本第一行作为标题）
                lines = text.split('\n')
                title = lines[0].strip()[:200] if lines[0].strip() else "无标题"
                
                # 内容（去除标题行后的剩余文本）
                content = '\n'.join(lines[1:]).strip() if len(lines) > 1 else text[:500]
                if not content:
                    content = title[:300]
                
                # 使用 Deduplicator 智能去重
                is_dup, reason = deduplicator.is_duplicate(title, content[:2000], message_id)
                if is_dup:
                    logger.debug(f"[Scraper] [{channel_name}] 跳过重复消息: {reason} - {title[:50]}...")
                    seen.add(message_id)
                    continue

                seen.add(message_id)

                success = save_callback(
                    news_id=news_id,
                    title=title,
                    content=content[:2000],
                    tags=channel_name,
                    url=main_url,
                    message_id=message_id
                )
                
                if success:
                    new_count += 1
                    total_new += 1
                    logger.info(f"[Scraper] [{channel_name}] 新消息: {title[:50]}...")
                
                # 记录最旧的消息ID用于翻页
                if oldest_message_id is None:
                    oldest_message_id = message_id
            
            if new_count > 0:
                logger.info(f"[Scraper] [{channel_name}] 本页新增 {new_count} 条")
            else:
                logger.info(f"[Scraper] [{channel_name}] 本页无新消息，停止翻页")
                break
            
            # 判断是否需要继续翻页
            page_count += 1
            if not scrape_all_history:
                # 常规抓取：翻 1-2 页即可
                if page_count >= 2:
                    break
            else:
                # 历史抓取：根据 max_new 判断
                if max_new and total_new >= max_new:
                    logger.info(f"[Scraper] [{channel_name}] 已达到目标抓取数量 {max_new}，停止")
                    break
                if page_count >= 50:  # 安全限制，最多50页
                    logger.info(f"[Scraper] [{channel_name}] 已达最大翻页数 50，停止")
                    break
            
            # 设置翻页参数
            if oldest_message_id:
                before_param = oldest_message_id
                time.sleep(0.5)  # 翻页间隔，避免被反爬
            else:
                break
        
        return total_new
    
    except requests.exceptions.RequestException as e:
        logger.error(f"[Scraper] [{channel_name}] 网络请求失败: {e}")
        return 0
    except Exception as e:
        logger.error(f"[Scraper] [{channel_name}] 解析失败: {e}", exc_info=True)
        return 0


def scrape_channel_history(channel_url, max_count: int = 1000):
    """
    专门用于频道绑定时的历史消息回填
    不受 seen 缓存限制，允许大量翻页
    """
    from database import save_news
    seen = load_seen_messages()
    
    def save_callback(news_id, title, content, tags, url, message_id):
        return save_news(
            news_id=news_id,
            title=title,
            content=content,
            tags=tags,
            url=url,
            message_id=message_id
        )
    
    channel_name = get_channel_name_from_url(channel_url)
    logger.info(f"[Scraper] 开始历史回填: {channel_name}, 目标: {max_count} 条")
    
    total = scrape_channel(
        channel_url=channel_url,
        seen=seen,
        save_callback=save_callback,
        max_new=max_count,
        scrape_all_history=True
    )
    
    save_seen_messages(seen)
    logger.info(f"[Scraper] 历史回填完成: {channel_name}, 共 {total} 条")
    return total

def scrape_all_channels(save_callback):
    """
    抓取所有配置的频道
    优先从数据库读取启用的频道，如果没有则从 config.TG_CHANNEL_URLS 读取
    """
    seen = load_seen_messages()
    total_new = 0
    
    # 尝试从数据库读取启用的频道
    try:
        from database import get_enabled_channels
        db_channels = get_enabled_channels()
        if db_channels:
            channel_urls = [c.url for c in db_channels]
            logger.info(f"[Scraper] 从数据库读取 {len(channel_urls)} 个频道")
        else:
            channel_urls = config.TG_CHANNEL_URLS
            logger.info(f"[Scraper] 数据库无频道，使用配置文件中的 {len(channel_urls)} 个频道")
    except Exception as e:
        channel_urls = config.TG_CHANNEL_URLS
        logger.warning(f"[Scraper] 读取数据库频道失败，使用配置文件: {e}")
    
    for channel_url in channel_urls:
        channel_name = get_channel_name_from_url(channel_url)
        logger.info(f"[Scraper] 开始抓取: {channel_name} ({channel_url})")
        count = scrape_channel(channel_url, seen, save_callback)
        total_new += count
        time.sleep(1)
    
    save_seen_messages(seen)
    
    return total_new


def scrape_channel_with_depth(channel_url: str, scrape_depth: int = 1000):
    """
    按照频道配置的历史条数深度抓取，用于频道绑定时的历史回填
    如果 scrape_depth <= 0，则不抓取历史
    """
    if scrape_depth <= 0:
        logger.info(f"[Scraper] 跳过历史回填: {channel_url}, scrape_depth={scrape_depth}")
        return 0
    
    from database import save_news
    
    def save_callback(news_id, title, content, tags, url, message_id):
        return save_news(
            news_id=news_id,
            title=title,
            content=content,
            tags=tags,
            url=url,
            message_id=message_id
        )
    
    seen = load_seen_messages()
    channel_name = get_channel_name_from_url(channel_url)
    logger.info(f"[Scraper] 深度抓取: {channel_name}, 目标: {scrape_depth} 条")
    
    total = scrape_channel(
        channel_url=channel_url,
        seen=seen,
        save_callback=save_callback,
        max_new=scrape_depth,
        scrape_all_history=True
    )
    
    save_seen_messages(seen)
    logger.info(f"[Scraper] 深度抓取完成: {channel_name}, 共 {total} 条")
    return total

# ============ 测试入口 ============
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    def test_save(news_id, title, content, tags, url, message_id):
        print(f"  -> title: {title[:50]}")
        print(f"  -> url: {url}")
        print(f"  -> id: {news_id}")
        print()
        return True
    
    print(f"配置频道数: {len(config.TG_CHANNEL_URLS)}")
    for url in config.TG_CHANNEL_URLS:
        print(f"   - {url}")
    print()
    
    total = scrape_all_channels(test_save)
    print(f"\n完成，共 {total} 条新消息")