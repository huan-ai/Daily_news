"""
报告生成器模块

负责将分析结果组装成最终的日报格式
"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import json

from ..collectors.base import NewsItem
from ..utils.logger import log


class ReportGenerator:
    """
    日报报告生成器
    
    将新闻和分析结果组装成Markdown格式的日报
    """
    
    def __init__(self, output_dir: str = "data/reports"):
        """
        初始化报告生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(
        self,
        report_content: str,
        items: List[NewsItem],
        date: Optional[datetime] = None
    ) -> str:
        """
        生成并保存报告
        
        Args:
            report_content: 报告内容（来自LLM）
            items: 原始新闻列表
            date: 日期
            
        Returns:
            保存的文件路径
        """
        date = date or datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        
        # 创建日期目录
        date_dir = self.output_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存Markdown报告
        md_path = date_dir / f"ai_daily_{date_str}.md"
        self._save_markdown(md_path, report_content)
        
        # 保存纯文本版本
        txt_path = date_dir / f"ai_daily_{date_str}.txt"
        self._save_text(txt_path, report_content)
        
        # 保存原始数据（JSON）
        json_path = date_dir / f"raw_data_{date_str}.json"
        self._save_raw_data(json_path, items)
        
        log.info(f"报告已保存到: {date_dir}")
        return str(md_path)
    
    def _save_markdown(self, path: Path, content: str):
        """
        保存Markdown文件
        
        Args:
            path: 文件路径
            content: 内容
        """
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        log.debug(f"Markdown报告已保存: {path}")
    
    def _save_text(self, path: Path, content: str):
        """
        保存纯文本文件（移除Markdown语法）
        
        Args:
            path: 文件路径
            content: 内容
        """
        import re
        
        # 移除Markdown语法
        text = content
        
        # 移除图片和链接
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
        
        # 移除标题符号但保留内容
        text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
        
        # 移除粗体和斜体
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'__(.*?)__', r'\1', text)
        text = re.sub(r'_(.*?)_', r'\1', text)
        
        # 移除代码块
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`(.*?)`', r'\1', text)
        
        # 清理多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.strip())
        log.debug(f"纯文本报告已保存: {path}")
    
    def _save_raw_data(self, path: Path, items: List[NewsItem]):
        """
        保存原始数据（JSON格式）
        
        Args:
            path: 文件路径
            items: 新闻列表
        """
        data = {
            "generated_at": datetime.now().isoformat(),
            "total_items": len(items),
            "items": [item.to_dict() for item in items]
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log.debug(f"原始数据已保存: {path}")
    
    def get_latest_report(self) -> Optional[str]:
        """
        获取最新的报告
        
        Returns:
            报告内容或None
        """
        # 查找最新的日期目录
        dirs = sorted(
            [d for d in self.output_dir.iterdir() if d.is_dir()],
            key=lambda x: x.name,
            reverse=True
        )
        
        if not dirs:
            return None
        
        latest_dir = dirs[0]
        md_files = list(latest_dir.glob("*.md"))
        
        if not md_files:
            return None
        
        with open(md_files[0], "r", encoding="utf-8") as f:
            return f.read()
    
    def list_reports(self, limit: int = 10) -> List[str]:
        """
        列出历史报告
        
        Args:
            limit: 限制数量
            
        Returns:
            报告路径列表
        """
        reports = []
        
        dirs = sorted(
            [d for d in self.output_dir.iterdir() if d.is_dir()],
            key=lambda x: x.name,
            reverse=True
        )
        
        for d in dirs[:limit]:
            md_files = list(d.glob("*.md"))
            if md_files:
                reports.append(str(md_files[0]))
        
        return reports
