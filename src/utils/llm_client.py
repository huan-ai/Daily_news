"""
Gemini LLM客户端模块

通过运行一个本地代理服务来调用Gemini API
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any
import httpx

from .logger import log


class GeminiClient:
    """
    Gemini API客户端
    
    通过本地代理服务调用Gemini进行内容分析
    """
    
    def __init__(self, model: str = "gemini-2.0-flash", timeout: int = 120):
        """
        初始化Gemini客户端
        
        Args:
            model: 模型名称
            timeout: 请求超时时间(秒)
        """
        self.model = model
        self.timeout = timeout
        self._prompts_cache: Dict[str, str] = {}
    
    def _load_prompt(self, prompt_name: str) -> str:
        """
        加载提示词模板
        
        Args:
            prompt_name: 提示词名称
            
        Returns:
            提示词内容
        """
        if prompt_name in self._prompts_cache:
            return self._prompts_cache[prompt_name]
        
        prompt_path = Path(f"config/prompts/{prompt_name}.txt")
        if not prompt_path.exists():
            raise FileNotFoundError(f"提示词模板不存在: {prompt_path}")
        
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        self._prompts_cache[prompt_name] = content
        return content
    
    async def generate(self, prompt: str) -> str:
        """
        调用Gemini生成内容
        
        注意：这个方法需要在有Gemini API访问权限的环境中运行
        实际使用时，可以通过以下方式之一：
        1. 使用google-generativeai SDK
        2. 通过Antigravity提供的API代理
        
        Args:
            prompt: 提示词
            
        Returns:
            生成的内容
        """
        try:
            import google.generativeai as genai
            
            # 配置API（需要设置GEMINI_API_KEY环境变量）
            import os
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
            
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)
            
            return response.text
            
        except ImportError:
            log.warning("google-generativeai未安装，使用模拟响应")
            return self._mock_response(prompt)
        except Exception as e:
            log.error(f"Gemini API调用失败: {e}")
            raise
    
    def _mock_response(self, prompt: str) -> str:
        """
        模拟响应（用于测试）
        
        Args:
            prompt: 提示词
            
        Returns:
            模拟的响应
        """
        return f"[模拟响应] 收到提示词，长度: {len(prompt)} 字符"
    
    async def summarize(self, content: str) -> str:
        """
        生成内容摘要
        
        Args:
            content: 原始内容
            
        Returns:
            摘要
        """
        prompt_template = self._load_prompt("summary")
        prompt = prompt_template.format(content=content)
        return await self.generate(prompt)
    
    async def analyze(self, news_items: str) -> str:
        """
        深度分析新闻
        
        Args:
            news_items: 新闻列表
            
        Returns:
            分析结果
        """
        prompt_template = self._load_prompt("analysis")
        prompt = prompt_template.format(news_items=news_items)
        return await self.generate(prompt)
    
    async def generate_report(self, date: str, news_summary: str, analysis: str) -> str:
        """
        生成日报报告
        
        Args:
            date: 日期
            news_summary: 新闻摘要
            analysis: 深度分析
            
        Returns:
            完整报告
        """
        prompt_template = self._load_prompt("report")
        prompt = prompt_template.format(
            date=date,
            news_summary=news_summary,
            analysis=analysis
        )
        return await self.generate(prompt)


# 同步版本的包装器
class GeminiClientSync:
    """
    同步版本的Gemini客户端
    """
    
    def __init__(self, model: str = "gemini-2.0-flash", timeout: int = 120):
        self._async_client = GeminiClient(model=model, timeout=timeout)
    
    def generate(self, prompt: str) -> str:
        """同步生成内容"""
        import asyncio
        return asyncio.run(self._async_client.generate(prompt))
    
    def summarize(self, content: str) -> str:
        """同步生成摘要"""
        import asyncio
        return asyncio.run(self._async_client.summarize(content))
    
    def analyze(self, news_items: str) -> str:
        """同步分析"""
        import asyncio
        return asyncio.run(self._async_client.analyze(news_items))
    
    def generate_report(self, date: str, news_summary: str, analysis: str) -> str:
        """同步生成报告"""
        import asyncio
        return asyncio.run(self._async_client.generate_report(date, news_summary, analysis))
