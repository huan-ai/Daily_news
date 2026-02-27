"""
数据收集器基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class NewsCategory(Enum):
    """新闻分类"""
    MODEL_PROGRESS = "大模型进展"
    MULTIMODAL = "多模态突破"
    AGENT_ECOSYSTEM = "智能体生态"
    OPENSOURCE = "开源动态"
    BUSINESS = "商业应用"
    OTHER = "其他"


@dataclass
class NewsItem:
    """
    新闻条目数据类
    """
    # 基础信息
    title: str
    content: str
    url: str
    source: str
    
    # 时间信息
    published_at: Optional[datetime] = None
    collected_at: datetime = field(default_factory=datetime.now)
    
    # 分类和标签
    category: NewsCategory = NewsCategory.OTHER
    tags: List[str] = field(default_factory=list)
    
    # 元数据
    author: Optional[str] = None
    summary: Optional[str] = None
    importance: str = "中"  # 高/中/低
    
    # 额外数据
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "collected_at": self.collected_at.isoformat(),
            "category": self.category.value,
            "tags": self.tags,
            "author": self.author,
            "summary": self.summary,
            "importance": self.importance,
            "extra": self.extra
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NewsItem":
        """从字典创建"""
        data = data.copy()
        if data.get("published_at"):
            data["published_at"] = datetime.fromisoformat(data["published_at"])
        if data.get("collected_at"):
            data["collected_at"] = datetime.fromisoformat(data["collected_at"])
        if data.get("category"):
            data["category"] = NewsCategory(data["category"])
        return cls(**data)


class BaseCollector(ABC):
    """
    数据收集器基类
    
    所有具体收集器需要继承此类并实现collect方法
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化收集器
        
        Args:
            name: 收集器名称
            config: 配置字典
        """
        self.name = name
        self.config = config or {}
    
    @abstractmethod
    async def collect(self) -> List[NewsItem]:
        """
        收集数据
        
        Returns:
            收集到的新闻列表
        """
        pass
    
    def validate(self, item: NewsItem) -> bool:
        """
        验证新闻条目是否有效
        
        Args:
            item: 新闻条目
            
        Returns:
            是否有效
        """
        # 基础验证：必须有标题和内容
        if not item.title or not item.title.strip():
            return False
        if not item.content or len(item.content.strip()) < 10:
            return False
        return True
    
    def filter_by_date(self, items: List[NewsItem], max_age_hours: int = 24) -> List[NewsItem]:
        """
        按时间过滤新闻
        
        Args:
            items: 新闻列表
            max_age_hours: 最大年龄(小时)
            
        Returns:
            过滤后的新闻列表
        """
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        result = []
        
        for item in items:
            if item.published_at is None:
                # 没有发布时间的保留
                result.append(item)
            elif item.published_at >= cutoff:
                result.append(item)
        
        return result
