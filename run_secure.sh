#!/bin/bash
# run_secure.sh — 安全启动脚本
# 从 macOS Keychain 读取敏感密钥，注入环境变量后运行日报系统
# LaunchAgent 调用此脚本，plist 中不含任何明文密钥

# 切换到项目目录
cd /Users/huan/Documents/CMIT/code/daily_news

# 从 Keychain 读取密钥
GEMINI_API_KEY=$(security find-generic-password -a "daily_news_ai" -s "GEMINI_API_KEY" -w 2>/dev/null)
EMAIL_USERNAME=$(security find-generic-password -a "daily_news_ai" -s "EMAIL_USERNAME" -w 2>/dev/null)
EMAIL_PASSWORD=$(security find-generic-password -a "daily_news_ai" -s "EMAIL_PASSWORD" -w 2>/dev/null)

# 检查密钥是否成功读取
if [ -z "$GEMINI_API_KEY" ]; then
    echo "[ERROR] 无法从 Keychain 读取 GEMINI_API_KEY" >&2
    exit 1
fi
if [ -z "$EMAIL_USERNAME" ] || [ -z "$EMAIL_PASSWORD" ]; then
    echo "[ERROR] 无法从 Keychain 读取邮件配置" >&2
    exit 1
fi

# 导出环境变量（不写入任何文件）
export GEMINI_API_KEY
export EMAIL_USERNAME
export EMAIL_PASSWORD

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 密钥已从 Keychain 加载，开始运行日报系统..."

# 执行 Python 脚本
exec /opt/anaconda3/bin/python3.12 /Users/huan/Documents/CMIT/code/daily_news/run.py --run-now
