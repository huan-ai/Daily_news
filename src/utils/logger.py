"""
日志工具模块
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logger(log_file: str = "logs/daily_news.log", level: str = "INFO"):
    """
    配置日志系统
    
    Args:
        log_file: 日志文件路径
        level: 日志级别
    """
    # 确保日志目录存在
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 移除默认处理器
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # 添加文件输出
    logger.add(
        log_file,
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8"
    )
    
    return logger


# 创建全局logger实例
log = logger
