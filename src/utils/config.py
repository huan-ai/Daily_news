"""
配置管理模块
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 全局配置缓存
_config: Optional[Dict[str, Any]] = None
_sources: Optional[Dict[str, Any]] = None


def _resolve_env_vars(value: Any) -> Any:
    """
    递归解析配置中的环境变量
    支持 ${VAR_NAME} 格式
    """
    if isinstance(value, str):
        if value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.getenv(env_var, "")
        return value
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """
    加载主配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置字典
    """
    global _config
    
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(path, "r", encoding="utf-8") as f:
        _config = yaml.safe_load(f)
    
    # 解析环境变量
    _config = _resolve_env_vars(_config)
    
    return _config


def load_sources(sources_path: str = "config/sources.yaml") -> Dict[str, Any]:
    """
    加载数据源配置文件
    
    Args:
        sources_path: 数据源配置文件路径
        
    Returns:
        数据源配置字典
    """
    global _sources
    
    path = Path(sources_path)
    if not path.exists():
        raise FileNotFoundError(f"数据源配置文件不存在: {sources_path}")
    
    with open(path, "r", encoding="utf-8") as f:
        _sources = yaml.safe_load(f)
    
    return _sources


def get_config() -> Dict[str, Any]:
    """
    获取已加载的配置
    
    Returns:
        配置字典
    """
    global _config
    if _config is None:
        load_config()
    return _config


def get_sources() -> Dict[str, Any]:
    """
    获取已加载的数据源配置
    
    Returns:
        数据源配置字典
    """
    global _sources
    if _sources is None:
        load_sources()
    return _sources


def get_prompt(prompt_name: str) -> str:
    """
    加载提示词模板
    
    Args:
        prompt_name: 提示词名称 (summary, analysis, report)
        
    Returns:
        提示词内容
    """
    prompt_path = Path(f"config/prompts/{prompt_name}.txt")
    if not prompt_path.exists():
        raise FileNotFoundError(f"提示词模板不存在: {prompt_path}")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()
