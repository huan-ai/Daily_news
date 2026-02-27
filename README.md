# 🤖 AI 行业日报自动生成系统

> 每日自动收集 AI 行业动态，使用 Gemini 生成深度分析报告，并通过邮件推送 —— 全流程无人值守。

## ✨ 功能特性

| 能力 | 说明 |
|------|------|
| 🔍 **多源采集** | GitHub Trending、Hacker News RSS、公众号、官方博客 |
| 🤖 **智能分析** | Gemini 2.5 Flash 深度分析 + 报告生成 |
| 📊 **自动分类** | 大模型进展 · 多模态突破 · 智能体生态 · 开源动态 · 商业应用 |
| 📧 **邮件推送** | SMTP 自动发送日报到指定收件人 |
| ⏰ **定时执行** | macOS LaunchAgent 全自动定时触发 |
| 🔐 **安全架构** | Keychain 存储密钥，零明文泄露 |

## 📐 项目结构

```
daily_news/
├── config/
│   ├── config.yaml            # 主配置（LLM / 调度 / 邮件 / 日志）
│   ├── sources.yaml           # 数据源配置（RSS / GitHub / 公众号）
│   └── prompts/               # LLM 提示词模板
├── src/
│   ├── collectors/            # 数据收集（GitHub、RSS、网页爬取）
│   ├── processors/            # 内容处理与分类
│   ├── generators/            # 报告生成（Markdown / 纯文本）
│   ├── scheduler/             # 定时调度引擎
│   ├── utils/                 # 工具模块（邮件发送、配置加载等）
│   └── main.py                # 主流程引擎
├── data/reports/              # 生成的日报（按日期归档）
├── logs/                      # 运行日志
├── run.py                     # 入口脚本
├── run_secure.sh              # 安全启动脚本（从 Keychain 注入密钥）
├── requirements.txt           # Python 依赖
├── .env.example               # 环境变量模板
└── .gitignore
```

## 🚀 快速开始

### 1. 克隆 & 安装

```bash
git clone https://github.com/<your-username>/daily_news.git
cd daily_news
pip install -r requirements.txt
```

### 2. 配置密钥

**方式 A — 环境变量（开发/测试）**

```bash
cp .env.example .env
# 编辑 .env，填入你的 GEMINI_API_KEY、EMAIL_USERNAME、EMAIL_PASSWORD
```

**方式 B — macOS Keychain（生产推荐）**

```bash
# 存储 Gemini API Key
security add-generic-password -a "daily_news_ai" -s "GEMINI_API_KEY" -w "你的API密钥"

# 存储邮件凭据（163 邮箱示例）
security add-generic-password -a "daily_news_ai" -s "EMAIL_USERNAME" -w "username@163.com"
security add-generic-password -a "daily_news_ai" -s "EMAIL_PASSWORD" -w "你的163邮箱授权码"
```

### 3. 编辑配置

```bash
# 修改 LLM 模型、调度时间、收件人等
vim config/config.yaml

# 修改数据源
vim config/sources.yaml
```

`config.yaml` 关键配置项：

```yaml
llm:
  model: "gemini-2.5-flash"        # Gemini 模型
scheduler:
  run_time: "17:30"                # 每日运行时间
notifications:
  email:
    enabled: true
    smtp_server: "smtp.163.com"    # SMTP 服务器
    recipients:                    # 收件人列表
      - "user@qq.com"
```

### 4. 运行

```bash
# 立即生成一次日报
python run.py --run-now

# 启动定时调度
python run.py --schedule
```

## ⏰ macOS 定时自动化（LaunchAgent）

本系统使用 macOS LaunchAgent 实现真正的全自动运行，无需手动启动。

### 配置步骤

**1. 创建 plist 文件**

```bash
cat > ~/Library/LaunchAgents/com.dailynews.ai.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dailynews.ai</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/path/to/daily_news/run_secure.sh</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/path/to/daily_news</string>

    <!-- 每日 17:30 执行（根据时区调整 UTC） -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>   <!-- UTC 09:30 = 北京时间 17:30 -->
        <key>Minute</key>
        <integer>30</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>/path/to/daily_news/logs/launchd_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/daily_news/logs/launchd_stderr.log</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF
```

> ⚠️ 请将 `/path/to/daily_news` 替换为你的实际项目路径。

**2. 加载定时任务**

```bash
launchctl load ~/Library/LaunchAgents/com.dailynews.ai.plist
```

**3. 管理命令**

```bash
# 手动触发一次
launchctl start com.dailynews.ai

# 查看状态
launchctl list | grep dailynews

# 卸载
launchctl unload ~/Library/LaunchAgents/com.dailynews.ai.plist
```

## 🔐 安全架构

```
┌─────────────────────────────┐
│   LaunchAgent (plist)       │  ← 不含任何密钥
│   → 调用 run_secure.sh      │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│   run_secure.sh             │  ← 从 Keychain 读取密钥
│   → security 命令注入环境变量  │     注入为环境变量（不落盘）
│   → 执行 python run.py       │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│   Python 应用               │  ← 通过 ${ENV_VAR} 读取
│   config.yaml 只含占位符     │     密钥仅存在于内存
└─────────────────────────────┘
```

- **Keychain** 加密存储所有敏感信息（API Key、邮箱凭据）
- **plist** 和代码中不含任何明文密钥
- **`.env`** 文件已加入 `.gitignore`，不会被提交

## 📧 邮件推送

系统生成日报后会自动通过 SMTP 发送到配置的收件人。

- 支持 163 / QQ / Gmail 等 SMTP 服务
- 邮件内容为 Markdown 渲染后的 HTML
- 在 `config.yaml` 的 `notifications.email` 中配置

## 📊 输出示例

每日报告保存在 `data/reports/YYYY-MM-DD/` 目录：

| 文件 | 用途 |
|------|------|
| `ai_daily_YYYY-MM-DD.md` | Markdown 格式（适合公众号/小红书） |
| `ai_daily_YYYY-MM-DD.txt` | 纯文本格式 |
| `raw_data_YYYY-MM-DD.json` | 原始采集数据备份 |

报告内容包含：
- **今日亮点**：5 个 GitHub 热门 AI 项目（含 Star 数与链接）
- **深度分析**：AI 行业动态分类汇总
- **新闻详情**：按分类展开的全部新闻
- **分析评论**：Gemini 生成的行业洞察

## 🛠️ 开发指南

### 测试单个模块

```bash
python -m src.collectors.github_collector
python -m src.collectors.rss_collector
```

### 调试模式

在 `config/config.yaml` 中设置：

```yaml
logging:
  level: "DEBUG"
```

### 添加新数据源

编辑 `config/sources.yaml`：

```yaml
rss_feeds:
  - name: "新的RSS源"
    url: "https://example.com/feed.xml"
    enabled: true
```

### 自定义提示词

编辑 `config/prompts/` 下的 Jinja2 模板文件。

## 📋 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.12 |
| LLM | Google Gemini 2.5 Flash |
| HTTP | httpx / aiohttp (异步) |
| 网页解析 | BeautifulSoup4 + lxml |
| RSS | feedparser |
| 调度 | APScheduler / macOS LaunchAgent |
| 模板 | Jinja2 |
| 日志 | Loguru |
| 配置 | PyYAML + python-dotenv |

## ⚠️ 注意事项

- 首次运行需配置 Gemini API 访问权限
- 网页爬取请遵守 robots.txt 和网站使用条款
- 默认请求间隔 5 秒，请勿过于频繁
- 生成的报告仅供参考，发布前请人工审核
- LaunchAgent 的 `Hour` 使用 UTC 时间，注意时区换算

## 📄 License

MIT
