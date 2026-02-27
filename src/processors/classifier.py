"""
内容分类模块
"""

from typing import List, Dict
from collections import defaultdict

from ..collectors.base import NewsItem, NewsCategory
from ..utils.logger import log


class Classifier:
    """
    新闻分类器
    
    根据关键词对新闻进行分类
    """
    
    # 默认分类关键词
    DEFAULT_KEYWORDS = {
        NewsCategory.MODEL_PROGRESS: [
            "gpt", "claude", "gemini", "llama", "qwen", "deepseek",
            "大模型", "语言模型", "llm", "模型", "参数", "训练",
            "benchmark", "reasoning", "推理", "能力"
        ],
        NewsCategory.MULTIMODAL: [
            "multimodal", "多模态", "vision", "视觉", "图像", "image",
            "video", "视频", "audio", "语音", "音频", "sora",
            "图文", "视听", "v2t", "t2i"
        ],
        NewsCategory.AGENT_ECOSYSTEM: [
            "agent", "智能体", "tool", "工具", "function calling",
            "mcp", "自主", "autonomous", "workflow", "工作流",
            "computer use", "browser", "浏览器"
        ],
        NewsCategory.OPENSOURCE: [
            "开源", "open source", "github", "release", "发布",
            "apache", "mit", "license", "仓库", "repo",
            "huggingface", "模型权重", "开放"
        ],
        NewsCategory.BUSINESS: [
            "商业", "企业", "产品", "product", "launch", "上线",
            "融资", "funding", "估值", "收购", "合作",
            "api", "服务", "收费", "订阅"
        ]
    }
    
    def __init__(self, custom_keywords: Dict[str, List[str]] = None):
        """
        初始化分类器
        
        Args:
            custom_keywords: 自定义关键词映射
        """
        self.keywords = self.DEFAULT_KEYWORDS.copy()
        
        if custom_keywords:
            for category_name, words in custom_keywords.items():
                # 尝试匹配分类
                for cat in NewsCategory:
                    if cat.value == category_name:
                        if cat in self.keywords:
                            self.keywords[cat].extend(words)
                        else:
                            self.keywords[cat] = words
                        break
    
    def classify(self, item: NewsItem) -> NewsItem:
        """
        对单条新闻进行分类
        
        Args:
            item: 新闻条目
            
        Returns:
            分类后的新闻条目
        """
        # 如果已经分类过且不是OTHER，保留原分类
        if item.category != NewsCategory.OTHER:
            return item
        
        # 合并标题和内容进行分析
        text = f"{item.title} {item.content}".lower()
        
        # 统计各分类的匹配分数
        scores: Dict[NewsCategory, int] = defaultdict(int)
        
        for category, keywords in self.keywords.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    scores[category] += 1
        
        # 选择得分最高的分类
        if scores:
            best_category = max(scores.items(), key=lambda x: x[1])[0]
            item.category = best_category
        
        return item
    
    def classify_all(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        对新闻列表进行分类
        
        Args:
            items: 新闻列表
            
        Returns:
            分类后的新闻列表
        """
        classified = [self.classify(item) for item in items]
        
        # 统计分类结果
        stats = defaultdict(int)
        for item in classified:
            stats[item.category.value] += 1
        
        log.info(f"分类完成: {dict(stats)}")
        return classified
    
    def group_by_category(self, items: List[NewsItem]) -> Dict[NewsCategory, List[NewsItem]]:
        """
        按分类分组
        
        Args:
            items: 新闻列表
            
        Returns:
            分类分组字典
        """
        groups: Dict[NewsCategory, List[NewsItem]] = defaultdict(list)
        
        for item in items:
            groups[item.category].append(item)
        
        return dict(groups)
