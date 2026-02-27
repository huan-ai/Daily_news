"""
新闻分析模块

使用LLM进行深度分析，当LLM不可用时自动生成高质量的中文日报
"""

import asyncio
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

from ..collectors.base import NewsItem, NewsCategory
from ..utils.logger import log
from ..utils.llm_client import GeminiClient


class NewsAnalyzer:
    """
    新闻分析器
    
    使用Gemini对收集的新闻进行深度分析
    """
    
    def __init__(self, llm_client: Optional[GeminiClient] = None):
        self.llm = llm_client or GeminiClient()
    
    async def summarize_item(self, item: NewsItem) -> str:
        try:
            summary = await self.llm.summarize(item.content)
            item.summary = summary
            return summary
        except Exception as e:
            log.error(f"生成摘要失败: {e}")
            return item.content[:200]
    
    async def analyze_news(self, items: List[NewsItem]) -> str:
        if not items:
            return "今日暂无重要AI行业动态。"
        
        news_text = self._format_news_for_analysis(items)
        
        try:
            analysis = await self.llm.analyze(news_text)
            return analysis
        except Exception as e:
            log.error(f"深度分析失败: {e}")
            return self._fallback_analysis(items)
    
    def _format_news_for_analysis(self, items: List[NewsItem]) -> str:
        grouped: Dict[str, List[NewsItem]] = defaultdict(list)
        for item in items:
            grouped[item.category.value].append(item)
        
        lines = []
        for category, category_items in grouped.items():
            lines.append(f"\n## {category}")
            for i, item in enumerate(category_items[:5], 1):
                lines.append(f"\n### {i}. {item.title}")
                lines.append(f"来源: {item.source}")
                if item.url:
                    lines.append(f"链接: {item.url}")
                content_text = item.content[:1000] if item.content else ""
                lines.append(f"\n{content_text}")
                if item.extra:
                    if item.extra.get("description"):
                        lines.append(f"\n项目描述: {item.extra['description']}")
                    if item.extra.get("stars"):
                        lines.append(f"Star数: {item.extra['stars']}")
        return "\n".join(lines)
    
    # ===== 智能中文内容生成（无需 LLM） =====
    
    def _extract_clean_readme(self, readme: str, max_len: int = 400) -> str:
        """从 README 中提取干净的文字描述"""
        if not readme:
            return ""
        
        # 去掉 HTML 标签
        text = re.sub(r'<[^>]+>', '', readme)
        # 去掉 markdown 图片
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        # 去掉 markdown 链接但保留文字
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # 去掉标题符号
        text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
        # 去掉 badge/shield
        text = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', '', text)
        # 去掉多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        # 去掉首尾空白
        text = text.strip()
        
        # 取前 N 个字符，在句末截断
        if len(text) > max_len:
            cutoff = text[:max_len].rfind('.')
            if cutoff > max_len * 0.5:
                text = text[:cutoff + 1]
            else:
                cutoff = text[:max_len].rfind('\n')
                if cutoff > max_len * 0.5:
                    text = text[:cutoff]
                else:
                    text = text[:max_len] + "..."
        
        return text
    
    def _generate_project_intro(self, item: NewsItem) -> str:
        """
        为 GitHub 项目生成 githubdaily 风格的中文介绍
        
        格式参考：
        - 一句话概括
        - 核心亮点
        - 推荐理由
        """
        extra = item.extra or {}
        repo_path = extra.get("repo_path", "")
        description = extra.get("description", "")
        stars = extra.get("stars", "N/A")
        today_stars = extra.get("today_stars", "")
        language = extra.get("language", "")
        readme = extra.get("readme_snippet", "")
        url = item.url or f"https://github.com/{repo_path}"
        
        # 清理 README 文本
        readme_text = self._extract_clean_readme(readme, 300)
        
        lines = []
        
        # 项目名 + 热度
        lines.append(f"### 📌 [{repo_path}]({url})")
        lines.append("")
        
        # Stars 信息行
        star_info = f"⭐ **{stars}** Stars"
        if today_stars:
            # 清理 today_stars 文本
            ts = today_stars.replace("stars today", "").replace("star today", "").strip()
            star_info += f"  |  📈 今日新增 **{ts}**"
        if language and language != "Unknown":
            star_info += f"  |  💻 {language}"
        lines.append(star_info)
        lines.append("")
        
        # 一句话简介
        if description:
            lines.append(f"**简介**：{description}")
            lines.append("")
        
        # 项目详情（来自 README）
        if readme_text:
            lines.append(f"**项目详情**：{readme_text}")
            lines.append("")
        
        # 推荐理由 — 根据 star 增长和描述自动生成
        if today_stars:
            ts_clean = re.sub(r'[^\d,]', '', today_stars.replace(",", ""))
            try:
                ts_num = int(ts_clean) if ts_clean else 0
            except ValueError:
                ts_num = 0
            
            if ts_num > 500:
                lines.append(f"🔥 **推荐理由**：今日 Star 增长迅猛（+{ts_num}），社区关注度极高，值得重点关注。")
            elif ts_num > 100:
                lines.append(f"👍 **推荐理由**：今日新增 {ts_num} Stars，属于持续热门项目。")
        
        lines.append("")
        return "\n".join(lines)
    
    def _generate_news_item_cn(self, item: NewsItem, index: int) -> str:
        """
        将英文新闻条目转换为中文格式的简报
        """
        title = item.title or ""
        content = item.content or ""
        url = item.url or ""
        source = item.source or ""
        
        # 清理 HN 格式的内容
        clean_content = content
        clean_content = re.sub(r'Article URL:\s*\n\s*https?://\S+', '', clean_content)
        clean_content = re.sub(r'Comments URL:\s*\n\s*https?://\S+', '', clean_content)
        clean_content = re.sub(r'Points:\s*\d+', '', clean_content)
        clean_content = re.sub(r'#\s*Comments:\s*\d+', '', clean_content)
        clean_content = clean_content.strip()
        
        # 提取有用的内容摘要
        if clean_content and len(clean_content) > 20:
            brief = clean_content[:200].strip()
            if len(clean_content) > 200:
                brief += "..."
        else:
            brief = ""
        
        lines = []
        lines.append(f"**{index}. {title}**")
        if source:
            lines.append(f"*来源：{source}*")
        lines.append("")
        
        if brief:
            lines.append(f"> {brief}")
            lines.append("")
        
        if url:
            lines.append(f"🔗 [查看详情]({url})")
        lines.append("")
        
        return "\n".join(lines)
    
    def _fallback_analysis(self, items: List[NewsItem]) -> str:
        """
        降级分析 — 按 githubdaily / 机器之心风格生成中文内容
        """
        categories = {}
        for item in items:
            cat = item.category.value
            categories[cat] = categories.get(cat, 0) + 1
        
        # GitHub 项目
        github_items = [item for item in items if item.source == "GitHub Trending"]
        non_github_items = [item for item in items if item.source != "GitHub Trending"]
        
        lines = []
        
        # ===== GitHub 热门项目精选 =====
        if github_items:
            lines.append("## 🔥 GitHub 热门项目精选")
            lines.append("")
            lines.append(f"今日共有 **{len(github_items)}** 个AI相关项目登上 GitHub Trending，以下是最值得关注的项目：")
            lines.append("")
            
            for item in github_items[:5]:
                lines.append(self._generate_project_intro(item))
        
        # ===== 行业动态 =====
        if non_github_items:
            lines.append("## 📰 行业动态")
            lines.append("")
            
            for i, item in enumerate(non_github_items[:8], 1):
                lines.append(self._generate_news_item_cn(item, i))
        
        return "\n".join(lines)
    
    async def generate_report(
        self,
        items: List[NewsItem],
        analysis: str,
        date: Optional[datetime] = None
    ) -> str:
        date = date or datetime.now()
        date_str = date.strftime("%Y年%m月%d日")
        
        news_summary = self._prepare_summary(items)
        
        try:
            report = await self.llm.generate_report(
                date=date_str,
                news_summary=news_summary,
                analysis=analysis
            )
            return report
        except Exception as e:
            log.error(f"生成报告失败: {e}")
            return self._generate_fallback_report(items, analysis, date_str)
    
    def _prepare_summary(self, items: List[NewsItem]) -> str:
        lines = []
        sorted_items = sorted(items, key=lambda x: (
            0 if x.importance == "高" else (1 if x.importance == "中" else 2),
            x.category.value
        ))
        
        for item in sorted_items[:15]:
            lines.append(f"\n### 【{item.category.value}】{item.title}")
            lines.append(f"来源：{item.source}")
            if item.url:
                lines.append(f"链接：{item.url}")
            if item.content:
                lines.append(f"\n{item.content[:600]}")
            if item.summary:
                lines.append(f"\n摘要：{item.summary[:150]}")
        
        return "\n".join(lines)
    
    def _generate_fallback_report(
        self,
        items: List[NewsItem],
        analysis: str,
        date_str: str
    ) -> str:
        """
        生成高质量降级报告 — githubdaily / 机器之心风格
        """
        github_items = [item for item in items if item.source == "GitHub Trending"]
        non_github_items = [item for item in items if item.source != "GitHub Trending"]
        
        # 按分类统计
        categories = {}
        for item in items:
            cat = item.category.value
            categories[cat] = categories.get(cat, 0) + 1
        
        lines = [
            f"# 🤖 AI日报 | {date_str}",
            "",
            f"> 每日精选 AI 领域最值得关注的开源项目与行业动态",
            "",
        ]
        
        # ===== 今日速览 =====
        lines.append("## ✨ 今日速览")
        lines.append("")
        
        total = sum(categories.values())
        lines.append(f"今日共收录 **{total}** 条AI相关动态：")
        
        cat_parts = []
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            cat_parts.append(f"{cat}（{count}条）")
        lines.append("、".join(cat_parts) + "。")
        lines.append("")
        
        # 用前 3 个 GitHub 项目做亮点
        if github_items:
            for i, item in enumerate(github_items[:3], 1):
                extra = item.extra or {}
                desc = extra.get("description", "")
                repo_path = extra.get("repo_path", item.title)
                ts = extra.get("today_stars", "")
                ts_clean = re.sub(r'[^\d,]', '', ts) if ts else ""
                
                if desc:
                    lines.append(f"- 🔥 **{repo_path}**：{desc}（今日 +{ts_clean} ⭐）")
                else:
                    lines.append(f"- 🔥 **{repo_path}**（今日 +{ts_clean} ⭐）")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # ===== 分析内容 =====
        if analysis:
            lines.append(analysis)
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # ===== 📎 资源链接 =====
        lines.append("## 📎 今日资源汇总")
        lines.append("")
        
        if github_items:
            lines.append("**开源项目**：")
            for item in github_items[:6]:
                extra = item.extra or {}
                repo_path = extra.get("repo_path", "")
                stars = extra.get("stars", "")
                if item.url:
                    lines.append(f"- [{repo_path}]({item.url})（⭐ {stars}）")
            lines.append("")
        
        if non_github_items:
            lines.append("**延伸阅读**：")
            for item in non_github_items[:5]:
                if item.url:
                    title = item.title.replace("Show HN: ", "").replace("Ask HN: ", "")
                    lines.append(f"- [{title}]({item.url})")
            lines.append("")
        
        lines.extend([
            "---",
            "",
            f"*本日报由 AI 自动整理生成于{date_str}，追踪AI前沿动态。*",
            f"*关注我们，每日 20:00 准时推送！*"
        ])
        
        return "\n".join(lines)
