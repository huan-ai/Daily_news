"""
网页数据收集器

爬取官方博客等网页内容
"""

import asyncio
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup

from .base import BaseCollector, NewsItem, NewsCategory
from ..utils.logger import log


class WebCollector(BaseCollector):
    """
    网页数据收集器
    
    爬取官方博客、新闻页面等
    """
    
    # User-Agent列表
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("Web", config)
        self.sources = self.config.get("sources", {})
        self.timeout = self.config.get("timeout", 30)
        self.interval = self.config.get("request_interval", 5)
        
    def _get_headers(self) -> Dict[str, str]:
        """获取随机请求头"""
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
    async def collect(self) -> List[NewsItem]:
        """
        收集网页数据
        
        Returns:
            收集到的新闻列表
        """
        items = []
        
        for source_name, source_config in self.sources.items():
            if not source_config.get("enabled", True):
                continue
            
            source_items = await self._collect_source(source_name, source_config)
            items.extend(source_items)
            
            await asyncio.sleep(self.interval)  # 请求间隔
        
        log.info(f"网页收集完成，共{len(items)}条")
        return items
    
    async def _collect_source(self, name: str, config: Dict[str, Any]) -> List[NewsItem]:
        """
        收集单个来源
        
        Args:
            name: 来源名称
            config: 来源配置
            
        Returns:
            新闻列表
        """
        items = []
        
        # 收集博客
        if config.get("blog"):
            blog_items = await self._collect_blog(name, config["blog"])
            items.extend(blog_items)
        
        # 可扩展：收集其他类型的页面
        
        return items
    
    async def _collect_blog(self, source_name: str, blog_url: str) -> List[NewsItem]:
        """
        收集博客页面
        
        Args:
            source_name: 来源名称
            blog_url: 博客URL
            
        Returns:
            新闻列表
        """
        items = []
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(blog_url, headers=self._get_headers())
                
                if response.status_code != 200:
                    log.warning(f"博客 {source_name} 请求失败: {response.status_code}")
                    return items
                
                # 根据来源选择解析方法
                parser = self._get_parser(source_name)
                if parser:
                    items = parser(response.text, source_name, blog_url)
                else:
                    items = self._generic_parse(response.text, source_name, blog_url)
                    
        except Exception as e:
            log.error(f"博客 {source_name} 收集失败: {e}")
        
        return items
    
    def _get_parser(self, source_name: str):
        """
        获取特定来源的解析器
        
        Args:
            source_name: 来源名称
            
        Returns:
            解析函数或None
        """
        parsers = {
            "anthropic": self._parse_anthropic,
            "google": self._parse_google,
            "meta": self._parse_meta,
            "deepmind": self._parse_deepmind,
        }
        return parsers.get(source_name.lower())
    
    def _parse_anthropic(self, html: str, source_name: str, base_url: str) -> List[NewsItem]:
        """解析Anthropic博客"""
        items = []
        soup = BeautifulSoup(html, "lxml")
        
        # Anthropic博客文章列表
        articles = soup.select("article, .post-card, [class*='blog-post']")
        
        for article in articles[:10]:
            try:
                # 标题和链接
                title_elem = article.select_one("h2, h3, .title, [class*='title']")
                link_elem = article.select_one("a[href]")
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                link = link_elem.get("href", "") if link_elem else ""
                
                # 补全相对链接
                if link and not link.startswith("http"):
                    from urllib.parse import urljoin
                    link = urljoin(base_url, link)
                
                # 摘要
                summary_elem = article.select_one("p, .excerpt, .summary, [class*='description']")
                summary = summary_elem.get_text(strip=True) if summary_elem else ""
                
                # 日期
                date_elem = article.select_one("time, .date, [class*='date']")
                published_at = None
                if date_elem:
                    date_text = date_elem.get("datetime") or date_elem.get_text(strip=True)
                    published_at = self._parse_date(date_text)
                
                item = NewsItem(
                    title=f"🤖 {title}",
                    content=summary,
                    url=link or base_url,
                    source=f"Anthropic Blog",
                    published_at=published_at,
                    category=NewsCategory.MODEL_PROGRESS,
                    tags=["anthropic", "claude"],
                )
                
                if self.validate(item):
                    items.append(item)
                    
            except Exception as e:
                log.debug(f"解析文章失败: {e}")
                continue
        
        return items
    
    def _parse_google(self, html: str, source_name: str, base_url: str) -> List[NewsItem]:
        """解析Google AI博客"""
        items = []
        soup = BeautifulSoup(html, "lxml")
        
        articles = soup.select("article, .uni-blog-article, [class*='article']")
        
        for article in articles[:10]:
            try:
                title_elem = article.select_one("h2, h3, .title")
                link_elem = article.select_one("a[href]")
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                link = link_elem.get("href", "") if link_elem else base_url
                
                if link and not link.startswith("http"):
                    from urllib.parse import urljoin
                    link = urljoin(base_url, link)
                
                summary_elem = article.select_one("p, .snippet")
                summary = summary_elem.get_text(strip=True) if summary_elem else ""
                
                item = NewsItem(
                    title=f"🔍 {title}",
                    content=summary,
                    url=link,
                    source="Google AI Blog",
                    category=NewsCategory.MODEL_PROGRESS,
                    tags=["google", "gemini"],
                )
                
                if self.validate(item):
                    items.append(item)
                    
            except Exception as e:
                log.debug(f"解析文章失败: {e}")
                continue
        
        return items
    
    def _parse_meta(self, html: str, source_name: str, base_url: str) -> List[NewsItem]:
        """解析Meta AI博客"""
        return self._generic_parse(html, "Meta AI", base_url)
    
    def _parse_deepmind(self, html: str, source_name: str, base_url: str) -> List[NewsItem]:
        """解析DeepMind博客"""
        return self._generic_parse(html, "DeepMind", base_url)
    
    def _generic_parse(self, html: str, source_name: str, base_url: str) -> List[NewsItem]:
        """
        通用解析器
        
        尝试从任意页面提取文章列表
        """
        items = []
        soup = BeautifulSoup(html, "lxml")
        
        # 常见的文章容器选择器
        selectors = [
            "article",
            "[class*='post']",
            "[class*='article']",
            "[class*='blog']",
            "[class*='card']",
            ".news-item",
            ".list-item"
        ]
        
        for selector in selectors:
            articles = soup.select(selector)
            if len(articles) >= 3:  # 找到足够多的文章
                break
        else:
            articles = []
        
        for article in articles[:10]:
            try:
                # 查找标题
                title_elem = (
                    article.select_one("h1, h2, h3, h4") or
                    article.select_one("[class*='title']") or
                    article.select_one("a")
                )
                
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                if len(title) < 5:
                    continue
                
                # 查找链接
                link_elem = article.select_one("a[href]") or title_elem.find_parent("a")
                link = link_elem.get("href", "") if link_elem else ""
                
                if link and not link.startswith("http"):
                    from urllib.parse import urljoin
                    link = urljoin(base_url, link)
                
                # 查找摘要
                summary_elem = article.select_one("p")
                summary = summary_elem.get_text(strip=True) if summary_elem else ""
                
                item = NewsItem(
                    title=title,
                    content=summary or title,
                    url=link or base_url,
                    source=source_name,
                    category=NewsCategory.OTHER,
                    tags=[source_name.lower().replace(" ", "-")],
                )
                
                if self.validate(item):
                    items.append(item)
                    
            except Exception as e:
                continue
        
        return items
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        解析日期字符串
        
        Args:
            date_str: 日期字符串
            
        Returns:
            datetime对象或None
        """
        if not date_str:
            return None
        
        # 常见日期格式
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
        
        return None


# 测试入口
if __name__ == "__main__":
    async def test():
        config = {
            "sources": {
                "anthropic": {
                    "blog": "https://www.anthropic.com/news",
                    "enabled": True
                }
            },
            "timeout": 30,
            "request_interval": 3
        }
        
        collector = WebCollector(config)
        items = await collector.collect()
        
        print(f"收集到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"- {item.title}")
            print(f"  URL: {item.url}")
            print()
    
    asyncio.run(test())
