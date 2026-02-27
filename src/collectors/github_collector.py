"""
GitHub数据收集器

收集GitHub上的热门AI项目和最新动态
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup

from .base import BaseCollector, NewsItem, NewsCategory
from ..utils.logger import log


class GitHubCollector(BaseCollector):
    """
    GitHub数据收集器
    
    收集GitHub Trending和指定仓库的最新动态
    """
    
    TRENDING_URL = "https://github.com/trending"
    API_BASE = "https://api.github.com"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("GitHub", config)
        self.topics = self.config.get("topics", ["artificial-intelligence", "llm"])
        self.repos = self.config.get("repositories", [])
        self.since = self.config.get("since", "daily")
        
    async def collect(self) -> List[NewsItem]:
        """
        收集GitHub数据
        
        Returns:
            收集到的新闻列表
        """
        items = []
        
        # 收集Trending项目
        trending_items = await self._collect_trending()
        items.extend(trending_items)
        
        # 收集指定仓库的最新release
        if self.repos:
            repo_items = await self._collect_repos()
            items.extend(repo_items)
        
        log.info(f"GitHub收集完成，共{len(items)}条")
        return items
    
    async def _collect_trending(self) -> List[NewsItem]:
        """
        收集GitHub Trending
        
        Returns:
            Trending项目列表
        """
        items = []
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # 收集各个主题的trending
                for topic in self.topics[:3]:  # 限制主题数量
                    url = f"{self.TRENDING_URL}?since={self.since}&spoken_language_code=&topic={topic}"
                    
                    response = await client.get(url, headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                    })
                    
                    if response.status_code == 200:
                        topic_items = await self._parse_trending_page(client, response.text, topic)
                        items.extend(topic_items[:5])  # 每个主题取前5个
                    
                    await asyncio.sleep(2)  # 请求间隔
                
                # 收集通用trending（所有语言）
                response = await client.get(
                    f"{self.TRENDING_URL}?since={self.since}",
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
                )
                
                if response.status_code == 200:
                    general_items = await self._parse_trending_page(client, response.text, "general")
                    # 过滤AI相关项目
                    ai_keywords = ["ai", "llm", "gpt", "model", "ml", "deep", "neural", "agent"]
                    for item in general_items[:20]:
                        title_lower = item.title.lower()
                        if any(kw in title_lower for kw in ai_keywords):
                            items.append(item)
                            
        except Exception as e:
            log.error(f"GitHub Trending收集失败: {e}")
        
        return items
    
    async def _fetch_readme_snippet(self, client: httpx.AsyncClient, repo_path: str) -> str:
        """
        获取仓库 README 的前 800 字符作为项目概要
        
        Args:
            client: HTTP客户端
            repo_path: 仓库路径 (owner/repo)
            
        Returns:
            README 摘要文本
        """
        try:
            url = f"{self.API_BASE}/repos/{repo_path}/readme"
            response = await client.get(url, headers={
                "Accept": "application/vnd.github.v3.raw",
                "User-Agent": "DailyNews/1.0"
            })
            if response.status_code == 200:
                readme_text = response.text
                # 去掉 markdown 图片/badge 行，只保留文字
                import re
                lines = readme_text.split("\n")
                clean_lines = []
                for line in lines:
                    stripped = line.strip()
                    # 跳过纯图片行、badge行、空HTML标签行
                    if stripped.startswith("![") or stripped.startswith("<img") or stripped.startswith("[!["):
                        continue
                    if stripped.startswith("<p align") or stripped.startswith("</p>"):
                        continue
                    clean_lines.append(line)
                clean_text = "\n".join(clean_lines).strip()
                return clean_text[:800]
        except Exception as e:
            log.debug(f"获取 {repo_path} README 失败: {e}")
        return ""
    
    async def _parse_trending_page(self, client: httpx.AsyncClient, html: str, topic: str) -> List[NewsItem]:
        """
        解析Trending页面，并为每个仓库获取 README 摘要
        
        Args:
            client: HTTP客户端
            html: 页面HTML
            topic: 主题
            
        Returns:
            新闻列表
        """
        items = []
        soup = BeautifulSoup(html, "lxml")
        
        # 查找仓库列表
        repo_list = soup.select("article.Box-row")
        
        for repo in repo_list:
            try:
                # 仓库名称和链接
                h2 = repo.select_one("h2 a")
                if not h2:
                    continue
                
                repo_path = h2.get("href", "").strip("/")
                repo_name = repo_path.replace("/", " / ")
                repo_url = f"https://github.com/{repo_path}"
                
                # 描述
                desc_elem = repo.select_one("p")
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                
                # 语言
                lang_elem = repo.select_one("[itemprop='programmingLanguage']")
                language = lang_elem.get_text(strip=True) if lang_elem else "Unknown"
                
                # Star数
                star_elem = repo.select_one("a[href$='/stargazers']")
                stars = star_elem.get_text(strip=True) if star_elem else "0"
                
                # 今日新增Star
                today_stars_elem = repo.select_one("span.d-inline-block.float-sm-right")
                today_stars = today_stars_elem.get_text(strip=True) if today_stars_elem else ""
                
                # 获取 README 摘要
                readme_snippet = await self._fetch_readme_snippet(client, repo_path)
                await asyncio.sleep(0.5)  # API 请求间隔
                
                # 构建丰富的中文内容
                content = f"""📌 项目：{repo_name}
🔗 地址：{repo_url}
📝 简介：{description}
💻 语言：{language} | ⭐ {stars} | 📈 今日 +{today_stars}
🏷️ 主题：{topic}

📄 项目详情：
{readme_snippet if readme_snippet else '暂无详细说明'}
"""
                
                item = NewsItem(
                    title=f"🔥 GitHub热门: {repo_name}",
                    content=content.strip(),
                    url=repo_url,
                    source="GitHub Trending",
                    published_at=datetime.now(),
                    category=NewsCategory.OPENSOURCE,
                    tags=["github", "trending", topic, language.lower()],
                    extra={
                        "repo_path": repo_path,
                        "language": language,
                        "stars": stars,
                        "today_stars": today_stars,
                        "topic": topic,
                        "description": description,
                        "readme_snippet": readme_snippet
                    }
                )
                
                items.append(item)
                
            except Exception as e:
                log.debug(f"解析仓库失败: {e}")
                continue
        
        return items
    
    async def _collect_repos(self) -> List[NewsItem]:
        """
        收集指定仓库的最新发布
        
        Returns:
            仓库动态列表
        """
        items = []
        
        async with httpx.AsyncClient(timeout=30) as client:
            for repo in self.repos[:10]:  # 限制仓库数量
                try:
                    # 获取最新release
                    url = f"{self.API_BASE}/repos/{repo}/releases/latest"
                    response = await client.get(url, headers={
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "DailyNews/1.0"
                    })
                    
                    if response.status_code == 200:
                        release = response.json()
                        
                        # 检查发布时间
                        published_at = datetime.fromisoformat(
                            release["published_at"].replace("Z", "+00:00")
                        )
                        
                        # 只收集最近24小时的发布
                        from datetime import timedelta, timezone
                        if datetime.now(timezone.utc) - published_at > timedelta(hours=48):
                            continue
                        
                        content = f"""
**版本**: {release.get('tag_name', 'N/A')}
**名称**: {release.get('name', 'N/A')}
**发布时间**: {published_at.strftime('%Y-%m-%d %H:%M')}

**更新内容**:
{release.get('body', '无描述')[:500]}
"""
                        
                        item = NewsItem(
                            title=f"📦 {repo} 发布新版本 {release.get('tag_name', '')}",
                            content=content.strip(),
                            url=release.get("html_url", f"https://github.com/{repo}"),
                            source=f"GitHub - {repo}",
                            published_at=published_at.replace(tzinfo=None),
                            category=NewsCategory.OPENSOURCE,
                            tags=["github", "release", repo.split("/")[0]],
                            extra={
                                "repo": repo,
                                "version": release.get("tag_name"),
                                "prerelease": release.get("prerelease", False)
                            }
                        )
                        
                        items.append(item)
                    
                    await asyncio.sleep(1)  # API请求间隔
                    
                except Exception as e:
                    log.debug(f"获取仓库 {repo} release失败: {e}")
                    continue
        
        return items


# 测试入口
if __name__ == "__main__":
    async def test():
        config = {
            "topics": ["artificial-intelligence", "llm"],
            "repositories": ["langchain-ai/langchain", "openai/openai-python"],
            "since": "daily"
        }
        
        collector = GitHubCollector(config)
        items = await collector.collect()
        
        print(f"收集到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"- {item.title}")
            print(f"  URL: {item.url}")
            print()
    
    asyncio.run(test())
