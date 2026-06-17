#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 新闻总结模块
- 使用 OpenAI 兼容 API（如 deepseek）生成每日财经新闻总结
- 调用 https://api.baipiao.eu.org/v1 上的模型
- 支持按分类组织新闻，生成结构化总结
- 支持基于多日总结生成3天/7天综合总结
"""

import os
import json
import logging
import httpx
import warnings
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import config

logger = logging.getLogger(__name__)

# 抑制 SSL 警告（verify=False 时需要）
warnings.filterwarnings("ignore", category=Warning, module="httpx")
warnings.filterwarnings("ignore", category=Warning, module="urllib3")
warnings.filterwarnings("ignore", category=Warning, module="httpcore")

# ============ AI 客户端配置 ============

def _load_ai_settings() -> dict:
    """
    从 config + 数据库加载 AI 设置（数据库优先覆盖）
    返回: {api_key, base_url, model}
    """
    api_key = config.AI_API_KEY or ""
    base_url = (config.AI_BASE_URL or "").rstrip("/")
    model = config.AI_MODEL or ""

    # 始终尝试从数据库读取，如有值则覆盖 config
    try:
        from database import get_all_settings
        db_settings = get_all_settings()
        if db_settings.get("ai_api_key"):
            api_key = db_settings["ai_api_key"]
        if db_settings.get("ai_base_url"):
            base_url = db_settings["ai_base_url"].rstrip("/")
        if db_settings.get("ai_model"):
            model = db_settings["ai_model"]
    except Exception as e:
        logger.debug(f"从数据库读取 AI 设置失败（非严重错误）: {e}")

    return {"api_key": api_key, "base_url": base_url, "model": model}


def _make_httpx_client(base_url: str, api_key: str) -> httpx.Client:
    """创建一个 httpx 客户端，使用 verify=False 绕过 SSL 问题"""
    client = httpx.Client(
        base_url=base_url,
        timeout=120.0,
        verify=False,  # 某些 Cloudflare API 需要绕过 SSL 验证
        headers={
            "Authorization": f"Bearer {api_key}" if api_key else "",
            "Content-Type": "application/json"
        }
    )
    return client


class AIClient:
    """OpenAI 兼容 API 客户端（每次请求实时读取最新设置）"""

    def __init__(self, use_db_settings: bool = True):
        """
        Args:
            use_db_settings: 是否从数据库读取设置（作为 config 的补充/覆盖）
        """
        self._settings = _load_ai_settings() if use_db_settings else {
            "api_key": config.AI_API_KEY or "",
            "base_url": (config.AI_BASE_URL or "").rstrip("/"),
            "model": config.AI_MODEL or "",
        }
        self.api_key = self._settings["api_key"]
        self.base_url = self._settings["base_url"]
        self.model = self._settings["model"]
        self.client = _make_httpx_client(self.base_url, self.api_key)

    def chat(self, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 4096) -> Optional[str]:
        """调用 AI 对话接口"""
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            logger.info(f"🤖 [AI] 正在调用 AI 模型: {self.model}")
            logger.info(f"📡 [AI] API 地址: {self.base_url}/chat/completions")
            response = self.client.post("/chat/completions", json=payload)

            if response.status_code != 200:
                logger.error(f"❌ [AI] API 返回错误: {response.status_code} - {response.text[:200]}")
                return None

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info(f"✅ [AI] AI 响应成功，长度: {len(content)} 字符")
            return content

        except httpx.TimeoutException:
            logger.error("❌ [AI] API 请求超时")
            return None
        except Exception as e:
            logger.error(f"❌ [AI] 请求失败: {str(e)}")
            return None

    def test_connection(self) -> bool:
        """测试 AI API 连接"""
        try:
            response = self.client.get("/models")
            if response.status_code == 200:
                models = response.json().get("data", [])
                logger.info(f"✅ [AI] API 连接成功，可用模型数: {len(models)}")
                for m in models[:5]:
                    logger.info(f"   - 模型: {m.get('id')}")
                return True
            else:
                logger.warning(f"⚠️ [AI] API 连接异常: {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"⚠️ [AI] API 连接测试失败: {e}")
            return False


def generate_daily_summary(
    news_items: List[Dict],
    time_range: str = "今日",
    categorized_news: Optional[Dict[str, List[Dict]]] = None,
    date_label: Optional[str] = None
) -> Optional[str]:
    """
    根据新闻数据生成 AI 总结（支持不同时间范围，支持按分类组织）

    Args:
        news_items: 新闻列表，每项包含 title, content, tags, source 等字段
        time_range: 时间范围描述（"今日"、"近3天"、"近1周"）
        categorized_news: 按标签分类后的新闻字典 {tag: [items]}
        date_label: 日期标签（如 "2026-06-16"），None 则用当天

    Returns:
        AI 生成的总结文本
    """
    if not config.AI_API_KEY:
        logger.warning("⚠️ [AI] AI_API_KEY 未配置，跳过 AI 总结")
        return None

    if not news_items:
        logger.warning("⚠️ [AI] 没有新闻数据，无法生成总结")
        return None

    client = AIClient()

    # 构建新闻摘要文本（不限制数量，全部传入）
    news_text = ""
    if categorized_news:
        for tag in sorted(categorized_news.keys()):
            items = categorized_news[tag]
            news_text += f"\n=== {tag} ==="
            for item in items:
                title = item.get('title', '无标题')
                content = item.get('content', '')[:150]
                source = item.get('source', '未知')
                news_text += f"\n【{tag}】标题: {title}\n内容: {content}\n来源: {source}\n"
    else:
        for i, item in enumerate(news_items, 1):
            title = item.get('title', '无标题')
            content = item.get('content', '')[:200]
            tags = item.get('tags', [])
            if isinstance(tags, str):
                tags = tags.split(',')
            tags_str = ', '.join(tags) if tags else '财经'
            source = item.get('source', '未知')
            news_text += f"\n【新闻{i}】标题: {title}\n内容: {content}\n标签: {tags_str}\n来源: {source}\n"

    # 收集标签和来源列表
    tag_set = set()
    source_set = set()
    for item in news_items:
        tags = item.get('tags', [])
        if isinstance(tags, str):
            tags = tags.split(',')
        for tag in tags:
            tag = tag.strip()
            if tag:
                tag_set.add(tag)
        src = item.get('source', '')
        if src:
            source_set.add(src)

    # 使用 date_label 或当前日期
    if date_label:
        current_date_str = date_label
        day_of_week = datetime.now().strftime("%A")
        current_date_str = f"{date_label} {day_of_week}"
    else:
        current_date_str = datetime.now().strftime("%Y-%m-%d %A")

    system_prompt = f"""你是一位专业的财经新闻分析师。请根据以下{time_range}的财经新闻数据，生成一份结构化的财经总结报告。

报告格式要求（用Markdown格式输出）：

---
## 📊 {time_range}财经总结
📅 日期：{current_date_str}

### 一、📈 市场概览
简要概括{time_range}财经市场的整体走势和主要情绪。

### 二、🔥 热门领域 TOP 3
1. **领域一** - 重要新闻简述
2. **领域二** - 重要新闻简述  
3. **领域三** - 重要新闻简述

### 三、💡 重点新闻解读
挑选 3-5 条最重要的新闻进行简要解读

### 四、🔮 趋势展望
基于{time_range}新闻对未来趋势的简要分析

### 五、📋 数据摘要
- 新闻总数：{len(news_items)} 条
- 涵盖领域：{'、'.join(sorted(tag_set))[:100]}
- 主要来源：{'、'.join(sorted(source_set))[:100]}

---

请用**中文**回答，语言精炼专业，每条解读不超过100字。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"请根据以下{time_range}财经新闻数据生成总结报告：\n{news_text}"}
    ]

    logger.info(f"📝 [AI] 开始生成 {time_range} 财经总结，共 {len(news_items)} 条新闻")
    result = client.chat(messages)

    if result:
        logger.info(f"✅ [AI] {time_range} 总结生成成功")
        return result
    else:
        logger.error(f"❌ [AI] {time_range} 总结生成失败")
        return None


def generate_merged_summary(
    daily_summaries: List[Dict],
    time_range: str = "近3天",
    date_label: Optional[str] = None
) -> Optional[str]:
    """
    根据多日的每日总结(1d)生成综合总结（用于3天/7天）
    
    Args:
        daily_summaries: 每日总结列表，每项包含 date_label, content, news_count
        time_range: 时间范围描述（"近3天"、"近1周"）
        date_label: 日期标签
    
    Returns:
        AI 生成的综合总结文本
    """
    if not config.AI_API_KEY:
        logger.warning("⚠️ [AI] AI_API_KEY 未配置，跳过 AI 总结")
        return None

    if not daily_summaries:
        logger.warning("⚠️ [AI] 没有每日总结数据，无法生成综合总结")
        return None

    client = AIClient()

    # 构建每日总结文本
    summaries_text = ""
    total_count = 0
    for i, s in enumerate(daily_summaries, 1):
        date = s.get('date_label', f'第{i}天')
        content = s.get('content', '无内容')[:2000]  # 每篇取前2000字符
        count = s.get('news_count', 0)
        total_count += count
        summaries_text += f"\n=== 📅 {date} 财经总结 ===\n"
        summaries_text += f"{content}\n"
        summaries_text += f"---该日新闻数: {count} 条---\n"

    if date_label is None:
        date_label = datetime.now().strftime("%Y-%m-%d")

    system_prompt = f"""你是一位专业的财经新闻分析师。请根据以下多日财经总结（每日一篇），生成一份{time_range}的综合财经总结报告。

要求：
1. 综合多日的市场变化，提炼出这{time_range}的整体走势和趋势
2. 按主题分类（如政策、股市、行业等）组织内容，而不是按天罗列
3. 突出{time_range}内最重大的事件和持续性的热点
4. 分析{time_range}的趋势变化和发展脉络

报告格式要求（用Markdown格式输出）：

---
## 📊 {time_range}财经综合总结
📅 日期：{date_label}

### 一、📈 市场整体回顾
概括{time_range}的市场整体表现和主要趋势

### 二、🔥 重要主题分类
#### 1️⃣ 主题一
- 事件脉络与关键点

#### 2️⃣ 主题二
- 事件脉络与关键点

#### 3️⃣ 主题三
- 事件脉络与关键点

### 三、💡 重点事件解读
挑选 3-5 个{time_range}最重要的跨日事件进行解读

### 四、🔮 趋势展望
基于{time_range}变化对未来趋势的分析

### 五、📋 数据摘要
- 涵盖天数：{len(daily_summaries)} 天
- 新闻总数：{total_count} 条
- 覆盖日期：{daily_summaries[0].get('date_label', '')} ~ {daily_summaries[-1].get('date_label', '')}

---

请用**中文**回答，语言精炼专业，按主题分类（不要按天分类），展现连续性和趋势变化。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"请根据以下每日财经总结生成{time_range}综合报告：\n{summaries_text}"}
    ]

    logger.info(f"📝 [AI] 开始生成 {time_range} 综合总结，基于 {len(daily_summaries)} 天每日总结")
    result = client.chat(messages)

    if result:
        logger.info(f"✅ [AI] {time_range} 综合总结生成成功")
        return result
    else:
        logger.error(f"❌ [AI] {time_range} 综合总结生成失败")
        return None


def generate_news_analysis(news_item: Dict) -> Optional[str]:
    """
    对单条新闻进行 AI 深度解读

    Args:
        news_item: 包含 title, content, tags 等字段的新闻字典

    Returns:
        AI 生成的解读文本
    """
    if not config.AI_API_KEY:
        return None

    client = AIClient()

    title = news_item.get('title', '无标题')
    content = news_item.get('content', '无内容')
    tags = news_item.get('tags', [])
    if isinstance(tags, str):
        tags = tags.split(',')
    tags_str = ', '.join(tags) if tags else '财经'

    messages = [
        {"role": "system", "content": "你是一位专业的财经分析师。请对以下财经新闻进行简要解读（100-150字），分析其市场影响和投资启示。"},
        {"role": "user", "content": f"新闻标题：{title}\n标签：{tags_str}\n内容：{content}\n\n请给出专业解读："}
    ]

    return client.chat(messages, max_tokens=1024)


def list_available_models() -> List[Dict]:
    """获取可用模型列表"""
    try:
        client = httpx.Client(
            base_url=config.AI_BASE_URL.rstrip('/'),
            timeout=10.0,
            verify=False
        )
        response = client.get("/models")
        if response.status_code == 200:
            return response.json().get("data", [])
        return []
    except Exception as e:
        logger.error(f"❌ [AI] 获取模型列表失败: {e}")
        return []
