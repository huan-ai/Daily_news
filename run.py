#!/opt/anaconda3/bin/python3.12
"""
AI行业日报自动生成系统 - 启动脚本

使用方法:
    # 立即执行一次
    python run.py --run-now
    
    # 启动定时调度（每日20:00执行）
    python run.py --schedule
    
    # 使用自定义配置
    python run.py --run-now --config config/custom.yaml
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 切换工作目录到项目根目录
os.chdir(project_root)

import asyncio
from src.main import main


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已退出")
        sys.exit(0)
    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)
