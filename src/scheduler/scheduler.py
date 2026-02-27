"""
定时调度模块

使用APScheduler实现每日定时任务
"""

import asyncio
from datetime import datetime
from typing import Optional, Callable, Awaitable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..utils.logger import log


class NewsScheduler:
    """
    新闻收集调度器
    
    实现每日定时执行新闻收集和报告生成
    """
    
    def __init__(
        self,
        run_time: str = "20:00",
        timezone: str = "Asia/Shanghai"
    ):
        """
        初始化调度器
        
        Args:
            run_time: 运行时间 (HH:MM格式)
            timezone: 时区
        """
        self.run_time = run_time
        self.timezone = timezone
        self.scheduler = AsyncIOScheduler(timezone=timezone)
        self._job_func: Optional[Callable[[], Awaitable[None]]] = None
    
    def set_job(self, func: Callable[[], Awaitable[None]]):
        """
        设置要执行的任务函数
        
        Args:
            func: 异步任务函数
        """
        self._job_func = func
    
    def start(self):
        """
        启动调度器
        """
        if not self._job_func:
            raise ValueError("请先使用 set_job() 设置任务函数")
        
        # 解析运行时间
        hour, minute = map(int, self.run_time.split(":"))
        
        # 添加定时任务
        self.scheduler.add_job(
            self._run_job,
            trigger=CronTrigger(hour=hour, minute=minute),
            id="daily_news_job",
            name="每日AI新闻收集",
            replace_existing=True
        )
        
        # 启动调度器
        self.scheduler.start()
        log.info(f"调度器已启动，每日 {self.run_time} ({self.timezone}) 执行")
    
    async def _run_job(self):
        """
        执行任务
        """
        log.info("开始执行定时任务...")
        start_time = datetime.now()
        
        try:
            await self._job_func()
            
            duration = (datetime.now() - start_time).total_seconds()
            log.info(f"定时任务执行完成，耗时: {duration:.2f}秒")
            
        except Exception as e:
            log.error(f"定时任务执行失败: {e}")
            raise
    
    async def run_now(self):
        """
        立即执行一次任务（手动触发）
        """
        if not self._job_func:
            raise ValueError("请先使用 set_job() 设置任务函数")
        
        log.info("手动触发任务执行...")
        await self._run_job()
    
    def stop(self):
        """
        停止调度器
        """
        if self.scheduler.running:
            self.scheduler.shutdown()
            log.info("调度器已停止")
    
    def get_next_run_time(self) -> Optional[datetime]:
        """
        获取下次运行时间
        
        Returns:
            下次运行时间
        """
        job = self.scheduler.get_job("daily_news_job")
        if job:
            return job.next_run_time
        return None
    
    def is_running(self) -> bool:
        """
        检查调度器是否运行中
        
        Returns:
            是否运行中
        """
        return self.scheduler.running
