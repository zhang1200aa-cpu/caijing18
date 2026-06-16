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

def scrape_channel(channel_url, seen, save_callback):
    """
    抓取单个频道的公开页面
    save_callback: func(news_id, title, content, tags, url, message_id) -> bool
    """
    channel_name = get_channel_name_from_url(channel_url)
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        
        resp = requests.get(channel_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"[Scraper] [{channel_name}] HTTP {resp.status_code}")
            return 0
        
        soup = BeautifulSoup(resp.text, 'lxml')
        messages = soup.select('.tgme_widget_message_wrap')
        
        if not messages:
            logger.warning(f"[Scraper] [{channel_name}] 页面中没有找到消息元素（可能被反爬）")
            return 0
        
        new_count = 0
        
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
                # 纯文本消息，使用消息本身的 Telegram 链接作为 URL
                main_url = f"https://t.me/{message_id}"
                news_id = generate_news_id(main_url + text[:100], channel_name)
            
            # 提取标题（取文本第一行作为标题）
            lines = text.split('\n')
            title = lines[0].strip()[:200] if lines[0].strip() else "无标题"
            
            # 内容（去除标题行后的剩余文本）
            content = '\n'.join(lines[1:]).strip() if len(lines) > 1 else text[:500]
            if not content:
                content = title[:300]
            
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
                logger.info(f"[Scraper] [{channel_name}] 新消息: {title[:50]}...")
        
        if new_count > 0:
            logger.info(f"[Scraper] [{channel_name}] 本次新增 {new_count} 条新闻")
        
        return new_count
    
    except requests.exceptions.RequestException as e:
        logger.error(f"[Scraper] [{channel_name}] 网络请求失败: {e}")
        return 0
    except Exception as e:
        logger.error(f"[Scraper] [{channel_name}] 解析失败: {e}", exc_info=True)
        return 0

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