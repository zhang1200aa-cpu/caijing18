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
    save_callback: func(news_id, title, content, tags, url, message_id, source) -> bool
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

                # 历史回填时跳过 seen 缓存，避免旧缓存阻塞新数据
                # 但常规增量抓取时仍用 seen 去重
                if not scrape_all_history and message_id in seen:
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

                # 传入 source=channel_name 确保新闻归属正确频道
                success = save_callback(
                    news_id=news_id,
                    title=title,
                    content=content[:2000],
                    tags=channel_name,
                    url=main_url,
                    message_id=message_id,
                    source=channel_name
                )

                if success:
                    new_count += 1
                    total_new += 1
                    logger.info(f"[Scraper] [{channel_name}] 新消息: {title[:50]}...")

            # 记录最旧（页面底部）的消息ID用于翻页（只取数字ID部分）
            oldest_message_id = message_id

            if new_count > 0:
                logger.info(f"[Scraper] [{channel_name}] 本页新增 {new_count} 条")
            else:
                # 历史回填时，即使本页无新增也要尝试翻页（可能整页都已被数据库去重过滤）
                if not scrape_all_history:
                    logger.info(f"[Scraper] [{channel_name}] 无新消息，停止翻页")
                    break
                else:
                    logger.info(f"[Scraper] [{channel_name}] 历史回填中本页无新增，继续翻页...")

            page_count += 1

            # 历史回填：达到 max_new 上限时停止
            if scrape_all_history and max_new is not None and total_new >= max_new:
                logger.info(f"[Scraper] [{channel_name}] 历史回填达到上限 {max_new} 条，停止")
                break

            # 增量抓取：连续 3 页无新增则停止
            if not scrape_all_history and new_count == 0:
                logger.info(f"[Scraper] [{channel_name}] 连续翻页无新消息，停止")
                break

            if oldest_message_id:
                # 从 data-post 格式（channelname/12345）中提取纯数字ID用于翻页
                before_param = oldest_message_id.split('/')[-1] if '/' in oldest_message_id else oldest_message_id
            else:
                break

            # 翻页间隔
            time.sleep(2)

        return total_new

    except Exception as e:
        logger.error(f"[Scraper] [{channel_name}] 抓取出错: {e}", exc_info=True)
        return total_new


def scrape_all_channels(save_callback, max_new=None):
    """
    抓取配置中的所有频道（包括 config 中的和数据库中的）
    返回新增总数和每个频道的增量字典
    """
    seen = load_seen_messages()
    total_new = 0
    channel_stats = {}

    # 合并 config 中的 URL 和数据库中的频道 URL
    urls = set()
    for url in config.TG_CHANNEL_URLS:
        urls.add(url)
    
    # 从数据库获取已启用的频道
    try:
        from database import get_enabled_channels
        db_channels = get_enabled_channels()
        for ch in db_channels:
            if hasattr(ch, 'url'):
                urls.add(ch.url)
            elif isinstance(ch, dict):
                urls.add(ch.get('url', ''))
    except Exception as e:
        logger.warning(f"[Scraper] 获取数据库频道失败: {e}")

    urls = [u for u in urls if u]  # 过滤空值
    logger.info(f"[Scraper] 开始抓取 {len(urls)} 个频道, max_new={max_new}")

    for channel_url in urls:
        channel_name = get_channel_name_from_url(channel_url)
        try:
            count = scrape_channel(channel_url, seen, save_callback, max_new=max_new)
            total_new += count
            channel_stats[channel_name] = {'new': count}
            logger.info(f"[Scraper] [{channel_name}] 完成，新增 {count} 条")
        except Exception as e:
            logger.error(f"[Scraper] [{channel_name}] 出错: {e}")
            channel_stats[channel_name] = {'new': 0, 'error': str(e)}

    save_seen_messages(seen)
    return total_new, channel_stats


def scrape_channel_history(channel_url, save_callback, max_count=500):
    """
    抓取指定频道的历史消息（用于频道首次绑定时的批量回填）
    save_callback: func(news_id, title, content, tags, url, message_id, source) -> bool
    max_count: 最多抓取多少条历史消息
    """
    seen = set()  # 历史回填不用 seen 缓存
    channel_name = get_channel_name_from_url(channel_url)
    logger.info(f"[Scraper] [{channel_name}] 开始历史回填，目标 {max_count} 条")

    try:
        count = scrape_channel(
            channel_url,
            seen,
            save_callback,
            max_new=max_count,
            scrape_all_history=True
        )
        logger.info(f"[Scraper] [{channel_name}] 历史回填完成，新增 {count} 条")
        return count
    except Exception as e:
        logger.error(f"[Scraper] [{channel_name}] 历史回填出错: {e}", exc_info=True)
        return 0