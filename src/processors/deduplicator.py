"""
内容去重模块
"""

import hashlib
from typing import List, Set, Dict
from difflib import SequenceMatcher

from ..collectors.base import NewsItem
from ..utils.logger import log


class Deduplicator:
    """
    新闻去重器
    
    基于标题相似度和内容hash进行去重
    """
    
    def __init__(self, similarity_threshold: float = 0.7):
        """
        初始化去重器
        
        Args:
            similarity_threshold: 相似度阈值 (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self._seen_hashes: Set[str] = set()
        self._seen_titles: List[str] = []
    
    def deduplicate(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        对新闻列表进行去重
        
        Args:
            items: 原始新闻列表
            
        Returns:
            去重后的新闻列表
        """
        unique_items = []
        
        for item in items:
            if self._is_duplicate(item):
                log.debug(f"去重: {item.title[:50]}...")
                continue
            
            unique_items.append(item)
            self._add_to_seen(item)
        
        log.info(f"去重完成: {len(items)} -> {len(unique_items)}")
        return unique_items
    
    def _is_duplicate(self, item: NewsItem) -> bool:
        """
        检查是否为重复内容
        
        Args:
            item: 新闻条目
            
        Returns:
            是否重复
        """
        # 检查内容hash
        content_hash = self._compute_hash(item.content)
        if content_hash in self._seen_hashes:
            return True
        
        # 检查标题相似度
        for seen_title in self._seen_titles:
            similarity = self._compute_similarity(item.title, seen_title)
            if similarity >= self.similarity_threshold:
                return True
        
        return False
    
    def _add_to_seen(self, item: NewsItem):
        """
        添加到已见集合
        
        Args:
            item: 新闻条目
        """
        content_hash = self._compute_hash(item.content)
        self._seen_hashes.add(content_hash)
        self._seen_titles.append(item.title)
    
    def _compute_hash(self, content: str) -> str:
        """
        计算内容hash
        
        Args:
            content: 内容
            
        Returns:
            hash值
        """
        # 标准化内容
        normalized = content.lower().strip()
        # 移除多余空白
        normalized = " ".join(normalized.split())
        
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度 (0-1)
        """
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def reset(self):
        """
        重置去重器状态
        """
        self._seen_hashes.clear()
        self._seen_titles.clear()
