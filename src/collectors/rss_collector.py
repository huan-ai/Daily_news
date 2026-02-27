"""
RSS数据收集器

收集RSS订阅源的最新内容
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from email.utils import parsedate_to_datetime
import httpx
import feedparser

from .base import BaseCollector, NewsItem, NewsCategory
from ..utils.logger import log


class RSSCollector(BaseCollector):
    """
    RSS数据收集器
    
    收集RSS订阅源的最新文章
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("RSS", config)
        self.feeds = self.config.get("feeds", [])
        self.timeout = self.config.get("timeout", 30)
        
    async def collect(self) -> List[NewsItem]:
        """
        收集RSS数据
        
        Returns:
            收集到的新闻列表
        """
        items = []
        
        for feed_config in self.feeds:
            if not feed_config.get("enabled", True):
                continue
            
            feed_items = await self._collect_feed(feed_config)
            items.extend(feed_items)
            
            await asyncio.sleep(2)  # 请求间隔
        
        log.info(f"RSS收集完成，共{len(items)}条")
        return items
    
    async def _collect_feed(self, feed_config: Dict[str, Any]) -> List[NewsItem]:
        """
        收集单个RSS源
        
        Args:
            feed_config: RSS源配置
            
        Returns:
            新闻列表
        """
        items = []
        name = feed_config.get("name", "Unknown")
        url = feed_config.get("url", "")
        
        if not url:
            return items
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers={
                    "User-Agent": "DailyNews/1.0 RSS Reader"
                })
                
                if response.status_code != 200:
                    log.warning(f"RSS源 {name} 请求失败: {response.status_code}")
                    return items
                
                # 解析RSS
                feed = feedparser.parse(response.text)
                
                for entry in feed.entries[:15]:  # 限制每个源的条目数
                    try:
                        item = self._parse_entry(entry, name)
                        if item and self.validate(item):
                            items.append(item)
                    except Exception as e:
                        log.debug(f"解析RSS条目失败: {e}")
                        continue
                        
        except Exception as e:
            log.error(f"RSS源 {name} 收集失败: {e}")
        
        return items
    
    def _parse_entry(self, entry: Any, source_name: str) -> Optional[NewsItem]:
        """
        解析RSS条目
        
        Args:
            entry: RSS条目
            source_name: 源名称
            
        Returns:
            新闻条目
        """
        # 获取标题
        title = entry.get("title", "").strip()
        if not title:
            return None
        
        # 获取链接
        link = entry.get("link", "")
        
        # 获取内容
        content = ""
        if entry.get("content"):
            content = entry.content[0].get("value", "")
        elif entry.get("summary"):
            content = entry.summary
        elif entry.get("description"):
            content = entry.description
        
        # 清理HTML标签
        from bs4 import BeautifulSoup
        if content:
            soup = BeautifulSoup(content, "html.parser")
            content = soup.get_text(separator="\n", strip=True)
        
        # 获取发布时间
        published_at = None
        if entry.get("published_parsed"):
            try:
                published_at = datetime(*entry.published_parsed[:6])
            except:
                pass
        elif entry.get("updated_parsed"):
            try:
                published_at = datetime(*entry.updated_parsed[:6])
            except:
                pass
        
        # 获取作者
        author = entry.get("author", None)
        
        # 获取标签
        tags = []
        if entry.get("tags"):
            for tag in entry.tags:
                if isinstance(tag, dict):
                    tags.append(tag.get("term", ""))
                elif isinstance(tag, str):
                    tags.append(tag)
        
        # 分类 (基于关键词)
        category = self._categorize(title, content)
        
        return NewsItem(
            title=title,
            content=content[:2000] if content else "",  # 限制长度
            url=link,
            source=source_name,
            published_at=published_at,
            category=category,
            tags=tags[:5],  # 限制标签数量
            author=author
        )
    
    def _categorize(self, title: str, content: str) -> NewsCategory:
        """
        根据内容分类
        
        Args:
            title: 标题
            content: 内容
            
        Returns:
            分类
        """
        text = (title + " " + content).lower()
        
        # 分类关键词映射
        category_keywords = {
            NewsCategory.MODEL_PROGRESS: ["gpt", "claude", "gemini", "llama", "qwen", "llm", "model"],
            NewsCategory.MULTIMODAL: ["multimodal", "vision", "image", "video", "audio", "多模态"],
            NewsCategory.AGENT_ECOSYSTEM: ["agent", "tool", "function calling", "mcp", "智能体"],
            NewsCategory.OPENSOURCE: ["open source", "github", "release", "开源"],
            NewsCategory.BUSINESS: ["launch", "product", "company", "funding", "发布", "产品"]
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in text for kw in keywords):
                return category
        
        return NewsCategory.OTHER


# 测试入口
if __name__ == "__main__":
    async def test():
        config = {
            "feeds": [
                {
                    "name": "Hacker News - AI",
                    "url": "https://hnrss.org/newest?q=AI+OR+LLM",
                    "enabled": True
                }
            ],
            "timeout": 30
        }
        
        collector = RSSCollector(config)
        items = await collector.collect()
        
        print(f"收集到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"- {item.title}")
            print(f"  分类: {item.category.value}")
            print()
    
    asyncio.run(test())
