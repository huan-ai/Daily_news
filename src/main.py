"""
AI行业日报自动生成系统 - 主模块

整合所有模块，实现完整的新闻收集、分析和报告生成流程
"""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from .collectors import GitHubCollector, RSSCollector, WebCollector, NewsItem
from .processors import Deduplicator, Classifier, NewsAnalyzer
from .generators import ReportGenerator
from .scheduler import NewsScheduler
from .utils import setup_logger, load_config, get_config, GeminiClient, EmailSender
from .utils.config import load_sources, get_sources


class DailyNewsEngine:
    """
    AI日报生成引擎
    
    整合数据收集、处理分析和报告生成的完整流程
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初始化引擎
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        self.config = load_config(config_path)
        self.sources = load_sources("config/sources.yaml")
        
        # 初始化日志
        log_config = self.config.get("logging", {})
        setup_logger(
            log_file=log_config.get("file", "logs/daily_news.log"),
            level=log_config.get("level", "INFO")
        )
        
        from .utils.logger import log
        self.log = log
        
        # 初始化组件
        self._init_collectors()
        self._init_processors()
        self._init_generator()
        self._init_email_sender()
        
    def _init_collectors(self):
        """初始化数据收集器"""
        # GitHub收集器
        github_config = self.sources.get("github", {})
        self.github_collector = GitHubCollector({
            "topics": github_config.get("trending", {}).get("topics", []),
            "repositories": github_config.get("repositories", []),
            "since": github_config.get("trending", {}).get("since", "daily")
        })
        
        # RSS收集器
        rss_config = self.sources.get("rss_feeds", [])
        self.rss_collector = RSSCollector({
            "feeds": rss_config,
            "timeout": self.config.get("collection", {}).get("timeout", 30)
        })
        
        # 网页收集器
        web_config = self.sources.get("official_sources", {})
        self.web_collector = WebCollector({
            "sources": web_config,
            "timeout": self.config.get("collection", {}).get("timeout", 30),
            "request_interval": self.config.get("collection", {}).get("request_interval", 5)
        })
    
    def _init_processors(self):
        """初始化处理器"""
        # 去重器
        self.deduplicator = Deduplicator(similarity_threshold=0.7)
        
        # 分类器
        category_keywords = self.sources.get("categories", {})
        self.classifier = Classifier(custom_keywords=category_keywords)
        
        # 分析器
        llm_config = self.config.get("llm", {})
        llm_client = GeminiClient(
            model=llm_config.get("model", "gemini-2.0-flash"),
            timeout=120
        )
        self.analyzer = NewsAnalyzer(llm_client=llm_client)
    
    def _init_generator(self):
        """初始化报告生成器"""
        output_config = self.config.get("output", {})
        self.generator = ReportGenerator(
            output_dir=output_config.get("base_dir", "data/reports")
        )
    
    def _init_email_sender(self):
        """初始化邮件发送器"""
        email_config = self.config.get("notifications", {}).get("email", {})
        self.email_enabled = email_config.get("enabled", False)
        if self.email_enabled:
            self.email_sender = EmailSender(email_config)
            self.log.info("邮件通知已启用")
        else:
            self.email_sender = None
    
    async def collect_all(self) -> List[NewsItem]:
        """
        收集所有数据源
        
        Returns:
            收集到的新闻列表
        """
        self.log.info("开始收集数据...")
        all_items = []
        
        # 并行收集多个数据源
        tasks = [
            self.github_collector.collect(),
            self.rss_collector.collect(),
            self.web_collector.collect()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            source_name = ["GitHub", "RSS", "Web"][i]
            if isinstance(result, Exception):
                self.log.error(f"{source_name}收集失败: {result}")
            else:
                self.log.info(f"{source_name}收集到{len(result)}条")
                all_items.extend(result)
        
        self.log.info(f"数据收集完成，共{len(all_items)}条")
        return all_items
    
    async def process(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        处理新闻数据（去重、分类）
        
        Args:
            items: 原始新闻列表
            
        Returns:
            处理后的新闻列表
        """
        self.log.info("开始处理数据...")
        
        # 去重
        items = self.deduplicator.deduplicate(items)
        
        # 分类
        items = self.classifier.classify_all(items)
        
        # 按时间过滤（只保留24小时内的）
        max_age = self.config.get("content_filter", {}).get("max_age_hours", 24)
        items = self.github_collector.filter_by_date(items, max_age_hours=max_age)
        
        self.log.info(f"数据处理完成，剩余{len(items)}条")
        return items
    
    async def analyze_and_generate(
        self,
        items: List[NewsItem],
        date: Optional[datetime] = None
    ) -> str:
        """
        分析新闻并生成报告
        
        Args:
            items: 新闻列表
            date: 日期
            
        Returns:
            报告文件路径
        """
        date = date or datetime.now()
        self.log.info("开始分析和生成报告...")
        
        # 深度分析
        analysis = await self.analyzer.analyze_news(items)
        
        # 生成报告
        report_content = await self.analyzer.generate_report(items, analysis, date)
        
        # 保存报告
        report_path = self.generator.generate(report_content, items, date)
        
        self.log.info(f"报告已生成: {report_path}")
        return report_path
    
    async def run(self) -> str:
        """
        执行完整的日报生成流程
        
        Returns:
            报告文件路径
        """
        self.log.info("="*50)
        self.log.info("AI日报生成任务开始")
        self.log.info("="*50)
        
        start_time = datetime.now()
        
        try:
            # 1. 收集数据
            items = await self.collect_all()
            
            if not items:
                self.log.warning("未收集到任何数据")
                return ""
            
            # 2. 处理数据
            items = await self.process(items)
            
            # 3. 分析并生成报告
            report_path = await self.analyze_and_generate(items)
            
            # 4. 发送邮件通知
            if self.email_enabled and self.email_sender and report_path:
                self.log.info("正在发送邮件通知...")
                self.email_sender.send_report(report_path)
            
            duration = (datetime.now() - start_time).total_seconds()
            self.log.info(f"任务完成，总耗时: {duration:.2f}秒")
            self.log.info("="*50)
            
            return report_path
            
        except Exception as e:
            self.log.error(f"任务执行失败: {e}")
            raise


async def main():
    """
    主函数
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="AI行业日报自动生成系统")
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="立即执行一次（不启动调度器）"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="启动调度器，每日定时执行"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="配置文件路径"
    )
    
    args = parser.parse_args()
    
    # 创建引擎
    engine = DailyNewsEngine(config_path=args.config)
    
    if args.run_now:
        # 立即执行
        report_path = await engine.run()
        print(f"\n报告已生成: {report_path}")
        
    elif args.schedule:
        # 启动调度器
        scheduler_config = engine.config.get("scheduler", {})
        scheduler = NewsScheduler(
            run_time=scheduler_config.get("run_time", "20:00"),
            timezone=scheduler_config.get("timezone", "Asia/Shanghai")
        )
        scheduler.set_job(engine.run)
        scheduler.start()
        
        print(f"调度器已启动")
        print(f"下次执行时间: {scheduler.get_next_run_time()}")
        print("按 Ctrl+C 停止...")
        
        try:
            # 保持运行
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            scheduler.stop()
            print("\n调度器已停止")
    else:
        # 默认立即执行一次
        report_path = await engine.run()
        print(f"\n报告已生成: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
