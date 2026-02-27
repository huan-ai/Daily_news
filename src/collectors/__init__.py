"""
数据收集器模块
"""

from .base import BaseCollector, NewsItem
from .github_collector import GitHubCollector
from .rss_collector import RSSCollector
from .web_collector import WebCollector

__all__ = [
    "BaseCollector",
    "NewsItem",
    "GitHubCollector",
    "RSSCollector",
    "WebCollector"
]
